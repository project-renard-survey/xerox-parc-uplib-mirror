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
import asyncore
import Cookie
import cgi
import traceback
import time
import stat
import tempfile
import types

from medusa import http_server
from medusa import default_handler
from medusa import logger
from medusa import script_handler
from medusa import filesys
from medusa import http_date
from medusa import producers

from medusa.default_handler import unquote, get_header, IF_MODIFIED_SINCE
from medusa.http_server import get_header_match
from medusa.counter import counter

from uplib.plibUtil import note, configurator, true, false, PATH_SEPARATOR, uthread
from uplib.extensions import find_and_load_extension, is_hierarchical_extension
from uplib.webutils import htmlescape, HTTPCodes, get_content_type

CONTENT_LENGTH = re.compile ('Content-Length: ([0-9]+)', re.IGNORECASE)
CONTENT_TYPE = re.compile ('Content-Type: (.+)', re.IGNORECASE)
USER_AGENT = re.compile ('User-Agent: (.+)', re.IGNORECASE)
HOST_HEADER = re.compile ('Host: (.+)', re.IGNORECASE)
ACCEPTS_HEADER = re.compile ('Accept: (.+)', re.IGNORECASE)
DOC_CHANGES_SINCE_HEADER = re.compile ('X-UpLib-Docs-Modified-Since: (.+)', re.IGNORECASE)
TOUCHPATH = re.compile('/docs/(?P<docid>[^/]+)/(.*\.(html|pdf|tiff)|contents.txt)')
DOCPATH = re.compile('/docs/(?P<docid>[^/]+)/.*\.(html|pdf|tiff|txt|png|bboxes)')
COOKIE = re.compile('Cookie: (.+)', re.IGNORECASE)
PASSWORD = re.compile('Password: (.+)', re.IGNORECASE)
MORSEL_KEY = None
FAVICON = None

REPO_EXTENSION_DIRS = None
ALLOW_OLD_EXTENSIONS = False

ONE_YEAR = 365 * 24 * 60 * 60   # seconds in one standard year

TOP_LEVEL_ACTION = ("basic", "repo_show")
"""What to revert to if asked for '/', a (MODULE-NAME, MODULE-FUNCTION) pair.
Could be overridden by an extension."""

def request_to_field_dict (request, inputstream, query=1):

    #FieldStorge default is to get the header info from enviroment variables
    #we can override this in the constructor of the FieldStorage class
    #the FieldStorage headers object must be a dictionary if it is overridden
    #the Medusa request.header will need to be converted into a dictionary...

    #create an empty dictionary object
    dicHeader = {}
    #break the request.header tuple apart...
    for varPart in request.header:
        #break each reqest header part apart into key/values pairs
        varKeyValuePair= varPart.split(": ")
        #Place them in the dictionary
        dicHeader[varKeyValuePair[0].lower()]=varKeyValuePair[1]

    # create another dictionary to act as the enviroment variables
    dicEnvir = {}
    #Add the Request Method from the request object
    dicEnvir['REQUEST_METHOD'] = request.command

    #put the query string in the dictionary...
    if query and query != 1:
        dicHeader['content-type'] = 'application/x-www-form-urlencoded'
        dicEnvir['QUERY_STRING'] = query[1:]

    #create a FieldStorage object with overridden headers and environ object

    #note("headers are:\n%s\n" % dicHeader)
    #note("environment is:\n%s\n" % dicEnvir)
    if (inputstream is None):
        inputstream = StringIO('')
    form = cgi.FieldStorage(fp=inputstream,headers=dicHeader,environ=dicEnvir)
    retdict = {}
    if form.list is not None:
        for key in form.keys():
            v = form[key]
            if type(v) == type([]) or type(v) == type(()):
                retdict[key] = map(lambda x: x.value, v)
            else:
                retdict[key] = v.value
            #note("key %s:  %s", key, retdict[key])
            if hasattr(v, 'filename') and v.filename:
                filenameKey = key+'-filename'
                retdict[filenameKey] = v.filename

    del form
    return retdict


