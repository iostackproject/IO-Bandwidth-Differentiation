# Copyright (c) 2010-2012 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, stat, subprocess, shlex, re, sys, time, psutil, pika
import threading, requests
from swift import gettext_ as _
from swift.common.utils import cache_from_env, get_logger, register_swift_info, json
from swift.common.swob import Request, Response

class LCircular(list):
    def append(self, item):
        _maxlen = 300 #5 min * 60 sec
        list.insert(self, 0, item)
        if len(self) > _maxlen: self[_maxlen:] = []

def diskstats_threaded(event, name, enabled, channel, interval, queue, BWstats):
    _waittime = 1 #1sec
    _sendtime = int(interval)
    stats = dict()
    arr = dict()
    arrjson = dict()
    devices = psutil.disk_partitions(all=False)
    for d in devices:
        arr[d.device[:-1]] = LCircular()
        stats[d.device[:-1]] = _getDiskStats(d.device[:-1])
    s = 0
    while True:
        if s>0:
            for i in arr:
                disks = dict()
                disks['insta'] = arr[i][0]
                disks['max-1min'] = max(arr[i][0:60])
                disks['max-2min'] = max(arr[i][0:120])
                disks['max-5min'] = max(arr[i])
                disks['min-1min'] = min(arr[i][0:60])
                disks['min-2min'] = min(arr[i][0:120])
                disks['min-5min'] = min(arr[i])
                disks['mean-1min'] = sum(arr[i][0:60])/60
                disks['mean-2min'] = sum(arr[i][0:120])/120
                disks['mean-5min'] = sum(arr[i])/300
                arrjson[name + i] = disks
                if enabled and s == _sendtime:
                    channel.basic_publish(exchange='', properties=pika.BasicProperties(
                                    content_type='application/json'),routing_key=queue, body=json.dumps(arrjson))
                    s = 0
        if event.wait(_waittime):
            break
        BWdisk = dict()
        s+=1
        for i in stats:
            read, write = _getDiskStats(i)
            oldread, oldwrite = stats[i]
            stats[i] = (read,write)
            arr[i].append((read-oldread)/_waittime + (write-oldwrite)/_waittime)
        BWstats[name] = arrjson

def bwinfo_threaded(event, name, channel, interval, queue, osip, osport):
    while True:
        if event.wait(int(interval)):
            break
        address = "http://" + osip + ":" + osport + "/osinfo/"
        r = requests.get(address)
        channel.basic_publish(exchange='', routing_key=queue, body=r.content)

def _getDiskStats(disk):
    """
    Aggregates all the partitions of the same disk 

    It should be better to put it out of the IOStackThreadPool

    :param disk: "sdc"
    :returns: read and write bytes of the disk.

    """
    stats = psutil.disk_io_counters(perdisk=True)
    read = 0.0;
    write = 0.0;
    if disk.startswith('/dev/'):
        disk = disk[5:]
    for i in stats:
        if disk in i[:-1]:
            read += stats[i].read_bytes/(1024.0*1024.0)
            write += stats[i].write_bytes/(1024.0*1024.0)
    return (read,write)




class BWInfoMiddleware(object):
    """
    Stores the BW info at /bwinfo middleware
    """

    def __init__(self, app, conf, logger=None):
        self.app = app
        self.conf = conf
        self.disable_path = conf.get('disable_path', '')
        self.logger = logger or get_logger(conf, log_route='bwlimit')
        self.event = threading.Event()
        self.BWstats = dict()
        try:
            self._monitoring_enabled = self.str2bool(self.conf.get('enabled'))
        except Exception:
            self._monitoring_enabled = False
            
        if self._monitoring_enabled:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.conf.get('monitoring_ip')))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.conf.get('queue_osinfo'))
            self.channel.queue_declare(queue=self.conf.get('queue_osstats'))

            self.thbw = threading.Thread(target = bwinfo_threaded, name = conf.get('__file__', ''), 
                                        args = (self.event, conf.get('__file__', ''), self.channel, 
                                            self.conf.get('interval_osinfo'), self.conf.get('queue_osinfo'), self.conf.get('bind_ip'),
                                            self.conf.get('bind_port'),))
            self.thbw.start()
            time.sleep(0.1)
            self.thstats = threading.Thread(target = diskstats_threaded, name = conf.get('__file__', ''), 
                                        args = (self.event, self.conf.get('bind_ip') + ":" + self.conf.get('bind_port'), self._monitoring_enabled,
                                            self.channel, self.conf.get('interval_osstats'), self.conf.get('queue_osstats'), self.BWstats,))
            self.thstats.start()
            time.sleep(0.1)

        else:

            self.thstats = threading.Thread(target = diskstats_threaded, name = conf.get('__file__', ''), 
                                            args = (self.event, self.conf.get('bind_ip') + ":" + self.conf.get('bind_port'), self._monitoring_enabled,
                                                None, self.conf.get('interval_osstats'), None, self.BWstats,))
            self.thstats.start()
            time.sleep(0.1)
        

    def __del__(self):
        try:
            self.event.set()
            if self._monitoring_enabled:
                self.thbw.join()
                self.connection.close()
            self.thstats.join()
            
        except RuntimeError as err:
            pass

    def str2bool(self, v):
      return v.lower() in ("yes", "true", "t", "1")

    def get_mount_point(self, path):
        dev = os.stat(path).st_dev
        major = os.major(dev)
        minor = os.minor(dev)
        out = subprocess.Popen(shlex.split("df /"), stdout=subprocess.PIPE).communicate()
        m=re.search(r'(/[^\s]+)\s',str(out))
        if m:
            mp= m.group(1)
            return mp 
        else:
            return -1   

    def GET(self, req):
        """Returns a 200 response with "OK" in the body."""

        """
            Here we have to present the actual MB/S of the OS.
            We can monitor here, but it will be updated per request

            The other alternative is to ask the OS.
            2. piggyback inside the response in an additional header

        """

        osdev = self.get_mount_point(self.conf.get('devices'))
        Bwstatsos = self.BWstats[self.conf.get('bind_ip') + ":" + self.conf.get('bind_port')]
        return Response(request=req, body=json.dumps(Bwstatsos), content_type="application/json")

    def DISABLED(self, req):
        """Returns a 503 response with "DISABLED BY FILE" in the body."""
        return Response(request=req, status=503, body="DISABLED BY FILE",
                        content_type="text/plain")

    def __call__(self, env, start_response):
        req = Request(env)
        try:
            if req.path == '/bwinfo/':
                handler = self.GET
                if self.disable_path and os.path.exists(self.disable_path):
                    handler = self.DISABLED
                return handler(req)(env, start_response)
        except UnicodeError:
            # definitely, this is not /bwinfo
            pass
        return self.app (env,start_response)


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def bwinfo_filter(app):
        return BWInfoMiddleware(app, conf)
    return bwinfo_filter
