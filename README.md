# BW Differentiation tests

Modifications to ThreadPool to assess a BW per object.
* Hardcoded -> BW Requirements, disk and object differentiation
* Hardcoded -> 4 threads per object store (we test with 4 streams)
* 1 thread/queue per stream
* Each queue checks if other queues need BW.

* We added controls to avoid interfering processes using the same devices
	* We use disk_read / disk_write and io_wait values.
	* io_wait is used to find if the disk is overloaded or not, so we can 
	  actually ask more bw even if it is shared
	* Those controls are useful in the All-in-One deployment, but they need to be tuned
	* We added another metric (elements in the disk queue), that seems better, but still 
	  disk / setup dependent.
	* TODO: Look for other metrics to find when we can issue more requests to the disk,
	* Disk characterization shouldn't be the best way as different patterns had different 
	  performances
	* TRY: IOWAit seconds per second.

* TODO: Shared queues, a queue may have requests from different tenants, so 
  instead of waiting, we just enqueue and get a new value. If all the tenants
  need waiting setup a small sleep, because we may get other elements in the queue
  that may be served at higher speed. I would prefer dynamic queues as it is more cleaner
  and eventlets can do a good job there.






# Swift

A distributed object storage system designed to scale from a single machine
to thousands of servers. Swift is optimized for multi-tenancy and high
concurrency. Swift is ideal for backups, web and mobile content, and any other
unstructured data that can grow without bound.

Swift provides a simple, REST-based API fully documented at
http://docs.openstack.org/.

Swift was originally developed as the basis for Rackspace's Cloud Files and
was open-sourced in 2010 as part of the OpenStack project. It has since grown
to include contributions from many companies and has spawned a thriving
ecosystem of 3rd party tools. Swift's contributors are listed in the AUTHORS
file.

## Docs

To build documentation install sphinx (`pip install sphinx`), run
`python setup.py build_sphinx`, and then browse to /doc/build/html/index.html.
These docs are auto-generated after every commit and available online at
http://docs.openstack.org/developer/swift/.

## For Developers

The best place to get started is the ["SAIO - Swift All In One"](http://docs.openstack.org/developer/swift/development_saio.html).
This document will walk you through setting up a development cluster of Swift
in a VM. The SAIO environment is ideal for running small-scale tests against
swift and trying out new features and bug fixes.

You can run unit tests with `.unittests` and functional tests with
`.functests`.

If you would like to start contributing, check out these [notes](CONTRIBUTING.md)
to help you get started.

### Code Organization

 * bin/: Executable scripts that are the processes run by the deployer
 * doc/: Documentation
 * etc/: Sample config files
 * swift/: Core code
    * account/: account server
    * common/: code shared by different modules
        * middleware/: "standard", officially-supported middleware
        * ring/: code implementing Swift's ring
    * container/: container server
    * obj/: object server
    * proxy/: proxy server
 * test/: Unit and functional tests

### Data Flow

Swift is a WSGI application and uses eventlet's WSGI server. After the
processes are running, the entry point for new requests is the `Application`
class in `swift/proxy/server.py`. From there, a controller is chosen, and the
request is processed. The proxy may choose to forward the request to a back-
end server. For example, the entry point for requests to the object server is
the `ObjectController` class in `swift/obj/server.py`.


## For Deployers

Deployer docs are also available at
http://docs.openstack.org/developer/swift/. A good starting point is at
http://docs.openstack.org/developer/swift/deployment_guide.html

You can run functional tests against a swift cluster with `.functests`. These
functional tests require `/etc/swift/test.conf` to run. A sample config file
can be found in this source tree in `test/sample.conf`.

## For Client Apps

For client applications, official Python language bindings are provided at
http://github.com/openstack/python-swiftclient.

Complete API documentation at
http://docs.openstack.org/api/openstack-object-storage/1.0/content/

----

For more information come hang out in #openstack-swift on freenode.

Thanks,

The Swift Development Team