class request_file_buffer (StringIO):

    def __init__(self, request, stream_format = 'text/html'):
        StringIO.__init__(self)
        self.__stream_format = stream_format
        self.__request = request
	self.__open = 1
        self.__utf8 = 0
        self.__textual = stream_format.startswith("text/")

    def write(self, s):
        if isinstance(s, unicode):
            StringIO.write(self, s.encode('UTF-8', 'replace'))
            self.__utf8 = 1
        else:
            StringIO.write(self, s)

    def discard(self):
        self.__request = None
        StringIO.close(self)
        self.__open = 0

    def close(self):
	if self.__open:
	    s = self.getvalue()
            if self.__textual:
                if self.__utf8:
                    self.__request['Content-Type'] = self.__stream_format + "; charset=UTF-8"
                else:
                    self.__request['Content-Type'] = self.__stream_format + "; charset=ISO-8859-1"
            else:
                self.__request['Content-Type'] = self.__stream_format
            self.__request['Content-Length'] = len(s)
            if (self.__request.command != "HEAD"):
                self.__request.push(s)
	    StringIO.close(self)
	self.__open = 0

############################################################
###
###  function signal_python_exception
###
###  HTML-quote a python traceback
###
############################################################

def python_exception_html(excn, extra = None):

    typ, value, tb = excn
    s = ''.join(traceback.format_exception(typ, value, tb))
    s2 = '<html><body><p>Error:'
    if extra:
        s2 = s2 + '  ' + htmlescape(extra)
    s2 = s2 + '<br>\n<p><pre>' + htmlescape(s) + '</pre></body></html>'
    return s2

def signal_python_exception(request, excn, extra=None):

    note(0, "signalling Python exception:\n%s", ''.join(traceback.format_exception(*excn)))
    try:
        s2 = python_exception_html (excn, extra)
        request.reply_code = 500
        request['Content-Type'] = 'text/html'
        request['Content-Length'] = len(s2)
        request.push(s2)
    except:
        note("signal_python_exception raises exception:\n%s", ''.join(traceback.format_exception(*sys.exc_info())))

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
        cookiedata = get_header(COOKIE, request.header)
        cookie = Cookie.BaseCookie(cookiedata)
        morsel = cookie.get(MORSEL_KEY)
        return morsel and repo.check_cookie(morsel.value)
    except:
        t, v, s = sys.exc_info()
        note("error in check_cookie:\n%s\n", ''.join(traceback.format_exception(t, v, s)))
        return false

def is_logged_in (repo, request):
    if not repo.has_password: return true
    header_password = get_header(PASSWORD, request.header)
    if header_password and repo.check_password(header_password):
        return true
    if check_cookie(request, repo):
        return true
    return false

authorized = is_logged_in

def output_login_page(request):
    request.reply_code = 401
    request['Content-Type'] = 'text/html'
    response = ('<head><title>Login Page</title>\n' +
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
                ('<input type=hidden name=originaluri value="%s"><P>&nbsp;<br>\n'
                 % htmlescape(request.uri, true)) +
                '<input type=password size=60 name=password value=""><P>&nbsp;<br>\n' +
                '<input type=submit value="Login">\n' +
                '</center></form></td></tr></table></td></tr></table></body>')
    request['Content-Length'] = len(response)
    request.push(response)


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
###  Class response
###
############################################################

def run_fn_in_new_thread(resp, fn, args):
    try:
        fn(*args)
    except:
        excn = sys.exc_info()
        note(0, "Exception calling %s with %s:\n%s", fn, args, ''.join(traceback.format_exception(*excn)))
        text = python_exception_html(sys.exc_info(), "Calling \"%s\" with %s" % (fn, args))
        resp.error(HTTPCodes.INTERNAL_SERVER_ERROR, text)
    try:
        resp.request.done()
    except:
        excn = sys.exc_info()
        note(0, "Exception finishing calling %s with %s:\n%s", fn, args, ''.join(traceback.format_exception(*excn)))


