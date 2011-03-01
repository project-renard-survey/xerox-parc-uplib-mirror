#
# This file is part of the "UpLib 1.7.11" release.
# Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
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
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
import os
import re
import socket
import signal
import string
import sys
import time
import traceback
import weakref
import types
import base64
import quopri

from StringIO import StringIO

from bisect import insort

from urllib import unquote, splitquery

# async modules
import asyncore
import asynchat

# we use select to do the SSL handshake (blocking)
import select

# medusa modules
from medusa import http_date
from medusa import producers
from medusa import status_handler
from medusa.logger import unresolving_logger, file_logger
from medusa.counter import counter

# UpLib modules
from uplib.plibUtil import note
UPLIB_MIN_VERSION = "1.7"

# we know we have the right email package, but just in case
import email
versions = email.__version__.split(".")
note(4, "email version numbers are " + str(versions) + "\n")
if (not versions) or (int(versions[0]) < 4):
    raise ValueError("Need email package 4.x or higher for imapServer module")
import email.Utils
import email.Message
import email.Header
import email.Encoders

import time, base64

try:
    import ssl
except ImportError:
    ssl = None

from IMAPServer.abstractclasses import imap_request, mailclient, clientchannel
from IMAPServer.abstractclasses import STATE_NOT_AUTHENTICATED, STATE_AUTHENTICATED, STATE_SELECTED, STATE_LOGOUT


# ===========================================================================
#                                                       self_deleting_file
# ===========================================================================

class self_deleting_file (file):

    def __init__(self, filename, mode=None, bufsize=-1):
        file.__init__(self, filename, mode, bufsize)

    def close(self):
        file.close(self)
        if os.path.exists(self.name):
            os.unlink(self.name)

    def __del__(self):
        if hasattr(file, "__del__"):
            file.__del__(self)
        if os.path.exists(self.name):
            note(3, "self_deleting_file.__del__:  deleting %s", self.name)
            os.unlink(self.name)

# ===========================================================================
#                                                authentication collectors
# ===========================================================================

class AuthenticationHandshakeFinished(asyncore.ExitNow):
    def __init__(self, userobj):
        asyncore.ExitNow.__init__(self, "authentication handshake finished")
        self.auth_user = userobj

class auth_plain_collector:

    # for collecting the client-side authentication PLAIN data

    def __init__ (self, request):
        self.request = request
        self.collected_data = ""
        # note("starting plain auth handshake...")
        self.request.client.channel.set_terminator('\r\n')
        self.request.client.channel.send("+ \r\n")

    def collect_incoming_data (self, data):
        self.collected_data += data
        # note("auth_plain_collector:  data is now %s, after adding %d bytes", repr(self.collected_data), len(data))

    def found_terminator (self):
        # decode base64 encoded values
        v = base64.decodestring(self.collected_data.strip())
        parts = v.strip().split('\x00')
        if len(parts) in (2, 3):
            userobj = self.request.mailcontext.check_login(parts[-2], parts[-1], True)
            # note("userobj is %s", userobj)
        else:
            userobj = None
        self.request.finish_authentication(userobj)
        return True

    def waiting_for_what(self):
        return "\\r\\n terminator"

class auth_anonymous_collector:

    # for collecting the client-side authentication PLAIN data

    def __init__ (self, request):
        self.request = request
        self.collected_data = ""
        self.request.client.channel.send("+ \r\n")
        self.request.client.channel.set_terminator('\r\n')

    def collect_incoming_data (self, data):
        self.collected_data += data
        # note("auth_anonymous_collector:  data is now %s, after adding %d bytes", repr(self.collected_data), len(data))

    def found_terminator (self):
        # decode base64 encoded values
        v = base64.decodestring(self.collected_data.strip())
        # note("auth_anonymous_collector:  v is %s", repr(v))
        self.request.finish_authentication(v)
        return True

    def waiting_for_what(self):
        return "\\r\\n terminator"

