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

import os

from swift.common.utils import cache_from_env, get_logger, register_swift_info
from swift.common.swob import Request, Response


class OSInfoMiddleware(object):
    """
    playground
    """

    def __init__(self, app, conf, logger=None):
        self.app = app
        self.conf = conf
        self.disable_path = conf.get('disable_path', '')
        self.logger = logger or get_logger(conf, log_route='osinfo')

    def GET(self, req):
        """Returns a 200 response with "OK" in the body."""

        """
            Here we have to present the actual MB/S of the OS.
            We can monitor here, but it will be updated per request

            The other alternative is to ask the OS.
            2. piggyback inside the response in an additional header

        """
        body = ""
        body = "Information from OS ...."
        return Response(request=req, body=body, content_type="text/plain")

    def DISABLED(self, req):
        """Returns a 503 response with "DISABLED BY FILE" in the body."""
        return Response(request=req, status=503, body="DISABLED BY FILE",
                        content_type="text/plain")

    def __call__(self, env, start_response):
        req = Request(env)
        response = self.app(env,,start_response)
        return response


def filter_factory(global_conf, **local_conf):
    conf = global_conf.copy()
    conf.update(local_conf)

    def osnfo_filter(app):
        return OSInfoMiddleware(app, conf)
    return osinfo_filter