def add_last_modified_headers(request, repo):
    request['X-UpLib-Repository-Last-Modified'] = http_date.build_http_date(repo.mod_time())
    wants_doc_changes = get_header(DOC_CHANGES_SINCE_HEADER, request.header)
    if wants_doc_changes:
        try:
            wants_doc_changes = float(wants_doc_changes.strip())
        except:
            pass
        else:
            docs = repo.get_touched_since(wants_doc_changes)
            request['X-UpLib-Docs-Modified'] = str(wants_doc_changes) + ";" + ";".join(["%s,%s" % (doc.id, doc.touch_time()) for doc in docs])

class response (object):

    def __init__(self, request, content, repo, logged_in = False):
	self.request = request
        self.logged_in = logged_in
        self.repo = repo
        path, params, query, fragment = request.split_uri()
        self.request_path = path
        self.content = content
        self.callers_idea_of_service = get_header(HOST_HEADER, request.header)
        self.user_agent = get_header (USER_AGENT, request.header)
        accepts = get_header(ACCEPTS_HEADER, request.header)
        self.xml_request = accepts and (accepts.lower().strip() == "application/xml")
	self.fp = None
        self.request['Cache-Control'] = "no-store"

    def open (self, content_type = "text/html"):
	self.fp = request_file_buffer(self.request, content_type)
        #add_last_modified_headers(self.request, self.repo)
	return self.fp

    def redirect (self, url):
	self.request['Location'] = (isinstance(url, unicode) and url.encode("ASCII", "replace")) or url
        self.request['Content-Length'] = 0
        self.request['Content-Type'] = "text/plain"
	self.request.reply_code = 302

    def error (self, code, message, content_type=None):
        if self.fp:
            self.fp.discard()
	self.request.reply_code = code
	self.request['Content-Type'] = content_type or (isinstance(message, unicode) and "text/html; charset=UTF-8") or "text/html"
        b = (isinstance(message, unicode) and message.encode("UTF-8", "replace")) or message
	self.request['Content-Length'] = len(b)
        add_last_modified_headers(self.request, self.repo)
        if (self.request.command != "HEAD" or (code/100 != 2)):
            self.request.push(b)

    def reply (self, message, content_type=None):
        # calls "error", so no need to check for unicode -- done in "error"
	self.error(200, message, content_type)

    def return_file (self, typ, path, delete_on_close=false, filename=None):
        stats = os.stat(path)
        if delete_on_close:
            fp = self_deleting_file(path, 'rb')
        else:
            fp = open(path, 'rb')
        self.request['Content-Type'] = (isinstance(typ, unicode) and typ.encode("ASCII", "replace")) or typ
        self.request['Content-Length'] = stats.st_size
        self.request['Last-Modified'] = http_date.build_http_date(stats.st_mtime)
        add_last_modified_headers(self.request, self.repo)
        if filename:
            filename = (isinstance(filename, unicode) and filename.encode("ASCII", "replace")) or filename
            self.request["Content-Disposition"] = "inline; filename=%s" % filename
        elif not delete_on_close:
            filename = os.path.split(path)[1]
            filename = (isinstance(filename, unicode) and filename.encode("ASCII", "replace")) or filename
            self.request["Content-Disposition"] = "inline; filename=%s" % filename
        if (self.request.command != "HEAD"):
            self.request.push(producers.file_producer(fp))

    def fork_request(self, fn, *args):
        note(3, "forking %s in new thread...", fn)
        id = uthread.start_new_thread(run_fn_in_new_thread, (self, fn, args),
                                      "handling request %s %s at %s" % (
                                          self.request.command, self.request_path, time.ctime()))
        raise ForkRequestInNewThread(id)

    def __del__(self):
	if self.fp: self.fp.close()


class error_handler (object):
    # has just one method, handle_data, which is called with the data
    # of a bad request.  It just throws away the data and signals the error.

    def __init__(self, errcode):
        self.errcode = errcode

    def handle_data (self, request, data):
        request.error(self.errcode)


