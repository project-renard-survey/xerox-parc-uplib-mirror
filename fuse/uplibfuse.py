#! /usr/bin/env python

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
# $Header: /project/uir/CVSROOT/uplib/fuse/uplibfuse.py,v 1.77 2009/01/07 19:57:55 janssen Exp $

# usage:
#   mount_uvfs ~/UbiDocs https://jh.parc.xerox.com:2080/

import base64
import cgi
import codecs
import ctypes
import errno
import hashlib
import httplib
import logging
import mimetypes
import os
import Queue
import re
import sha
import stat
import string
import StringIO
import struct
import sys
import thread
import threading
import time
import traceback
import types
import urllib
import urllib2
import urlparse
import xattr
import zipfile
import zlib
from errno import EACCES, EEXIST, EFAULT, EINVAL, ENODATA, ENOENT, ENOSYS, \
    EOPNOTSUPP as ENOTSUP, EBADF
from stat import S_IFDIR, S_IFLNK, S_IFREG, S_IRUSR, S_IWUSR, S_IXUSR, S_IRWXU
from time import gmtime, mktime, strftime, sleep
from pprint import pprint as pp

from uplib.fuse.ctypesfuse import FUSE, FuseError, FuseOperations
from uplib.addDocument import CONTENT_TYPES
from uplib.webutils import fetch_url, get_content_type, \
    get_extension_for_type, https_post_multipart, HTTPCodes
from uplib.plibUtil import note, parse_date, read_metadata, DOC_ID_RE  # MutexLock

import LaunchServices           # to look up OSType

CATEGORIESPATH_PATTERN=re.compile(r"^/categories/(?P<filepath>.*)$")
DOCS_FOLDER_PATTERN=re.compile(r"/docs/(?P<id>[0-9]{5}-[0-9]{2}-[0-9]{4}-[0-9]{3})(/.*)?")
TEMPFILE_ENDINGS=re.compile(r"^.*(.tmp|autosave)$")

CAT_DIR='/categories'

SAFECHARS = string.digits + string.letters + '_' + '-' + ':'

EXPIRE_INTERVAL = 20  # twenty-second default

DIR_RX = S_IFDIR | S_IRUSR | S_IXUSR  # no write permission

NON_STRING_METADATA_KEYS = ("is_wpc",)

CONTENT_CACHER = None

def _build_statinfo(size, extra_fields={}):
    now = time.time()
    stat = {'st_mode':  S_IRUSR,
            'st_nlink': 1,
            'st_uid':   os.getuid(),
            'st_gid':   os.getgid(),
            'st_size':  size,
            'st_atime': now,
            'st_ctime': now,
            'st_mtime': now,
            }
    for k,v in extra_fields.iteritems():
        stat[k] = v
    return stat

def fetch_url_result(url, password=''):
    """Match impedance between fetch_url (file output) and urlopen(...).read() (string output)."""
    temp = StringIO.StringIO()
    headers, hard_to_read_p = fetch_url(url, temp, password=password)
    temp.seek(0)
    result = temp.read()
    if hard_to_read_p and len(result) > 6000:
        result = '[x]'  # huge HTML elided
    return result

def initial_component(relative_filespec):
    """Returns pathname up to first slash, so 'abc/d/e.f' => 'abc'."""
    return relative_filespec.split(os.path.sep)[0]


