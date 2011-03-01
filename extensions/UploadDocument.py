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
"""
This module provides a Web-based interface that allows uploading of documents
to a repository without using the normal client-side UpLib programs.
It runs the ``uplib-add-document`` program on the server as a subprocess under the repository daemon.

From a Web browser, use `upload` to obtain a Web page to upload a document with,
or `addnote` to get a form to add some text as a 3x5 card to the repository.
The `help` page also provides a bookmarklet you can add to a
browser's bookmark bar to quickly capture the current page to the
repository.

Programs can call `add` via HTTP to add documents to the repository.

:author: Bill Janssen
:author: Randy Gobbel
:author: Ken Pier
"""
__docformat__ = "restructuredtext"
__version__ = "$Revision: 1.37 $"


import sys, os, tempfile, time, string, traceback, shutil, re, urllib, StringIO, pipes, itertools

from uplib.plibUtil import note, uthread, configurator, subproc, get_fqdn, Job, get_note_sink, read_metadata
from uplib.webutils import HTTPCodes, htmlescape, Cache
from uplib.addDocument import CONTENT_TYPES, calculate_originals_fingerprint
from uplib.basicPlugins import STANDARD_BACKGROUND_COLOR, SWIRLIMG, SWIRLSPACER, JOBS_JAVASCRIPT, STANDARD_TOOLS_COLOR

_conf = configurator.default_configurator()
_uplib_add_document = _conf.get("uplib-add-program")
_use_http = _conf.get_bool("use-http", False)
del _conf

_BOOKMARKLET_PATTERN = re.compile(r'<script\s[^>]*id="KeepUp"[^>]*></script>')
_ADD_FORM_PATTERN = re.compile(r'<form.*?/action/UploadDocument/add.*?>.*?</form>', re.IGNORECASE | re.DOTALL)

def _rewrite_job_output (ostream, content):
    Job.JOB_TABLE_LOCK.acquire()
    ostream.seek(0, 0L)
    ostream.truncate()
    ostream.write(content)
    Job.JOB_TABLE_LOCK.release()

class _OurCacher (Cache):

    def __init__(self, url, filename=None, bits=None, content_type=None):
        Cache.__init__(self, url, filename=filename, bits=bits, content_type=content_type)

    # we don't want to pull our own bookmark...

    def scan_nested_content(self):
        Cache.scan_nested_content(self)
        for url in self.nested_content.keys():
            host, port, upath = parse_URL(url)
            if upath.startswith("/action/UploadDocument/"):
                del self.nested_content[url]


def _first (seq, pred):
    "Returns True if pred(x) is true for at least one element in the iterable"
    for elem in itertools.ifilter(pred, seq):
        return elem
    return None


