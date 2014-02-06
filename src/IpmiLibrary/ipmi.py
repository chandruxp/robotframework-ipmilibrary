#
# Kontron IpmiLibrary
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

import functools
import picmg

def create_connection(interface):
    session = Session()
    session.interface = interface
    ipmi = Ipmi()
    ipmi.interface = interface
    ipmi.session = session
    return ipmi

class Target:
    """The Target class represents an IPMI target.
    """
    class Routing:
        def __init__(self, address, bridge_channel):
            self.address = address
            self.bridge_channel = bridge_channel

    def __init__(self, target_address):
        self.target_address = target_address

    def set_routing_information(self, rinfo):
        """Set the path over which a target is reachable.

        The path is given as a list of tuples in the form (address,
        bridge_channel).
        """

        self.routing = [ self.Routing(*r) for r in rinfo ]

class Session:
    AUTH_TYPE_NONE        = 0x00
    AUTH_TYPE_MD2         = 0x01
    AUTH_TYPE_MD5         = 0x02
    AUTH_TYPE_PASSWORD    = 0x04
    AUTH_TYPE_OEM         = 0x05

    def __init__(self):
        self.auth_type = self.AUTH_TYPE_NONE
        self.established = False

    def _get_interface(self):
        try:
            return self._interface
        except AttributeError:
            raise RuntimeError('No interface has been set')

    def _set_interface(self, interface):
        self._interface = interface

    def set_session_type_rmcp(self, host):
        self._rmcp_host = host

    def set_auth_type_user(self, username, password):
        self._requested_auth_type = self.AUTH_TYPE_PASSWORD
        self._auth_username = username
        self._auth_password = password

    def establish(self):
        if hasattr(self.interface, 'establish_session'):
            self.interface.establish_session(self)

    def close(self):
        if hasattr(self.interface, 'close_session'):
            self.interface.close_session(self)

    interface = property(_get_interface, _set_interface)

class Ipmi:
    COMMAND_CLS = [ picmg.Commands ]

    def __init__(self):
        self._cmd_objs = [ cls() for cls in self.COMMAND_CLS ]

    def __getattr__(self, name):
        # map in ipmi commands
        for o in self._cmd_objs:
            if hasattr(o, name):
                return self._cmd_wrapper(getattr(o, name))
        raise AttributeError()

    def _cmd_wrapper(self, callable):
        return functools.partial(callable, self._send_and_receive)

    def _send_and_receive(self, req):
        rsp = self.interface.send_and_receive(self.target, req)
        return rsp

    def _get_interface(self):
        try:
            return self._interface
        except AttributeError:
            raise RuntimeError('No interface has been set')

    def _get_session(self):
        try:
            return self._session
        except AttributeError:
            raise RuntimeError('No IPMI session has been set')

    def _get_target(self):
        try:
            return self._target
        except AttributeError:
            raise RuntimeError('No IPMI target has been set')

    def _set_interface(self, interface):
        self._interface = interface

    def _set_session(self, session):
        self._session = session

    def _set_target(self, target):
        self._target = target

    target = property(_get_target, _set_target)
    interface = property(_get_interface, _set_interface)
    session = property(_get_session, _set_session)


