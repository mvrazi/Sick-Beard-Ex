# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of Sick Beard.
#
# Sick Beard is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Sick Beard is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Sick Beard.  If not, see <http://www.gnu.org/licenses/>.
from datetime import datetime
import json

import urllib
import urllib2
import base64

import sickbeard

from sickbeard import logger
from sickbeard import common
from sickbeard.exceptions import ex
from sickbeard.encodingKludge import fixStupidEncodings

try:
    import xml.etree.cElementTree as etree
except ImportError:
    import xml.etree.ElementTree as etree


class PLEXNotifier:
    client_update_time = 5 * 60  # 5 minutes

    def __init__(self):
        self.clients = {}
        self.clients_updated = None

    def _split_client_list(self, s):
        return [x.strip().lower() for x in s.split(',')]

    def _get_clients(self, host, clients):
        clients = list(clients)
        found = {}

        logger.log('_get_clients host: %s' % host)

        try:
            client_request = urllib2.urlopen('http://%s:32400/clients' % host)
            client_result = etree.fromstring(client_request.read())
        except urllib2.HTTPError, err:
            logger.log(str(err), logger.ERROR)
            return None

        for server in client_result.findall('Server'):
            if server.get('name').lower() in clients:
                clients.remove(server.get('name').lower())
                protocol = server.get('protocol', 'xbmchttp')

                if protocol in ['xbmcjson', 'xbmchttp']:
                    found[server.get('name')] = {
                        'name': server.get('name'),
                        'address': server.get('address'),
                        'port': server.get('port'),
                        'protocol': protocol
                    }

        if len(clients) > 0:
            logger.log('unable to find some plex clients: %s' % ', '.join(clients), logger.WARNING)

        logger.log('found hosts: %s' % ', '.join(found.keys()))

        return found

    def _update_clients(self, host, client_names, force=False):
        if host is None:
            logger.log('Plex media server host required', logger.WARNING)
            return

        since_update = ((datetime.now() - self.clients_updated).total_seconds())\
            if self.clients_updated is not None else None

        if force or self.clients_updated is None or since_update > self.client_update_time:
            self.clients = self._get_clients(host, self._split_client_list(client_names))
            self.clients_updated = datetime.now()

    def _send_http(self, command, client):
        url = 'http://%s:%s/xbmcCmds/xbmcHttp/?%s' % (
            client['address'],
            client['port'],
            urllib.urlencode(command)
        )

        headers = {}

        try:
            r = urllib2.Request(url, headers=headers)
            urllib2.urlopen(r)
        except Exception, err:
            logger.log("Couldn't sent command to Plex: %s" % err, logger.ERROR)
            return False

        return True

    def _notify_http(self, message='', title="Sick Beard", clients=None):
        total = 0
        successful = 0

        data = {
            'command': 'ExecBuiltIn',
            'parameter': 'Notification(%s, %s)' % (title, message)
        }

        for name, client in clients.items():
            if client['protocol'] == 'xbmchttp':
                total += 1
                if self._send_http(data, client):
                    successful += 1

        return successful == total

    def _send_json(self, method, params, client):
        url = 'http://%s:%s/jsonrpc' % (
            client['address'],
            client['port']
        )

        headers = {
            'Content-Type': 'application/json'
        }

        request = {
            'id':1,
            'jsonrpc': '2.0',
            'method': method,
            'params': params
        }

        try:
            r = urllib2.Request(url, json.dumps(request), headers)
            urllib2.urlopen(r)
        except Exception, err:
            logger.log("Couldn't sent command to Plex: %s" % err, logger.ERROR)
            return False

        return True

    def _notify_json(self, message='', title="Sick Beard", clients=None):
        total = 0
        successful = 0

        params = {
            'title': title,
            'message': message
        }

        for name, client in clients.items():
            if client['protocol'] == 'xbmcjson':
                total += 1
                if self._send_json('GUI.ShowNotification', params, client):
                    successful += 1

        return successful == total

    def _notify(self, message, title, clients=None, force=False):
        if clients is None:
            clients = self.clients

        http_result = self._notify_http(message, title, clients)
        json_result = self._notify_json(message, title, clients)

        return http_result and json_result

    def _notify_pmc(self, message, title="Sick Beard", host=None, client_names=None, force=False):
        """Internal wrapper for the notify_snatch and notify_download functions

        Args:
            message: Message body of the notice to send
            title: Title of the notice to send
            host: Plex Media Server
            client_name: Plex client names
            force: Used for the Test method to override config saftey checks

        Returns:
            Returns a list results in the format of host:ip:result
            The result will either be 'OK' or False, this is used to be parsed by the calling function.

        """

        if host is None:
            host = sickbeard.PLEX_SERVER_HOST

        if client_names is None:
            client_names = sickbeard.PLEX_CLIENT_NAMES

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not sickbeard.USE_PLEX and not force:
            logger.log("Notification for Plex not enabled, skipping this notification", logger.DEBUG)
            return False

        self._update_clients(host, client_names, force=force)
        self._notify(message, title)

##############################################################################
# Public functions
##############################################################################

    def notify_snatch(self, ep_name):
        if sickbeard.PLEX_NOTIFY_ONSNATCH:
            self._notify_pmc(ep_name, common.notifyStrings[common.NOTIFY_SNATCH])

    def notify_download(self, ep_name):
        if sickbeard.PLEX_NOTIFY_ONDOWNLOAD:
            self._notify_pmc(ep_name, common.notifyStrings[common.NOTIFY_DOWNLOAD])

    def test_notify(self, host, client_name):
        clients = self._get_clients(host, [client_name.lower()])

        if clients is None or len(clients) != 1:
            return False

        return self._notify("Testing Plex notifications from Sick Beard", "Test Notification", clients, force=True)

    def update_library(self):
        """Handles updating the Plex Media Server host via HTTP API

        Plex Media Server currently only supports updating the whole video library and not a specific path.

        Returns:
            Returns True or False

        """

        if sickbeard.USE_PLEX and sickbeard.PLEX_UPDATE_LIBRARY:
            if not sickbeard.PLEX_SERVER_HOST:
                logger.log(u"No Plex Server host specified, check your settings", logger.DEBUG)
                return False

            logger.log(u"Updating library for the Plex Media Server host: " + sickbeard.PLEX_SERVER_HOST, logger.MESSAGE)

            url = "http://%s:32400/library/sections" % sickbeard.PLEX_SERVER_HOST
            try:
                xml_sections = etree.fromstring(urllib.urlopen(url).read())
            except IOError, e:
                logger.log(u"Error while trying to contact Plex Media Server: " + ex(e), logger.ERROR)
                return False

            sections = xml_sections.findall('Directory')
            if not sections:
                logger.log(u"Plex Media Server not running on: " + sickbeard.PLEX_SERVER_HOST, logger.MESSAGE)
                return False

            for s in sections:
                if s.get('type') == "show":
                    url = "http://%s:32400/library/sections/%s/refresh" % (sickbeard.PLEX_SERVER_HOST, s.get('key'))
                    try:
                        urllib.urlopen(url)
                    except Exception, e:
                        logger.log(u"Error updating library section for Plex Media Server: " + ex(e), logger.ERROR)
                        return False

            return True

notifier = PLEXNotifier