def _add_internal (ostream, percent_done_fn, repo, response, params, content, wait):

    # this can be called in several different ways.
    # In general, you post a multipart/form-data body which
    # contains a "contenttype" for the document, and either a "URL"
    # for the content, or a "content" parameter containing the
    # the actual content.  If both "URL" and "content" are present,
    # the URL is added as the "original-url" value for the metadata,
    # and if the content is HTML, it's used as the "original.html"
    # and the URL is used to pull ancillary content referenced in it.

    content_type = params.get("contenttype")
    url = params.get("URL")
    noredir = params.get("no-redirect")
    noredir = noredir and (noredir.lower() == "true")
    uploadloc = url
    docname = params.get("documentname")
    tempf = None
    suppress_duplicates = params.get("suppress-duplicates")
    suppress_duplicates = suppress_duplicates and (suppress_duplicates.lower() == "true")
    bury = params.get("bury")
    bury = bury and (bury.lower() == "true")
    verbosity = int(params.get("verbosity") or "0")
    if content:
        if wait and ostream:
            _rewrite_job_output(ostream, '{ state: 0, msg: "Caching page..."}')
        extension = CONTENT_TYPES.get(content_type)
        if not extension:
            if wait:
                msg = "Don't know what to do with contenttype \"%s\"" % content_type
                if ostream:
                    _rewrite_job_output(ostream, '{state: 1, msg: "' + urllib.quote(msg) + '"}')
                else:
                    response.error(HTTPCodes.UNSUPPORTED_MEDIA_TYPE, msg)
            return
        # special case HTML/XHTML
        if content and (content_type.lower() in ("text/html", "application/xhtml+xml")):
            tempf = tempfile.mkdtemp()
            uploadloc = os.path.join(tempf, "original.html")
            # make sure that the folder for other parts exists, even if empty
            os.mkdir(os.path.join(tempf, "original_files"))
            # remove our bookmarklet, if present
            content = _BOOKMARKLET_PATTERN.sub('', content)
            content = _ADD_FORM_PATTERN.sub('', content)
            c = _OurCacher(url, filename=uploadloc, bits=content, content_type=content_type)
            # make sure that the folder for other parts exists, even if empty
            other_parts = os.path.join(tempf, "original_files")
            if not os.path.exists(other_parts):
                os.mkdir(other_parts)
        # special case 3x5 cards
        elif (docname and (content_type.lower() == "text/plain") and os.path.splitext(docname)[1] == ".3x5"):
            fd, tempf = tempfile.mkstemp(".3x5")
            fp = os.fdopen(fd, "wb")
            fp.write(content)
            fp.close()
            uploadloc = tempf
        else:
            fd, tempf = tempfile.mkstemp("." + extension)
            fp = os.fdopen(fd, "wb")
            fp.write(content)
            fp.close()
            uploadloc = tempf
        if suppress_duplicates:
            hash = calculate_originals_fingerprint(tempf)
            results = repo.do_query("sha-hash:"+hash)
            if results:
                # it's a duplicate
                doc = results[0][1]
                if os.path.isdir(tempf):
                    shutil.rmtree(tempf)
                elif os.path.exists(tempf):
                    os.remove(tempf)
                if ostream:
                    _rewrite_job_output(ostream, '{ state: 2, doc_id: "' + doc.id + '"}')
                elif noredir:
                    response.reply(doc.id, "text/plain")
                else:
                    response.redirect("/action/basic/dv_show?doc_id=%s" % doc.id)
                return
    try:
        try:
            # get a cookie for authentication
            cookie = repo.new_cookie(url or content[:min(100, len(content))])
            cookie_str = '%s=%s; path=/; Secure' % (cookie.name(), cookie.value())
            os.environ["UPLIB_COOKIE"] = cookie_str
            doctitle = params.get("md-title")
            docauthors = params.get("md-authors")
            docdate = params.get("md-date")
            doccats = params.get("md-categories")
            metadata = params.get("metadata")
            if metadata:
                mdtmpfile = tempfile.mktemp()
                open(mdtmpfile, "w").write(metadata)
                # check to see if we're replacing an existing document
                md2 = read_metadata(StringIO.StringIO(metadata))
                existing_doc_id = md2.get("replacement-contents-for")
                if existing_doc_id and not repo.valid_doc_id(existing_doc_id):
                    raise ValueError("Invalid doc ID %s specified for replacement" % existing_doc_id)
            else:
                mdtmpfile = None
                existing_doc_id = None
            # now form the command
            scheme = ((repo.get_param("use-http", "false").lower() == "true") or _use_http) and "http" or "https"
            cmd = '%s --verbosity=%s --repository=%s://127.0.0.1:%s ' % (_uplib_add_document, verbosity, scheme, repo.port())
            if doctitle:
                cmd += ' --title=%s' % pipes.quote(doctitle)
            if docauthors:
                cmd += ' --authors=%s' % pipes.quote(docauthors)
            if docdate:
                cmd += ' --date="%s"' % docdate
            if doccats:
                cmd += ' --categories=%s' % pipes.quote(doccats)
            if mdtmpfile:
                cmd += ' --metadata="%s"' % mdtmpfile
            cmd += ' "%s"' % uploadloc
            if ostream:
                _rewrite_job_output(ostream, '{state: 0, msg: "' + urllib.quote(cmd) + '"}')
            # and invoke the command
            status, output, tsignal = subproc(cmd)
            note(4, "cmd is %s, status is %s, output is %s", repr(cmd), status, repr(output.strip()))
            if mdtmpfile:
                os.unlink(mdtmpfile)
            if status == 0:
                # success; output should be doc-id
                doc_id = existing_doc_id or output.strip().split()[-1]
                note(4, "output is '%s'; doc_id for new doc is %s", output.strip(), doc_id)
                if wait and ostream:
                    _rewrite_job_output(ostream, '{ state: 1, doc_id: "' + doc_id + '", msg: "' + urllib.quote(output) + '"}')
                # wait for it to come on-line
                if percent_done_fn:
                    percent_done_fn(40)         # estimate 40% of work done on client side
                while not repo.valid_doc_id(doc_id):
                    if ostream:
                        pending = repo.list_pending(full=True)
                        s = _first(pending, lambda x: x['id'] == doc_id)
                        if not s:
                            break
                        dstatus = s['status']
                        if dstatus == 'error':
                            msg = 'server-side error incorporating document'
                            _rewrite_job_output(ostream, '{ state: 3, doc_id: "' + doc_id
                                                + '", msg: "' + urllib.quote(s['error']) + '"}')
                            break
                        if dstatus == 'unpacking':
                            msg = 'starting ripper process...'
                        elif dstatus == 'ripping':
                            msg = "ripping with ripper '" + s['ripper'] + "'..."
                        elif dstatus == 'moving':
                            msg = 'adding to registered document set...'
                        _rewrite_job_output(ostream, '{ state: 1, doc_id: "' + doc_id
                                            + '", msg: "' + urllib.quote(msg) + '"}')
                    time.sleep(1.0)
                if percent_done_fn:
                    percent_done_fn(100)        # finished
                if repo.valid_doc_id(doc_id):
                    if bury:
                        # wait up to 100 seconds for it to show up in history list
                        # after that, wait another second, then bury it
                        counter = 100
                        while counter > 0:
                            h = [x.id for x in repo.history()]
                            if doc_id in h:
                                break
                            counter -= 1
                            time.sleep(1)
                        time.sleep(1)
                        repo.touch_doc(doc_id, bury=True, notify=False)
                        note(3, "buried %s", doc_id)
                    if wait:
                        if ostream:
                            _rewrite_job_output(ostream, '{ state: 2, doc_id: "' + doc_id + '"}')
                        elif noredir:
                            response.reply(doc_id, "text/plain")
                        else:
                            response.redirect("/action/basic/dv_show?doc_id=%s" % doc_id)
            else:
                note("cmd <<%s>> failed with status %s:\n%s", cmd, status, output)
                if wait:
                    if ostream:
                        _rewrite_job_output(ostream, '{ state: 3, msg: "' + urllib.quote('Error processing the document:\n' + output) + '"}')
                    else:
                        response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "<pre>" + htmlescape(output) + "</pre>")
        except:
            e = ''.join(traceback.format_exception(*sys.exc_info()))
            if wait:
                note(3, "Exception processing uplib-add-document request:\n%s", htmlescape(e))
                if ostream:
                    _rewrite_job_output(ostream, '{state: 3, msg: "' + urllib.quote("Exception processing uplib-add-document request:\n" + e) + '"}')
                else:
                    response.error(HTTPCodes.INTERNAL_SERVER_ERROR,
                                   "Exception processing uplib-add-document request:\n<pre>" +
                                   htmlescape(e) + "\n</pre>")
            else:
                note("Exception processing uplib-add-document request:\n%s", e)
    finally:
        if tempf and os.path.isfile(tempf):
            os.unlink(tempf)
        elif tempf and os.path.isdir(tempf):
            shutil.rmtree(tempf)


