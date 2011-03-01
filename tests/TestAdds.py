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

import sys, os, re, time, tempfile, unittest, traceback, pprint, subprocess, inspect, urllib2, urlparse, urllib, cgi, zipfile, StringIO, types, shutil
from xml.etree.ElementTree import XML
import TestSupport

UPLIB_ADD_DOCUMENT = None
UPLIB_GET_DOCUMENT = None
UPLIB_MAKE_REPOSITORY = None
UPLIB_CHECK_ANGEL = None
UPLIB_POST_MULTIPART = None

def _rmtree(top):
    # Delete everything reachable from the directory named in 'top',
    # assuming there are no symbolic links.
    # CAUTION:  This is dangerous!  For example, if top == '/', it
    # could delete all your disk files.
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

def _remove_repository(repodir):
    if sys.platform == "win32":
        port = int(open(os.path.join(repodir, "overhead", "angel.port")).read().strip())
        servicename = "UpLibGuardianAngel_%s" % port

        # need to actually remove the repository service

        p = subprocess.Popen("sc stop %s" % servicename,
                             stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        returncode = p.wait()
        # we don't really care if this worked
        del p

        p = subprocess.Popen("sc delete %s" % servicename,
                             stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        returncode = p.wait()
        if returncode != 0:
            sys.stderr.write("Error %s deleting service %s:\n" % (returncode, servicename))
            sys.stderr.write(p.stdout.read())
    _rmtree(repodir)

def _encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields.items():
        if isinstance(key, unicode):
            key = key.encode("ASCII", "strict")
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        if isinstance(value, unicode):
            value = value.encode('UTF-8', 'strict')
            L.append('Content-Type: text/plain;charset=UTF-8')
        elif type(value) in types.StringTypes:
            L.append('Content-Type: application/octet-stream')
        else:
            raise ValueError("field value for key '%s' must be a string type" % key)
        L.append('Content-Transfer-Encoding: binary')
        L.append('Content-Length: %d' % len(value))
        L.append('')
        L.append(value)
    if files:
        for fil in files:
            key = fil[0]
            if isinstance(key, unicode):
                key = key.encode("ASCII", "strict")
            filename = fil[1]
            if isinstance(filename, unicode):
                filename = filename.encode("Latin-1", "strict")
            if len(fil) > 2:
                value = fil[2]
                if isinstance(value, unicode):
                    value = value.encode("UTF-8", "strict")
            else:
                value = None
            if len(fil) > 3:
                content_type = fil[3]
            else:
                from uplib.webutils import get_content_type
                content_type = get_content_type(filename)
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, os.path.basename(filename)))
            L.append('Content-Type: %s' % content_type)
            if value:
                L.append('')
                L.append(value)
            else:
                L.append('Content-Transfer-Encoding: binary')
                L.append('')
                fp = open(filename, 'rb')
                L.append(fp.read())
                fp.close()
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body


class SubProcTest(unittest.TestCase):

    def __init__(self, methodName='runTest', password=None):
        unittest.TestCase.__init__(self, methodName=methodName)
        self.stdout = None
        self.stderr = None
        self.returncode = None
        self.command = None
        self.password = password

    def runSubProc(self, command):

        self.command = command
        env = os.environ.copy()
        if self.password:
            env["UPLIB_PASSWORD"] = self.password
        # on Windows, all env values must be either str or Unicode
        if sys.platform == "win32":
            for key, value in env.items():
                if isinstance(value, unicode):
                    value = value.encode("UTF-8", "strict")
                    env[key] = value
        p = subprocess.Popen(command, bufsize=2<<20, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                             env=env, shell=(sys.platform != "win32"))
        self.returncode = p.wait()
        self.stdout = p.stdout.read().strip()
        self.stderr = p.stderr.read().strip()
        return self.stdout

    def checkRunSuccess(self):
        if self.returncode != 0:
            self.fail("Invalid return status %d from '%s'.\n" % (self.returncode, self.command) +
                      "Stdout was:  %s\n" % self.stdout +
                      "Stderr was:  %s\n" % self.stderr)

    def waitFor(self, folder, timeout):
        while (timeout > 0):
            if not os.path.exists(folder):
                timeout -= 1
                time.sleep(1)
            else:
                break
        return (timeout > 0)


