from __future__ import unicode_literals


# Generate these for your app at https://dev.twitter.com/apps/new
TWITTER = {
    'AUTH': {
        'consumer_key': 'rym1JOQ7Z8s6uRLAMDBQQ',
        'consumer_secret': 'NRtIvPoW9c5rJQAnEpJ3WIUWGZGxGZlcUP0eeCbX5s',
        'token': '584021415-rw1qpbslAtP7gDM6M8V0FaYnozDdlnH5XQakQetZ',
        'token_secret': '7kUDLx4VcXecqZsfVGmbTcqd7kd5fSNNyJFxvrlszGg',
    },
}


# We're pulling data from graphite to calculate the uptime. Each service has a
# list of counters that it uses to help calculate the % of successful / failed
# requests.
UPTIME = {
    'root_uri': 'http://graphite.balancedpayments.com/render/?',
    'username': 'USERNAME',
    'password': 'PASSWORD',
    'services': {
        'DASH': {
            'OK_TARGETS': [
                'stats_counts.status.dashboard.2xx',
                'stats_counts.status.dashboard.3xx',
                'stats_counts.status.dashboard.4xx',
            ],
            'ERROR_TARGETS': [
                'stats_counts.status.dashboard.5xx',
                'stats_counts.status.dashboard.timeout',
            ]
        },
        'JS': {
            'OK_TARGETS': [
                'stats_counts.status.balanced-js.2xx',
                'stats_counts.status.balanced-js.3xx',
                'stats_counts.status.balanced-js.4xx',
            ],
            'ERROR_TARGETS': [
                'stats_counts.status.balanced-js.5xx',
                'stats_counts.status.balanced-js.timeout',
            ]
        },
        'API': {
            'OK_TARGETS': [
                'stats_counts.status.balanced-api.2xx',
                'stats_counts.status.balanced-api.3xx',
                'stats_counts.status.balanced-api.4xx',
            ],
            'ERROR_TARGETS': [
                'stats_counts.status.balanced-api.5xx',
                'stats_counts.status.balanced-api.timeout',
            ]
        },
    }
}

LIBRATO_UPTIME = {
    'root_uri': 'https://metrics-api.librato.com/v1/metrics/',
    'username': 'vendors@balancedpayments.com',
    'password': '14d624cde57cfba7cfa76baf0284d94c33de7f289db5ee4172f20c117234afff',
    'services': {
        'API': {
            'SOURCE': '*bapi-live*',
            'OK_TARGETS': [
                'AWS.ELB.HTTPCode_Backend_2XX',
                'AWS.ELB.HTTPCode_Backend_3XX',
                'AWS.ELB.HTTPCode_Backend_4XX',
            ],
            'ERROR_TARGETS': [
                'AWS.ELB.HTTPCode_Backend_5XX',
                # TODO: where is our timeout in aws cloudwatch?
                #'stats_counts.status.balanced-api.timeout',
            ]
        },
    }
}

# We're using a basic username and password to keep the boogie man out
HTTP_AUTH = ('username', 'password')


DEBUG = True
