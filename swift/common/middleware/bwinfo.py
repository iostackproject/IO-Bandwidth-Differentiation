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

import os, stat, subprocess, shlex, re, sys, time, psutil
import threading
from swift import gettext_ as _
from swift.common.utils import cache_from_env, get_logger, register_swift_info
from swift.common.swob import Request, Response


def threaded_function(event, name, BWstats):
    _waittime = 1
    stats = dict()
    devices = psutil.disk_partitions(all=False)
    for d in devices:
        stats[d.device[:-1]] = _getDiskStats(d.device[:-1])

    while True:
        if event.wait(_waittime):
            break
        BWdisk = dict()
        for i in stats:
            read, write = _getDiskStats(i)
            oldread, oldwrite = stats[i]
            stats[i] = (read,write)
            BWdisk[i] = ((read-oldread)/_waittime, (write-oldwrite)/_waittime)
        BWstats[name] = BWdisk
        

def _getDiskStats (disk):
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
    Stores the BW info at /bwinfo
    """

    def __init__(self, app, conf, logger=None):
        self.app = app
        self.conf = conf
        self.disable_path = conf.get('disable_path', '')
        self.logger = logger or get_logger(conf, log_route='bwlimit')
        self.event = threading.Event()
        self.BWstats = dict()
        self.th = threading.Thread(target = threaded_function, name = conf.get('__file__', ''), 
                                    args = (self.event, conf.get('__file__', ''), self.BWstats,))
        self.th.start()
        time.sleep(0.1)

    def __del__(self):
        try:
            self.event.set()
            self.th.join()
        except RuntimeError as err:
            pass


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
        BWList = self.BWstats[self.conf.get('__file__', '')]
        timing = ""
        try:
            for element in BWList:
                read,write = BWList[element]
                if osdev[:-1] == element:
                    timing = str(float(read)+float(write))
        except Exception as err:
            pass
        return Response(request=req, body=timing, content_type="text/plain")

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
