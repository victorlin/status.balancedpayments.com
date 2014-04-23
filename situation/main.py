#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import base64
from collections import defaultdict
from datetime import datetime, timedelta
import functools
import logging
import os
import time

import webapp2
from google.appengine.api import memcache
from google.appengine.ext.webapp import template

import encoding
import settings
import tweeter
import uptime
import librato_uptime


LOGGER = logging.getLogger(__name__)


def cache(method, seconds=60 * 60 * 24):
    """ A basic caching wrapper that will generate a key based off of the URL
    of the request """
    def wrapped(handler, *a, **kw):
        key = (handler.request.path.replace('/', '') +
               handler.request.query_string)
        data = memcache.get(key)
        if not data:
            LOGGER.info('CACHE miss')
            data = method(handler, *a, **kw)
            if not memcache.add(key=key, value=data, time=seconds):
                LOGGER.error('Failed to set cache ' + key)
        return data
    return wrapped


def require_basic_auth(method):
    """ Authenticates using HTTP Basic Authorization.  """
    @functools.wraps(method)
    def http_basic_auth(self, *args):
        def fail_basic_auth():
            self.error(401)
            self.response.headers['WWW-Authenticate'] = (
                'Basic realm="status.balancedpayments.com"')

        basic_auth = self.request.headers.get('Authorization')
        if not basic_auth:
            LOGGER.debug("Request does not carry auth.")
            return fail_basic_auth()
        try:
            user_info = base64.decodestring(basic_auth[6:])
            username, password = user_info.split(':')
        except Exception as ex:
            LOGGER.exception(ex)
            return fail_basic_auth()
        else:
            if (username, password) != settings.HTTP_AUTH:
                return fail_basic_auth()
        self.auth = (username, password)
        return method(self, *args)
    return http_basic_auth


class TwitterBaseController(webapp2.RedirectHandler):
    def __init__(self, *a, **kw):
        super(TwitterBaseController, self).__init__(*a, **kw)
        self.tweet_manager = tweeter.TwitterStatusProcessor(
            **settings.TWITTER['AUTH']
        )


class TwitterHandler(TwitterBaseController):

    def get(self, service=None, **_):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(self._get(service))

    @cache
    def _get(self, service):
        tweets = []
        services = [service] if service else tweeter.SERVICES
        for service in services:
            tweets += self.tweet_manager.get(service)
        return encoding.to_json({
            'messages': [encoding.to_dict(m) for m in tweets]
        })

    @require_basic_auth
    def post(self):
        self.tweet_manager.run()
        keys = [
            self.request.path.replace('/', ''),
            'twittermessages',
            'twittermessageslatest',
        ]
        memcache.delete_multi(keys)

        self.get()


class TwitterMessageHandler(TwitterBaseController):

    def get(self, *a, **kw):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(self._get())

    @cache
    def _get(self):
        offset = int(self.request.get('offset', 0))
        max_date = datetime.utcnow() - timedelta(days=offset)
        min_date = max_date - timedelta(days=30)
        messages = defaultdict(list)   # messages by service
        messages['min'] = time.mktime(min_date.timetuple())
        messages['max'] = time.mktime(max_date.timetuple())

        for service in tweeter.SERVICES:
            tweets = self.tweet_manager.get_by_dates(
                service,
                max_date=max_date,
                min_date=min_date,
            )
            tweets = [t for t in tweets]
            messages[service] = [encoding.to_dict(m)
                                 for m in reversed(tweets)]

        return encoding.to_json({
            'messages': messages,
        })


class TwitterLatestMessageHandler(TwitterBaseController):
    """
    Mounted at /twitter/messages/latest
    GET returns a dictionary of messages by service
    {
        'DASH': message1,
        'API': message1,
        'JS': message1,
    }
    """

    def get(self, *a, **kw):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(self._get())

    @cache
    def _get(self):
        messages = {}   # messages by date + service

        for service in tweeter.SERVICES:
            tweet = self.tweet_manager.get_last_message(service)
            if tweet:
                if tweet.created_at < datetime.utcnow() - timedelta(days=1):
                    tweet = None
            messages[service] = encoding.to_dict(
                tweet,
            ) if tweet else None

        return encoding.to_json({
            'messages': messages,
        })


class UptimeHandler(TwitterBaseController):
    """
    Mounted at /uptime
    GET returns a dictionary of uptime for the various services
    POST deletes cached results, the subsequent GET will re-populate the cache
    """
    def __init__(self, request, method):
        super(UptimeHandler, self).__init__(request, method)
        self.uptime_managers = [
            uptime.Calculator(**settings.UPTIME),
            librato_uptime.Calculator(**settings.LIBRATO_UPTIME)
        ]

    def get(self, *a, **kw):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(self._get())

    @cache
    def _get(self):
        uptimes = []
        for manager in self.uptime_managers:
            uptimes.extend(manager.refresh())
        raw = {
            'uptime': dict(uptimes)
        }
        for service in tweeter.SERVICES:
            # if a service is UP and a tweet says it's down, then the down
            # takes precedence
            _s = raw['uptime'][service]
            if _s['status'] == 'UP':
                tweet_state = self.tweet_manager.get_latest_state(
                    service
                )
                _s['status'] = tweet_state or _s['status']
        return encoding.to_json(raw)

    @require_basic_auth
    def post(self):
        key = self.request.path.replace('/', '')
        memcache.delete(key)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(self._get())


class MainHandler(webapp2.RequestHandler):
    """
    Serves the index.html, that's it.
    """
    def get(self, *a, **kw):
        path = os.path.join(
            os.path.dirname(__file__),
            'templates',
            'index.html')
        self.response.out.write(template.render(path, {}))


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/uptime', UptimeHandler),
    ('/twitter', TwitterHandler),
    ('/twitter/messages', TwitterMessageHandler),
    ('/twitter/messages/latest', TwitterLatestMessageHandler),
    ('/twitter/(.*)', TwitterHandler),
], debug=settings.DEBUG)
