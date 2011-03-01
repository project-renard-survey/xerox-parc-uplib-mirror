# -*- Mode: Python -*-
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

import re, sys, os, string
from StringIO import StringIO
import Cookie
import cgi
import httplib
import traceback
import time
import stat
import tempfile
import types
import datetime
import urlparse

from tornado.web import RequestHandler, HTTPError
from tornado import version as TornadoVersion

assert(tuple([int(x) for x in TornadoVersion.split('.')]) >= (1, 2))

from uplib.plibUtil import note, configurator, PATH_SEPARATOR, uthread, get_note_sink
from uplib.extensions import find_and_load_extension, is_hierarchical_extension
from uplib.webutils import htmlescape, HTTPCodes, get_content_type

TOUCHPATH = re.compile('/docs/(?P<docid>[^/]+)/(.*\.(html|pdf|tiff)|contents.txt)')
DOCPATH = re.compile('/docs/(?P<docid>[^/]+)/.*\.(html|pdf|tiff|txt|png|bboxes)')
MORSEL_KEY = None
FAVICON = None

REPO_EXTENSION_DIRS = None
ALLOW_OLD_EXTENSIONS = False

ONE_YEAR = 365 * 24 * 60 * 60   # seconds in one standard year

TOP_LEVEL_ACTION = ("basic", "repo_show")
"""What to revert to if asked for '/', a (MODULE-NAME, MODULE-FUNCTION) pair.
Could be overridden by an extension."""

def request_to_field_dict (request):

    # With Tornado we get request.arguments, a property containing an
    # query-string encoded parameters (which may have multiple values)
    # and we also get request.files, which contains multipart/form-data
    # values uploaded as the body of the request.  To be compatible
    # with Medusa usage, we need to combine both of those together into
    # a single dictionary

    retdict = dict()
    for k, v in request.arguments.items():
        if isinstance(v, list):
            if len(v) == 1:
                retdict[k] = v[0]
            elif len(v) > 1:
                retdict[k] = v
        else:
            retdict[k] = v
    for k, v in request.files.items():
        if isinstance(v, list):
            if len(v) == 1:
                retdict[k] = v[0].get("body")
            elif len(v) > 1:
                retdict[k] = [x.get("body") for x in v]
        else:
            retdict[k] = v.get("body")
    return retdict

############################################################
###
###  function find_action_function (MODULE, FUNCTION)
###
###  Find and return the specified function.
###
############################################################

def find_action_function (module_name, function_name, repo_actions_path):

    # special case "basic" module

    if module_name == "basic":
        import uplib.basicPlugins
        return uplib.basicPlugins.lookup_action(function_name)

    # special case "externalAPI" module

    if module_name == "externalAPI":
        import uplib.externalAPI
        return getattr(uplib.externalAPI, function_name)

    # for others, we load the module and search for the function in it (eventually)
    else:

        import string, traceback

        try:
            module = find_and_load_extension (module_name, repo_actions_path, REPO_EXTENSION_DIRS,
                                              allow_old_extensions=ALLOW_OLD_EXTENSIONS)
            if module:
                note(4, "module %s was found", module_name)
                if hasattr(module, function_name):
                    value = getattr(module, function_name)
                    if callable(value):
                        return value
                if hasattr(module, "lookup_action"):
                    return module.lookup_action(function_name)
            else:
                note(3, "module %s was not found.  repo_actions_path = [%s].  REPO_EXTENSION_DIRS = [%s]", module_name, repo_actions_path, REPO_EXTENSION_DIRS)
        except:
            typ, value, tb = sys.exc_info()
            note(2, "%s", ''.join(traceback.format_exception(typ, value, tb)))
        return None


def check_cookie(request, repo):
    global MORSEL_KEY
    try:
        if not MORSEL_KEY:
            MORSEL_KEY = "uplibnonce%d" % repo.secure_port()
        cookiedata = request.request.headers.get("Cookie")
        cookie = Cookie.BaseCookie(cookiedata)
        morsel = cookie.get(MORSEL_KEY)
        return morsel and repo.check_cookie(morsel.value)
    except:
        t, v, s = sys.exc_info()
        note("error in check_cookie:\n%s\n", ''.join(traceback.format_exception(t, v, s)))
        return False

