# BW Differentiation tests

Modifications to ThreadPool to assess a BW per object.

* IOStackThreadPool automatically creates a worker per data stream. 
* Using the eventlet model, all the reads go to a different thread.
* Using ioprio is not possible due to that problem, so we tried 
  different alternatives to use directly read system call. However,
  read from libc is monkey_patched and is moved to another thread
  automatically.
* We created an external (C) augmentedRead accepting a priority value,
  working as expected. We still have thread switching not being able to 
  fix it, but at least the priority value can be setup accordingly.
* As we are now setting up, priority values we can avoid the interference 
  controls.



* We tried HTTP proxy alternatives but they do not work as expected, as the stream
  is provided directly by the object servers, so we may need to go lower level.

* We also tried middleware coding, but we are only using it to monitor and get information
about the object server used instant BW (using some external utility)


# Compilation of external code
 * gcc -c -fPIC iostackmodule.c -o iostackmodule.o 
 * gcc -shared -Wl,-soname,libiostackmodule.so -o libiostackmodule.so iostackmodule.o
 * cp to a suitable location (i.e., /usr/lib/libiostackmodule.so)

# BWGatherer.py
  Creates a /tmp/bwfile with disk BW information each second, the file will be used
  to provide BW statistics to the proxy so it can select an object server


We still have the device and the "needed BW" information hard coded.
Finally, we will need some extra testing to see if 
the extra priority information is working as intended. 

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