class FetchTest(unittest.TestCase):
    def __init__(self, repo_url, methodName='runTest', password=None):
        unittest.TestCase.__init__(self, methodName=methodName)
        self.password = password
        self.repo_url = repo_url
        o = urlparse.urlparse(repo_url)
        self.scheme = o.scheme
        self.host = o.hostname
        self.port = o.port or 80

    def break_headers(headers):
        # break up list of headers into a dictionary
        headers = map(cgi.parse_header, headers)
        d = {}
        for header, params in headers:
            i = header.index(':')
            key = header[:i].strip().lower()
            value = header[i+1:].strip()
            d[key] = (value, params)
        return d
    break_headers = staticmethod(break_headers)

    def https_post_multipart(host, port, selector, password=None, fields=None, files=None, ca_certs=None, certfile=None, keyfile=None, cookies=None, headers=None, method=None):
        """
        Post fields and files via https as multipart/form-data.
        FIELDS is a sequence of (name, value) elements for regular form fields.
        FILES is a sequence of (name, filename [, value]) elements for data to be uploaded as files.
        Return the server's response page.
        """
        from uplib.webutils import VerifiedHTTPS
        if fields or files:
            content_type, body = _encode_multipart_formdata(fields, files)
        else:
            content_type, body = None, None
        h = VerifiedHTTPS(host, port, ca_certs=ca_certs, cert_file=certfile, key_file=keyfile)
        if method is None:
            method = "POST"
        h.putrequest(method, selector)
        if password:
            h.putheader('Password', password)
        if headers:
            for name in headers:
                h.putheader(name, headers.get(name))
        if cookies:
            for cookie in cookies:
                h.putheader('Cookie', cookie)
        if body:
            h.putheader('Content-Type', content_type)
            h.putheader('Content-Length', str(len(body)))
        h.endheaders()
        if body:
            h.send(body)
        errcode, errmsg, headers = h.getreply()
        return errcode, errmsg, headers, h.file and h.file.read()
    https_post_multipart = staticmethod(https_post_multipart)

    def http_post_multipart(host, port, selector, password=None, fields=None, files=None, ca_certs=None, certfile=None, keyfile=None, cookies=None, headers=None, method=None):
        """
        Post fields and files to an http host as multipart/form-data.
        FIELDS is a sequence of (name, value) elements for regular form fields.
        FILES is a sequence of (name, filename [, value]) elements for data to be uploaded as files.
        Return the server's response page.
        """
        import httplib
        if fields or files:
            content_type, body = _encode_multipart_formdata(fields, files)
        else:
            content_type, body = None, None
        h = httplib.HTTP(host, port)
        if method is None:
            method = "POST"
        h.putrequest(method, selector)
        if password:
            h.putheader('Password', password)
        if headers:
            for name in headers:
                h.putheader(name, headers.get(name))
        if cookies:
            for cookie in cookies:
                h.putheader('Cookie', cookie)
        if body:
            h.putheader('Content-Type', content_type)
            h.putheader('Content-Length', str(len(body)))
        h.endheaders()
        if body:
            h.send(body)
        errcode, errmsg, headers = h.getreply()
        return errcode, errmsg, headers, h.file and h.file.read()
    http_post_multipart = staticmethod(http_post_multipart)

    def doFetch(self, action, parameters=None, headers=None, files=None, raise_http_errors=False, method=None):

        if method and (method.lower == "get"):
            url = urlparse.urljoin(self.repo_url, action)
            try:
                d = {}
                if parameters:
                    url = url + "?" + urllib.urlencode(parameters)
                if headers:
                    d.update(headers)
                if self.password: d["Password"] = self.password
                req = urllib2.Request(url, None, d)
                fh = urllib2.urlopen(req)
            except urllib2.HTTPError, x:
                if raise_http_errors:
                    raise x
                else:
                    code = x.code
                    url = x.filename
                    standard_message = x.msg
                    custom_message = x.read() or "no details provided"
                    self.fail("Can't fetch %s:\n  HTTP result code %s (%s):  %s" % (
                        url, code, standard_message, custom_message.strip()))
            except:
                self.fail("Can't fetch %s:\n%s" % (
                    url, ''.join(traceback.format_exception(*sys.exc_info()))))
            else:
                headers = FetchTest.break_headers(fh.info().headers)
                data = fh.read()
                fh.close()
                return data, headers
        else:
            if self.scheme == "https":
                errcode, errmsg, headers, result = FetchTest.https_post_multipart(
                    self.host, self.port, action, password=self.password, headers=headers,
                    fields=parameters, files=files, method=method)
            else:
                errcode, errmsg, headers, result = FetchTest.http_post_multipart(
                    self.host, self.port, action, password=self.password, headers=headers,
                    fields=parameters, files=files, method=method)
            if errcode == 200:
                headers = FetchTest.break_headers(headers.headers)
                return result, headers
            elif raise_http_errors:
                raise urllib2.HTTPError(urlparse.urljoin(self.repo_url, action),
                                        errcode, errmsg, headers, StringIO.StringIO(result))
            else:
                self.fail("Can't fetch %s:\n  HTTP result code %s (%s):  %s" % (
                    urlparse.urljoin(self.repo_url, action), errcode, errmsg, result.strip()))