def is_logged_in (repo, request):
    if not repo.has_password:
        return True
    header_password = request.request.headers.get("Password")
    if header_password and repo.check_password(header_password):
        return True
    if check_cookie(request, repo):
        return True
    return False

authorized = is_logged_in


def my_http_date(date=None):
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", date or time.gmtime())


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

class SelfDeletingFileObject (object):

    def __init__(self, filename):
        self.__filename = filename
        self.__fp = None

    def open(self, mode='rb'):
        self.__fp = open(self.__filename, mode)
        return self.__fp

    def __del__(self):
        if self.__fp is not None:
            self.__fp.close()
        os.unlink(self.__filename)


############################################################
###
###  Exception ForkRequestInNewThread
###
###  Raised from do_action() to signal that the request is being
###  handled in a separate thread.
###
############################################################

class ForkRequestInNewThread (Exception):
    def __init__(self, id):
        self.thread_id = id

############################################################
###
###  UpLibHandler:  base class for RequestHandlers
###
############################################################

class UpLibHandler(RequestHandler):

    def initialize(self, **kwargs):
        self.repo = kwargs.get("repository")
        self.logger = get_note_sink()

    def get_error_html (self, status_code, **kwargs):

        if 'message' in kwargs and 'content_type' in kwargs:
            content_type = kwargs.get('content_type')
            message = kwargs.get('message')
            if content_type.startswith("text/plain"):
                message = '<pre>' + htmlescape(message) + '</pre>'
                content_type = "text/html"
            if (content_type is None) or (content_type == "text/html"):
                return "<html><title>%(code)d: %(stdmsg)s</title>" \
                       "<body>%(code)d: %(message)s</body></html>" % {
                           "code": status_code,
                           "stdmsg": httplib.responses[status_code],
                           "message" : message,
                           }
            else:
                raise RuntimeError("Error messages must be HTML")
        else:
            RequestHandler.get_error_html(self, status_code, **kwargs)            

    def get_header(self, header_name):
        return self.request.headers.get(header_name)

    def get_login_page(self):
        return ('<head><title>Login Page</title>\n' +
                '<script>\n' +
                '<!--\n' +
                'function sf(){document.f.password.focus();}\n' +
                '// -->\n' + 
                '</script></head>\n' +
                '<body bgcolor="#ef280e" onload="sf()">\n' +
                '<table width=100% height=100%><tr align=center><td align=center>' +
                '<table bgcolor=black cellpadding=10><tr bgcolor=white><td>' +
                '<center>Please enter pass-phrase:<br>' +
                '<form action="/login" method=POST enctype="multipart/form-data" name=f>\n' +
                '<input type=password size=60 name=password value=""><P>&nbsp;<br>\n' +
                ('<input type=hidden name=originaluri value="%s"><P>&nbsp;<br>\n'
                 % htmlescape(self.request.uri, True)) +
                '<input type=submit value="Login">\n' +
                '</center></form></td></tr></table></td></tr></table></body>')

    def prepare (self):
        try:
            if not authorized(self.repo, self):
                self.send_error(HTTPCodes.UNAUTHORIZED, message=self.get_login_page())
        except:
            raise HTTPError(
                HTTPCodes.INTERNAL_SERVER_ERROR,
                ''.join(traceback.format_exception(*sys.exc_info())))
        self.add_last_modified_headers()

    def add_last_modified_headers(self):
        # self is a tornado.web.SelfHandler
        self.set_header('X-UpLib-Repository-Last-Modified', datetime.datetime.fromtimestamp(self.repo.mod_time()))
        wants_doc_changes = self.request.headers.get("x-uplib-docs-modified-since")
        if wants_doc_changes:
            try:
                wants_doc_changes = float(wants_doc_changes.strip())
            except:
                pass
            else:
                docs = self.repo.get_touched_since(wants_doc_changes)
                self.set_header('X-UpLib-Docs-Modified',
                                str(wants_doc_changes) + ";" +
                                ";".join(["%s,%s" % (doc.id, doc.touch_time()) for doc in docs]))

    def close(self):
        # noop
        pass

    def _request_summary(self):
        return self.request.method + " " + self.request.uri + " (" + \
            self.request.remote_ip + ")"

    def _log(self):
        request_time = 1000.0 * self.request.request_time()
        bytecount = self._headers.get("Content-Length")
        if bytecount:
            bytecount = int(bytecount)
            if bytecount > 0:
                bytecount = " (%d bytes)" % bytecount
            else:
                bytecount = ""
        else:
            bytecount = ""
        msg = ("%s => %d%s %.2fms" % (self._request_summary(), self._status_code,
                                      bytecount, request_time))
        if self._status_code < 400:
            note(2, msg)
        elif self._status_code < 500:
            note(1, msg)
        else:
            note(0, msg)

    def done(self):
        RequestHandler.finish(self)

