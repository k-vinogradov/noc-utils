import json
import urllib
import urllib2

ROUTERS = {'MessagingRouter': 'messaging',
           'EventsRouter': 'evconsole',
           'ProcessRouter': 'process',
           'ServiceRouter': 'service',
           'DeviceRouter': 'device',
           'NetworkRouter': 'network',
           'TemplateRouter': 'template',
           'DetailNavRouter': 'detailnav',
           'ReportRouter': 'report',
           'MibRouter': 'mib',
           'ZenPackRouter': 'zenpack'}

PRODUCTION_STATES = {
    'production': 1000,
    'pre-Production': 500,
    'test': 400,
    'maintenance': 300,
    'decommissioned': -1, }


def debug_msg(msg, move_to_start=False, cr=True):
    """
    Print text message to the stdout
    :param msg: text message
    :type msg: str
    :param move_to_start: move cursor to the beginning of the line
    :type move_to_start: bool
    :param cr: add CR to the end of the line
    :type cr: bool
    :return: None
    """
    from sys import stdout
    stdout.write('{start}{msg}{trail}'.format(
        start='\r' if move_to_start else '',
        msg=msg,
        trail='\n' if cr else ''))


class ZenossExceptin(Exception):
    """
    Custom exception
    """

    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        return 'ZenossAPI: {0}'.format(self._msg)

    def __repr__(self):
        return self.__str__()


class ZenossAPI:
    """
    Zenoss JSON API representation
    """

    def __init__(self, host, username, password, port='8080', debug=False, limit=200):
        self._url_opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        self._zenoss_instance = 'http://{host}:{port}'.format(host=host, port=port)

        login_params = urllib.urlencode(dict(
            __ac_name=username,
            __ac_password=password,
            submitted='true',
            came_from=self._zenoss_instance + '/zport/dmd'))
        self._debug = debug
        if self._debug:
            debug_msg('Zenoss JSON API client to the host {0} initialization...'.format(host))
            debug_msg('Authentication with the username and the password...')
        self._url_opener.open(self._zenoss_instance + '/zport/acl_users/cookieAuthHelper/login', login_params)
        self._req_counter = 1
        self._limit = limit

    def _router_request(self, router, method, data=None):
        """
        Internal method to make calls to the Zenoss request router
        :param router: Zenoss API router
        :type router: str
        :param method: Zenoss API method
        :type method: str
        :param data: additional data for the json-request
        :type data: list
        :return: JSON deserialized response
        :rtype: dict
        """
        import sys
        if router not in ROUTERS:
            raise Exception('Router {0} isn\'t availible')
        if not data:
            data = []
        req = urllib2.Request('{0}/zport/dmd/{1}_router'.format(self._zenoss_instance, ROUTERS[router]))
        req.add_header('Content-type', 'application/json; charset=utf-8')
        req_data = json.dumps([dict(action=router, method=method, data=data, type='rpc', tid=self._req_counter)])
        self._req_counter += 1
        try:
            return json.loads(self._url_opener.open(req, req_data).read())
        except:
            raise ZenossExceptin(sys.exc_info()[1] if sys.exc_info()[1] else sys.exc_info()[0])

    def get_devices(self, organizer='/Devices', params=None):
        """
        Get device descriptions
        :param organizer: Zenoss infrastructure organizer's name
        :type organizer: str
        :param params: Pairs of filters. Can be one of the following: name, ipAddress, deviceClass, productionState
        :type params: dict
        :return:
        """
        router = 'DeviceRouter'
        method = 'getDevices'
        path = '/zport/dmd' + organizer

        if not params:
            params = {}

        if 'productionState' in params:
            production_states = []
            for state in params['productionState']:
                if type(state) is int:
                    production_states.append(state)
                elif state.lower() in PRODUCTION_STATES:
                    production_states.append(PRODUCTION_STATES[state.lower()])
                else:
                    raise ZenossExceptin('Production state \'{0}\' is unknown.'.format(state))
            params['productionState'] = production_states

        if self._debug:
            debug_msg('Call the detDevices method through router DeviceRouter:\n'
                      '  - organizer: {0}\n'
                      '  - records per query limit: {1}'.format(organizer, self._limit))
            for key in params:
                debug_msg('  - {0}: {1}'.format(key, ', '.join(map(str, params[key]))))
            debug_msg('Download device descriptions ... '.format(method, router), cr=False)

        devices = []
        total_count = len(devices) + 1
        devices_hash = None
        start = 0

        counter = 1

        while len(devices) < total_count:
            try:
                resp = self._router_request(
                    router,
                    method,
                    data=[dict(uid=path, start=start, limit=self._limit, params=params)])['result']
            except Exception as e:
                if self._debug:
                    debug_msg('Download device descriptions ... FAILED!', move_to_start=True)
                    debug_msg(
                        'Received {0} device description(s) using {1} request(s).'.format(len(devices), counter - 1))
                raise e

            if resp['success']:
                total_count = resp['totalCount']
                devices_hash = resp['hash']
                devices += resp['devices']

                if self._debug:
                    if total_count:
                        percents = round(len(devices) * 100 / total_count)
                    else:
                        percents = 100.0
                    debug_msg('Download device descriptions ... {0}%'.format(percents), cr=False, move_to_start=True)
                start = len(devices)
                counter += 1
            else:
                if self._debug:
                    debug_msg('Download device descriptions ... FAILED!', move_to_start=True)
                    debug_msg(
                        'Received {0} device description(s) using {1} request(s).'.format(len(devices), counter - 1))
                    debug_msg('Request #{0} was finished with the error \'{1}\'.'.format(counter, resp['msg']))
                raise ZenossExceptin(resp['msg'])
        if self._debug:
            debug_msg('')
            debug_msg('GetDevices executing finished.\n'
                      'Received {0} device description(s) using {1} request(s).'.format(len(devices), counter - 1))
        return dict(total_count=total_count, devices=devices, hash=devices_hash)
