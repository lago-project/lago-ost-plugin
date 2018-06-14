#
# Copyright 2014-2017 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#
import contextlib
import functools
import os
import threading
import pkg_resources
import sys
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import ThreadingTCPServer

from . import constants


def generate_request_handler(root_dir):
    """
    Factory for _BetterHTTPRequestHandler classes

    Args:
        root_dir (path): Path to the dir to serve

    Returns:
        _BetterHTTPRequestHandler: A ready to be used improved http request
            handler
    """

    class _BetterHTTPRequestHandler(SimpleHTTPRequestHandler):
        __root_dir = root_dir

        def translate_path(self, path):
            return os.path.join(
                self.__root_dir,
                SimpleHTTPRequestHandler.translate_path(
                    self, path
                )[len(os.getcwd()):].lstrip('/')
            )

        def log_message(self, *args, **kwargs):
            pass

    return _BetterHTTPRequestHandler


class LagoThreadingTCPServer(ThreadingTCPServer):
    """
    A custom multi-threaded TCP server.
    """
    allow_reuse_address = True


def _create_http_server(listen_ip, listen_port, root_dir):
    """
    Starts an http server with an improved request handler

    Args:
        listen_ip (str): Ip to listen on
        port (int): Port to register on
        root_dir (str): path to the directory to serve

    Returns:
        LagoThreadingTCPServer: instance of the http server, already running
            on a thread.
    """
    server = LagoThreadingTCPServer(
        (listen_ip, listen_port),
        generate_request_handler(root_dir),
    )
    threading.Thread(target=server.serve_forever).start()
    return server


@contextlib.contextmanager
def repo_server_context(prefix):
    """
    Context manager that starts an http server that serves the given prefix's
    yum repository. Will listen on :class:`constants.REPO_SERVER_PORT` and on
    the first network defined in the previx virt config

    Args:
        prefix(ovirtlago.prefix.OvirtPrefix): prefix to start the server for

    Returns:
        None
    """
    gw_ip = prefix.virt_env.get_net().gw()
    port = constants.REPO_SERVER_PORT
    server = _create_http_server(
        listen_ip=gw_ip,
        listen_port=port,
        root_dir=prefix.paths.internal_repo(),
    )
    try:
        yield
    finally:
        server.shutdown()


def get_data_file(basename):
    """
    Load a data as a string from the data directory

    Args:
        basename(str): filename

    Returns:
        str: string representation of the file
    """
    return pkg_resources.resource_string(
        __name__, '/'.join(['data', basename])
    )


def available_sdks(modules=None):
    modules = modules or sys.modules
    res = []
    if 'ovirtsdk' in modules:
        res.append('3')
    if 'ovirtsdk4' in modules:
        res.append('4')
    return res


def require_sdk(version, modules=None):
    modules = modules or sys.modules

    def wrap(func):
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            sdks = available_sdks(modules)
            if version not in sdks:
                raise RuntimeError(
                    (
                        '{0} requires oVirt Python SDK v{1}, '
                        'available SDKs: {2}'
                    ).format(func.__name__, version, ','.join(sdks))
                )
            else:
                return func(*args, **kwargs)

        return wrapped_func

    return wrap


def partial(func, *args, **kwargs):
    partial_func = functools.partial(func, *args, **kwargs)
    functools.update_wrapper(partial_func, func)
    return partial_func