# ===========================================================================
#                                                      IDLE loop collector
# ===========================================================================

class idle_collector:

    # for collecting the client-side authentication PLAIN data

    def __init__(self, request, thread, flag):
        self.request = request
        self.collected_data = ""
        self.stopflag = flag
        self.request.client.channel.send("+ \r\n")
        self.request.client.channel.set_terminator('DONE\r\n')
        thread.start()

    def collect_incoming_data (self, data):
        note(3, "%s received from client while in IDLE processing loop", repr(data))

    def found_terminator (self):
        self.stopflag.set()             # turn off idle thread
        self.request.finish()           # send OK
        self.request.client.channel.set_terminator('\r\n')
        return True

    def waiting_for_what(self):
        return "'DONE\\r\\n' IDLE terminator"

# ===========================================================================
#                                                       data collector
# ===========================================================================

class data_collector:

    # for accepting and buffering large messages

    def __init__ (self, length, channel):
        self.collected_data     = ""
        self.length             = length
        self.channel    = channel
        self.old_terminator = self.channel.get_terminator()
        self.channel.set_terminator(None)
        self.bytes_in   = 0
        if length > (1 << 20):
            self.fp = self_deleting_file(tempfile.mktemp(), 'wb+')
        else:
            self.fp = StringIO()

    def collect_incoming_data (self, data):
        ld = len(data)
        bi = self.bytes_in
        # note("collect_incoming_data:  received %d bytes, need %d\n", ld, self.length - bi)
        if (bi + ld) >= self.length:
            # last bit of data
            self.fp.write(data[:(self.length - bi)])
            self.fp.seek(0, 0)
            # set the channel terminator back to the default
            self.channel.set_terminator(self.old_terminator)
            # avoid circular reference
            ch = self.channel
            self.channel = None
            ch.handle_data(self.fp, data[(self.length - bi):])
        else:
            self.fp.write(data)
            self.bytes_in = self.bytes_in + ld

    def found_terminator (self):
        # shouldn't be called
        note("found_terminator called on data_collector!")
        raise Exception()

    def waiting_for_what(self):
        return "%d bytes" % (self.length - self.bytes_in)

# ===========================================================================
#                                                IMAP connection
# ===========================================================================

#                    +----------------------+
#                    |connection established|
#                    +----------------------+
#                               ||
#                               \/
#             +--------------------------------------+
#             |          server greeting             |
#             +--------------------------------------+
#                       || (1)       || (2)        || (3)
#                       \/           ||            ||
#             +-----------------+    ||            ||
#             |Not Authenticated|    ||            ||
#             +-----------------+    ||            ||
#              || (7)   || (4)       ||            ||
#              ||       \/           \/            ||
#              ||     +----------------+           ||
#              ||     | Authenticated  |<=++       ||
#              ||     +----------------+  ||       ||
#              ||       || (7)   || (5)   || (6)   ||
#              ||       ||       \/       ||       ||
#              ||       ||    +--------+  ||       ||
#              ||       ||    |Selected|==++       ||
#              ||       ||    +--------+           ||
#              ||       ||       || (7)            ||
#              \/       \/       \/                \/
#             +--------------------------------------+
#             |               Logout                 |
#             +--------------------------------------+
#                               ||
#                               \/
#                 +-------------------------------+
#                 |both sides close the connection|
#                 +-------------------------------+
#
#          (1) connection without pre-authentication (OK greeting)
#          (2) pre-authenticated connection (PREAUTH greeting)
#          (3) rejected connection (BYE greeting)
#          (4) successful LOGIN or AUTHENTICATE command
#          (5) successful SELECT or EXAMINE command
#          (6) CLOSE command, or failed SELECT or EXAMINE command
#          (7) LOGOUT command, server shutdown, or connection closed


