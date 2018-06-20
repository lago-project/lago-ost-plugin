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
import errno
import logging
import os
import threading
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import ThreadingTCPServer
import sys
import traceback

LOGGER = logging.getLogger(__name__)


class LagoThreadingTCPServer(ThreadingTCPServer):
    """ A custom multi-threaded TCP server.

    We use `allow_reuse_address` in order to avoid a race when opening and
    closing multiple servers (at each point in time only one server is
    listening).
    For example, the first server has a connection in 'time_wait' state,
    while the second server tries to bind its socket.

    Attributes:
        _allowed_exceptions(tuple of Exceptions): If an exception occurs
            and its type isn't not in `_allowed_exceptions`, its traceback
            will be printed to the log.
        _allowed_errnos(tuple of ints): If an OSError exception occurs
            and its errno isn't not in `_allowed_errnos`, its traceback
            will be printed to the log.
    """
    allow_reuse_address = True

    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        allowed_exceptions=(),
        allowed_errnos=(errno.EPIPE, ),
    ):
        # We can't use super since the superclass isn't  a new style class
        ThreadingTCPServer.__init__(self, server_address, RequestHandlerClass)
        self._allowed_exceptions = allowed_exceptions
        self._allowed_errnos = allowed_errnos

    def handle_error(self, request, client_address):
        """ Handle an error gracefully

        Overrides the default implementation which prints
        the error to stdout and stderr
        """
        _, value, _ = sys.exc_info()
        ignore_err_conditions = [
            hasattr(value, 'errno') and value.errno in self._allowed_errnos,
            isinstance(value, self._allowed_exceptions),
        ]

        if any(ignore_err_conditions):
            return

        LOGGER.debug(traceback.format_exc())


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
        _len_cwd = len(os.getcwd())

        def translate_path(self, path):
            return os.path.join(
                self.__root_dir,
                SimpleHTTPRequestHandler.translate_path(
                    self, path
                )[self._len_cwd:].lstrip('/')
            )

        def log_message(self, *args, **kwargs):
            pass

    return _BetterHTTPRequestHandler


def _create_http_server(listen_ip, listen_port, root_dir):
    """
    Starts an http server with an improved request handler

    Args:
        listen_ip (str): Ip to listen on
        port (int): Port to register on
        root_dir (str): path to the directory to serve

    Returns:
        BaseHTTPServer: instance of the http server, already running on a
            thread
    """
    server = LagoThreadingTCPServer(
        (listen_ip, listen_port),
        generate_request_handler(root_dir),
    )
    threading.Thread(target=server.serve_forever).start()
    return server


@contextlib.contextmanager
def repo_server_context(gw_ip, port, root_dir):
    """
    Context manager that starts a generic http server that serves `root_dir`,
    and listens on `gw_ip`:`port`.

    Args:
        gw_ip(str): IP to listen on
        port(int): Port to listen on
        root_dir(str): The root directory that will be served.
    """

    server = _create_http_server(
        listen_ip=gw_ip,
        listen_port=port,
        root_dir=root_dir,
    )
    try:
        yield
    finally:
        server.shutdown()