class SingleCaseDict(dict):
    """A SingleCaseDict behaves like a dictionary, but with restrictions on dup keys.

    For example, after d['ReadMe'] = 1, attempting d['README'] = 2
    or d['readme'] = 3 would raise a Duplicate Key exception."""

    def __init__(self, arg=[]):
        self.lower = {}
        temp = dict(arg)
        for key in temp:
            self.lower[key.lower()] = key
        return super(SingleCaseDict, self).__init__(arg)

    def __setitem__(self, key, value):
        key_low = key.lower()
        if key_low not in self.lower:
            self.lower[key_low] = key
        if self.lower[key_low] != key:
            msg = 'duplicate key: %s cannot be added when %s is present'
            raise FuseError(msg % (key, self.lower[key_low]))
        return super(SingleCaseDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        key_low = key.lower()
        if key_low in self.lower:
            del(self.lower[key_low])
        return super(SingleCaseDict, self).__delitem__(key)


class PathsDict(SingleCaseDict):
    """A PathsDict behaves like a dictionary, but with UVFS-specific error checking."""

    def __setitem__(self, key, value):
        #note('setting %s to a %s', key, display_type(value))
        assert key != ''
        if not key.startswith('/'):
            raise ValueError('pathname must start with slash -- ' + key)

        if key != '/':
            if key.endswith('/'):
                raise ValueError('directory path must not have trailing slash -- ' + key)
            # Ensure that parent entries exist.
            components = key[1:].split('/')
            ancestor = ''
            for i in range(len(components)-1):
                ancestor += '/' + components[i]
                if not ancestor in self:  # Entry is missing.
                    raise FuseError('Tried to insert %s, but parent %s is missing.' % (key, ancestor))
                    #dict.__setitem__(self, ancestor, FileObj({}))

        # Now ensure that self[parent].data[basename] is already == value.

        return super(PathsDict, self).__setitem__(key, value)


class FilenameDict(dict):
    """A FilenameDict only admits Filename()'s."""

    def __setitem__(self, key, value):
        """Preserves the RepInvariant by adding keys to the dict only if they are Filename()s."""
        if not isinstance(key, Filename):
            raise UvfsValueError('%s is not a Filename().' % key)
        return super(FilenameDict, self).__setitem__(key, value)

    def __getitem__(self, key):
        """Attempted probes of d[3] or d['3'] won't corrupt the dict, but we helpfully tell the caller about his type error."""
        if not isinstance(key, Filename):
            raise UvfsValueError('%s is not a Filename().' % key)
        return super(FilenameDict, self).__getitem__(key)


class LowerCaseDict(dict):
    """A LowerCaseDict is a dictionary which case smashes keys to lower."""

    def __setitem__(self, key, value):
        return super(LowerCaseDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(LowerCaseDict, self).__getitem__(key.lower())


class LowerCaseSet(set):
    """A LowerCaseSet is a set which case smashes keys to lower."""

    def add(self, key):
        return super(LowerCaseSet, self).add(key.lower())

    def __contains__(self, key):
        return super(LowerCaseSet, self).__contains__(key.lower())


class UvfsError(StandardError):
    pass

class UvfsValueError(UvfsError):
    pass


class Pathname(unicode):
    """Pathname comparison is case-insensitive.

    Also, certain characters are forbidden:    \r \n
    """
    def __init__(self, name):
        if re.search('[\n]', name):  # This now accepts names like '._Icon\r'
            raise UvfsValueError('bad pathname: %s contains CRLF' % repr(name))
        super(Pathname, self).__init__(name)

    def __hash__(self):
        return zlib.adler32(unicode(self).lower())

    def __eq__(self, other):
        return unicode(self).lower() == unicode(other).lower()

    def __cmp__(self, other):
        return cmp(unicode(self).lower(), unicode(other).lower())


class Filename(Pathname):
    """Filename comparison is case-insensitive.

    Also, certain characters are forbidden:  / \r \n
    """
    def __init__(self, name):
        if re.search('[/\n]', name):
            raise UvfsValueError('bad filename: %s contains slash or CRLF' % repr(name))
        super(Filename, self).__init__(name)



class FileContent(object):

    """This implements a multi-way content store.  Could be a string,
    in which case it refers to a local file in the filesystem, and the
    content is stored there.  Could be an open file, in which case
    that's an open r/w file, and it contains the content.  Could be a
    StringIO instance, same as the open file.  Could be None, in which
    case it needs to be resolved."""

    def __init__(self, fp):
        assert isinstance(fp, (StringIO.StringIO, file, Pathname))
        self.__handle = fp

    def __str__(self):
        return '<FileContent %s>' % repr(self.__handle)

    def __nonzero__(self):
        return True

    def __len__(self):
        if isinstance(self.__handle, StringIO.StringIO):
            return len(self.__handle.getvalue())
        elif isinstance(self.__handle, file):
            return os.fstat(self.__handle.fileno())
        elif isinstance(self.__handle, Pathname):
            return os.stat(self.__handle).st_size
        else:
            return 0

    def tell(self):
        if isinstance(self.__handle, (StringIO.StringIO, file)):
            v = self.__handle.tell()
        else:
            v = 0
        return v

    def seek(self, pos, kind=0):
        logging.debug("self.__handle is %s, pos is %s, kind is %s", self.__handle, pos, kind)
        try:
            if isinstance(self.__handle, Pathname) and ((pos != 0) or (kind != 0)):
                self.__handle = open(self.__handle, "r+b", 0)
            if isinstance(self.__handle, (StringIO.StringIO, file)):
                return self.__handle.seek(pos, long(kind))
        except IOError:
            logging.debug("self.__handle is %s, pos is %s, kind is %s", self.__handle, pos, kind)
            raise

    def flush (self):
        if isinstance(self.__handle, file):
            self.__handle.flush()

    def close(self):
        # noop
        self.flush()
        h = self.__handle
        if not isinstance(h, Pathname):
            h.close()

    def read(self, nbytes=-1):
        if isinstance(self.__handle, Pathname):
            self.__handle = open(self.__handle, "r+b", 0)
        if isinstance(self.__handle, StringIO.StringIO) or isinstance(self.__handle, file):
            return self.__handle.read(nbytes)

    def write(self, value):
        if isinstance(self.__handle, Pathname):
            self.__handle = open(self.__handle, "r+b", 0)
        if isinstance(self.__handle, StringIO.StringIO) or isinstance(self.__handle, file):
            return self.__handle.write(value)

    def getvalue(self):
        if isinstance(self.__handle, Pathname):
            self.__handle = open(self.__handle, "r+b", 0)
        pos = self.__handle.tell()
        self.__handle.seek(0)
        v = self.__handle.read()
        self.__handle.seek(pos)
        return v    

class ContentCacher(object):

    def __init__(self, cache_root):
        if not os.path.exists(cache_root):
            os.mkdir(cache_root)
        elif not os.path.isdir(cache_root):
            raise ValueError("cache_root (%s) must be a directory we can write")
        self.__root = cache_root

    def get_cached_path(self, path):
        while path.startswith("/"):
            path = path[1:]
        filepath = os.path.join(self.__root, "paths", path)
        if os.path.exists(filepath):
            return FileContent(Pathname(filepath))
        else:
            return None

    def get_cached_hash(self, hash):
        filepath = os.path.join(self.__root, "hashes", hash)
        if os.path.exists(filepath):
            return FileContent(Pathname(filepath))
        else:
            return None

    def cache_bits(self, content, hash=None, path=None):
        if path is not None:
            while path.startswith("/"):
                path = path[1:]
            filepath = os.path.join(self.__root, "paths", path)
        elif hash is not None:
            filepath = os.path.join(self.__root, "hashes", hash)
        else:
            raise ValueError("Either 'hash' or 'path' must be specified.")
        d = os.path.dirname(filepath)
        logging.debug("directory to cache %s in is %s", filepath, d)
        try:
            if not os.path.exists(d):
                os.makedirs(d)
        except:
            if not os.path.exists(d):
                raise
        if not os.path.exists(d):
            raise IOError("Couldn't create directory %s" % d)
        fp = open(filepath, 'wb+', 0)
        fp.write(content)
        fp.close()
        return FileContent(Pathname(filepath))


class UvfsFileObject(object):
    def __init__(self, filename):
        self.filename = Filename(filename)  # Just a hint, for debugging; the .dir keys hold the "real" filenames.
        self.stat = _build_statinfo(0)
        self.icns = ''  # custom Finder icon, if any
        self._last_verified = time.time()
        self._doc_id = None
        self.expires_after = self._last_verified + EXPIRE_INTERVAL
        self.parent = None

    def set_nonexpiring(self):
        self.expires_after = 2**31 - 1  # denotes a permanent entry

    def get_doc_id(self):
        return self._doc_id

    def set_doc_id(self, id):
        self._doc_id = id

    def __repr__(self):
        vtime = strftime('%d%b%Y %H:%M:%S', gmtime(self._last_verified))
        mtime = strftime('%d%b%Y %H:%M:%S', gmtime(self.stat['st_mtime']))
        return '<%s "%s" %s %.1f %o %s>' % (self.__class__.__name__,
                                            self.filename, vtime,
                                            self.expires_after - self._last_verified,
                                            self.stat['st_mode'], mtime)

    ## # Equality is based on simple filename comparison, for "f in parent.dir".
    ##def __hash__(self):
    ##    return zlib.adler32(self.filename)
    ##def __eq__(self, other):
    ##    return self.filename == other.filename


class UvfsSymlink(UvfsFileObject):
    def __init__(self, filename, target=''):
        super(UvfsSymlink, self).__init__(filename)
        self.stat['st_mode'] |= S_IFLNK
        self.target = Pathname(target)

class UvfsFile(UvfsFileObject):
    def __init__(self, filename, contents='', ctime=None):
        super(UvfsFile, self).__init__(filename)
        self.doc_id = None
        self.digest = ''  # could call it sha.new().hexdigest(), or da39...

        # this field is set to a new UvfsFile if this file has been opened for write
        # on 'release', the new file replaces the existing file
        self.writing = None  # default is read-only access (no need to persist changes)

        self.writer_lock = threading.Lock()  # protects .writer manipulations
        self.write_request = Queue.Queue()
        if isinstance(contents, FileContent):
            self.content = contents
        else:
            self.content = FileContent(StringIO.StringIO(contents))
        self.stat['st_size'] = len(contents)
        self.stat['st_mode'] |= S_IFREG
        if ctime:
            self.stat['st_ctime'] = ctime
            self.stat['st_mtime'] = ctime
        else:
            self.stat['st_mtime'] = time.time()
            self.stat['st_ctime'] = time.time()

class UvfsDirectory(UvfsFileObject):
    def __init__(self, filename):
        super(UvfsDirectory, self).__init__(filename)
        self.parent = None  # Points to a UvfsDirectory.
        self.stat['st_mode'] |= (S_IFDIR | S_IXUSR)
        self.dir = FilenameDict()  # immediate children (Uvfs* objects)

    def get_file(self, key):
        self.dir.get(Filename(key))

    def put_file(self, f):
        assert f and f.filename
        self.dir[f.filename] = f

    def __repr__(self):
        mtime = strftime('%d%b%Y %H:%M:%S', gmtime(self.stat['st_mtime']))
        return '<%s "%s" %o %s %s>' % (self.__class__.__name__,
                                    self.filename or '/',
                                    self.stat['st_mode'], mtime,
                                    sorted(self.dir.keys()))

class DeferredFile(UvfsFile):
    """We have not yet populated self.content, so consult the server before reading it."""
    def __init__(self, filename, content_hook=None):
        super(DeferredFile, self).__init__(filename)
        assert content_hook  # The super() dance makes it *look* optional.
        self.content_hook = content_hook  # a content-providing method
        self.content = None  # Don't even *think* about reading it just yet.
        self.sha_hash = None
        self.doc_id = None

class DeferredDirectory(UvfsDirectory):
    """We have not yet populated self.dir, so consult the server before reading it."""
    def __init__(self, filename, content_hook=None):  # hook is not optional
        super(DeferredDirectory, self).__init__(filename)
        assert content_hook
        self.content_hook = content_hook  # a content-providing method
        self.dir = None  # Don't even *think* about reading it just yet.

    def __repr__(self):
        """Describe all but the contents of self.dir."""
        mtime = strftime('%d%b%Y %H:%M:%S', gmtime(self.stat['st_mtime']))
        return '%s %s %o %s <<empty>>' % ('<DeferredDirectory object>',
                                          self.filename or '/',
                                          self.stat['st_mode'], mtime)




class UbidocsBackingStore():
    """Provides RAM-based and persistent (repo-based) storage for metadata + document contents."""
    def __init__(self, repo_url, password='', expire_interval = 20):
        self.repo_url = repo_url
        self.password = password
        # seconds that we may use metadata without requerying the Ubidocs server
        self.expire_interval = expire_interval
        # After e.g. ten minutes of the client ignoring some metadata, we will
        # no longer attempt to proactively keep a cached copy fresh.
        self.max_unused_interval = 30 * expire_interval
        # As cache entries age, they are either rejuvenated or reaped.
        self.fresh = PriorityQueue()  # We *don't* want it to fill up.
        self.docs = {}  # metadata cache, indexed by doc_id
        #icon_path = '/Library/UbiDocs/1.0/ContextBar/ContextBar.app/Contents/Resources/ubidocs-logo.icns'  # Must process with 'sips -i'.
        #self.ubi_icns = xattr.getxattr(icon_path, 'com.apple.ResourceFork')
        line = self._extension_result('/UVFS/repo_root_and_most_recent_docid')
        self._repo_root = line.split()[1]
        self._init_logging()
        self.root = UvfsDirectory('')
        self.root.set_nonexpiring()
        self.root.stat['st_mode'] |= S_IWUSR
        self.add(self.root, UvfsDirectory('docs'))
        self.get('/docs').set_nonexpiring()
        self._init_top_level()
        self._init_logging()
        # self._init_caching()
        mimetypes.init()
        id = line.split()[0]
        if len(id)==17 and DOC_ID_RE.search(id):
            self.create_docs_entry(id)  # Show at least one doc in Finder.

    def _init_top_level(self):
        """Replace top level directories with empty/deferred ones so the repo will be queried for fresh data."""
        self.fresh = PriorityQueue()  # Should carefully delete old entries.
        for dir_name, hook in [('search', self.content_for_search),
                               ('categories', self.content_for_categories)]:
            if self.root.dir.get(Filename(dir_name)):
                del(self.root.dir[Filename(dir_name)])
            dir = DeferredDirectory(dir_name, hook)
            dir.set_nonexpiring()
            self.add(self.root, dir)

    def _init_caching(self):
        global CONTENT_CACHER
        CONTENT_CACHER = ContentCacher(os.path.join(self._repo_uvfs_dir(), "cache"))

    def _init_logging(self):
        """Make this daemon log to overhead/UVFS/request.log by default."""
        logger = logging.getLogger()
        if logger.getEffectiveLevel() != 30:  # Still at default setting?
            return  #  Some logging config has been done already; don't disturb it.
        logging.basicConfig(level=logging.DEBUG, filemode='w',
                            filename=os.path.join(self._repo_uvfs_dir(), 'request.log'))

    def _repo_uvfs_dir(self):
        """Return full path to overhead/UVFS, typically /var/ubidocs/${USER}/overhead/UVFS."""
        assert os.path.exists(self._repo_root)
        dir = os.path.join(self._repo_root, 'overhead', 'UVFS')
        if not os.path.exists(dir):
            os.mkdir(dir)
        assert os.path.exists(dir)
        return dir


    def _extension_result(self, url_ending):
        assert url_ending.startswith('/')
        url = urlparse.urljoin(self.repo_url, 'action' + url_ending)
        temp = StringIO.StringIO()
        try:
            headers, hard_to_read_p = fetch_url(url, temp, password=self.password)
        except (urllib2.URLError, httplib.HTTPException), e:
            logging.error('Failed to retrieve result for %s  %s', url, e)
            raise e
        temp.seek(0)
        result = temp.read()
        if hard_to_read_p and len(result) > 6000:
            result = '[x]'  # huge HTML elided
        return result

    def _is_cached(self, path):
        """Predicate, returns True if a valid (fresh) cache entry was found.

        Side effect:  removes all traces of entry if it was stale."""
        if path not in self.paths:
            return False
        e = self.paths[path]
        if time.time() > e.expires_after:
            del(self.paths[path])
            self.fresh.delete(e)  # Takes linear time, rather than log(n).
            return False  # It is as though the stale entry was never there.
        return True

    def _parse_metadata(self, text):
        """Turns one line of document metadata into a dict."""
        pool = LaunchServices.NSAutoreleasePool.alloc().init()
        try:
            d = {}
            m = re.search('(.*?), (filename) (.*)', text)
            if m:
                text = m.group(1)
                d[m.group(2)] = m.group(3)  # filename may contain commas
                for pair in text.split(', '):
                    k, v = pair.split(' ')
                    if k in NON_STRING_METADATA_KEYS:
                        d[k] = eval(v)
                    else:
                        d[k] = v

            if 'apparent-mime-type' in d:

                mtype = d['apparent-mime-type']

                if mtype == "message/rfc822":
                    # email can only be tagged by adding .eml to the filename
                    filename = d.get("filename")
                    if filename and not filename.endswith(".eml"):
                        d["filename"] = os.path.splitext(d["filename"])[0] + ".eml"

                else:
                    # otherwise, figure out the OSType
                    uti = LaunchServices.UTTypeCreatePreferredIdentifierForTag(
                        LaunchServices.kUTTagClassMIMEType, mtype, "public.data")
                    ostype = LaunchServices.UTTypeCopyPreferredTagWithClass(
                        uti, LaunchServices.kUTTagClassOSType)
                    if ostype:
                        try:
                            ostype2 = ostype.encode('Latin-1', 'strict')
                            # logging.debug("* OSType for %s (%s) is %s", d['filename'], mtype, repr(ostype2))
                            d['OSType'] = ostype2
                        except:
                            logging.debug("Exception fetching OSType for %s:\n%s" % (
                                d['filename'], ''.join(traceback.format_exception(*sys.exc_info()))))
                    else:
                        d['OSType'] = 'TEXT'
                        # logging.debug("* default OSType for %s (%s) to %s", d['filename'], mtype, d['OSType'])
            return d
        finally:
            del pool

    def _exists(self, path):
        """Predicate.  Returns True if path exists in the backing store provided by self.base_url or was created by FS client."""
        assert path.startswith('/')
        if path == '/':
            return True
        if self._is_cached(path):  # Do we have it already?
            return True
        initial_component = path.split('/')[1]
        # Can we synthesize it?
        m = DOCS_FOLDER_PATTERN.search(path)
        if m:
            id = m.group('id')
            if len(id) == 17 and DOC_ID_RE.match(id):
                # very expensive call
                self.docs[id] = self._parse_metadata(self._extension_result('/UVFS/metadata_for_docs?id=' + id))
                return True
        return False

    def _pathquote(self, path):
        retval = ''
        for c in path:
            if c not in SAFECHARS:
                retval += '_'
            else:
                retval += c
        return retval

    def _is_zip(self, bytes):
        """Same as zipfile.is_zipfile(), but takes a bytestring, not a filespec."""
        try:
            file = StringIO.StringIO(bytes)
            z = zipfile.ZipFile(file)
            return True
        except zipfile.BadZipfile:
            return False

    def _add_directory_icon(self, id, directory):
        icon = UvfsFile('Icon\r', contents = self._icns_for(id))
        self.add(directory, icon)
        directory.icns = icon.content.getvalue()

    def _fetch_doc_metadata (self, id):
        assert len(id) == 17 and DOC_ID_RE.match(id)

        if id in self.docs:
            return self.docs[id]

        self.create_docs_entry(id)
        return self.docs[id]

    def set_doc_id(self, f, path):
        id = None
        m = DOCS_FOLDER_PATTERN.search(path)
        if m:
            id = m.group('id')
            f.set_doc_id(id)
        else:
            f2 = self.get(path)
            if f2 and (f2 != f):
                id = f2.get_doc_id()
                if id:
                    f.set_doc_id(id)
                elif isinstance(f2, UvfsSymlink):
                    m = DOCS_FOLDER_PATTERN.search(str(f2.target))
                    if m:
                        id = m.group('id')
                        f.set_doc_id(id)
        return id

    def _icns_for(self, doc_id):
        empty = 'eNoDAAAAAAE='  # This is what '' looks like after gzip & b64
        icns = self.get_metadata(doc_id).get('icns', empty)
        return zlib.decompress(base64.b64decode(icns))


    def get_contenttype(self, filename, apparent_mime_type=None):
        ct = get_content_type(filename)
        if apparent_mime_type:
            ct = apparent_mime_type
        if ct == 'application/octet-stream':
            ct = 'text/plain'
        # NB:  add_document() will get 415 HTTPCodes.UNSUPPORTED_MEDIA_TYPE
        # if we fail to pick one of the known repo.content_types(), e.g.
        # an attempt to use 'application/octet-stream'.
        return ct

    def ensure_good_suffix(self, filename, content_type):
        """Return a filename (perhaps unchanged) which reflects the MIME type.

        For example, a text/plain 'Readme' will be mapped to 'Readme.txt'."""
        filename = re.sub('[ \.]+$', '', filename)  # trim trailing elipses
        # You won't see many foo.wiz Word documents, nor foo.xlw spreadsheets.
        fix = {'.wiz': '.doc', '.xlw': '.xls', '.pwz': '.ppt'}
        ext = '.txt'
        for ext in sorted(mimetypes.guess_all_extensions(content_type)):
            ext = fix.get(ext, ext)
            if filename.lower().endswith(ext):
                return filename
        return filename + ext
        # We don't want '.pl' from mimetypes.guess_extension('text/plain').


    def add_document(self, path, content_type=None, contents=None, metadata_title=None, category='recent', old_digest=''):
        f = self.get(path)
        assert isinstance(f, UvfsFile)
        f.content.flush()
        f.content.seek(0)
        if contents is None:
            contents = f.content.getvalue()
        f.snapshot_hash = hashlib.sha1(contents)
        title = metadata_title or f.filename
        content_type = self.get_contenttype(title, content_type)
        title = self.ensure_good_suffix(title, content_type)
        selector = '/action/UploadDocument/add'
        parsed_url = urlparse.urlparse(urlparse.urljoin(self.repo_url, selector))
        fields = [('wait', 'true'),
                  ('no-redirect', 'true'),
                  ('content', f.content.getvalue()),
                  ('contenttype', content_type),
                  ('md-title', title),
                  ('md-categories', category)]
        if old_digest:  # Describe the previous version of the current document.
            fields.append(('metadata', 'version-of: ' + old_digest))
        logging.debug('uploading %d bytes of %s, path is %s',
                      len(f.content.getvalue()), content_type, path)
        status, ok, httpMessageInstance, doc_id = \
            https_post_multipart(parsed_url.hostname, parsed_url.port,
                                 self.password, selector, fields, [])
        status = int(status)
        if status != HTTPCodes.OK:  # 200
            raise UvfsError('uploading %s failed, %d %s; %s' % (path, status,
                                                                ok, doc_id))
        return doc_id


    def delete_document(self, doc_id):
        """Remove a document from a repo, or signal an error."""
        delete = '/basic/doc_delete?confirmed=yes&doc_id='
        result = self._extension_result(delete + doc_id)
        if re.search('No document with id .* It must already have been deleted', result):
            result = re.sub('</*b>', '', result)  # remove ID <b> bolding
            raise UvfsError(result)


    def _expand_deferred_directory(self, path, content_method):
        f = content_method(path)
        assert type(f) == UvfsDirectory
        return f

    def get_parent(self, path):
        return self.get(os.path.dirname(path))

    def get_or_create_parent(self, path):
        """Does 'mkdir -p' up to, but not including, the given path.

        Caller may mkdir('new'), then get_or_create_parent('new/a/b/foo.txt').
        Caller should expect no joy from touching file 'a' then attempting
        to get 'a/b/c'."""
        path = os.path.dirname(path)  # parent's path
        p = self.get(path)
        if p:
            return p
        assert path != '/'
        cur = self.root
        for component in [Filename(c) for c in path.split('/')[1:]]:
            assert type(cur) == UvfsDirectory  # precondition *must* be satisfied by caller
            if component not in cur.dir:
                cur.dir[component] = UvfsDirectory(component)
            cur = cur.dir[component]
        return cur

    def get(self, path):
        """Return a UvfsFileObject, or None if file not found.

        DeferredDirectories are expanded by get();
        DeferredFiles are not.
        """
        if path == '/':
            return self.root
        m = DOCS_FOLDER_PATTERN.match(path)
        if m:
            self.create_docs_entry(m.group('id'))
        p = ''
        cur = self.root
        for component in [Filename(c) for c in path.split('/')[1:]]:
            p += '/' + component
            if (not isinstance(cur, UvfsDirectory)) or \
                    (component not in cur.dir):
                #print 'ENOENT for %s' % path  #(get_or_create_parent hits this routinely)
                return None
            cur = cur.dir[component]
            if isinstance(cur, DeferredDirectory):
                self.remove(p, verify_path=False)
                cur = self._expand_deferred_directory(p, cur.content_hook)

        assert isinstance(cur, UvfsFileObject)
        assert not isinstance(cur, DeferredDirectory)
        return cur

    def get_chasing_deferred_file(self, path):
        f = self.get(path)

        # See if request is a cache-miss for an existing repo document.
        m = DOCS_FOLDER_PATTERN.match(path)
        id = m and m.group('id')
        if id:
            self.create_docs_entry(id)
            f = self.get(path)

        if isinstance(f, DeferredFile):
            hook = f.content_hook
            self.remove(path)
            f = hook(path)
            assert type(f) == UvfsFile

        return f

    def get_chasing_symlinks(self, path):
        """Return either a UvfsDirectory or UvfsFile, or None if file not found.

        We chase symbolic links, so UvfsSymlink will never be returned.
        """
        i = 6  # Break symlink loops after half a dozen dereferences.
        f = self.get_chasing_deferred_file(path)
        while isinstance(f, UvfsSymlink) and i > 0:  # Usually a single dereference suffices.
            i -= 1
            path = os.path.normpath(os.path.join(os.path.dirname(path), f.target))
            f = self.get_chasing_deferred_file(path)
        assert i > 0  # Zero implies a cycle of symlinks pointing at each other.
        return f

    def remove(self, path, verify_path=True):
        assert isinstance(path, types.StringTypes)  # no UvfsFileObjects, please
        if verify_path:
            f = self.get(path)
            if not f:
                raise UvfsError('ENOENT: cannot remove %s as it does not exist' % path)
        parent = self.get(os.path.dirname(path))
        filename = Filename(os.path.basename(path))
        assert filename in parent.dir
        del(parent.dir[filename])
        assert filename not in parent.dir
        if path.startswith('/search/'):
            self.persist_searches()
        self.display_tree_to_file()

    def add(self, parent, file_object):
        assert isinstance(parent, UvfsDirectory)
        assert isinstance(file_object, UvfsFileObject)
        if file_object.filename in parent.dir:
            raise UvfsError('cannot add {%s} to {%s} as it already exists' % (file_object, parent))
        #print 'adding %s to %s' % (file_object.filename, parent.filename)
        parent.dir[file_object.filename] = file_object
        parent.stat['st_mtime'] = time.time()
        file_object.parent = parent
        self.fresh.put((file_object.expires_after,
                        (parent, file_object.filename)))

    def add_search(self, parent, query):
        assert parent.filename == 'search'
        if query == '.DS_Store':  # ignore
            return
        query_dir = DeferredDirectory(query, self.content_for_a_specific_search)
        query_dir.stat['st_mode'] |= S_IWUSR
        self.add(parent, query_dir)
        self.persist_searches()

    def persist_searches(self):
        search_directory = self.get('/search')
        persist = codecs.open(self._get_searches_txt_filespec(), 'w', 'utf-8')
        persist.write("# These are UbiDocs UVFS search/* queries, stored by uplibfuse.py\n")
        persist.write(time.strftime("# at %H:%M %d-%b-%Y.\n\n"))
        persist.write("\n".join(sorted(search_directory.dir.keys())) + "\n")
        persist.close()
        self.display_tree_to_file()

    def _get_searches_txt_filespec(self):
        """Return a path like /var/ubidocs/jhanley/overhead/UVFS/searches.txt"""
        return os.path.join(self._repo_uvfs_dir(), 'searches.txt')

    def _rename(self, directory, old_name, new_name):
        assert isinstance(directory, UvfsDirectory)
        assert old_name in directory.dir
        assert new_name not in directory.dir
        f = directory.dir[old_name]
        del(directory.dir[old_name])
        directory.dir[new_name] = f
        directory.stat['st_mtime'] = time.time()


    def display_tree_to_file(self):
        codecs.open('/tmp/display_tree.txt', 'w', 'utf8').write(self.display_tree('/'))

    def display_tree(self, dir_path):
        """Returns a string with one line per file object, suitably idented."""

        def indented(path):
            n = 4 * path.count('/')
            return (' ' * n) + path

        directory = self.get(dir_path)
        if dir_path == '/':
            dir_path = ''
        assert type(directory) == UvfsDirectory  # but *not* DeferredDirectory subclass
        result = []
        for name in sorted(directory.dir.keys()):
            pathname = dir_path + '/' + name
            f = directory.dir[name]
            assert f.filename == name
            assert isinstance(f, UvfsFileObject)
            if type(f) == UvfsDirectory:
                result.append("%s/:\n" % indented(pathname))
                result.append(self.display_tree(pathname))
            else:
                t = str(f)
                if isinstance(f, UvfsSymlink):
                    t = repr(f)
                result.append("%s\t%s\n" % (indented(pathname), t))
        return ''.join(result)


    ############################################################################
    #
    #  content_for_x adds a UvfsDirectory to take place of a DeferredDirectory
    #
    ############################################################################


    def content_for_categories(self, path):
        """/categories/
        """
        categories_dir = UvfsDirectory('categories')
        categories_dir.stat['st_mode'] |= S_IWUSR
        self.add(self.root, categories_dir)
        for category in self._extension_result('/UVFS/get_categories').split('\n'):
            parent_path = '/categories'
            parts = category.split('/')
            for part in parts:
                parent = self.get(parent_path)
                dirpath = os.path.join(parent_path, part)
                logging.debug("looking at %s", dirpath)
                dir = self.get(dirpath)
                # This would be better modeled by having the content method
                # add entries rather than replacing.
                if not dir:
                    dir = self.content_for_a_category_level(dirpath)
                    logging.debug("added %s", dirpath)
                dir.stat['st_mode'] |= S_IWUSR
                parent_path = dirpath
        return categories_dir


    def content_for_a_specific_category(self, path):
        """/categories/a/b/c/
        Note that though DeferredDirectories a,b,c are created simultaneously,
        children like c may be expanded long after expansion of parent.
        """
        assert path.startswith('/categories/')
        parent = self.get('/categories')
        # Handle a multi-level category tag.
        levels = path.split('/')
        for i in range(2, len(levels)):
            p = '/'.join(levels[:i+1])
            d = self.get(p)
            if (d is None) or isinstance(d, DeferredDirectory):
                if d:
                    self.remove(p, verify_path=False)
                d = self._expand_deferred_directory(p, self.content_for_a_category_level)
            parent = d
        return d


    def content_for_a_category_level(self, path):
        # TODO -- this should just update the current dir instead of building a new one
        category = re.sub('^/categories/', '', path)
        basename = os.path.basename(path)
        parent = self.get(os.path.dirname(path))
        dir = UvfsDirectory(basename)
        dir.stat['st_mode'] |= S_IWUSR
        if parent.dir.get(basename):
            self.remove(path)
        # no paths for this sub-category now
        for f in self.links_for_a_category_level(category):
            if f.filename not in dir.dir:
                self.add(dir, f)
        self.add(parent, dir)
        return dir


    def old_links_for_a_category_level(self, category):
        """Return a list of UvfsSymlinks."""
        #logging.debug("  links_for_a_category_level(%s):\n%s", category,
        #              ''.join(traceback.format_stack()[:-1]))
        result = []
        md4cat = '/UVFS/metadata_for_category?category=' + urllib.quote_plus(category)
        for line in self._extension_result(md4cat).split('\n'):
            if not line:
                continue  # There were no matching documents for that category.
            md = self._parse_metadata(line)
            filename = md['filename']
            dots = '../' * (1+len(category.split('/')))
            f = UvfsSymlink(filename, target='%sdocs/%s/originals/%s' % (dots, md['id'], filename))
            f.doc_id = md['id']
            f.stat['st_mtime'] = float(md['mtime'])
            f.icns = zlib.decompress(base64.b64decode(md['icns']))
            result.append(f)
            self.docs[f.doc_id] = md  # Cache the metadata for later.
        return result


    def _new_symlink_for_category_doc (self, category, md):
        filename = md['filename']
        dots = '../' * (1+len(category.split('/')))
        f = UvfsSymlink(filename, target='%sdocs/%s/originals/%s' % (dots, md['id'], filename))
        f.doc_id = md['id']
        f.stat['st_mtime'] = float(md['mtime'])
        f.icns = zlib.decompress(base64.b64decode(md['icns']))
        return f

    def links_for_a_category_level(self, category):
        """Return a list of UvfsSymlinks."""
        #logging.debug("  links_for_a_category_level(%s):\n%s", category,
        #              ''.join(traceback.format_stack()[:-1]))

        result = []
        docs4cat = '/UVFS/docs_for_category?category=' + urllib.quote_plus(category)
        need_metadata_for = []
        for line in self._extension_result(docs4cat).split('\n'):
            if not line:
                continue  # There were no matching documents for that category.
            id, hash = line.strip().split()
            if id not in self.docs:
                need_metadata_for.append(id)
            else:
                result.append(
                    self._new_symlink_for_category_doc(category, self.docs[id]))
        # now get md for docs we don't know about yet
        if need_metadata_for:
            md4docs = '/UVFS/metadata_for_docs?id=' + '&id='.join(need_metadata_for)
            for line in self._extension_result(md4docs).split('\n'):
                if not line:
                    continue
                md = self._parse_metadata(line)
                result.append(self._new_symlink_for_category_doc(category, md))
                self.docs[md['id']] = md
        return result


    def get_metadata(self, doc_id):
        """Return cached copy of document metadata dict.

        On cache-miss will query the repo and populate the cache.
        """
        #logging.debug("  get_metadata(%s):\n%s", doc_id,
        #              ''.join(traceback.format_stack()[:-1]))
        md = self.docs.get(doc_id)
        if not md:
            request = '/UVFS/metadata_for_docs?doc_id=' + doc_id
            self.docs[doc_id] = md = self._parse_metadata(self._extension_result(request))
        return md

    def title_with_good_suffix(self, doc_id):
        """Provide consistent document names for use in docs/ search/ and categories/."""
        return self.get_metadata(doc_id)['filename']
        #same as _extension_result('/UVFS/title_with_good_suffix?doc_id=' + doc_id)

    def content_for_docs(self, path):
        """/docs/NNNN-NN-NNNN-NNN/
        """
        m = DOCS_FOLDER_PATTERN.search(path)
        if m:
            return self.create_docs_entry(m.group('id'))
        return None

    def create_docs_entry(self, id):
        """Create id/metadata and id/originals."""
        docs = self.get('/docs')
        if docs.dir.get(Filename(id)):
            return  # Nothing to do -- it already exists.
        md = self.get_metadata(id)

        id_dir = UvfsDirectory(id)
        self.add(docs, id_dir)

        md_dir = DeferredDirectory('metadata', self.content_for_metadata_dir)
        self.add(id_dir, md_dir)
        self._add_directory_icon(id, id_dir)

        orig = DeferredDirectory('originals', self.content_for_originals_dir)
        self.add(id_dir, orig)

        return docs

##        pagecount = int(md.get('page-count') or md['pagecount'] or '1')
##        return self._create_originals_entry(id, id_dir, md['ctime'], md.get('sha-hash'), pagecount)

    def content_for_originals_dir(self, path):
        m = DOCS_FOLDER_PATTERN.search(path)
        if not m:
            return None
        id = m.group('id')
        logging.debug("content_for_originals_dir(%s), CONTENT_CACHER is %s", path, CONTENT_CACHER)
        md = self.get_metadata(id)
        f = None
        if CONTENT_CACHER:
            if "sha-hash" in md:
                logging.debug("   get_cached_hash(%s)", md["sha-hash"])
                f = CONTENT_CACHER.get_cached_hash(md["sha-hash"])
            if not f:
                logging.debug("   get_cached_path(%s)", path)
                f = CONTENT_CACHER.get_cached_path(Pathname(path))
        if not f:
            result = StringIO.StringIO()
            # This may raise 'HTTPError: HTTP Error 404: Not Found' if id not valid.
            headers, hard_to_read = fetch_url(urlparse.urljoin(self.repo_url,
                '/action/externalAPI/fetch_original?doc_id=' + id),
                result, redirect_allowed=True, password=self.password)
            if CONTENT_CACHER and ("sha-hash" in md):
                logging.debug("   cache_bits(hash=%s)", md["sha-hash"])
                f = CONTENT_CACHER.cache_bits(result.getvalue(), hash=md["sha-hash"])
                result.close()
            elif CONTENT_CACHER:
                logging.debug("   cache_bits(path=%s)", path)
                f = CONTENT_CACHER.cache_bits(result.getvalue(), path=Pathname(path))
                result.close()
            else:
                logging.debug("   no caching, just returning bits")
                result.seek(0, 0)
                f = FileContent(result)

        logging.debug("f for %s is %s, unzipping", id, f)

        orig_dir = UvfsDirectory('originals')
        orig_dir.set_doc_id(id)
        if not md.get('is_wpc'):  # WebPage,Complete documents are immutable.
            orig_dir.stat['st_mode'] |= S_IWUSR  # Others may be freely edited.
        id_dir = self.get('/docs/%s' % id)
        self.add(id_dir, orig_dir)
        self._add_directory_icon(id, orig_dir)
        fname = self.title_with_good_suffix(id)
        ctime = int(float(md['mtime']))
        if md['is_wpc']:
            # extract each file and build a file tree
            zf = zipfile.ZipFile(f, 'r')
            for name in zf.namelist():
                if '/' in name:  # Rename only the top-level .html
                    path = os.path.join('/docs', id, 'originals', name)
                else:
                    path = os.path.join('/docs', id, 'originals', fname)
                parent = self.get_or_create_parent(path)
                content = zf.read(name)
                if CONTENT_CACHER:
                    c = CONTENT_CACHER.cache_bits(content, path=path)
                else:
                    c = FileContent(StringIO.StringIO(content))
                f = UvfsFile(os.path.basename(path), ctime=ctime, contents=c)
                logging.debug(self.display_tree(os.path.join('/docs', id, 'originals')))
                self.add(parent, f)
            zf.close()
        else:
            # single file
            assert not md['is_wpc']
            f = UvfsFile(fname, ctime=ctime, contents=f)
            f.stat['st_mode'] |= S_IWUSR
            digest = sha.new()  # Single files are mutable; zips are not.
            logging.debug("f.content is %s", f.content)
            digest.update(f.content.read())
            f.digest = digest.hexdigest()
            self.add(orig_dir, f)

        # now fill out page-images skeleton
        page_images_dir = UvfsDirectory('page-images')
        self.add(id_dir, page_images_dir)
        thumbnails_dir = UvfsDirectory('thumbnails')
        self.add(id_dir, thumbnails_dir)
        # A redundant copy allows easy hi-res spacebar previews in the Finder.
        f = UvfsSymlink('first.png', target='originals/page-images/page00001.png')
        self.add(id_dir, f)  # redundant copy
        self.add(thumbnails_dir, DeferredFile('first.png',
                                              self.content_for_originals))

        for i in range(1, 1 + int(md['pagecount'])):
            self.add(page_images_dir, DeferredFile(
                'page%05d.png' % i, self.content_for_originals))
            self.add(thumbnails_dir, DeferredFile(
                'big%05d.png' % i, self.content_for_originals))
            self.add(thumbnails_dir, DeferredFile(
                '%d.png' % i, self.content_for_originals))
        return id_dir

    def content_for_originals(self, path):
    # sample valid URL fragments (appended to 'https://127.0.0.1:2080'):
    #   /docs/01227-20-3894-512/page-images/page00001.png
    #   /docs/01227-20-3894-512/thumbnails/big00001.png
    #   /docs/01227-20-3894-512/thumbnails/first.png
    #   /docs/01227-20-3894-512/thumbnails/1.png
        m = re.search('/docs/([\d-]{17})/originals/(|thumbnails|page-images)/([^/]+)$', path)
        if not m:
            return None
        id, dir, filename = m.group(1), m.group(2), m.group(3)
        logging.debug("content_for_originals(%s)", path)
        url = urlparse.urljoin(self.repo_url, re.sub('/originals', '', path))
        temp = StringIO.StringIO()
        headers, hard_to_read_p = fetch_url(url, temp, password=self.password)
        f = UvfsFile(filename, contents=temp.getvalue())
        assert f.stat['st_size'] == len(f.content.getvalue())
        parent = self.get(os.path.dirname(path))
        self.add(parent, f)
        return f

    def content_for_metadata_dir(self, path):
        """/docs/NNNN-NN-NNNN-NNN/metadata/       &
           /docs/NNNN-NN-NNNN-NNN/metadata/*.txt
        """
        m = re.search('/docs/([\d-]{17})/metadata', path)
        assert m
        if not m:
            return None
        id = m.group(1)
        url_frag = '/externalAPI/doc_metadata?doc_id=' + id
        mdfile = StringIO.StringIO(self._extension_result(url_frag))
        md = read_metadata(mdfile)
        md2 = self.get_metadata(id)
        md['ctime'] = md2['mtime']
        md['id'] = id

        md_dir = UvfsDirectory('metadata')
        md_dir.set_doc_id(id)
        # Leading underscore makes filename sort to the front.
        self.add(md_dir, UvfsFile('_metadata.txt', contents=mdfile.getvalue()))
        #self._add_directory_icon(id, md_dir)
        for key in md:
            f = UvfsFile('%s.txt' % key, ctime=int(float(md2['mtime'])),
                         contents=unicode(md[key]).encode('UTF-8', 'strict'))
            self.add(md_dir, f)
        self.add(self.get('/docs/%s' % id), md_dir)
        return md_dir


    def content_for_search(self, path):
        """/search/
        """
        search_dir = UvfsDirectory('search')
        search_dir.stat['st_mode'] |= S_IWUSR
        self.add(self.root, search_dir)

        fspec = self._get_searches_txt_filespec()
        if os.path.exists(fspec):
            s = []
            for line in codecs.open(fspec, 'r', 'utf-8').readlines():
                line = re.sub('#.*', '', line).strip()
                if line and ('/' not in line) and ('\r' not in line):
                    s.append(line.strip())
            for line in s:
                self.add_search(search_dir, line)

        return search_dir


    def content_for_a_specific_search(self, path):
        """/search/query/
        """
        m = re.search('^/search/([^/]+)$', path)
        assert m
        query = m.group(1)
        query_dir = UvfsDirectory(query)
        query_dir.stat['st_mode'] |= S_IWUSR
        self.add(self.get('/search'), query_dir)
        # It isn't clear why search results list some documents multiple times.
        search_results = {}  # used to suppress dups
        url = '/UVFS/matching_ids_and_filenames?query=' + urllib.quote_plus(query)
        for line in self._extension_result(url).split("\n"):
            m = re.search('^([\d-]{17})\s+(.*)', line)
            if m and DOC_ID_RE.match(m.group(1)):
                id, filename = m.group(1), m.group(2)
                sym = UvfsSymlink(filename, target='../../docs/%s/originals/%s' % (id, filename))
                search_results[filename] = sym
        for sym in search_results.values():
            self.add(query_dir, sym)

        return query_dir



    def _poller(self):
        """Thread polls repo in the background, looking for changes."""
        prev = 0.0
        while self.bg:
            time.sleep(0.2)  # Limit our attempted poll rate during net fail.
            r = '/UVFS/patient_mod_time?max_delay=119&last_mod_time=%.2f'
            result = self._extension_result(r % prev)
            if not result:
                # EOF if repository shuts down
                self.bg = False
                break
            mod_time = float(self._extension_result(r % prev))  # every 2 minutes
            if mod_time > prev:
                prev = mod_time
                self._init_top_level()  # Make client getattr re-query the repo.
            if time.time() > prev + 3600:
                prev = time.time()
                self._init_top_level()  # Don't cache for more than an hour. 

    def file_writer(self, path, contents, old_docid, new_category):
        """Thread adds document to repo, then exits.

        If subsequent write()s and close()s occur during the repo submission,
        we save additional snapshots until the file stabilizes, and *then*
        we exit, knowing that the bits are persistent on the repository.
        There may be several file_writer threads for several recently
        updated files; each file will have at most one file_writer active.
        """
        try:
            logging.debug('path is %s, old id is %s, category is %s', path, old_docid, new_category)
            f = self.get(path)
            if not f:
                logging.info('file %s not written', path)
                return
            if f.filename.startswith('.'):
                return  # We do not persist dot files in the repository.
            if not contents:
                return  # Don't add empty files to the repository
            ct = self.get_contenttype(f.filename)
            assert '/' in ct
            mdtitle = self.ensure_good_suffix(f.filename, ct)
            if old_docid:
                get_categories = '/UVFS/categories_for_doc?doc_id=' + old_docid
                categories = self._extension_result(get_categories)
            elif new_category:
                categories = new_category
            else:
                categories='added-via/UVFS'
            digest = 'sentinel'  # definitely won't match file's digest
            still_busy = True
            while still_busy:
                try:
                    still_busy = f.write_request.get(block=False)
                    # Check if file contents changed, to avoid duplicate submissions.
                    cdigest = hashlib.sha1(contents).hexdigest()
                    if digest != cdigest:
                        digest = cdigest
                        id = self.add_document(path, content_type=ct,
                                               contents=contents,
                                               metadata_title=mdtitle,
                                               category=categories,
                                               old_digest=f.digest)
                        logging.debug('new doc id for %s is %s (%s) %s',
                                      mdtitle, id, digest,
                                      threading.currentThread().getName())
                        contents = f.content.getvalue()
                        f = self.get(path)  # Check for unlink + create.
                        if f:
                            contents = f.content.getvalue()
                            f.doc_id = id
                        else:
                            still_busy = False
                            break
                except Queue.Empty, e:    # No additional release()s have occurred.
                    f.writer_lock.acquire()
                    del(f.writer)         # Indicate that this thread is gone, and..
                    f.writer_lock.release()
                    still_busy = False    # ..exit.
        except:
            msg = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.debug(msg)


class UVFS(FuseOperations):
    """Impedence matcher between FUSE and UbidocsBackingStore.

    At this layer, *nothing* gets persisted."""

    def __init__(self, backing_store):
        self.backing = backing_store
        self.files = {}  # maps from small-integer filedescriptors to UvfsFile


    def _next_file_descriptor(self):
        if len(self.files) == 0:
            return 0
        return 1 + max(self.files.keys())


    def init(self):
        self.backing.bg = 1
        self.backing.bg = threading.Thread(target=self.backing._poller)
        self.backing.bg.start()
        return 0

    def destroy(self):
        self.backing.persist_searches()
        thrd = self.backing.bg
        self.backing.bg = None
        # Wait for helper to notice None and to exit.
        #thrd.join()


    def chmod(self, path, mode):
        f = self.backing.get(path)
        if f:
            f.stat['st_mode'] = (f.stat['st_mode'] & ~S_IRWXU) | (mode & S_IRWXU)
            return 0
        raise FuseError(EACCES)

    def chown(self, path, uid, gid):
        f = self.backing.get(path)
        if f:
            f.stat['st_uid'] = uid
            f.stat['st_gid'] = gid
            return 0
        raise FuseError(EACCES)

    def create(self, path, mode):
        """Returns a numerical file handle."""
        if self.backing.get_chasing_deferred_file(path):
            raise FuseError(EACCES)  # Fail if file already exists.
        parent = self.backing.get_chasing_deferred_file(os.path.dirname(path))
        if not parent:
            raise FuseError(ENOENT)  # Parent directory must exist.
        filename = Filename(os.path.basename(path))
        assert filename not in parent.dir

        f = UvfsFile(filename)
        f.stat['st_mode'] = ((mode | S_IWUSR) & S_IRWXU) | S_IFREG
        f.writing = f  # Later release() will need this.

        logging.debug(" requested mode is %o, actual mode is %o", mode, f.stat['st_mode'])

        fd = self._next_file_descriptor()
        assert fd not in self.files
        self.files[fd] = f
        parent.dir[filename] = f
        return fd

    def flush(self, path, fh):
        return 0

    def fsync(self, path, datasync, fh):
        return 0

    def getattr(self, path, fh=None):
        """Returns a dictionary with keys identical to the `struct stat`
        C structure. `st_atime`, `st_mtime` and `st_ctime` should be floats.
        """
        if (fh is not None) and (fh in self.files):
            f = self.files[fh]
        else:
            f = self.backing.get_chasing_deferred_file(path)
        logging.debug(" for %s, f is %s, f.parent is %s", path, f, f and f.parent)
        if f and f.parent:
            id = f.get_doc_id()
            #logging.debug("id of %s is %s", path, id)
            if id is None:
                # not initialized
                id = self.backing.set_doc_id(f, path)
                #logging.debug("id of %s is %s", path, id)
            # WebPage,Complete must either expose link or replicate original_files/
            # Note that space bar (cover flow preview) shows WPC very nicely.
            if id and (self.backing.get_metadata(id).get('is_wpc')):
                f = self.backing.get(path)
        if f:
            if isinstance(f, UvfsFile) and f.writing:
                f.stat['st_size'] = len(f.writing.content)
            assert f.stat['st_size'] >= 0
            if ((fh is not None) and (self.files.get(fh) == f)) or (isinstance(f, UvfsFile) and f.writing):
                logging.debug("  stat for %s is %s", path, f.stat)
            logging.debug(" getstat(%s) => { st_mode: %o }", path, f.stat['st_mode'])
            return f.stat
        raise FuseError(ENOENT)

    def link(self, source, target):
        raise FuseError(EACCES)

    def mkdir(self, path, mode):
        parent = self.backing.get(os.path.dirname(path))
        if not parent:
            raise FuseError(ENOENT)  # Parent directory must exist.
        parent.stat['st_mtime'] = time.time()
        filename = Filename(os.path.basename(path))
        if filename in parent.dir:
            raise FuseError(EACCES)  # Can't create a name which already exists.
        m = re.search('^/search/([^/]+)$', path)
        if m and not path.startswith('/search/untitled folder'):
            self.backing.add_search(parent, m.group(1))
        else:
            dir = UvfsDirectory(filename)
            dir.stat['st_mode'] |= S_IWUSR
            self.backing.add(parent, dir)
        return 0

    def open(self, path, mode):
        """Returns a numerical file handle."""
        if path == '/':
            raise FuseError(EACCES)
        parent = self.backing.get_chasing_deferred_file(os.path.dirname(path))
        if not parent:
            raise FuseError(ENOENT)
        basename = os.path.basename(path)
        f = self.backing.get_chasing_deferred_file(path)
        if (not f) and (mode & os.O_RDONLY):
            raise FuseError(ENOENT)
        if (not f) and (basename not in parent.dir):  # We're writing a new file.
            assert False                                # should never happen (create is for that)
            f = UvfsFile(basename)
            self.backing.add(parent, f)
        if isinstance(f, DeferredFile):
            f = self.backing.query_server(path)  # This has side effects on parent.
        assert isinstance(f, UvfsFile)
        if (mode & (os.O_WRONLY | os.O_RDWR)):
            assert (not f.writing)
            f.writing = UvfsFile(basename)
            logging.debug("f is %s, f.content is %s (%s)", f, f.content,
                          (isinstance(f.content, StringIO.StringIO) and f.content.closed) or "n/a")
            f.writing.content = FileContent(StringIO.StringIO(f.content.getvalue()[:]))
            f.writing.writing = f       # link back
        fd = self._next_file_descriptor()
        assert fd not in self.files
        self.files[fd] = f.writing or f
        return fd

    def read(self, path, size, offset, fh):
        """Returns a string containing the data requested."""
        if fh not in self.files:
            raise FuseError(EBADF)
        f = self.files.get(fh)
        assert isinstance(f, UvfsFile)
        if f:
            content = f.content
            content.seek(offset)
            return content.read(size)
        raise FuseError(EACCES)

    def readdir(self, path, fh):
        directory = self.backing.get(path)
        if (not directory) or (not isinstance(directory, UvfsDirectory)):
            raise FuseError(ENOENT)
        if isinstance(directory, DeferredDirectory):
            directory = self.backing.query_server(path)  # This has side effects on parent.
        assert type(directory) == UvfsDirectory
        entries = []
        for name in directory.dir:
            # Filtering out one filename will improve the Finder experience.
            if name != 'Icon\r':
                entries.append(name)
        entries.sort()
        return entries

    def readlink(self, path):
        f = self.backing.get(path)
        if f:
            assert isinstance(f, UvfsSymlink)
            return f.target
        raise FuseError(EACCES)

    def release(self, path, fh):
        if fh in self.files:
            if not isinstance(self.files[fh], UvfsFile):
                logging.debug("Non-UvfsFile found for fd %s:  %s", fh, self.files[fh])
                raise FuseError(EBADF)

            #del(self.files[fh])
            m = DOCS_FOLDER_PATTERN.match(path)
            id = None
            category = None
            if m:
                # editing an existing document
                id = m.group('id')
            else:
                # copying a file into a category
                if path.startswith("/categories/"):
                    category = '/'.join(os.path.split(path)[0][len("/categories/"):].split('/'))
            f = self.files[fh]
            # if a new file, (f.writing == f)
            dirname, basename = os.path.split(path)
            parent = self.backing.get(dirname)
            existing_file = parent.dir.get(Filename(basename))
            if f.writing:
                logging.debug("content is %s", repr(f.content))
                # need to do something with the finished file
                if (id or category) and (not (f.filename.startswith('.') or TEMPFILE_ENDINGS.match(path))):
                    # OK, add it to UpLib appropriately
                    f.stat['st_mtime'] = time.time()
                    f.writer_lock.acquire()
                    in_progress = hasattr(f, 'writer')
                    if not in_progress:
                        # Each file has, at most, one file_writer thread.
                        f.writer = threading.Thread(target=self.backing.file_writer,
                            args=(path, f.content.getvalue(), id, category))
                        logging.debug('spawned %s', f.writer.getName())
                    # now break up the symlinks
                    f.writing.writing = None
                    if f.writing:
                        f.writing = None
                    # this is a bit tricky.
                    if category:
                        # If it's a new (or changed) entry in a category, we make sure it's in the dir...
                        parent.dir[Filename(basename)] = f
                    elif id:
                        # If it's a new version of an existing doc, we just add it and move on
                        pass
                    f.writer_lock.release()
                    f.write_request.put(True)  # Ask writer to submit a snapshot.
                    if not in_progress:
                        f.writer.start()
                else:
                    # not something for UpLib, but we still need to keep it around
                    if existing_file:
                        if f.writing != existing_file:
                            logging.debug("bad write file for %s -- self.files[%s] is %s, but backing.get yields %s"
                                          % (path, fh, f, existing_file))
                            return -EBADF
                        # update contents
                        logging.debug("oldcontent is %s, f.content is %s", existing_file.content, f.content)
                        oldcontent = existing_file.content
                        existing_file.content = f.content
                        existing_file.stat['st_mtime'] = time.time()
                        existing_file.stat['st_size'] = len(existing_file.content)
                        if oldcontent != existing_file.content:
                            oldcontent.close()      # release buffer
                        f.writing = None
                    else:
                        f.writing = None
                        parent.dir[Filename(basename)] = f
            return 0
        return -EBADF

    def rename(self, old, new):
        f_old = self.backing.get(old)
        f_new = self.backing.get(new)
        f_parent = self.backing.get(os.path.dirname(new))
        if f_old and f_parent and not f_new:
            f_new = f_old
            f_new.filename = Filename(os.path.basename(new))
            self.backing.remove(old)
            if re.search('^/search/([^/]+)$', new):
                self.mkdir(new, 0777)
            else:
                self.backing.add(f_parent, f_new)
            return 0
        raise FuseError(EACCES)

    def rmdir(self, path):
        directory = self.backing.get(path)
        if not isinstance(directory, UvfsDirectory):
            raise FuseError(EACCES)

        if re.search('^/search/[^/]+$', path):
            # Allow "cd /search; mkdir foo; rmdir foo" to succeed.
            for entry in directory.dir.keys():
                if isinstance(directory.dir[entry], UvfsSymlink):
                    del(directory.dir[entry])

        # Allow deletion of a directory containing only .xattr files.
        attrs = [1  for f in directory.dir.values()  if f.filename.startswith('._')]
        if len(attrs) == len(directory.dir):
            for entry in directory.dir.keys():
                del(directory.dir[entry])

        if len(directory.dir) == 0:
            self.backing.remove(path)

            # Remove all trace of path, including extended attributes.
            xattr = os.path.join(os.path.dirname(path),
                                 '._' + os.path.basename(path))
            assert self.backing.get(xattr) == None
            self.backing.display_tree_to_file()
            if self.backing.get(xattr):
                self.unlink(xattr)
            return 0

        raise FuseError(EACCES)


    def listxattr (self, path):
        
        f = self.backing.get_chasing_symlinks(path)
        if not f:
            raise FuseError(ENOENT)
        id = f.get_doc_id()
        if id is None:
            id = self.backing.set_doc_id(f, path)
        attrs = []
        fattrs = f.stat.get("_xattr_attributes")
        if fattrs:
            for k, v in fattrs.items():
                if v is not None:
                    attrs.append(k)
        for a in [u'com.apple.FinderInfo', u'com.apple.ResourceFork']:
            if a not in attrs:
                attrs.append(a)
        if path.endswith(".txt") and u'com.apple.TextEncoding' not in attrs:
            attrs.append(u'com.apple.TextEncoding')
        if id and ((not fattrs) or (u'com.parc.ubidocs.DocID' not in fattrs)):
            attrs.append(u'com.parc.ubidocs.DocID')
        return attrs

        if False:

            attrs = []
            if f.filename.endswith('.txt'):
                attrs.append('com.apple.TextEncoding')
            if icon:  # or f.filename == 'Icon\r':
                attrs.append(u'com.apple.FinderInfo')
                attrs.append(u'com.apple.ResourceFork')
            return attrs

    def getxattr(self, path, attrname, position=0):

        # Remember to `killall Finder` after changing icns behavior,
        # as Finder will cache old icon bitmaps, even across umount / remount.

        f = self.backing.get_chasing_symlinks(path)

        if not f:
            raise FuseError(ENOENT)

        assert type(f) in [UvfsFile, UvfsDirectory]

        id = f.get_doc_id()
        if id is None:
            # not initialized
            id = self.backing.set_doc_id(f, path)

        # did we cache a non-standard value with setxattr?
        v = f.stat.get("_xattr_attributes")
        if v:
            v = v.get(attrname)
            if v is not None:
                return v

        # is it asking for doc ID?
        if id and (attrname == u'com.parc.ubidocs.DocID'):
            return id

        # no, so we do what we do

        #fdType         = 0x54455854 (TEXT)
        #fdType         = 0x69636f6e (icon)
        #fdCreator      = 0x4d414353 (MACS)

        # see http://developer.apple.com/DOCUMENTATION/Carbon/reference/Finder_Interface/Reference/reference.html
        # see /System/Library/Frameworks/CoreServices.framework/Frameworks/CarbonCore.framework/Headers/Finder.h
        #    struct FileInfo {
        #      OSType              fileType;               /* The type of the file */
        #      OSType              fileCreator;            /* The file's creator */
        #      UInt16              finderFlags;            /* ex: kHasBundle, kIsInvisible... */
        #      Point               location;               /* File's location in the folder */
        #                                                  /* If set to {0, 0}, the Finder will place the item automatically */
        #      UInt16              reservedField;          /* (set to 0) */
        #    };

        kHasCustomIcon = 0x0400  # from CoreServices' Finder.h
        kNameLocked    = 0x1000  # name is fixed
        kHasBundle     = 0x2000  # Set this to hide a directory's contents.
        kIsInvisible   = 0x4000  # directories in /.Trashes are invisible

        if attrname == 'com.apple.TextEncoding':
            if not path.endswith('.txt'):
                logging.debug('getxattr reporting UTF-8 for %s' % path)
            return 'UTF-8;'

        if id:

            icon = self.backing._icns_for(id)
            if attrname == 'com.apple.FinderInfo':
                flags = icon and kHasCustomIcon
                ostype = 4 * '\0'
                docinfo = self.backing.docs.get(id)
                if docinfo:
                    v = docinfo.get('OSType')
                    if v and isinstance(v, str):
                        ostype = v
                # type, creator, flags, misc. reserved
                finfo  = struct.pack('!4sLHHHH', ostype, 0, flags, 0, 0, 0) + 16 * '\0'
                return finfo
            if attrname == 'com.apple.ResourceFork' and icon:
                return icon

        elif type(f) == UvfsDirectory and attrname == 'com.apple.FinderInfo':
            # search folders can be renamed
            if path.startswith("/search/"):
                return 32 * '\0'
            else:
                return struct.pack('!LLHHHH', 0, 0, kNameLocked, 0, 0, 0) + 16 * '\0'
            

        return ''


    def setxattr(self, path, name, value, options, position=0):
        # 'position' only significant if "name" is "com.apple.ResourceFork"
        f = self.backing.get_chasing_symlinks(path)
        # chasing_symlinks lso loads deferred files...

        if not f:
            raise FuseError(ENOENT)

        assert type(f) in [UvfsFile, UvfsDirectory]
        if position > 0:
            # need a value to start with
            v = self.getxattr(path, name)
            if v:
                value = v[:position] + value + v[position + len(value):]
            else:
                logging.debug("* setxattr of %s on %s with non-zero position %d, but no existing attr value!",
                              name, path, position)
                raise FuseError(EACCES)
        attrs = f.stat.get("_xattr_attributes")
        if not attrs:
            f.stat["_xattr_attributes"] = { name : value }
        else:
            attrs[name] = value
        return 0
        #raise FuseError(ENOTSUP)


    def removexattr(self, path, name):
        self.setxattr(path, name, '')


    def statvfs(self, path):
        s = os.statvfs('/')  # Typically this will be the native HFS+ volume.
        return dict(f_bsize  = s.f_bsize,
                    f_frsize = s.f_frsize,
                    f_blocks = s.f_blocks,
                    f_bfree  = s.f_bfree,
                    f_bavail = s.f_bavail,
                    f_ffree  = s.f_ffree,
                    f_favail = s.f_favail,
                    f_flag   = s.f_flag,
                    f_namemax= s.f_namemax,
                    f_files=self.backing.fresh.qsize())  # number of file objects currently in RAM (view with 'df -i')

    def symlink(self, source, target):
        raise FuseError(EACCES)

    def truncate(self, path, length, fh=None):
        if fh not in self.files:
            fh = self.open(path, 0600)
        if fh in self.files:
            self.files[fh].truncate(length)
            return 0
        raise FuseError(EACCES)

    def unlink(self, path):
        f = self.backing.get(path)
        if isinstance(f, (UvfsFile, UvfsSymlink)):
            self.backing.remove(path)
            return 0
        raise FuseError(EACCES)

    def utimens(self, path, atime, mtime):
        """If `atime`, `mtime` are zero, use current time."""
        now = time.time()
        if atime == 0:
            atime = now
        if mtime == 0:
            mtime = now
        f = self.backing.get(path)
        if f:
            f.stat['st_atime'] = atime
            f.stat['st_mtime'] = mtime
            f.stat['st_ctime'] = mtime
        return 0

    def write(self, path, data, offset, fh):
        if fh not in self.files:
            raise FuseError(EBADF)
        f = self.files[fh]
        if (not f) or (not isinstance(f, UvfsFile)) or (not f.writing):
            logging.debug("** write:  bad UvfsFile %s for fd %s", f, fh)
            raise FuseError(EACCES)
        f.content.seek(offset)
        f.content.write(data)
        parent = self.backing.get_chasing_deferred_file(os.path.dirname(path))
        if parent and f.writing != f:
            parent.stat['st_mtime'] = time.time()
            f.writing.stat['st_mtime'] = time.time()
        return len(data)

# from http://code.activestate.com/recipes/87369/  by Simo Salminen 11-Nov-2001 (Python license)
import Queue
class PriorityQueue(Queue.Queue):
    """Allows Python 2.5 clients to use a 2.6 feature.

    Delete when no longer needed."""

    def _init(self, maxsize):
        # We must have a list as underlying queue.
        self.maxsize = maxsize
        self.queue = []

    def delete(item):
        # Performance is linear with queue size; log(n) would
        # be a definite improvement.
        for i in range(len(self.queue)):
            if self.fresh.queue[i][1] == item:
                note(3, 'deleting stale entry %s: %s', i, item)
                del(self.queue[i])
                return
        raise UvfsError('failed to find %s in priority queue' % item)

    def _put(self, item):
        priority, data = item
        self._insort_right((priority, data))

    def _get(self):
        return self.queue.pop(0)[1]

    def _insort_right(self, x):
        """Insert item x in list, and keep it sorted assuming a is sorted.

        If x is already in list, insert it to the right of the rightmost x."""

        a = self.queue
        lo = 0
        hi = len(a)

        while lo < hi:
            mid = (lo+hi)/2
            if x[0] < a[mid][0]: hi = mid
            else: lo = mid+1
        a.insert(lo, x)



# we make the files accessible only to the person mounting the filesystem
UID = os.getuid()
GID = os.getgid()

if __name__ == '__main__':
    print 'Please run mount_uvfs instead.'
