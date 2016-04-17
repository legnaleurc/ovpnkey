# ex: ts=4 sts=4 sw=4 et

import datetime
import os
import tempfile
import zipfile

from tornado import web, process

from . import utils


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
            p = process.Subprocess(['./gk.sh', easy_rsa_path, email, name], stdout=null, stderr=null)
            exit_code = await p.wait_for_exit()

        if exit_code != 0:
            self.set_status(400)
            return

        prefix = name
        with tempfile.TemporaryFile() as fout:
            with zipfile.ZipFile(fout, 'w') as zout:
                with open('./client.conf', 'r') as tpl:
                    openvpn_host = self.settings['openvpn_host']
                    openvpn_port = self.settings['openvpn_port']
                    zout.writestr('{0}/client.conf'.format(prefix), tpl.read().format(host=openvpn_host, port=openvpn_port, name=name))
                zout.write('{0}/keys/ca.crt'.format(easy_rsa_path), '{0}/ca.crt'.format(prefix))
                zout.write('{0}/keys/{1}.crt'.format(easy_rsa_path, name), '{0}/{1}.crt'.format(prefix, name))
                zout.write('{0}/keys/{1}.key'.format(easy_rsa_path, name), '{0}/{1}.key'.format(prefix, name))
            fout.seek(0, 0)

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', 'attachment; filename="{0}.zip"'.format(name))
            self.write(fout.read())
            await self.flush()
