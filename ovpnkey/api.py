# ex: ts=4 sts=4 sw=4 et

import datetime
import os
import tempfile
import zipfile

from tornado import web, process

from . import utils


EASY_RSA_ROOT = '/etc/openvpn/easy-rsa/2.0'
OPENVPN_HOST = 'wcpan.me'
OPENVPN_PORT = 1194


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

        with open(os.devnull, 'w') as null:
            p = process.Subprocess(['./gk.sh', EASY_RSA_ROOT, email, name], stdout=null, stderr=null)
            exit_code = await p.wait_for_exit()

        if exit_code != 0:
            self.set_status(400)
            return

        prefix = name
        with tempfile.TemporaryFile() as fout:
            with zipfile.ZipFile(fout, 'w') as zout:
                with open('./client.conf', 'r') as tpl:
                    zout.writestr('{0}/client.conf'.format(prefix), tpl.read().format(host=OPENVPN_HOST, port=OPENVPN_PORT, name=name))
                zout.write('{0}/keys/ca.crt'.format(EASY_RSA_ROOT), '{0}/ca.crt'.format(prefix))
                zout.write('{0}/keys/{1}.crt'.format(EASY_RSA_ROOT, name), '{0}/{1}.crt'.format(prefix, name))
                zout.write('{0}/keys/{1}.key'.format(EASY_RSA_ROOT, name), '{0}/{1}.key'.format(prefix, name))
            fout.seek(0, 0)

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', 'attachment; filename="{0}.zip"'.format(name))
            self.write(fout.read())
            await self.flush()
