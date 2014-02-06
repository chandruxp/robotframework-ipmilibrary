#
# Kontron Ipmitool Interface
#
# author: Heiko Thiery <heiko.thiery@kontron.com>
# author: Michael Walle <michael.walle@kontron.com>
#

from IpmiLibrary.errors import TimeoutError
from IpmiLibrary.ipmi import Session
from IpmiLibrary.logger import log
from subprocess import Popen, PIPE
import re

class Ipmitool:
    """This interface uses the ipmitool raw command to "emulate" a RMCP
    session.
    
    It uses the session information to assemble the correct ipmitool
    parameters. Therefore, a session has to be established before any request
    can be sent.
    """

    NAME = 'ipmitool'
    IPMITOOL_PATH = 'ipmitool'

    def __init__(self):
        self.re_err = re.compile(
                "Unable to send RAW command \(.*rsp=(0x[0-9a-f]+)\)")
        self.re_timeout = re.compile(
                "Unable to send RAW command \(.*cmd=0x[0-9a-f]+\)")

    def establish_session(self, session):
        # just remember session parameters here
        self._session = session

    def send_and_receive(self, target, req):
        """Sends an IPMI request message and waits for its response.

        The request's data is given as a byte array in `req`.

        Returns a tuple (cc, rsp_data), with `cc` being the completion code.
        """

        log().debug('IPMI Request [%s]', ' '.join(['%02x' % d for d in req]))

        lun = req[0] & 0x3
        req[0] = req[0] >> 2
        cmd = ('-l %d raw' % lun)
        for byte in req:
            cmd += ' 0x%02x' % byte
        
        output, rc = self._run_ipmitool(target, cmd)
        match_err = self.re_err.match(output)
        match_timeout = self.re_timeout.match(output)
        if match_err:
            cc = int(match_err.group(1), 16)
            data = None
        elif match_timeout:
            raise TimeoutError()
        else:
            if rc != 0:
                raise RuntimeError('ipmitool failed with rc=%d' % rc)
            cc = 0
            output = output.replace('\n','').replace('\r','').strip()
            if len(output) == 0:
                data = None
            else:
                data = [ int(x,16) for x in output.split(' ') ]

        log().debug('IPMI Response (cc 0x%02x data [%s])', cc,
                data and ' '.join(['%02x' % d for d in data]) or '')
   
        return (cc, data)
 
    def _run_ipmitool(self, target, ipmitool_cmd):
        """Legacy call of ipmitool (will be removed in future).
        """

        if not hasattr(self, '_session'):
            raise RuntimeError('Session needs to be set')

        cmd = self.IPMITOOL_PATH
        cmd += (' -I lan')
        cmd += (' -H %s' % self._session._rmcp_host)

        if hasattr(target, 'routing'):
            # we have to do bridging here
            if len(target.routing) == 1:
                # ipmitool/shelfmanager does implicit bridging
                cmd += (' -b %d' % target.routing[0].bridge_channel)
            elif len(target.routing) == 2:
                cmd += (' -B %d' % target.routing[0].bridge_channel)
                cmd += (' -T 0x%02x' % target.routing[1].address)
                cmd += (' -b %d' % target.routing[1].bridge_channel)
            else:
                raise RuntimeError('The impitool interface at most double '
                       'briding')

        cmd += (' -t 0x%02x' % target.target_address)

        if self._session.auth_type == Session.AUTH_TYPE_NONE:
            cmd += ' -P ""'
        elif self._session_auth_type == Session.AUTH_TYPE_PASSWORD:
            cmd += (' -U "%s"' % self._session._auth_username)
            cmd += (' -P "%s"' % self._session._auth_password)
        else:
            raise RuntimeError('Session type %d not supported' %
                    self._session.auth_type)

        cmd += (' %s' % ipmitool_cmd)
        cmd += (' 2>&1')

        log().debug('Run ipmitool "%s"', cmd)

        child = Popen(cmd, shell=True, stdout=PIPE)
        output = child.communicate()[0]

        log().debug('return with rc=%d, output was:\n%s', child.returncode,
                output)

        return output, child.returncode

