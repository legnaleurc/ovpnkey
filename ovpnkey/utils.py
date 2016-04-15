# ex: ts=4 sts=4 sw=4 et

import contextlib
import grp
import os
import pwd
import re
import sys

from tornado import ioloop, web, httpserver, netutil, log

from . import views, api


def check_name(name):
    m = re.match(r'^[a-zA-Z0-9_@.\-]+$', name)
    return bool(m)


@contextlib.contextmanager
def unix_socket(path, u, g):
    uid = pwd.getpwnam(u).pw_uid
    gid = grp.getgrnam(g).gr_gid
    with netutil.bind_unix_socket(path) as socket:
        os.chown(path, uid, gid)
        try:
            yield socket
        finally:
            os.remove(path)


def main(args=None):
    if args is None:
        args = sys.argv

    log.enable_pretty_logging()
    main_loop = ioloop.IOLoop.instance()

    application = web.Application([
        (r'/', views.IndexHandler),
        (r'/key', api.OpenVPNHandler),
    ])
    server = httpserver.HTTPServer(application)
    with unix_socket('/tmp/ovpnkey.socket', 'www-data', 'www-data') as socket:
        server.add_socket(socket)
        main_loop.start()

    return 0
