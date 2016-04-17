# ex: ts=4 sts=4 sw=4 et

import argparse
import contextlib
import grp
import os
import pwd
import re
import socket
import sys

from tornado import ioloop, web, httpserver, netutil, log

from . import views, api


class TCPEndpoint(object):

    def __init__(self, interface, port):
        self._interface = interface
        self._port = port

    def __enter__(self):
        self._sockets = netutil.bind_sockets(self._port, self._interface, socket.AF_INET)
        return self._sockets

    def __exit__(self, exc_type, exc_value, traceback):
        for skt in self._sockets:
            skt.close()


class UNIXEndpoint(object):

    def __init__(self, path):
        self._path = path
        self._user = 'www-data'
        self._group = 'www-data'

    def __enter__(self):
        uid = pwd.getpwnam(self._user).pw_uid
        gid = grp.getgrnam(self._group).gr_gid
        self._socket = netutil.bind_unix_socket(self._path)
        os.chown(self._path, uid, gid)
        return [self._socket]

    def __exit__(self, exc_type, exc_value, traceback):
        self._socket.close()
        os.remove(self._path)


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


@contextlib.contextmanager
def create_sockets(endpoint_list):
    with contextlib.ExitStack() as stack:
        sockets = (stack.enter_context(_) for _ in endpoint_list)
        sockets = [skt for list_ in sockets for skt in list_]
        yield sockets


def parse_args(args):
    parser = argparse.ArgumentParser('ovpnkey')

    parser.add_argument('-l', '--listen', type=str, action='append')
    parser.add_argument('-h', '--openvpn-host', required=True, type=str)
    parser.add_argument('-p', '--openvpn-port', nargs='?', type=int, default=1194)
    parser.add_argument('-e', '--easy-rsa-path', required=True, type=str)

    args = parser.parse_args(args)
    safe_args = {}
    safe_args['listen'] = [verify_listen_string(_) for _ in args.listen]
    safe_args['openvpn_host'] = args.openvpn_host
    safe_args['openvpn_port'] = args.openvpn_port
    safe_args['easy_rsa_path'] = args.easy_rsa_path

    return safe_args


def verify_listen_string(listen):
    # port only
    if verify_port(listen):
        return TCPEndpoint('0.0.0.0', int(listen))
    # ipv4:port
    m = listen.split(':', 1)
    if len(m) == 2 and verify_ipv4(m[0]) and verify_port(m[1]):
        return TCPEndpoint(m[0], int(m[1]))
    # path of unix socket
    return UNIXEndpoint(listen)


def verify_ipv4(ipv4):
    m = re.match(r'^(0|([1-9][0-9]{0,2}))\.(0|([1-9][0-9]{0,2}))\.(0|([1-9][0-9]{0,2}))\.(0|([1-9][0-9]{0,2}))$', ipv4)
    if m:
        m = m.groups()
        m = [m[_] for _ in range(0, len(m), 2)]
        m = [0 <= int(_) < 256 for _ in m]
        m = all(m)
        if m:
            return True
    return False


def verify_port(port):
    m = re.match(r'^[1-9]\d{0,4}$', port)
    if m:
        m = int(port)
        if 1 <= m < 65536:
            return True
    return False


def main(args=None):
    if args is None:
        args = sys.argv

    args = parse_args(args[1:])

    log.enable_pretty_logging()
    main_loop = ioloop.IOLoop.instance()

    application = web.Application([
        (r'/', views.IndexHandler),
        (r'/key', api.OpenVPNHandler),
    ], openvpn_host=args['openvpn_host'], openvpn_port=args['openvpn_port'], easy_rsa_path=args['easy_rsa_path'])
    server = httpserver.HTTPServer(application)
    with create_sockets(args['listen']) as sockets:
        server.add_sockets(sockets)
        main_loop.start()

    return 0
