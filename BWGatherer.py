import psutil
import time



def _getDiskIOQueue (disk):
    """
    reads /proc/diskstats ioqueue column

    :param disk: "sdc"
    :returns: ioqueue value

    """
    for line in (open("/proc/diskstats",'r').xreadlines()):
        values = line.split ()
        if values[2] == disk:
            return int(values[11])
    return 0
    

def _getDiskStats (disk):
    """
    Aggregates all the partitions of the same disk 

    It should be better to put it out of the IOStackThreadPool

    :param disk: "sdc"
    :returns: read and write bytes of the disk.

    """
    stats = psutil.disk_io_counters(perdisk=True)
    read = 0;
    write = 0;
    for i in stats:
        if disk in i[:-1]:
            read += stats[i].read_bytes/(1024.0*1024.0)
            write += stats[i].write_bytes/(1024.0*1024.0)
    return (read,write)

def _getCPUIOWait ():
    """
    Returns IOWait , 
    :returns: IOWait absolute value.

    """
    stats = psutil.cpu_times().iowait
    return stats       


stats = dict()

stats['sda'] = _getDiskStats("sda")
stats['sdb'] = _getDiskStats("sdb")
stats['sdc'] = _getDiskStats("sdc")

while (1):
    f = open('/tmp/bwfile', 'w')
    for i in stats:
        read, write = _getDiskStats(i)
        oldread, oldwrite = stats[i]
        stats[i] = (read,write)
        string = "{0[i]:s} {0[read]:f} {0[write]:f}#".format({'i':i,'read':read-oldread,'write':write-oldwrite})
        f.write(string)
    f.close()
    time.sleep (1)