class authentication_handler (object):
    # has just one method, handle_data, which is called with the data
    # of an unauthorized request.  It just throws away the data and
    # sends back the login page

    def handle_data (self, request, data):
        output_login_page(request)
        request.done()


def return_bits (request, bits, mime_type, status_code):
    request.reply_code = status_code
    request["Content-Type"] = mime_type
    request["Content-Length"] = len(bits)
    request.push(bits)


def _ignore_request_logging (x):
    pass

def _read_and_reset(f):
    data = f.read()
    f.seek(0)
    return data


class folder_handler (default_handler.default_handler):

    def __init__(self, filesystem, repository):

        default_handler.default_handler.__init__(self, filesystem)
        self.__repo__ = repository
        conf = configurator.default_configurator()
        if conf.get('no-caching'):
            self.allow_cache = False
        else:
            self.allow_cache = True
        self.version = repository.get_version()
        self.version = (isinstance(self.version, unicode) and self.version.encode("ASCII", "replace")) or self.version

    def set_content_type(self, filename, request):
        # override this to provide better types
        request['Content-Type'] = get_content_type(filename) or "application/octet-stream"

    def match(self, request):

        # only handle GET or HEAD requests for documents from the "docs/" or "html/" subdirectories

        if request.command not in ("GET", "HEAD"):
            return 0

        path, params, query, fragment = request.split_uri()

        # The clause, path.endswith("crossdomain.xml") in the next line allows an UpLib repository
        # to be used from the Flash/Flex system by adding a crossdomain.xml file as a sibling to the overhead/
        # directory.  (This is being used for Anna Wu's geocoding project in 2011)
        return (path[0:6] == "/docs/" or path[0:6] == "/html/" or path.endswith("crossdomain.xml"))

    def handle_request(self, request):

        request.handler = "folder"
        request['Server'] = "UpLib/%s" % self.version
        request.version = '1.0'         # stick with 1.0 for Medusa

        try:
            if not authorized(self.__repo__, request):
                output_login_page(request)
                request.done()
                return
        except:
            signal_python_exception(request, sys.exc_info(), None)
            request.done()
            return

        path, params, query, fragment = request.split_uri()

        if path.startswith("/html/") and (not path.startswith("/html/temp/")):
            # no need to re-fetch UpLib images or HTML or jar files or Javascript
            pass
        elif self.allow_cache:
            # no need to re-fetch doc images or HTML
            request['Expires'] = my_http_date(time.gmtime(time.time() + ONE_YEAR))
        else:
            # dynamic content
            request['Cache-Control'] = 'no-store'
            # we also need to remove the request's If-Modified-Since header (if any)
            # to use the default_handler's method
            ims = get_header_match (IF_MODIFIED_SINCE, request.header)
            while (ims):
                request.header.remove(ims.string)
                note(0, "removed If-Modified-Since header <<%s>>", ims.string.strip())
                ims = get_header_match (IF_MODIFIED_SINCE, request.header)

        try:
            # we check to see if this request is on a document.  If so, it may
            # need special handling
            m = DOCPATH.match(path)
            if m:
                docid = m.group('docid')
                if self.__repo__.valid_doc_id(docid):
                    if TOUCHPATH.match(path):
                        self.__repo__.touch_doc(docid)
                    # we check to see if the file exists.  If not, we invoke the document
                    # object's method to fetch it
                    if ((not os.path.exists(os.path.join(self.__repo__.docs_folder(), path[6:]))) or
                        path[5:].endswith("/contents.txt") or
                        path[5:].endswith("/summary.txt") or
                        path[5:].endswith("/metadata.txt")):
                        doc = self.__repo__.get_document(docid)
                        bits, mime_type = doc.get_requested_part(path, params, query, fragment)
                        if bits:
                            return_bits(request, bits, mime_type, 200)
                            request.done()
                            return
            p = os.path.join(self.__repo__.root(), path[1:])
            if os.path.exists(p):
                filename = os.path.split(p)[1]
                filename = (isinstance(filename, unicode) and filename.encode("ASCII", "replace")) or filename
                request["Content-Disposition"] = "inline; filename=%s" % filename
                default_handler.default_handler.handle_request(self, request)
            else:
                note("Didn't find %s", p)
                request.error(404)
        except:
            signal_python_exception(request, sys.exc_info(), None)
            request.done()
            return

        def set_content_type(self, filename, request):
            request['Content-Type'] = get_content_type(filename) or "application/octet-stream"