class imap_connection (asynchat.async_chat, clientchannel):

    # use a larger default output buffer
    ac_out_buffer_size = 1<<20

    current_request = None
    channel_counter = counter()

    def __init__ (self, server, conn, addr):
        self.collector = None
        self.outgoing = []
        self.channel_number = imap_connection.channel_counter.increment()
        self.request_counter = counter()
        asynchat.async_chat.__init__ (self, conn)
        self.clientstate = mailclient(self, STATE_NOT_AUTHENTICATED, False, None)
        self.server = server
        self.pending_request = None
        self.addr = addr
        self.in_buffer = ''
        self.creation_time = int (time.time())
        self.check_maintenance()
        self.set_terminator('\r\n')
        self.greet()
        note("*** new imap_connection %s", repr(self))

    def __repr__ (self):
        ar = asynchat.async_chat.__repr__(self)[1:-1]
        return '<%s channel#: %s %srequests:%s>' % (
                ar,
                self.channel_number,
                (self.is_secure() and "(encrypted) ") or "",
                self.request_counter
                )

    def greet(self):
        msg = "* OK [CAPABILITY %s] %s ready.\r\n" % (
            self.server.mailcontext.capabilities(self.clientstate),
            self.server.mailcontext.IDENT)
        # msg = "* OK %s ready.\r\n" % self.server.SERVER_IDENT
        self.push_with_producer (producers.simple_producer(msg))

    def can_tls(self):
        if not ssl:
            return "No SSL support in this server"
        if not self.socket:
            return "No open socket to wrap with SSL"
        if isinstance(self.socket, ssl.SSLSocket) or (self.server.stunnel_pid is not None):
            return "Already in SSL context"
        if not self.server.mailcontext.server_certificate_file():
            return "No server certificate to use with SSL"
        return None

    def starttls (self):
        if not ssl:
            raise RuntimeError("No SSL support in this Python")
        if not self.socket:
            raise RuntimeError("No socket to wrap with SSL")
        if isinstance(self.socket, ssl.SSLSocket):
            raise RuntimeError("Already wrapped with SSL")

        note(3, "Starting TLS handshake...")

        # remove the channel handler from the event loop
        self.del_channel()
        # now wrap with an SSL context
        try:
            wrapped_socket = ssl.wrap_socket(self.socket,
                                             server_side=True,
                                             certfile=self.server.mailcontext.server_certificate_file(),
                                             do_handshake_on_connect=False)
        except ssl.SSLError, err:
            # Apple Mail seems to do one connect just to check the certificate,
            # then it drops the connection
            if err.args[0] == ssl.SSL_ERROR_EOF:
                self.handle_close()
                return
            else:
                raise

        # now do the handshake, blocking till it completes
        timeout = wrapped_socket.gettimeout()
        try:
            if timeout == 0.0:
                wrapped_socket.settimeout(None)
            try:
                wrapped_socket.do_handshake()
            except ssl.SSLError, err:
                # Apple Mail seems to do one connect just to check the certificate,
                # then it drops the connection
                if err.args[0] == ssl.SSL_ERROR_EOF:
                    self.handle_close()
                    return
                else:
                    raise
        finally:
            wrapped_socket.settimeout(timeout)

        # now replace the socket
        self.set_socket(wrapped_socket)
        note(3, "Now using SSLSocket %s for connection", wrapped_socket)

    def start_authentication(self, authtype):
        # note("do_authentication(%s, %s)", repr(self), authtype)
        if authtype == 'plain':
            self.collector = auth_plain_collector(self.current_request)
            return

        elif authtype == 'anonymous':
            self.collector = auth_anonymous_collector(self.current_request)
            return

        else:
            raise ValueError("Can't do authentication type %s" % authtype)
            
    def start_idle(self, idlethread, stopflag):
        self.collector = idle_collector(self.current_request, idlethread, stopflag)
        return

    def is_secure(self):
        return (self.server.stunnel_pid is not None) or (ssl and isinstance(self.socket, ssl.SSLSocket))

    # Channel Counter, Maintenance Interval...
    maintenance_interval = 500

    def check_maintenance (self):
        if not self.channel_number % self.maintenance_interval:
            self.maintenance()

    def maintenance (self):
        self.kill_zombies()

    # 30-minute zombie timeout.  status_handler also knows how to kill zombies.
    zombie_timeout = 30 * 60

    def kill_zombies (self):
        now = int (time.time())
        for channel in asyncore.socket_map.values():
            if channel.__class__ == self.__class__:
                if (now - channel.creation_time) > channel.zombie_timeout:
                    channel.close()

    # --------------------------------------------------
    # send/recv overrides, good place for instrumentation.
    # --------------------------------------------------

    # this information needs to get into the request object,
    # so that it may log correctly.
    def send (self, data):
        if len(data) > 3000:
            note(3, "c%d:  sending %d bytes:  %s", self.channel_number,
                 len(data), repr(data[:100] + "..."))
            pass
        else:
            note(3, "c%d:  sending %d bytes:  %s", self.channel_number,
                 len(data), repr(data))
        result = asynchat.async_chat.send (self, data)
        self.server.bytes_out.increment (len(data))
        return result

    def recv (self, buffer_size):
        try:
            result = asynchat.async_chat.recv (self, buffer_size)
            self.server.bytes_in.increment (len(result))
            if len(result) < 1:
                note(3, "c%d: EOF", self.channel_number)
            else:
                note(3, "c%d:  receiving %d bytes:  %s", self.channel_number,
                     len(result), repr(result[:min(100,len(result))]))
            return result
        except MemoryError:
            # --- Save a Trip to Your Service Provider ---
            # It's possible for a process to eat up all the memory of
            # the machine, and put it in an extremely wedged state,
            # where medusa keeps running and can't be shut down.  This
            # is where MemoryError tends to get thrown, though of
            # course it could get thrown elsewhere.
            sys.exit ("Out of Memory!")

    def handle_error (self):
        t, v = sys.exc_info()[:2]
        if t is SystemExit:
            raise t, v
        else:
            asynchat.async_chat.handle_error (self)

    def log_info (self, msg, state='info'):
        self.server.log_info(msg, state)

    # --------------------------------------------------
    # async_chat methods
    # --------------------------------------------------

    def push (self, thing):
        if type(thing) == type(''):
            self.outgoing.append(producers.simple_producer (thing))
        elif type(thing) == types.UnicodeType:
            # note("Unicode push:  <%s>", thing)
            self.outgoing.append(producers.simple_producer (thing.encode('latin-1', 'replace')))
        else:
            self.outgoing.append(thing)

    def done (self):
        "finalize this transaction - send output to the http channel"

        outgoing_producer = producers.composite_producer (self.outgoing)

        # apply a few final transformations to the output
        self.push_with_producer (
            # globbing gives us large packets
            producers.globbing_producer ( producers.composite_producer(self.outgoing), 1 << 20)
            )

        self.current_request = None

    def collect_incoming_data (self, data):
        # note("--- collect_incoming_data(%s) with %s == waiting for %s",
        #     repr(self.collector), repr(data), self.collector and self.collector.waiting_for_what())
        if self.collector:
            # we are receiving data (probably POST data) for a request
            self.collector.collect_incoming_data (data)
        else:
            # we are receiving header (request) data
            self.in_buffer = self.in_buffer + data

    def parse_request (self, rline):

        # note("IMAP request:  %s", rline.strip())
        m = re.match(r"(?P<tag>[^\s]+)\s+(?P<command>[^\s]+)(\s+(?P<args>.*))?$", rline, re.MULTILINE | re.DOTALL)
        if m:
            r = imap_request(m.group('tag'), m.group('command'), self.clientstate, self.server.mailcontext)
            count, litcount = r.parse_args(m.group('args'))
            # note("count is %s, litcount is %s", count, litcount)
            self.current_request = r
            if count > 0:
                self.collector = data_collector(count, self)
                if not litcount:
                    self.push_with_producer (producers.simple_producer('+ Ready for more data\r\n'))
            return r
        else:
            return imap_request(None, None, self.clientstate, self.server.mailcontext)

    def do_request(self):
        try:
            self.current_request.handle_request()
        except:
            typ, v, tb = sys.exc_info()
            note("exception handling request %s:\n%s", repr(self), string.join(traceback.format_exception(typ, v, tb)))
            raise v

    def handle_data (self, fp, extra):
        self.current_request.args.append(fp.read())
        fp.close()
        note("handle_data:  extra is %s", repr(extra))
        count, litcount = self.current_request.parse_args(extra)
        # note("count is %s, litcount is %s", count, litcount)
        self.collector = None
        if count > 0:
            # need still more stuff from the client
            self.collector = data_collector(count, self)
            if not litcount:
                self.push_with_producer (producers.simple_producer('+ Ready for more data\r\n'))
        else:
            self.do_request()

    def found_terminator (self):
        # note("--- found_terminator(%s), collector is %s", repr(self), repr(self.collector))
        if self.collector:
            if self.collector.found_terminator():
                self.collector = None
        else:
            header = self.in_buffer
            self.in_buffer = ''
            lines = string.split (header, '\r\n')

            # --------------------------------------------------
            # crack the request header
            # --------------------------------------------------

            # note("--- lines are <%s>", lines)

            if not lines:
                self.close_when_done()
                return

            request = lines[0].strip()
            note("c%d:  request is <%s>", self.channel_number, request)

            r = self.parse_request(request)
            # note("--- r is %s", repr(r))

            self.request_counter.increment()
            self.server.total_requests.increment()

            if not r.valid():
                note("c%d:  invalid request %s", self.channel_number, r)
                self.log_info ('Bad IMAP request: %s' % repr(request), 'error')
                r.error ('Bad request:  %s' % repr(request))
                return

            try:
                self.current_request = r
                if self.collector:
                    note(3, "c%d:  waiting for more data (%s) %s...", self.channel_number,
                         self.collector.waiting_for_what(), self.collector)
                    return
                # note("--- about to handle request")
                self.do_request()
                note(3, "--------  c%d:  handled request", self.channel_number)
            except:
                self.server.exceptions.increment()
                (file, fun, line), t, v, tbinfo = asyncore.compact_traceback()
                self.log_info('c%d:  server Error: %s, %s: file: %s line: %s'
                              % (self.channel_number, t,v,file,line), 'error')
                try:
                    r.error ('server exception: %s, %s: file: %s line: %s' % (t,v,file,line))
                except:
                    pass

    def writable_for_proxy (self):
        # this version of writable supports the idea of a 'stalled' producer
        # [i.e., it's not ready to produce any output yet] This is needed by
        # the proxy, which will be waiting for the magic combination of
        # 1) hostname resolved
        # 2) connection made
        # 3) data available.
        if self.ac_out_buffer:
            return 1
        elif len(self.producer_fifo):
            p = self.producer_fifo.first()
            if hasattr (p, 'stalled'):
                return not p.stalled()
            else:
                return 1

    def log_info (self, msg, state='info'):
        self.server.log_info(msg, state)

    def log_date_string (self, when):
        gmt = time.gmtime(when)
        if time.daylight and gmt[8]:
            tz = time.altzone
        else:
            tz = time.timezone
        if tz > 0:
            neg = 1
        else:
            neg = 0
            tz = -tz
        h, rem = divmod (tz, 3600)
        m, rem = divmod (rem, 60)
        if neg:
            offset = '-%02d%02d' % (h, m)
        else:
            offset = '+%02d%02d' % (h, m)

        return time.strftime ( '%d/%b/%Y:%H:%M:%S ', gmt) + offset