class TestAdds (SubProcTest):

    def __init__(self, repo_url, directory, docsmapping, methodName='testPNG', password=None, hierarchical=False):
        SubProcTest.__init__(self, methodName=methodName, password=password)
        self.url = repo_url
        self.directory = directory
        self.docsmapping = docsmapping
        self.hierarchical = hierarchical

    def _doc_folder(self, id):
        if self.hierarchical:
            return os.path.join(self.directory, "docs", *id.split("-"))
        else:
            return os.path.join(self.directory, "docs", id)

    def testPNG (self):
        """Test add of PNG file"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/uplib-logo.png" %
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.strip().split()
        self.assert_(docname == "docs/uplib-logo.png")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testPNG'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 10))          # appears within 10 seconds
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "uplib-logo.png")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "image/png")
        self.assertEquals([int(x) for x in md.get("images-size").strip().split(",")], [256, 256])
        self.assertEquals(int(md.get("images-dpi").strip()), 72)

    def testBMP (self):
        """Test add of Windows NT BMP file -- should fail"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/uplib-logo.bmp"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.assert_(self.returncode != 0)

    def testJPEG (self):
        """Test add of JPEG file"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/uplib-logo.jpg"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/uplib-logo.jpg")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testJPEG'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 10))          # appears within 10 seconds
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "uplib-logo.jpg")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "image/jpeg")
        self.assertEquals([int(x) for x in md.get("images-size").strip().split(",")], [256, 256])
        self.assertEquals(int(md.get("images-dpi").strip()), 75)

    def testJPEG2000 (self):
        """Test add of JPEG 2000 file"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/uplib-logo.jp2"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/uplib-logo.jp2")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testJPEG2000'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 10))          # appears within 10 seconds
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "uplib-logo.jp2")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "image/jp2")
        self.assertEquals([int(x) for x in md.get("images-size").strip().split(",")], [256, 256])
        self.assertEquals(int(md.get("images-dpi").strip()), 75)

    def testGIF (self):
        """Test add of GIF file"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/uplib-logo.gif"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/uplib-logo.gif")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testGIF'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 10))          # appears within 10 seconds
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "uplib-logo.gif")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "image/gif")
        self.assertEquals([int(x) for x in md.get("images-size").strip().split(",")], [256, 256])
        self.assertEquals(int(md.get("images-dpi").strip()), 75)

    def testTIFF (self):
        """Test add of TIFF file"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/uplib-logo.tiff"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/uplib-logo.tiff")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testTIFF'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 10))          # appears within 10 seconds
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "uplib-logo.tiff")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "image/tiff")
        self.assertEquals([int(x) for x in md.get("images-size").strip().split(",")], [256, 256])
        self.assertEquals(int(md.get("images-dpi").strip()), 75)

    def testWebPageComplete (self):
        """Test add of Mozilla "web page complete" cache of UpLib web page"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/UpLib.html"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/UpLib.html")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testWebPageComplete'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 30))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "UpLib.html")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "text/html")

    def testWebPageDirect (self):
        """Test add of the UpLib web page from http://uplib.parc.com/"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword http://uplib.parc.com/"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "http://uplib.parc.com/")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testWebPageDirect'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 30))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "original.html")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "text/html")

    def testPDF (self):
        """Test add of PDF file"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/testpage.pdf"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/testpage.pdf")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testPDF'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 30))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "testpage.pdf")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "application/pdf")

    def testText (self):
        """Test add of plain text file"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc('%s --verbosity=0 --repository=%s --nopassword docs/testpage.txt' %
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/testpage.txt")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testText'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 30))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "testpage.txt")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "text/plain")

    def testMP3 (self):
        """Test add of MP3 file"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/elephant-trumpeting.mp3"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/elephant-trumpeting.mp3")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testMP3'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 30))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "elephant-trumpeting.mp3")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "audio/mpeg")

    def testPython (self):
        """Test add of Python file"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=2 --repository=%s --nopassword ./TestSupport.py"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split('\n')[-1].split()
        self.assert_(docname == "./TestSupport.py")
        self.assert_(DOC_ID_RE.match(docid))
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 30))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "TestSupport.py")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "text/x-python")
        self.docsmapping['testPython'] = docid

    def testJava (self):
        """Test add of Java file"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword ../java/testClass.java"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "../java/testClass.java")
        self.assert_(DOC_ID_RE.match(docid))
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 20))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "testClass.java")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "text/x-java")
        self.docsmapping['testJava'] = docid

    def testEmailWithAttachment (self):
        """Test add of email with an attached photo"""
        global DOC_ID_RE, subproc, read_metadata, read_file_handling_charset
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/email-with-attached-picture.eml"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/email-with-attached-picture.eml")
        self.assert_(DOC_ID_RE.match(docid))
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 30))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "email-with-attached-picture.eml")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "message/rfc822")
        self.assertEquals(md.get("email-from-address"), "janssen@uplib.parc.com")
        self.assertEquals(md.get("email-from-name"), "Bill Janssen")
        self.assertEquals(md.get("email-message-id"), "<DE0F9A3C-1D54-47F3-B782-612FA7DA6937@parc.com>")
        # check contents
        contents_path = os.path.join(folder, "contents.txt")
        self.assert_(os.path.exists(contents_path))
        contents, charset, language = read_file_handling_charset(contents_path, True)
        self.assert_("Found " in contents)
        self.assert_("Bill" in contents)
        # self.assertEquals(charset, "utf8")    # not true for wkhtmltopdf
        self.assert_(language.startswith("en"))
        # check attachment
        attachmentid = [x.strip() for x in md.get("email-attachments").split(",")][0]
        afolder = os.path.join(self.directory, "docs", attachmentid)
        self.assert_(os.path.exists(afolder))
        amd = read_metadata(os.path.join(afolder, "metadata.txt"))
        self.assertEquals([int(x) for x in amd.get("images-size").strip().split(",")], [600, 600])
        self.assertEquals(amd.get("email-attachment-filename"), "NiceShotOfBuzzAldrinOnTheMoon.jpg")
        self.assert_(os.path.exists(os.path.join(afolder, "originals", "NiceShotOfBuzzAldrinOnTheMoon.jpg")))        
        # make sure link from attachment to email works, too
        self.assertEquals(amd.get("email-attachment-to").strip(), md.get("email-guid").strip())
        self.docsmapping['testEmailWithAttachment'] = docid


    def testMicrosoftWordMac2004 (self):
        """Test add of Microsoft Word file produced with Mac Office 2004"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/testpageMac2004.doc"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/testpageMac2004.doc")
        self.assert_(DOC_ID_RE.match(docid))
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 30))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "testpageMac2004.doc")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "application/msword")
        self.docsmapping['testMicrosoftWordMac2004'] = docid

    def testMicrosoftWordMac2008docx (self):
        """Test add of Microsoft Word file produced with Mac Office 2008 in docx format"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/testpageMac2008.docx"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/testpageMac2008.docx")
        self.assert_(DOC_ID_RE.match(docid))
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 30))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "testpageMac2008.docx")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.docsmapping['testMicrosoftWordMac2008docx'] = docid

    def testMicrosoftWordMac2008doc (self):
        """Test add of Microsoft Word file produced with Mac Office 2008"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --nopassword docs/testpageMac2008.doc"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/testpageMac2008.doc")
        self.assert_(DOC_ID_RE.match(docid))
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 30))
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "testpageMac2008.doc")))
        md = read_metadata(metadata_path)
        self.assertEquals(md.get("apparent-mime-type"), "application/msword")
        self.docsmapping['testMicrosoftWordMac2008doc'] = docid

    def testInvalidOptions (self):
        """Test add with an invalid uplib-add-document option"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --invalid-options --verbosity=0 --repository=%s --nopassword docs/uplib-logo.png"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.assert_(self.returncode != 0)

    def testAddFlags (self):
        """Test add flags (authors, title, date, categories)"""
        global DOC_ID_RE, subproc, read_metadata
        output = self.runSubProc("%s --verbosity=0 --repository=%s --title=\"Now is the time's we know\" --authors=\"Test Author\" --categories=\"cat1, cat2/cat3\" --date=\"12/3/2004\" --nopassword docs/uplib-logo.png"%
                                 (UPLIB_ADD_DOCUMENT, self.url))
        self.checkRunSuccess()
        docname, docid = output.split()
        self.assert_(docname == "docs/uplib-logo.png")
        self.assert_(DOC_ID_RE.match(docid))
        self.docsmapping['testAddFlags'] = docid
        folder = self._doc_folder(docid)
        self.assert_(self.waitFor(folder, 10))          # appears within 10 seconds
        metadata_path = os.path.join(folder, "metadata.txt")
        self.assert_(os.path.isdir(folder))
        self.assert_(os.path.exists(metadata_path))
        self.assert_(os.path.exists(os.path.join(folder, "originals", "uplib-logo.png")))
        md = read_metadata(metadata_path)
        self.assert_(md.get("title") == "Now is the time's we know")
        self.assert_(md.get("authors") == "Test Author")
        self.assert_(md.get("categories") == "cat1, cat2/cat3")
        self.assert_(md.get("date") == "12/3/2004")

class TestJava (SubProcTest):

    def __init__(self, repo_url, directory, docsmapping, methodName='testJava', password=None):
        SubProcTest.__init__(self, methodName=methodName, password=password)
        self.url = repo_url
        self.directory = directory
        self.docsmapping = docsmapping
        conf = configurator.default_configurator()
        self.java = conf.get("java")
        self.codedir = conf.get("uplib-code")
        self.classpathsep = conf.get("java-classpath-separator")

    def runJavaTest(self, args):
        output = self.runSubProc(('%s -classpath "%s/ShowDoc.jar%s." Tests %s ' % (
                    self.java, self.codedir, self.classpathsep, self.url)) + ' '.join([str(arg) for arg in args]))
        self.checkRunSuccess()
        return output

    def testRepo (self):
        """Try using the Java client to obtain some info about the repository"""
        output = self.runJavaTest(["repo",])
        self.assert_("0 categories" in output)

class TestSearches (SubProcTest):

    def __init__(self, repo_url, directory, docsmapping, methodName='testFindByText', password=None):
        SubProcTest.__init__(self, methodName=methodName, password=password)
        self.url = repo_url
        self.directory = directory
        self.docsmapping = docsmapping

    def flipMap(self):
        mp2 = {}
        for key, value in self.docsmapping.items():
            mp2[value] = key
        return mp2

    def testFindByType (self):
        """Test searching by MIME type"""
        if not self.docsmapping:
            self.fail("No documents were successfully added, so can't do a search!")
        mp = self.flipMap()
        expected_results=set([])
        if "testWebPageDirect" in self.docsmapping: expected_results.add("testWebPageDirect")
        if "testWebPageComplete" in self.docsmapping: expected_results.add("testWebPageComplete")
        if "testPython" in self.docsmapping: expected_results.add("testPython")
        if "testJava" in self.docsmapping: expected_results.add("testJava")
        if "testText" in self.docsmapping: expected_results.add("testText")
        output = self.runSubProc('%s --verbosity=0 --pickall --repository=%s --format=doc-id --nopassword "apparent-mime-type:text/*"' %
                                 (UPLIB_GET_DOCUMENT, self.url))
        self.checkRunSuccess()
        docs = set([mp.get(x.strip()) for x in output.split()])
        self.assertEqual(docs, expected_results)

    def testFindByText (self):
        """Test searching for some strings"""
        if not self.docsmapping:
            self.fail("No documents were successfully added, so can't do a search!")
        mp = self.flipMap()
        expected_results=set([])
        if "testWebPageDirect" in self.docsmapping: expected_results.add("testWebPageDirect")
        if "testWebPageComplete" in self.docsmapping: expected_results.add("testWebPageComplete")
        if expected_results:
            output = self.runSubProc('%s --verbosity=0 --pickall --repository=%s --format=doc-id --nopassword "UpLib"' %
                                     (UPLIB_GET_DOCUMENT, self.url))
            self.checkRunSuccess()
            docs = set([mp.get(x.strip()) for x in output.split()])
            self.assertEqual(docs, expected_results)
        expected_results=set([])
        if "testPython" in self.docsmapping: expected_results.add("testPython")
        if expected_results:
            output = self.runSubProc('%s --verbosity=0 --pickall --repository=%s --format=doc-id --nopassword "uplib True"' %
                                     (UPLIB_GET_DOCUMENT, self.url))
            self.checkRunSuccess()
            docs = set([mp.get(x.strip()) for x in output.split()])
            self.assertEqual(docs, expected_results)

class TestExternalAPI(FetchTest):

    # We don't test /action/externalAPI/upload_document, because that's already
    # exercised by adding documents to the repository with uplib-add-document

    def __init__(self, repo_url, docsmapping, methodName='testSearchRepository', password=None):
        FetchTest.__init__(self, repo_url, methodName=methodName, password=password)
        self.docsmapping = docsmapping

    def testSearchRepository(self):
        """Test of /action/externalAPI/search_repository"""

        data, headers = self.doFetch("/action/externalAPI/search_repository",
                                     { "query": 'categories:"_(all)_"' })
        assert(headers.get("content-type")[0] == "text/plain")
        # now with XML results
        data, headers = self.doFetch("/action/externalAPI/search_repository",
                                     { "query": 'categories:"_(all)_"', "format": "xml" })
        assert(headers.get("content-type")[0] == "application/xml")
        # TODO:  here, we should really parse the XML and see if the right fields are in there
        data, headers = self.doFetch("/action/externalAPI/search_repository",
                                     { "query": 'categories:"_(all)_"'},
                                     { "Accept": "application/xml" })
        assert(headers.get("content-type")[0] == "application/xml")
        # now with a zipfile
        data, headers = self.doFetch("/action/externalAPI/search_repository",
                                     { "query": 'categories:"_(all)_"', "format": "ziplist" })
        assert(headers.get("content-type")[0] == "application/x-uplib-searchresults-zipped")
        length1 = int(headers.get("content-length")[0])
        # TODO:  here, we should really parse the zipfile and see if the right fields are in there
        data, headers = self.doFetch("/action/externalAPI/search_repository",
                                     { "query": 'categories:"_(all)_"', "format": "ziplist", "no-icon": "true" })
        assert(headers.get("content-type")[0] == "application/x-uplib-searchresults-zipped")
        length2 = int(headers.get("content-length")[0])
        self.assert_(length1 > length2, "length without icons (%d) should be less than length with icons (%d)" % (length2, length1))
        data, headers = self.doFetch("/action/externalAPI/search_repository",
                                     { "query": 'uplibdate:today' })
        assert(headers.get("content-type")[0] == "text/plain")
        lines = [x.strip() for x in data.split('\n') if x.strip()]
        assert(len(lines) > 0)

    def testFetchDocumentInfo(self):
        """Test of /action/externalAPI/fetch_document_info"""

        action = "/action/externalAPI/fetch_document_info"
        assert(len(self.docsmapping) > 0)
        doc_id = self.docsmapping.values()[0]
        data, headers = self.doFetch(action, { "doc_id": doc_id })
        assert(headers.get("content-type")[0] == "application/x-uplib-docinfo-zipped")
        try:
            zf = zipfile.ZipFile(StringIO.StringIO(data))
        except:
            self.fail("Invalid zipfile returned:\n%s\n" % ''.join(traceback.format_exception(*sys.exc_info())))
        else:
            names = zf.namelist()
            assert(len(names) > 0)
            assert(("%s/" % doc_id) in names)
            assert(("%s/metadata.txt" % doc_id) in names)
            assert(("%s/first.png" % doc_id) in names)
        # now with XML results
        data, headers = self.doFetch(action, { "doc_id": doc_id, "format": "xml" })
        assert(headers.get("content-type")[0] == "application/xml")
        # TODO:  here, we should really parse the XML and see if the right fields are in there
        data, headers = self.doFetch(action, { "doc_id": doc_id },
                                     { "Accept": "application/xml" })
        assert(headers.get("content-type")[0] == "application/xml")

    def testDocMetadata(self):
        """Test of /action/externalAPI/doc_metadata"""

        action = "/action/externalAPI/doc_metadata"
        assert(len(self.docsmapping) > 0)
        doc_id = self.docsmapping.values()[0]
        data, headers = self.doFetch(action, { "doc_id": doc_id })
        assert(headers.get("content-type")[0] == "text/rfc822-headers")
        # now with XML results
        data, headers = self.doFetch(action, { "doc_id": doc_id, "format": "xml" })
        assert(headers.get("content-type")[0] == "application/xml")
        # TODO:  here, we should really parse the XML and see if the right fields are in there
        data, headers = self.doFetch(action, { "doc_id": doc_id },
                                     { "Accept": "application/xml" })
        assert(headers.get("content-type")[0] == "application/xml")

    def testSearchDocumentPages(self):
        """Test of /action/externalAPI/search_document_pages"""

        action = "/action/externalAPI/search_document_pages"
        qterm = "False"
        assert("testPython" in self.docsmapping)
        doc_id = self.docsmapping["testPython"]
        data, headers = self.doFetch(action, { "doc_id": doc_id, "query": qterm })
        assert(headers.get("content-type")[0] == "text/plain")
        # now with XML results
        data, headers = self.doFetch(action, { "doc_id": doc_id, "query": qterm },
                                     { "Accept": "application/xml" })
        assert(headers.get("content-type")[0] == "application/xml")
        data, headers = self.doFetch(action, { "doc_id": doc_id, "query": qterm, "format": "xml" })
        assert(headers.get("content-type")[0] == "application/xml")
        tree = XML(data.strip())
        assert(tree.tag == "result")
        query = tree.find("query")
        assert(query.get("doc_id") == doc_id)
        assert(query.get("query") == qterm)
        hits = tree.findall("hit")
        #sys.stderr.write("hits are %s\n" % [h.items() for h in hits])
        # should be 1 or more hits, one from testPython, others from the UpLib web page (possibly)
        assert(len(hits) >= 1)
        assert("page_index" in hits[0].keys())
        assert("score" in hits[0].keys())
            

    def testFetchFolder(self):
        """Test of /action/externalAPI/fetch_folder"""

        action = "/action/externalAPI/fetch_folder"
        assert(len(self.docsmapping) > 0)
        doc_id = self.docsmapping.values()[0]
        data, headers = self.doFetch(action, { "doc_id": doc_id })
        assert(headers.get("content-type")[0] == "application/x-uplib-folder-zipped")
        try:
            zf = zipfile.ZipFile(StringIO.StringIO(data))
        except:
            self.fail("Invalid zipfile returned:\n%s\n" % ''.join(traceback.format_exception(*sys.exc_info())))
        else:
            names = zf.namelist()
            assert(len(names) > 0)
            assert("metadata.txt" in names)
            assert("contents.txt" in names)
            assert("page-images/page00001.png" in names)
            assert("thumbnails/big1.png" in names)
            assert("thumbnails/1.png" in names)
            assert("thumbnails/first.png" in names)

    def testFetchOriginal(self):
        """Test of /action/externalAPI/fetch_original"""

        action = "/action/externalAPI/fetch_original"
        assert("testPNG" in self.docsmapping)
        doc_id = self.docsmapping["testPNG"]
        data, headers = self.doFetch(action, { "doc_id": doc_id })
        assert(headers.get("content-type")[0] == "image/png")
        cd, params = headers.get("content-disposition")
        assert(cd == "inline")
        assert("filename" in params)
        assert(params["filename"] == "uplib-logo.png")
        if "testWebPageDirect" in self.docsmapping:
            doc_id = self.docsmapping["testWebPageDirect"]
            data, headers = self.doFetch(action, { "doc_id": doc_id })
            assert(headers.get("content-type")[0] == "application/x-folder-zipped")
            try:
                zf = zipfile.ZipFile(StringIO.StringIO(data))
            except:
                self.fail("Invalid zipfile returned:\n%s\n" % ''.join(traceback.format_exception(*sys.exc_info())))
            else:
                names = zf.namelist()
                assert(len(names) > 0)
                assert("original.html" in names)
            # try for the redirect result
            try:
                data, headers = self.doFetch(action, { "doc_id": doc_id, "browser": "true" },
                                             raise_http_errors=True)
            except urllib2.HTTPError, x:
                self.assert_(x.code == 302, "Bad HTTP result code %s (%s) received" % (x.code, x.read()))
            else:
                self.fail("No redirect signaled on fetch of HTML document with browser=true")


    def testRepoProperties(self):
        """Test of /action/externalAPI/repo_properties"""

        action = "/action/externalAPI/repo_properties"
        data, headers = self.doFetch(action)
        assert(headers.get("content-type")[0] == "text/plain")
        # now as XML
        data, headers = self.doFetch(action, { "format": "xml"} )
        assert(headers.get("content-type")[0] == "application/xml")
        # TODO:  parse the XML and check the values
        data, headers = self.doFetch(action, {}, { "Accept": "application/xml" })
        assert(headers.get("content-type")[0] == "application/xml")
        
    def testReserveDocumentID(self):
        """Test of /action/externalAPI/reserve_document_id"""

        action = "/action/externalAPI/reserve_document_id"
        data, headers = self.doFetch(action)
        assert(headers.get("content-type")[0] == "text/plain")
        id1 = data.strip()
        data, headers = self.doFetch(action, {"format": "xml"})
        assert(headers.get("content-type")[0] == "application/xml")
        e = XML(data.strip())
        assert(e.tag == "result")
        id2 = e.text
        assert(isinstance(id2, (str, unicode)) and (id2 != id1))        
        
    def testRepoIndex(self):
        """Test of /action/externalAPI/repo_index"""

        action = "/action/externalAPI/repo_index"
        data, headers = self.doFetch(action)
        assert(headers.get("content-type")[0] == "application/x-uplib-repository-index")
        data, headers = self.doFetch(action, { "modtime": "0.0" })
        assert(headers.get("content-type")[0] == "application/x-uplib-repository-index")
        try:
            data, headers = self.doFetch(action, { "modtime": str(time.time() + 100000) },
                                         raise_http_errors=True)
        except urllib2.HTTPError, x:
            self.assert_(x.code == 304, "Bad HTTP result code %s (%s) received" % (x.code, x.read()))
        else:
            self.fail("Successful retrieval of an index from the future!")

class TestBasic (FetchTest):

    def __init__(self, repo_url, docsmapping, methodName='testHelp', password=None):
        FetchTest.__init__(self, repo_url, methodName=methodName, password=password)
        self.docsmapping = docsmapping

    def testDocPDFText(self):
        """Test of /action/basic/doc_pdf (on a text doc)"""

        # exercises ReportLab

        action = "/action/basic/doc_pdf"
        assert("testPython" in self.docsmapping)
        doc_id = self.docsmapping["testPython"]
        try:
            data, headers = self.doFetch(action, { "doc_id": doc_id }, raise_http_errors=True)
        except urllib2.HTTPError, x:
            self.assert_(x.code == 302, "Expected redirect to actual PDF, got %s" % str(x))
            self.assert_(x.hdrs.get("Location").strip() == "/html/temp/TestSupport_py.pdf",
                         "redirect header has unexpected value:  %s" % x.hdrs.get("Location").strip())
        else:
            self.fail("Successful retrieval of a PDF without redirect!")

    def testDocPDFImage(self):
        """Test of /action/basic/doc_pdf (on an image doc)"""

        # exercises ReportLab

        action = "/action/basic/doc_pdf"
        assert("testPNG" in self.docsmapping)
        doc_id = self.docsmapping["testPNG"]
        try:
            data, headers = self.doFetch(action, { "doc_id": doc_id }, raise_http_errors=True)
        except urllib2.HTTPError, x:
            self.assert_(x.code == 302, "Expected redirect to actual PDF, got %s" % str(x))
            self.assert_(x.hdrs.get("Location").strip() == "/html/temp/docs_uplib-logo_png.pdf",
                         "redirect header has unexpected value:  %s" % x.hdrs.get("Location").strip())
        else:
            self.fail("Successful retrieval of a PDF without redirect!")

    def testDocHTML(self):
        """Test of /action/basic/doc_html"""

        action = "/action/basic/doc_html"
        assert("testPDF" in self.docsmapping)
        doc_id = self.docsmapping["testPDF"]
        data, headers = self.doFetch(action, { "doc_id": doc_id })
        self.assert_(headers.get("content-type")[0] == "text/html",
                     "Bad content-type %s received" % headers.get("content-type")[0])
        data, headers = self.doFetch(action, { "doc_id": doc_id, "htmltype": "image", "debug": "rebuild" })
        self.assert_(headers.get("content-type")[0] == "text/html",
                     "Bad content-type %s received" % headers.get("content-type")[0])

class TestUploadDocument (FetchTest):

    def __init__(self, repo_url, docsmapping, methodName='testHelp', password=None):
        FetchTest.__init__(self, repo_url, methodName=methodName, password=password)
        self.docsmapping = docsmapping

    def testHelp(self):
        """Test of /action/UploadDocument/help"""

        data, headers = self.doFetch("/action/UploadDocument/help")
        assert(headers.get("content-type")[0] == "text/html")

    def testAddNote(self):
        """Test of /action/UploadDocument/addnote"""

        data, headers = self.doFetch("/action/UploadDocument/addnote")
        assert(headers.get("content-type")[0] == "text/html")

    def testUpload(self):
        """Test of /action/UploadDocument/upload"""

        data, headers = self.doFetch("/action/UploadDocument/upload")
        assert(headers.get("content-type")[0] == "text/html")

    def testAdd(self):
        """Test of /action/UploadDocument/add (PNG, Web page, PNG again with redirect)"""

        data, headers = self.doFetch("/action/UploadDocument/add",
                                     { "wait": "true", "no-redirect": "true",
                                       "contenttype": "image/png",
                                       "documentname": "test PNG image"},
                                     files=(("content", "./docs/uplib-logo.png"),))
        assert(headers.get("content-type")[0] == "text/plain")
        data, headers = self.doFetch("/action/UploadDocument/add",
                                     { "wait": "true", "no-redirect": "true",
                                       "URL": "http://uplib.parc.com",
                                       })
        assert(headers.get("content-type")[0] == "text/plain")
        try:
            data, headers = self.doFetch("/action/UploadDocument/add",
                                         { "wait": "true",
                                           "contenttype": "image/png",
                                           "documentname": "test PNG image"},
                                         files=(("content", "./docs/uplib-logo.png"),),
                                         raise_http_errors=True)
        except urllib2.HTTPError, x:
            self.assert_(x.code == 302, "Bad HTTP result code %s (%s) received" % (x.code, x.read()))
        else:
            self.fail("No redirect received for document!")

class TestRepositoryCreation(SubProcTest):

    def __init__(self, directory, port, methodName='testNoPasswordNoGuardian', password=None):
        SubProcTest.__init__(self, methodName=methodName, password=password)
        self.directory = directory
        self.port = port
        self.password = password

    def _set_verbosity(self, level):
        mdfile = os.path.join(self.directory, "overhead", "metadata.txt")
        if os.path.exists(mdfile):
            from uplib.plibUtil import update_metadata
            update_metadata(mdfile, { "verbosity" : str(level) })

    def testNoPasswordNoGuardianFlat(self):
        """Try creating a test repository (no password, no guardian angel, flat doc folder layout)"""
        output = self.runSubProc('%s --expert --no-guardian --password= --nouser --port=%d --directory="%s"' %
                                 (UPLIB_MAKE_REPOSITORY, self.port, self.directory))
        self.checkRunSuccess()
        shutil.copyfile("extensions/TestSupportExt.py",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.py"))
        shutil.copyfile("extensions/TestSupportExt.info",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.info"))
        self._set_verbosity(4)

    def testNoPasswordNoGuardianFlatResearch(self):
        """Try creating a test repository (no password, no guardian angel, flat doc folder layout, HTTP)"""
        output = self.runSubProc('%s --expert --research --no-guardian --nouser --port=%d --directory="%s"' %
                                 (UPLIB_MAKE_REPOSITORY, self.port, self.directory))
        self.checkRunSuccess()
        shutil.copyfile("extensions/TestSupportExt.py",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.py"))
        shutil.copyfile("extensions/TestSupportExt.info",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.info"))
        self._set_verbosity(4)

    def testNoPasswordNoGuardianHierarchical(self):
        """Try creating a test repository (no password, no guardian angel, hierarchical doc folder layout)"""
        output = self.runSubProc('%s --expert --no-guardian --password= --nouser --port=%d --hierarchical --directory="%s"' %
                                 (UPLIB_MAKE_REPOSITORY, self.port, self.directory))
        self.checkRunSuccess()
        shutil.copyfile("extensions/TestSupportExt.py",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.py"))
        shutil.copyfile("extensions/TestSupportExt.info",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.info"))

    def testNoPasswordGuardian(self):
        """Try creating a test repository (nopassword, guardian angel)"""
        output = self.runSubProc('%s --expert --password= --port=%d --nouser --directory="%s"' %
                                 (UPLIB_MAKE_REPOSITORY, self.port, self.directory))
        self.checkRunSuccess()
        shutil.copyfile("extensions/TestSupportExt.py",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.py"))
        shutil.copyfile("extensions/TestSupportExt.info",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.info"))

    def testPasswordNoGuardian(self):
        """Try creating a test repository (password, no guardian angel)"""
        output = self.runSubProc('%s --expert --no-guardian --password="%s" --nouser --port=%d --directory="%s"' %
                                 (UPLIB_MAKE_REPOSITORY, self.password, self.port, self.directory))
        self.checkRunSuccess()
        shutil.copyfile("extensions/TestSupportExt.py",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.py"))
        shutil.copyfile("extensions/TestSupportExt.info",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.info"))

    def testPasswordGuardian(self):
        """Try creating a test repository (password, guardian angel)"""
        output = self.runSubProc('%s --expert --password="%s" --nouser --port=%d --directory="%s"' %
                                 (UPLIB_MAKE_REPOSITORY, self.password, self.port, self.directory))
        self.checkRunSuccess()
        shutil.copyfile("extensions/TestSupportExt.py",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.py"))
        shutil.copyfile("extensions/TestSupportExt.info",
                        os.path.join(self.directory, "overhead", "extensions", "active", "TestSupportExt.info"))

class TestRepositoryStart(SubProcTest):

    def __init__(self, directory, port, password=None, protocol=None):
        SubProcTest.__init__(self, password=password)
        self.directory = directory
        self.port = port
        self.protocol = protocol or "https"

    def runTest(self):
        """Try starting the test repository"""
        output = self.runSubProc('%s --start "%s"' % (UPLIB_CHECK_ANGEL, self.directory))
        self.checkRunSuccess()
        # now try reading from it
        try:
            d = {}
            if self.password: d["Password"] = self.password
            req = urllib2.Request("%s://127.0.0.1:%s" % (self.protocol, self.port), None, d)
            fh = urllib2.urlopen(req)
        except:
            self.fail("Can't read from started repository:\n%s" %
                      ''.join(traceback.format_exception(*sys.exc_info())))
        else:
            fh.close()
        try:
            d = {}
            if self.password: d["Password"] = self.password
            req = urllib2.Request("%s://127.0.0.1:%s/action/TestSupportExt/print_env" % (self.protocol, self.port), None, d)
            fh = urllib2.urlopen(req)
        except:
            self.fail("Can't read from started repository:\n%s" %
                      ''.join(traceback.format_exception(*sys.exc_info())))
        else:
            #sys.stderr.write(fh.read())
            fh.close()

class TestRepositoryRestart(SubProcTest):

    def __init__(self, directory, port, password=None, protocol=None):
        SubProcTest.__init__(self, password=password)
        self.directory = directory
        self.port = port
        self.protocol = protocol or "https"

    def runTest(self):
        """Try restarting the test repository"""
        output = self.runSubProc('%s --restart "%s"' % (UPLIB_CHECK_ANGEL, self.directory))
        self.checkRunSuccess()
        # now try reading from it
        try:
            d = {}
            if self.password: d["Password"] = self.password
            req = urllib2.Request("%s://127.0.0.1:%s" % (self.protocol, self.port), None, d)
            fh = urllib2.urlopen(req)
        except:
            self.fail("Can't read from started repository:\n%s" %
                      ''.join(traceback.format_exception(*sys.exc_info())))
        else:
            fh.close()

class TestRepositoryShutdown(SubProcTest):

    def __init__(self, directory, port):
        SubProcTest.__init__(self)
        self.directory = directory
        self.port = port

    def runTest(self):
        """Try stopping the test repository"""
        output = self.runSubProc('%s --stop "%s"' % (UPLIB_CHECK_ANGEL, self.directory))
        self.checkRunSuccess()


if __name__ == "__main__":

    if len(sys.argv) != 3:
        sys.stderr.write("Usage:  python %s UPLIB_HOME UPLIB_VERSION\n" % sys.argv[0])
        sys.exit(1)
    if not TestSupport.setup_uplib(sys.argv[1], sys.argv[2]):
        sys.stderr.write("Usage:  python %s UPLIB_HOME UPLIB_VERSION\n" % sys.argv[0])
        sys.exit(1)
    os.environ["UPLIB_VERBOSITY"] = "0"

    from uplib.plibUtil import note, configurator, subproc, DOC_ID_RE, read_metadata, getpass
    from uplib.plibUtil import read_file_handling_charset
    from uplib.webutils import https_post_multipart

    if (sys.platform == "win32"):
        winpassword = os.environ.get("WINDOWS_PASSWORD")
        if not winpassword:
            sys.stderr.write("On Windows, you need to set the environment variable WINDOWS_PASSWORD\n"
                             "to your password before running the tests.  This is used to create the\n"
                             "test repositories.\n")
            sys.exit(1)

    settings = {}
    conf = configurator.default_configurator()
    UPLIB_ADD_DOCUMENT = conf.get("uplib-add-program")
    UPLIB_GET_DOCUMENT = conf.get("uplib-get-program")
    UPLIB_MAKE_REPOSITORY = conf.get("uplib-make-repository-program")
    UPLIB_CHECK_ANGEL = conf.get("uplib-check-repository-program")
    UPLIB_POST_MULTIPART = https_post_multipart

    # set up the UPLIBRC
    if os.environ.get("UPLIBRC"):
        # need a canonical pathname here
        sys.stderr.write("UPLIBRC = " + os.environ.get("UPLIBRC") + "\n")
        os.environ["UPLIBRC"] = os.path.realpath(os.environ["UPLIBRC"])
        sys.stderr.write("UPLIBRC = " + os.environ.get("UPLIBRC") + "\n")
    else:
        # figure out whether we should push over to ToPDF
        using_topdf = TestSupport.use_topdf(settings)
        if settings:
            TestSupport.setup_uplibrc(settings)
        uplibrc = os.environ.get("UPLIBRC")
        if uplibrc:
            sys.stderr.write("Using updated UPLIBRC %s\n" % uplibrc)

    d = tempfile.mkdtemp()
    port = TestSupport.find_unused_port()
    sys.stderr.write("Test repository at %s; repository port is %s\n" % (d, port))

    mp = {}

    suite = unittest.TestSuite()
    suite.addTest(TestRepositoryCreation(d, port, methodName="testNoPasswordNoGuardianFlat"))
    suite.addTest(TestRepositoryStart(d, port))
    suite.addTest(TestRepositoryRestart(d, port))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testPNG'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testGIF'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testJPEG'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testTIFF'))
    if conf.get("jasper"):
        suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testJPEG2000'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testBMP'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testPDF'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testText'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testWebPageDirect'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testWebPageComplete'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testEmailWithAttachment'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testMicrosoftWordMac2004'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testMicrosoftWordMac2008docx'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testMicrosoftWordMac2008doc'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testMP3'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testPython'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testJava'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testAddFlags'))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testInvalidOptions'))
    suite.addTest(TestSearches("https://localhost:%s/" % port, d, mp, methodName='testFindByType'))
    suite.addTest(TestSearches("https://localhost:%s/" % port, d, mp, methodName='testFindByText'))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testSearchRepository'))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testFetchDocumentInfo'))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testFetchFolder'))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testRepoProperties'))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testDocMetadata'))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testFetchOriginal'))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testReserveDocumentID'))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testSearchDocumentPages'))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testRepoIndex'))
    suite.addTest(TestBasic("https://localhost:%s/" % port, mp, methodName='testDocHTML'))
    suite.addTest(TestBasic("https://localhost:%s/" % port, mp, methodName='testDocPDFText'))
    suite.addTest(TestBasic("https://localhost:%s/" % port, mp, methodName='testDocPDFImage'))
    suite.addTest(TestJava("https://localhost:%s/" % port, d, mp, methodName='testRepo'))
    suite.addTest(TestUploadDocument("https://localhost:%s/" % port, mp, methodName='testHelp'))
    suite.addTest(TestUploadDocument("https://localhost:%s/" % port, mp, methodName='testAddNote'))
    suite.addTest(TestUploadDocument("https://localhost:%s/" % port, mp, methodName='testUpload'))
    suite.addTest(TestUploadDocument("https://localhost:%s/" % port, mp, methodName='testAdd'))
    suite.addTest(TestRepositoryShutdown(d, port))

    erred = False
    result = None
    try:
        result = unittest.TextTestRunner(verbosity=4).run(suite)
    except:
        sys.stderr.write(''.join(traceback.format_exception(*sys.exc_info())))
        erred = True

    TestRepositoryShutdown(d, port).runTest()

    if erred or not result.wasSuccessful():
        sys.stderr.write("Test repository is in %s.\n" % d)
        sys.exit(1)
    else:
        _remove_repository(d)

    # now try with a password

    sys.stderr.write("\nNow running some of the same tests, with a password-protected repository...\n\n")

    mp = {}
    suite = unittest.TestSuite()
    suite.addTest(TestRepositoryCreation(d, port, methodName="testPasswordNoGuardian", password="foo"))
    suite.addTest(TestRepositoryStart(d, port, password="foo"))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testPNG', password="foo"))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testPython', password="foo"))
    suite.addTest(TestSearches("https://localhost:%s/" % port, d, mp, methodName='testFindByText', password="foo"))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testSearchRepository', password="foo"))
    suite.addTest(TestRepositoryShutdown(d, port))

    erred = False
    result = None
    try:
        result = unittest.TextTestRunner(verbosity=4).run(suite)
    except:
        sys.stderr.write(''.join(traceback.format_exception(*sys.exc_info())))
        erred = True

    TestRepositoryShutdown(d, port).runTest()

    if erred or not result.wasSuccessful():
        sys.stderr.write("Test repository is in %s.\n" % d)
        sys.exit(1)
    else:
        _remove_repository(d)

    # now try the research switch

    sys.stderr.write("\nNow running some of the same tests, using a --research repository...\n\n")

    mp = {}
    suite = unittest.TestSuite()
    suite.addTest(TestRepositoryCreation(d, port, methodName="testNoPasswordNoGuardianFlatResearch"))
    suite.addTest(TestRepositoryStart(d, port, password="foo", protocol="http"))
    suite.addTest(TestAdds("http://localhost:%s/" % port, d, mp, methodName='testPNG'))
    suite.addTest(TestAdds("http://localhost:%s/" % port, d, mp, methodName='testPython'))
    suite.addTest(TestSearches("http://localhost:%s/" % port, d, mp, methodName='testFindByText'))
    suite.addTest(TestExternalAPI("http://localhost:%s/" % port, mp, methodName='testSearchRepository'))
    suite.addTest(TestRepositoryShutdown(d, port))

    erred = False
    result = None
    try:
        result = unittest.TextTestRunner(verbosity=4).run(suite)
    except:
        sys.stderr.write(''.join(traceback.format_exception(*sys.exc_info())))
        erred = True

    TestRepositoryShutdown(d, port).runTest()

    if erred or not result.wasSuccessful():
        sys.stderr.write("Test repository is in %s.\n" % d)
        sys.exit(1)
    else:
        _remove_repository(d)

    # now try without a password, but using hierarchical doc folders

    sys.stderr.write("\nNow running some of the same tests, with a repository using hierarchical doc folders...\n\n")

    mp = {}
    suite = unittest.TestSuite()
    suite.addTest(TestRepositoryCreation(d, port, methodName="testNoPasswordNoGuardianHierarchical"))
    suite.addTest(TestRepositoryStart(d, port))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testPNG', hierarchical=True))
    suite.addTest(TestAdds("https://localhost:%s/" % port, d, mp, methodName='testPython', hierarchical=True))
    suite.addTest(TestSearches("https://localhost:%s/" % port, d, mp, methodName='testFindByText'))
    suite.addTest(TestExternalAPI("https://localhost:%s/" % port, mp, methodName='testSearchRepository'))
    suite.addTest(TestRepositoryShutdown(d, port))

    erred = False
    result = None
    try:
        result = unittest.TextTestRunner(verbosity=4).run(suite)
    except:
        sys.stderr.write(''.join(traceback.format_exception(*sys.exc_info())))
        erred = True

    TestRepositoryShutdown(d, port).runTest()

    if erred or not result.wasSuccessful():
        sys.stderr.write("Test repository is in %s.\n" % d)
        sys.exit(1)
    else:
        _remove_repository(d)

    sys.exit(0)