############################################################
###
###  Class response
###
############################################################

class _request_file_buffer (StringIO):

    def __init__(self, handler, stream_format = 'text/html'):
        # 'handler' is a RequestHandler
        StringIO.__init__(self)
        self.__stream_format = stream_format
        self.__handler = handler
	self.__open = True
        self.__utf8 = False
        self.__textual = stream_format.startswith("text/")

    def write(self, s):
        if isinstance(s, unicode):
            StringIO.write(self, s.encode('UTF-8', 'replace'))
            self.__utf8 = True
        else:
            StringIO.write(self, s)

    def discard(self):
        self.__handler = None
        StringIO.close(self)
        self.__open = False

    def finish(self):
        s = self.getvalue()
        if self.__textual:
            if self.__utf8:
                self.__handler.set_header('Content-Type', self.__stream_format + "; charset=UTF-8")
            else:
                self.__handler.set_header('Content-Type', self.__stream_format + "; charset=ISO-8859-1")
        else:
            self.__handler.set_header('Content-Type', self.__stream_format)
        if (self.__handler.request.method != "HEAD"):
            self.__handler.write(s)

    def close(self):
	self.__open = False

def _python_exception_html(excn, extra = None):

    typ, value, tb = excn
    s = ''.join(traceback.format_exception(typ, value, tb))
    s2 = '<html><body><p>Error:'
    if extra:
        s2 = s2 + '  ' + htmlescape(extra)
    s2 = s2 + '<br>\n<p><pre>' + htmlescape(s) + '</pre></body></html>'
    return s2

def run_fn_in_new_thread(resp, fn, args):
    resp._in_new_thread = True
    try:
        fn(*args)
    except:
        excn = sys.exc_info()
        note(0, "Exception calling %s with %s:\n%s", fn, args, ''.join(traceback.format_exception(*excn)))
        text = _python_exception_html(sys.exc_info(), "Calling \"%s\" with %s" % (fn, args))
        resp.error(HTTPCodes.INTERNAL_SERVER_ERROR, text)
    try:
        resp.finish()
    except:
        excn = sys.exc_info()
        note(0, "Exception finishing calling %s with %s:\n%s", fn, args, ''.join(traceback.format_exception(*excn)))