class ping_handler (default_handler.default_handler):

    def __init__(self, repository, conf):

        self.__repo__ = repository
        self.hit_counter = counter()
        self.login_counter = counter()
        self.allow_insecure_cookies = conf.get_bool("allow-insecure-login-cookies", false)
        self.version = repository.get_version()

    IDENT = "UpLib Ping Handler"

    def status (self):
        return producers.simple_producer (
                '<li>%s' % status_handler.html_repr (self)
                + '<ul>'
                + '  <li><b>Total Hits:</b> %s'                 % self.hit_counter
                + '  <li><b>Logins Handled:</b> %s'             % self.login_counter
                + '</ul>'
                )

    def match(self, request):

        # only handle GET "/ping" or POST "/login" or GET "/favicon"

        return ((request.command == "GET" and request.uri == "/ping") or
                (request.command == "GET" and request.uri == "/html/signedreadup.jar") or
                (request.command == "HEAD" and request.uri == "/html/signedreadup.jar") or
                (request.command == "GET" and request.uri == "/html/images/ReadUpJWS.gif") or
                (request.command == "HEAD" and request.uri == "/html/images/ReadUpJWS.gif") or
                (request.command == "GET" and request.uri == "/favicon.ico") or
                (request.command == "POST" and request.uri == "/login"))

    def handle_request (self, request):

        request['Server'] = "UpLib/%s" % self.version
        request.version = '1.0'         # stick with 1.0 for Medusa

        if request.uri == "/ping":
            # too many things pinging us, turn off logging of ping
            request.log = _ignore_request_logging
            add_last_modified_headers(request, self.__repo__)
            request.error(200)
            return
        elif request.uri == "/login":
            handler = self
        elif request.uri == "/favicon.ico":
            handler = self
        elif request.uri == "/html/signedreadup.jar":
            handler = self
        elif request.uri == "/html/images/ReadUpJWS.gif":
            handler = self
        else:
            handler = error_handler(400)

        self.hit_counter.increment()

        cl = get_header (CONTENT_LENGTH, request.header)
        if cl:
            request.collector = data_collector (int(cl), request, handler)
            request.channel.set_terminator (None)
            # don't respond yet, wait until we've received the data...
        elif request.uri == "/favicon.ico":
            global FAVICON
            if not FAVICON:
                FAVICON = self.__repo__.get_favicon()
            if FAVICON:
                request.reply_code = 200
                request["Content-Type"] = "image/vnd.microsoft.icon"
                request["Content-Length"] = len(FAVICON)
                request.push(FAVICON)
                request.done()
            else:
                request.error(404)
        elif request.uri == "/html/signedreadup.jar":
            jarpath = os.path.join(self.__repo__.html_folder(), "signedreadup.jar")
            # simplest way to do this is to create a response object
            r = response(request, None, self.__repo__)
            if not os.path.exists(jarpath):
                request.error(404)
                return
            else:
                r.return_file("application/x-java-archive", jarpath)
                request.done()
        elif request.uri == "/html/images/ReadUpJWS.gif":
            imgpath = os.path.join(self.__repo__.html_folder(), "images", "ReadUpJWS.gif")
            # simplest way to do this is to create a response object
            r = response(request, None, self.__repo__)
            if not os.path.exists(imgpath):
                request.error(404)
                return
            else:
                r.return_file("image/gif", imgpath)
                request.done()
        else:
            request.error(400)

    def handle_data (self, request, dp):

        # only called for "/login"
        if request.uri != "/login":
            request.error(400)
            return

        self.login_counter.increment()

        if type(dp) == type(types.FileType):
            data = dp
        elif isinstance(dp, SelfDeletingFileObject):
            data = dp.open()
        elif isinstance(dp, StringIO):
            data = dp

        form = request_to_field_dict(request, data, None)
        note("form is %s", repr(form))
        data.close()

        r = self.__repo__

        if (authorized(r, request) or
            ((authorized is is_logged_in) and 
             form.has_key("password") and r.check_password(form.get("password")))):

            # OK, authorized, so set cookie and redirect to original URI
            cookie = r.new_cookie(str(request.header))

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
            note("request.channel.addr is %s, cookie_str is \"%s\"", request.channel.addr, cookie_str)
            request['Set-Cookie'] = cookie_str
            request['Cache-Control'] = "no-cache=\"set-cookie\""   # cf RFC 2109
            if form.has_key("originaluri"):
                request['Location'] = form["originaluri"]
            else:
                request['Location'] = "/"
            request.error(302)  # moved temporarily
        else:
            request.error(401)


