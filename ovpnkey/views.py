#! /usr/bin/env python3
# ex: ts=4 sts=4 sw=4 et

from tornado import web

from .resources import index_html


class IndexHandler(web.RequestHandler):

    def get(self):
        self.render(index_html)