class response (object):

    def __init__(self, handler, logged_in = False):
	self.request = handler  # a RequestHandler instance
        self.logged_in = logged_in
        self.repo = handler.repo
        self.request_path = urlparse.urlsplit(handler.request.uri).path
        self.content = StringIO(handler.request.body)
        self.callers_idea_of_service = handler.request.host
        self.user_agent = handler.request.headers.get("user-agent")
        accepts = handler.request.headers.get("accept")
        self.xml_request = accepts and (accepts.lower().strip() == "application/xml")
	self.fp = None
        self.request.set_header('Cache-Control', 'no-store')
        self.request.uri = self.request.request.uri
        self._in_new_thread = False

    def open (self, content_type = "text/html"):
        self.fp = _request_file_buffer(self.request, content_type)
        return self.fp

    def redirect (self, url, permanent=False):
        if self._in_new_thread:
            self.request.request.connection.stream.io_loop.add_callback(lambda: self.request.redirect(url))
        else:
            self.request.redirect(url)

    def error (self, code, message, content_type=None):
        if code < 400:
            self.request.set_status(code)
            return self.reply(message, content_type)
        if self._in_new_thread:
            self.request.request.connection.stream.io_loop.add_callback(
                lambda: self.request.send_error(code, message=message, content_type=content_type))
        else:
            self.request.send_error(code, message=message, content_type=content_type)

    def reply (self, message, content_type=None):
        # calls "error", so no need to check for unicode -- done in "error"
        if self._in_new_thread:
            def _new_fn():
                if content_type is not None:
                    self.request.set_header('Content-Type', content_type)
                self.request.write(message)
            self.request.request.connection.stream.io_loop.add_callback(_new_fn)
        else:
            if content_type is not None:
                self.request.set_header('Content-Type', content_type)
            self.request.write(message)

    def return_file (self, typ, path, delete_on_close=False, filename=None):
        stats = os.stat(path)
        if delete_on_close:
            fp = self_deleting_file(path, 'rb')
        else:
            fp = open(path, 'rb')
        self.request.set_header('Content-Type', (isinstance(typ, unicode) and typ.encode("ASCII", "replace")) or typ)
        self.request.set_header('Content-Length', str(stats.st_size))
        self.request.set_header('Last-Modified', datetime.datetime.fromtimestamp(stats.st_mtime))
        if filename:
            filename = (isinstance(filename, unicode) and filename.encode("ASCII", "replace")) or filename
            self.request.set_header("Content-Disposition", "inline; filename=%s" % filename)
        elif not delete_on_close:
            filename = os.path.split(path)[1]
            filename = (isinstance(filename, unicode) and filename.encode("ASCII", "replace")) or filename
            self.request.set_header("Content-Disposition", "inline; filename=%s" % filename)
        if (self.request.request.method != "HEAD"):
            self.request.write(fp.read())

    def fork_request(self, fn, *args):
        note(3, "forking %s in new thread...", fn)
        id = uthread.start_new_thread(run_fn_in_new_thread, (self, fn, args),
                                      "handling request %s %s at %s" % (
                                          self.request.request.method,
                                          self.request.request.uri, time.ctime()))
        raise ForkRequestInNewThread(id)

    def finish(self):
        if isinstance(self.fp, _request_file_buffer):
            self.request.request.connection.stream.io_loop.add_callback(self.fp.finish)
        self.fp = None
        self.request.request.connection.stream.io_loop.add_callback(self.request.finish)

    def __del__(self):
        if isinstance(self.fp, _request_file_buffer):
            self.fp.finish()

class PingHandler (UpLibHandler):

    SUPPORTED_METHODS = ("GET", "HEAD")

    def prepare(self):
        """No authentication needed for these"""
        self.set_header('Server', "UpLib/%s (Tornado %s)" % (self.repo.get_version(), TornadoVersion))

    def _common(self):

        if self.request.uri == '/ping':
            self.add_last_modified_headers()
            self.set_status(HTTPCodes.OK)
            return
        elif self.request.uri == '/favicon.ico':
            global FAVICON
            if not FAVICON:
                FAVICON = self.repo.get_favicon()
            if FAVICON:
                self.set_status(HTTPCodes.OK)
                self.set_header("Content-Type", "image/vnd.microsoft.icon")
                self.write(FAVICON)
            else:
                self.send_error(404)
        elif self.request.uri == "/html/signedreadup.jar":
            jarpath = os.path.join(self.repo.html_folder(), "signedreadup.jar")
            # simplest way to do this is to create a response object
            if not os.path.exists(jarpath):
                self.send_error(404)
                return
            response(self).return_file("application/x-java-archive", jarpath)
        elif request.uri == "/html/images/ReadUpJWS.gif":
            imgpath = os.path.join(self.repo.html_folder(), "images", "ReadUpJWS.gif")
            # simplest way to do this is to create a response object
            if not os.path.exists(imgpath):
                request.error(404)
                return
            response(self).return_file("image/gif", imgpath)
        else:
            self.send_error(404)

    def get(self, *args, **kwargs):
        self._common()

    def head(self, *args, **kwargs):
        self._common()