############################################################
###
###  Class action_handler
###
###  Medusa handler to handle "/action" urls
###
############################################################

class action_handler (object):

    valid_commands = ("GET", "HEAD", "POST")

    def __init__(self, repository):

        self.__repo__ = repository
        self.hit_counter = counter()
        self.action_counter = counter()
        self.version = repository.get_version()

    def status (self):
        return producers.simple_producer (
                '<li>%s' % status_handler.html_repr (self)
                + '<ul>'
                + '  <li><b>Total Hits:</b> %s'                 % self.hit_counter
                + '  <li><b>Actions Performed:</b> %s'          % self.action_counter
                + '</ul>'
                )

    def match (self, request):
        # make sure the command is GET, HEAD, or POST:
        if request.command not in self.valid_commands:
            return 0

        path, params, query, fragment = request.split_uri()

        if '%' in path:
            path = unquote (path)

        request.angel_action = None

        if len(path) > 1:
            # strip off all leading slashes
            while path and path[0] == '/':
                path = path[1:]
            if path:
                parts = path.split('/')
                if len(parts) == 3 and parts[0] == 'action':
                    request.angel_action = (parts[1:], params, query, fragment)
                    return 1
                elif (len(parts)==4 and parts[0] == 'action' and parts[3][0:3]=='seq'):
                    note(2, "in match with 4 parts, parts = %s", str(parts))
                    request.angel_action = (parts[1:3], params, query, fragment)
                    return 1
                elif (len(parts) > 3) and (parts[0] == 'action') and (is_hierarchical_extension(parts[1])):
                    # to support extensions with hierarchical static elements, like GWT-generated UIs
                    note(4, "hierarchical request, parts = %s", str(parts))
                    request.angel_action = ((parts[1], '/'.join(parts[2:])), params, query, fragment)
                    return 1
                    
                else:
                  # This case occurs when the browser requests that an image
                  # be downloaded.  In that case parts look like:
                  # parts = ['docs', '01070-41-2044-555', 'thumbnails', '1.png']
                  pass

        elif path == '/':
            request.angel_action = (TOP_LEVEL_ACTION, params, query, fragment)
            return 1

        return 0


    def do_action (self, request, field_values, content):

        note(4, "in do_action (%s)", request.angel_action)

        global REPO_EXTENSION_DIRS, ALLOW_OLD_EXTENSIONS
        if not REPO_EXTENSION_DIRS:
            conf = configurator.default_configurator()
            REPO_EXTENSION_DIRS = PATH_SEPARATOR.join((
                os.path.join(self.__repo__.overhead_folder(), "extensions", "active"),
                os.path.join(conf.get('uplib-lib'), 'site-extensions')))
            ALLOW_OLD_EXTENSIONS = conf.get_bool("allow-old-extensions")

        module_name, function_name = request.angel_action[0]
        exception = None
        callable = None
        try:
            callable = find_action_function(module_name, function_name, self.__repo__.get_actions_path())
        except:
            t, v, b = sys.exc_info()
            exception = ''.join(traceback.format_exception(t, v, b))
            note(0, "find_action_function(%s/%s) raised an exception:\n%s", module_name, function_name, exception)
        if callable:
            try:
                self.action_counter.increment()
                if field_values == None: field_values = {}
                logged_in = is_logged_in(self.__repo__, request)
                resp = response(request, content, self.__repo__, logged_in)
                if module_name == 'basic' and function_name == 'repo_status_json':
                    # try not to log this call
                    request.log = _ignore_request_logging
                callable(self.__repo__, resp, field_values)
                return true
            except ForkRequestInNewThread, x:
                note(4, "forked off request")
                return false
            except Exception, x:
                note(0, "signalling exception <%s> at point 1a:", x)
                excn_data = sys.exc_info()
                signal_python_exception(request, excn_data)
