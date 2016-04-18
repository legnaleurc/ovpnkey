# ex: ts=4 sts=4 sw=4 et

import datetime
import os
import tempfile
import zipfile

from tornado import web, process

from . import utils
from .resources import gk_sh, client_ovpn


class OpenVPNHandler(web.RequestHandler):

    async def post(self):
        email = self.get_argument('email', None)
        if not email:
            self.set_status(400)
            return

        timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        name = '{0}_{1}'.format(email, timestamp)
        if not utils.check_name(name):
            self.set_status(400)
            return

        easy_rsa_path = self.settings['easy_rsa_path']
        with open(os.devnull, 'w') as null:
            p = process.Subprocess([gk_sh, easy_rsa_path, email, name], stdout=null, stderr=null)
            exit_code = await p.wait_for_exit()

        if exit_code != 0:
            self.set_status(400)
            return

        data = {
            'host': self.settings['openvpn_host'],
            'port': self.settings['openvpn_port'],
        }
        with open(os.path.join(easy_rsa_path, 'keys/ca.crt'), 'r') as fin:
            data['ca'] = fin.read()
        with open(os.path.join(easy_rsa_path, 'keys/ta.key'), 'r') as fin:
            data['tls_auth'] = fin.read()
        with open(os.path.join(easy_rsa_path, 'keys/{0}.crt'.format(name)), 'r') as fin:
            data['crt'] = fin.read()
        with open(os.path.join(easy_rsa_path, 'keys/{0}.key'.format(name)), 'r') as fin:
            data['key'] = fin.read()
        output = client_ovpn.format(**data)

        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment; filename="{0}.ovpn"'.format(name))
        self.write(output.encode('utf-8'))
        await self.flush()