class LoginHandler (RequestHandler):

    SUPPORTED_METHODS = ("GET", "POST")

    def _common(self):
        self.set_header('Server', "UpLib/%s (Tornado %s)" % (self.repo.get_version(), TornadoVersion))
        password = self.get_argument("password", default=None)
        if (authorized(self.repo, self) or
            ((authorized is is_logged_in) and password and self.repo.check_password(password))):

            # OK, authorized, so set cookie and redirect to original URI
            randomness = str(self.request.headers)
            cookie = self.repo.new_cookie(randomness)

            # would be nice if we could omit the secure if the web browser is local,
            # but we can't tell, because with stunnel in the chain, every request we
            # receive comes from localhost.  If we could get rid of stunnel, we could
            # tell, though.
            #
            # cookie_str = '%s=%s; path=/' % (cookie.name(), cookie.value())
            # if not (request.channel.addr[0] == '127.0.0.1' or request.channel.addr[0] == 'localhost'):
            #    cookie_str = cookie_str + '; secure'

            cookie_str = '%s=%s; path=/' % (cookie.name(), cookie.value())
            if not self.allow_insecure_cookies:
                cookie_str = cookie_str + "; Secure"
            note("request.channel.addr is %s, cookie_str is \"%s\"", self.request.host, cookie_str)
            self.set_header('Set-Cookie', cookie_str)
            self.set_header('Cache-Control', 'no-cache="set-cookie"')   # cf RFC 2109
            self.redirect(self.get_argument("originaluri", default=None) or "/")
            return True
        else:
            return False

    def output_login_page(self):
        self.set_status(HTTPCodes.UNAUTHORIZED)
        self.set_header('Content-Type', 'text/html')
        self.write('<head><title>Login Page</title>\n' +
                   '<script>\n' +
                   '<!--\n' +
                   'function sf(){document.f.password.focus();}\n' +
                   '// -->\n' + 
                   '</script></head>\n' +
                   '<body bgcolor="#ef280e" onload="sf()">\n' +
                   '<table width=100% height=100%><tr align=center><td align=center>' +
                   '<table bgcolor=black cellpadding=10><tr bgcolor=white><td>' +
                   '<center>Please enter pass-phrase:<br>' +
                   '<form action="/login" method=POST enctype="multipart/form-data" name=f>\n' +
                   '<input type=password size=60 name=password value=""><P>&nbsp;<br>\n' +
                   '<input type=submit value="Login">\n' +
                   '</center></form></td></tr></table></td></tr></table></body>')

    def get(self, *args, **kwargs):
        if not self._common():
            self.output_login_page()

    def post(self, *args, **kwargs):
        if not self._common():
            self.output_login_page()

class DocsHandler(UpLibHandler):

    SUPPORTED_METHODS = ("GET", "HEAD")

    def initialize(self, **kwargs):

        super(DocsHandler, self).initialize(**kwargs)
        self.allow_cache = kwargs.get('allow-caching')

    def _common(self):

        if self.allow_cache:
            # no need to re-fetch doc images or HTML
            self.set_header('Expires', datetime.datetime.utcnow() + datetime.timedelta(days=EXPIRES_DAYS))
        else:
            # dynamic content
            self.set_header('Cache-Control', 'no-store')
        self.set_header('Server', "UpLib/%s (Tornado %s)" % (self.repo.get_version(), TornadoVersion))
        # we check to see if this request is on a document.  If so, it may
        # need special handling
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(self.request.uri)
        m = DOCPATH.match(path)
        if m:
            docid = m.group('docid')
            if self.repo.valid_doc_id(docid):
                if TOUCHPATH.match(path):
                    self.repo.touch_doc(docid)
                # we check to see if the file exists.  If not, we invoke the document
                # object's method to fetch it
                filepath = os.path.join(self.repo.docs_folder(), path[6:])
                if ((not os.path.exists(filepath)) or
                    path[5:].endswith("/contents.txt") or
                    path[5:].endswith("/summary.txt") or
                    path[5:].endswith("/metadata.txt")):
                    doc = self.repo.get_document(docid)
                    bits, mime_type = doc.get_requested_part(path, params, query, fragment)
                else:
                    try:
                        bits = open(filepath, 'rb').read()
                        mime_type = get_content_type(filepath)
                    except:
                        bits = None
                        mime_type = None
                        raise
                if bits and mime_type:
                    self.set_header('Content-Type', mime_type)
                    self.set_status(200)
                    self.write(bits)
        return None

    def get(self, *args, **kwargs):
        self._common()

    def head(self, *args, **kwargs):
        self._common()