# ===========================================================================
#                                               IMAP Server Object
# ===========================================================================

class imap_server (asyncore.dispatcher):

    channel_class = imap_connection

    def __init__ (self, context, ip=None, port=143, logger=None, stunnel_pid=None):
        if not ip:
            self.ip = "0.0.0.0"
        else:
            self.ip = ip
        self.port = port
        self.mailcontext = context 
        self.logger = logger or unresolving_logger(file_logger(sys.stderr))
        self.stunnel_pid = stunnel_pid

        asyncore.dispatcher.__init__ (self)
        self.create_socket (socket.AF_INET, socket.SOCK_STREAM)

        self.handlers = []

        self.set_reuse_addr()
        self.bind ((ip, port))

        # lower this to 5 if your OS complains
        self.listen (1024)

        host, port = self.socket.getsockname()
        if not ip:
            self.log_info('Computing default hostname', 'warning')
            ip = socket.gethostbyname (socket.gethostname())
        try:
            self.server_name = socket.gethostbyaddr (ip)[0]
        except socket.error:
            self.log_info('Cannot do reverse lookup', 'warning')
            self.server_name = ip       # use the IP address as the "hostname"

        self.server_port = port
        self.total_clients = counter()
        self.total_requests = counter()
        self.exceptions = counter()
        self.bytes_out = counter()
        self.bytes_in  = counter()

        info = ('UpLib IMAP (V4r1) started at %s'
                '\n\tHostname: %s'
                '\n\tPort: %d'
                '\n' % (
                    time.ctime(time.time()),
                    self.server_name,
                    port,
                    )
                )
        # self.log_info (info, 'info')
        self.mailcontext.note(info)

    def __str__(self):
        return '<IMAP server %s:%d %s %s>' % (self.server_name, self.server_port, id(self), str(self.mailcontext))

    def close(self):
        self.mailcontext.checkpoint()
        asyncore.dispatcher.close(self)

    def writable (self):
        return 0

    def handle_read (self):
        pass

    def readable (self):
        return self.accepting

    def handle_connect (self):
        pass

    def handle_accept (self):
        self.total_clients.increment()
        try:
            conn, addr = self.accept()
            # self.mailcontext.note("accepted conn %s on addr %s", conn, addr)
        except socket.error:
            # linux: on rare occasions we get a bogus socket back from
            # accept.  socketmodule.c:makesockaddr complains that the
            # address family is unknown.  We don't want the whole server
            # to shut down because of this.
            self.log_info ('warning: server accept() threw an exception', 'warning')
            return
        except TypeError:
            # unpack non-sequence.  this can happen when a read event
            # fires on a listening socket, but when we call accept()
            # we get EWOULDBLOCK, so dispatcher.accept() returns None.
            # Seen on FreeBSD3.
            self.log_info ('warning: server accept() threw EWOULDBLOCK', 'warning')
            return

        self.channel_class (self, conn, addr)

    def log_info(self, message, type='info'):
        self.logger.log(self.ip, '%s: %s\n' % (type, message))

    def status (self):
        def nice_bytes (n):
            return string.join (status_handler.english_bytes (n))

        if self.total_clients:
            ratio = self.total_requests.as_long() / float(self.total_clients.as_long())
        else:
            ratio = 0.0

        return producers.composite_producer (
                [producers.lines_producer (
                        ['<h2>%s</h2>'                          % self.mailcontext.IDENT,
                        '<br>Listening on: <b>Host:</b> %s'     % self.server_name,
                        '<b>Port:</b> %d'                       % self.port,
                         '<p><ul>'
                         '<li>Total <b>Clients:</b> %s'         % self.total_clients,
                         '<b>Requests:</b> %s'                  % self.total_requests,
                         '<b>Requests/Client:</b> %.1f'         % (ratio),
                         '<li>Total <b>Bytes In:</b> %s'        % (nice_bytes (self.bytes_in.as_long())),
                         '<b>Bytes Out:</b> %s'                 % (nice_bytes (self.bytes_out.as_long())),
                         '<li>Total <b>Exceptions:</b> %s'      % self.exceptions,
                         '</ul><p>'
                         '<b>Extension List</b><ul>',
                         ])] + [producers.simple_producer('</ul>')]
                )