#                 s2 = python_exception_html (excn_data, None)
#                 request.reply_code = 500
#                 request['Content-Type'] = 'text/html'
#                 request['Content-Length'] = len(s2)
#                 request.push(s2)
                return true
        else:
            # can't use request.error() here because request.done() will be called twice
            request.reply_code = 501
            action = htmlescape("/action/" + module_name + "/" + function_name)
            if exception:
                s = u"<html><head><title>Error loading module:  %s</title></head><body><p>Attempt to load module/function <i>%s/%s</i> raised an exception:\n<pre>%s</pre><p>(extensions path = [<tt>%s</tt>], sys.path = <tt>%s</tt>)</body></html>" % (action, module_name, function_name, exception, self.__repo__.get_actions_path(), htmlescape(str(sys.path)))
            else:
                s = u"<html><head><title>No such action:  %s</title></head><body><p>No such action:  %s.<br>actions path = [%s]</body></html>" % (action, action, self.__repo__.get_actions_path())
            s = s.encode("UTF-8", "replace")
            request['Content-Type'] = "text/html; charset=UTF-8"
            request['Content-Length'] = len(s)
            request.push(s)
            return true


    def handle_request (self, request):

        request['Server'] = "UpLib/%s" % self.version
        request.version = '1.0'         # stick with 1.0 for Medusa

        if request.command not in self.valid_commands:
            request.error (400) # bad request
            return

        self.hit_counter.increment()

        # note(0, "request is %s (%s):\n%s", request.command, request.uri, request.header);

        request.handler = "action"

        try:
            if not authorized(self.__repo__, request):
                handler = authentication_handler()
                # note(0, "not authorized")
            else:
                handler = self
        except:
            fakefile = StringIO()
            traceback.print_exc(None, fakefile)
            s = fakefile.getvalue()
            fakefile.close()
            request['Content-Type'] = "text/plain"
            request['Content-Length'] = len(s)
            request.reply_code = 500
            request.push(s)
            request.done()
            return

        # check for payload
        query = request.angel_action[2]
        cl = get_header (CONTENT_LENGTH, request.header)
        if cl:

            note(4, "content-length is %s", cl)
            request.collector = data_collector (int(cl), request, handler)

            # no terminator while receiving POST data
            request.channel.set_terminator (None)

            # don't respond yet, wait until we've received the data...

        elif (handler != self):

            output_login_page(request)
            request.done()

        elif request.command == 'HEAD' and not (request.uri.endswith(".jnlp") or request.uri.endswith(".jar")):
            # we don't do HEAD requests on /action methods, so send back 405
            # but allow head on .jnlp files
            request['Allow'] = "GET, POST"
            request.reply_code = 405
            request.done()
            return

        else:

            try:
                if query:
                    # there's a query, so process it
                    dict = request_to_field_dict (request, None, request.angel_action[2])
                    if self.do_action(request, dict, None):
                        request.done()

                else:
                    if self.do_action(request, None, None):
                        request.done()
            except:
                note("signalling exception in data-free request handler:\n%s", "".join(traceback.format_exception(*sys.exc_info())))


    def handle_data (self, request, dp):

        # note(0, "handle_data:  %s, dp is %s, command is %s", request, dp, request.command)

        if type(dp) == type(types.FileType):
            data = dp
        elif isinstance(dp, SelfDeletingFileObject):
            data = dp.open()
        elif isinstance(dp, StringIO):
            data = dp

        if request.command == 'HEAD' and not (request.uri.endswith(".jnlp") or request.uri.endswith(".jar")):
            # we don't do HEAD requests on /action methods, so send back 405
            data.close()
            request['Allow'] = "GET, POST"
            request.reply_code = 405
            request.done()
            return

        stat = true
        try:
            ct = get_header (CONTENT_TYPE, request.header)
            if (ct and (ct.strip().startswith("multipart/form-data") or
                        ct.strip().startswith("application/x-www-form-urlencoded"))):
                #note(5, "processing %s; headers are:\n%s\ndata is\n<%s>\n", ct, request.header, _read_and_reset(data))
                form = request_to_field_dict(request, data, request.angel_action[2])
                data.close()
                data = None
            else:
                form = request_to_field_dict(request, None, request.angel_action[2])

            # for key in form.keys():
            #    value = form[key]
            #    note(3, "field %s: <%s>", key, value[:min(50, len(value))])

            stat = self.do_action(request, form, data)
            if data:
                data.close()

        except:
            info = sys.exc_info()
            signal_python_exception(request, info)

        if stat:
            request.done()