def add(repo, response, params):
    """
    Add a document to the repository, calling ``uplib-add-document`` in a subprocess.

    :param wait: optional, whether to wait for the incorporation and ripping to \
           happen.  If not specified, ``add`` returns immediately after starting \
           the incorporation process.  If specified as ``true``, ``add`` will wait \
           until the document is available in the repository.  If specified as ``watch``, \
           ``add`` will start a new ``Job`` which can be "watched" with the ``fetch_job_output`` \
           function in ``uplib.externalAPI``.  If specified as ``bounce``, and the ``URL`` \
           parameter is also specified, the incorporation \
           will be started, and ``add`` will immediately return an HTTP redirect to \
           the value of ``URL``.  If specified as ``watchexternal``, will start a new ``Job`` \
           and immediately return the Job ID as a text/plain string.
    :type wait: string containing either ``watch`` or ``true`` or ``bounce``
    :param content: the actual bits of the document.  One of either ``content`` or ``URL`` must be specified.
    :type content: byte sequence
    :param contenttype: the MIME type for the document content
    :type contenttype: string containing MIME type
    :param URL: the URL for the document.  One of either ``content`` or ``URL`` must be specified.
    :type URL: string
    :param documentname: the name of the document
    :type documentname: string
    :param no-redirect: if specified as ``true``, no redirect to the incorporated document \
           will be returned; instead, a document ID string as "text/plain" will be returned, \
           if ``wait`` is specified as ``true``.  Optional, defaults to "false".
    :type no-redirect: boolean
    :param bury: optional, defaults to "false", if specified as "true" will cause \
           the newly added document to be "buried" in the history list, so that it \
           won't show up in the most-recently-used listing, as it normally would
    :type bury: boolean
    :param md-title: title to put in the document metadata
    :type md-title: string
    :param md-authors: standard UpLib authors line (" and "-separated) to put in the document metadata
    :type md-authors: string
    :param md-date: standard UpLib date ([MM[/DD]/]YYYY) to put in the document metadata
    :type md-date: string
    :param md-categories: standard UpLib categories string (comma-separated category names) to put in the document metadata
    :type md-categories: string
    :param metadata: contents of a standard UpLib metadata.txt file.  If this file is provided, \
           it is typically just passed unchanged to ``uplib-add-document``.  However, it is \
           inspected for the metadata element ``replacement-contents-for``, and if that is found, \
           ``add`` will check to see that the specified document ID is still valid in that repository.
    :type metadata: string containing "text/rfc822-headers" format data
    :returns: depends on what parameters are passed.  If ``wait`` is specified as ``true`` and ``no-redirect`` \
              is specified as ``true``, will simply wait until the document has been incorporated and \
              return the document ID as a plain text string.  If ``no-redirect`` is not specified, \
              and ``wait`` is ``true``, will return an HTTP redirect to the new document in the repository. \
              If ``wait`` is specified as ``bounce``, will return an immediate redirect to the original \
              URL for the document.  If ``wait`` is not specified, will simply immediately return an HTTP \
              200 (Success) code and a non-committal message.
    :rtype: various
    """

    wait = params.get("wait")
    content = params.get("content")
    url = params.get("URL")
    docname = params.get("documentname")
    if content and (not params.get("contenttype")):
        note(3, "add:  No contenttype specified.");
        response.error(HTTPCodes.BAD_REQUEST, "No contenttype specified")
        return
    if (not content) and (not url):
        note(3, "add:  Neither content nor URL specified.");
        response.error(HTTPCodes.BAD_REQUEST, "Nothing to upload!")
        return
    
    if wait and (wait.lower() in ("watch", "watchexternal")):
        job = Job(_add_internal, repo, None, params, content, True)
        note(3, "job id is %s", job.id)
        if url:
            title = htmlescape(url)
        elif docname:
            title = htmlescape(docname)
        else:
            title = 'document'
        if (wait.lower() == "watchexternal"):
            response.reply(job.id, "text/plain")
        else:
            fp = response.open()
            fp.write('<head><title>Adding %s to repository...</title>\n' % title)
            fp.write('<script type="text/javascript" language="javascript" src="/html/javascripts/prototype.js"></script>\n')
            fp.write(JOBS_JAVASCRIPT)
            fp.write('</head><body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
            fp.write('<p style="background-color: %s;"><span id="swirl">%s</span> <span id="titlespan">Adding <b>%s</b>...</span></p>\n' % (
                STANDARD_TOOLS_COLOR, SWIRLIMG, title))
            fp.write('<p id="progressreport"></p>\n')
            fp.write('<script type="text/javascript">\n'
                     'function report_error (req) {\n'
                     '  // alert("Can\'t check status of job");\n'
                     '}\n'
                     'function update_progress_report(jobid, percent_done, update_text) {\n'
                     '  // alert("update_text is " + update_text);\n'
                     '  var state = eval("(" + update_text + ")");\n'
                     '  // alert("state is " + state);\n'
                     '  if (percent_done >= 100) {\n'
                     '     $("swirl").innerHTML = \'' + SWIRLSPACER + '\';\n'
                     '     $("titlespan").innerHTML = "Finished adding ' + title + '.";\n'
                     '  }\n'
                     '  if (state.state == 2) {\n'
                     '    $("progressreport").innerHTML = \'Finished.\\n<p>Click here <a href="/action/basic/dv_show?doc_id=\' + unescape(state.doc_id) + \'"><img src="/docs/\' + unescape(state.doc_id) + \'/thumbnails/first.png" border=0></a> to open the document in the UpLib browser viewer.\';\n'
                     '  } else if (state.state == 0) {\n'
                     '    $("progressreport").innerHTML = "Extracting page images and text...";\n'
                     '  } else if (state.state == 1) {\n'
                     '    $("progressreport").innerHTML = "Finished client side, ID is " + unescape(state.doc_id) + "<br>" + unescape(state.msg);\n'
                     '  } else {\n'
                     '    $("progressreport").innerHTML = "Error:<br><pre>" + unescape(state.msg) + "</pre>";\n'
                     '  }\n'
                     '}\n'
                     'Jobs.monitor("' + job.id + '", update_progress_report, 3, report_error);\n'
                     '</script>\n')
            fp.write('</body>\n')
        return
        
    elif wait and (wait.lower() == "true"):
        response.fork_request(_add_internal, None, None, repo, response, params, content, True)
    else:
        uthread.start_new_thread(_add_internal, (None, None, repo, response, params, content, False),
                                 "UploadDocument:  adding %s" % (docname or url or time.ctime()))
        if url and (wait.lower() == "bounce"):
            response.redirect(url)
        else:
            response.reply("Started new thread to add document", "text/plain")

### TODO:  would be nice if "action/UploadDocument" could be dynamic somehow

_BOOKMARKLET = """javascript:void(q=document.body.appendChild(document.createElement('script')));void(q.language='javascript');void(q.type='text/javascript');void(q.src='%s://%s/action/UploadDocument/_bookmarklet?action=%s');void(q.id='KeepUp');"""

def help(repo, response, params):
    """
    Displays a help page for this extension.

    :return: a help page
    :rtype: text/html
    """

    # displays the help page, including a bookmarklet to use this code

    scheme = ((repo.get_param("use-http", "false").lower() == "true") or _use_http) and "http" or "https"
    fp = response.open()
    fp.write("<html><head><title>UploadDocument Help</title><head><body><h3>UploadDocument Help</h3>\n")
    fp.write("<p>Here's a bookmarklet that pushes the browser's cache of the page into UpLib"
             " and reloads the page:  <a href=\"%s\">KeepUp (reload)</a>\n"
             % (_BOOKMARKLET % (scheme, response.callers_idea_of_service, 'reload')))
    fp.write("<p>Here's a bookmarklet that pushes the browser's cache of the page into UpLib"
             " and opens a new window that tracks UpLib's incorporation of the page:  <a href=\"%s\">KeepUp (watch)</a>\n"
             % (_BOOKMARKLET % (scheme, response.callers_idea_of_service, 'watch')))
    fp.write('<p>Or, if you just want a page that lets you upload a file to the repository, with'
             ' some metadata, <a href="/action/UploadDocument/upload">click here</a>.\n')
    fp.write('<hr>'
             '<a href="/html/doc/api/UploadDocument-module.html" target=_blank>'
             "(Click here to open the API documentation for the 'UploadDocument' module in another window.)</a>"
             '</body></html>')
    fp.close()

def _bookmarklet (repo, response, params):

    # sends back the real Javascript code for the upload to UpLib

    action = params.get("action")
    verbosity = params.get("verbosity", "0")
    if action == 'reload':
        target = '_top'
        wait = 'bounce'
    elif action == 'watch':
        target = '_blank'
        wait = 'watch'
    else:
        target = '_blank'
        wait = 'false'
    scheme = ((repo.get_param("use-http", "false").lower() == "true") or _use_http) and "http" or "https"
    fp = response.open("text/javascript")
    fp.write("function showSaved (text) { alert('Saved. ' + text); };\n")
    fp.write("""function saveit(saddr) {
                var data = new String(document.documentElement.innerHTML);
                // data = data.replace('<script[^>]* id="KeepUp"[^>]*></script>', '');
                var form = document.body.appendChild(document.createElement('form'));
                form.action = '%s://' + saddr + '/action/UploadDocument/add';
                form.method = 'POST';
                form.target = '%s';
                var elt = form.appendChild(document.createElement('input'));
                elt.type = 'hidden';
                elt.name = 'contenttype';
                elt.value = 'text/html';
                elt = form.appendChild(document.createElement('input'));
                elt.type = 'hidden';
                elt.name = 'URL';
                elt.value = document.location;
                elt = form.appendChild(document.createElement('input'));
                elt.type = 'hidden';
                elt.name = 'wait';
                elt.value = '%s';
                elt = form.appendChild(document.createElement('input'));
                elt.type = 'hidden';
                elt.name = 'content';
                elt.value = data;
                elt = form.appendChild(document.createElement('input'));
                elt.type = 'hidden';
                elt.name = 'verbosity';
                elt.value = '%s';
                form.submit();
                if ('%s' != 'bounce') { document.remove(form); };
                }\n""" % (scheme, target, wait, verbosity, wait))
    fp.write("saveit('%s');\n" % response.callers_idea_of_service);
    fp.close()
    
def upload(repo, response, params):
    """
    Obtain a Web form which supports file upload from a Web browser.

    :returns:  a Web form supporting file upload
    :rtype: text/html
    """

    fp = response.open()
    fp.write('<html><head><title>Upload document to "%s"</title><head>\n' % htmlescape(repo.name()))
    fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
    fp.write('<script type="text/javascript" src="/html/javascripts/prototype.js"></script>\n')
    fp.write('<script type="text/javascript">\n'
             'var ext_to_content_type_mapping = {\n')
    for key in CONTENT_TYPES:
        fp.write('   "%s": "%s",\n' % (CONTENT_TYPES[key], key))
    fp.write('   };\n\n'
             'function choose_appropriate_type(filename) {\n'
             '  var ext = filename.split(".")[1];\n'
             '  for (var e in ext_to_content_type_mapping) {\n'
             '     if (e == ext)\n'
             '        return ext_to_content_type_mapping[e];\n'
             '  };\n'
             '  return "undefined";\n'
             '}\n\n'
             'function on_filename_change (e) {\n'
             '  var a = choose_appropriate_type(document.forms.uploadform.content.value);\n'
             '  document.forms.uploadform.contenttype.value = a;\n'
             '  document.forms.uploadform.documentname.value = document.forms.uploadform.content.value;\n'
             '}\n'
             '</script>\n')
    fp.write('<form enctype="multipart/form-data" id="uploadform" action="/action/UploadDocument/add" method="POST" target="_top">\n')
    fp.write('<input type=hidden name=wait value=watch>\n')
    fp.write('<input type=hidden name=documentname value="">\n')
    referer = response.request.get_header('referer')
    fp.write('<p>File to upload:  <input type="file" name=content size=50 value="%s"' % (referer or "") +
             '  onchange="{void(on_filename_change(this));}">\n')
    fp.write('<p>Content-Type of file: <select name="contenttype" size=1>\n')
    fp.write('<option value="undefined" selected>-- undefined --</option>\n')
    for key in CONTENT_TYPES:
        hkey = htmlescape(key)
        fp.write('<option value="%s">%s</option>\n' % (hkey, hkey))
    fp.write('</select>\n')
    fp.write('<p>Optional metadata for the document:<br><table>'
             '<tr><td>Title for document: </td><td><input type=text name="md-title" size=60></td></tr>\n'
             '<tr><td>Authors <i>(" and "-separated)</i>:  </td><td><input type=text name="md-authors" size=60></td></tr>\n'
             '<tr><td>Publication date <i>(mm/dd/yyyy)</i>: </td><td><input type=text name="md-date" size=60></td></tr>\n'
             '<tr><td>Categories <i>(comma-separated)</i>: </td><td><input type=text name="md-categories" size=60></td></tr>\n'
             '</table>\n')
    fp.write('<p><input type=submit name=submit value=submit>\n')
    fp.write('</form></body></html>\n')

def addnote(repo, response, params):
    """
    Obtain a Web form with which to add a note to the repository.  Useful
    for taking notes in meeting.

    :return: a Web form with which to add a note to the repository
    :rtype: text/html
    """
    

    # send back a note to upload

    fp = response.open()
    fp.write('<html><head><title>Add note to "%s"</title><head>\n' % htmlescape(repo.name()))
    fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
    fp.write('<form enctype="multipart/form-data" id="addnote" action="/action/UploadDocument/add" method="POST" target="_top">\n')
    fp.write('<input type=hidden name=wait value=true>\n')
    # add fake filename with 3x5 extension to trigger CardDoc parser
    fp.write('<input type=hidden name=documentname value="note.3x5">\n')
    fp.write('<input type=hidden name=contenttype value="text/plain">\n')
    fp.write('<p><input type=textarea name="content" value="" style="width: 100%; height: 50%;">\n')
    fp.write('<p><input type=submit name=submit value=submit>\n')
    fp.write('<p>Optional metadata for the document:<br><table>'
             '<tr><td>Categories <i>(comma-separated)</i>: </td><td><input type=text name="md-categories" size=60></td></tr>\n'
             '<tr><td>Title for document: </td><td><input type=text name="md-title" size=60></td></tr>\n'
             '<tr><td>Authors <i>(" and "-separated)</i>:  </td><td><input type=text name="md-authors" size=60></td></tr>\n'
             '</table>\n')
    fp.write('</form></body></html>\n')