class ActionHandler (UpLibHandler):

    SUPPORTED_METHODS = ("GET", "HEAD", "POST")

    def prepare(self):

        global TOP_LEVEL_ACTION

        super(ActionHandler, self).prepare()

        self.set_header('Server', "UpLib/%s (Tornado %s)" % (self.repo.get_version(), TornadoVersion))

        self.angel_action = None
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(self.request.uri)
        parts = [x for x in path.split('/') if x.strip()]

        if len(parts) == 3 and parts[0] == 'action':
            self.angel_action = (parts[1:], params, query, fragment)
        elif (len(parts)==4 and parts[0] == 'action' and parts[3][0:3]=='seq'):
            note(2, "in match with 4 parts, parts = %s", str(parts))
            self.angel_action = (parts[1:3], params, query, fragment)
        elif (len(parts) > 3) and (parts[0] == 'action') and (is_hierarchical_extension(parts[1])):
            # to support extensions with hierarchical static elements, like GWT-generated UIs
            note(4, "hierarchical request, parts = %s", str(parts))
            self.angel_action = ((parts[1], '/'.join(parts[2:])), params, query, fragment)
        elif path == '/':
            self.redirect('/'.join(("/action",) + TOP_LEVEL_ACTION))
        else:
            raise HTTPError(HTTPCodes.BAD_REQUEST, "Invalid /action request %s received", self.request.uri)

    def _common(self):

        global REPO_EXTENSION_DIRS, ALLOW_OLD_EXTENSIONS
        if not REPO_EXTENSION_DIRS:
            conf = configurator.default_configurator()
            REPO_EXTENSION_DIRS = PATH_SEPARATOR.join((
                os.path.join(self.repo.overhead_folder(), "extensions", "active"),
                os.path.join(conf.get('uplib-lib'), 'site-extensions')))
            ALLOW_OLD_EXTENSIONS = conf.get_bool("allow-old-extensions")

        module_name, function_name = self.angel_action[0]
        exception = None
        callable = None
        try:
            callable = find_action_function(module_name, function_name, self.repo.get_actions_path())
        except:
            t, v, b = sys.exc_info()
            exception = ''.join(traceback.format_exception(t, v, b))
            note(0, "find_action_function(%s/%s) raised an exception:\n%s", module_name, function_name, exception)
        if callable:
            field_values = request_to_field_dict(self.request) or {}
            try:
                resp = response(self, self.current_user is not None)
                callable(self.repo, resp, field_values)
                return True
            except ForkRequestInNewThread, x:
                note(4, "forked off request")
                self._auto_finish = False
                return False
            except:
                raise
        else:
            action = htmlescape("/action/" + module_name + "/" + function_name)
            if exception:
                s = u"<html><head><title>Error loading module:  %s</title></head><body><p>Attempt to load module/function <i>%s/%s</i> raised an exception:\n<pre>%s</pre><p>(extensions path = [<tt>%s</tt>], sys.path = <tt>%s</tt>)</body></html>" % (action, module_name, function_name, exception, self.repo.get_actions_path(), htmlescape(str(sys.path)))
            else:
                s = u"<html><head><title>No such action:  %s</title></head><body><p>No such action:  %s.<br>actions path = [%s]</body></html>" % (action, action, self.repo.get_actions_path())
            self.send_error(HTTPCodes.NOT_IMPLEMENTED, message=s)
            return True

    def get(self, *args, **kwargs):
        self._auto_finish = self._common()

    def post(self, *args, **kwargs):
        note("POST %s (%d bytes)", self.request.uri, len(self.request.body))
        self._auto_finish = self._common()

    def head(self, *args, **kwargs):
        """We don't generally do HEAD requests on /action, but JNLP requires it"""
        if self.request.uri.endswith(".jnlp") or self.request.uri.endswith(".jar"):
            self._auto_finish = self._common()
        else:
            self.send_error(HTTPCodes.METHOD_NOT_ALLOWED)