class data_collector (object):
    def __init__ (self, length, request, callback):
        self.collected_data     = ""
        self.length             = length
        self.request    = request
        self.bytes_in   = 0
        if length > (1 << 20):
            self.filename = tempfile.mktemp()
            self.fp = open(self.filename, 'wb+')
        else:
            self.filename = None
            self.fp = StringIO()
        self.callback_obj = callback

    def collect_incoming_data (self, data):
        ld = len(data)
        bi = self.bytes_in
        if (bi + ld) >= self.length:
            # last bit of data
            self.fp.write(data[:(self.length - bi)])

            # do some housekeeping
            r = self.request
            ch = r.channel
            ch.current_request = None
            # set the terminator back to the default
            ch.set_terminator ('\r\n\r\n')
            self.fp.seek(0, 0)
            if self.filename:
                self.fp.close()
                fileobj = SelfDeletingFileObject(self.filename)
            else:
                fileobj = self.fp
            self.callback_obj.handle_data(r, fileobj)
            # avoid circular reference
            del self.request
        else:
            self.fp.write(data)
            self.bytes_in = self.bytes_in + ld

    def found_terminator (self):
        # shouldn't be called
        pass

############################################################
###
###  Class thread_safe_rotating_file_logger
###
###  Wrap a lock around the write calls, and the call
###  to rotate the file log
###
############################################################

class thread_safe_rotating_file_logger(logger.rotating_file_logger):

    def __init__(self, file, freq=None, maxsize=None, flush=1, mode='a'):
        logger.rotating_file_logger.__init__(self, file, freq=freq, maxsize=maxsize, flush=flush, mode=mode)
        self.lock = uthread.allocate_lock()

    def rotate (self):
        self.lock.acquire()
        try:
            logger.rotating_file_logger.rotate(self)
        finally:
            self.lock.release()

    def write (self, data):
        self.lock.acquire()
        try:
            logger.rotating_file_logger.write(self, data)
        finally:
            self.lock.release()

    def writeline (self, line):
        self.lock.acquire()
        try:
            logger.rotating_file_logger.writeline(self, line)
        finally:
            self.lock.release()

    def writelines (self, lines):
        self.lock.acquire()
        try:
            logger.rotating_file_logger.writelines(self, lines)
        finally:
            self.lock.release()

    def flush (self):
        self.lock.acquire()
        try:
            logger.rotating_file_logger.flush(self)
        finally:
            self.lock.release()
