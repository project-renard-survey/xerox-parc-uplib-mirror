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


# sample URL:  https://taste.parc.xerox.com:2080/action/UVFS/mod_time

import base64
import mimetypes
import os
import re
import struct
import sys
import threading
import time
import types
import zlib
from xml.dom.minidom import getDOMImplementation

from uplib.addDocument import CONTENT_TYPES
from uplib.collection import PrestoCollection
from uplib.document import Document
from uplib.plibUtil import configurator, uthread, note
from uplib.webutils import get_content_type, get_extension_for_type, HTTPCodes

def echo(repo, response, params):
    """Params is a dict listing HTTP query components.  Try /action/UVFS/echo?a=1&b=2."""
    response.reply(str(params), 'text/plain')

def current_version(repo, response, params):
    """Returns the extension code's CVS tag."""
    version = '$Id: UVFS.py,v 1.32 2010/02/20 20:00:40 janssen Exp $'
    response.reply(version, 'text/plain')

def repo_root(repo, response, params):
    """Return the path where 'docs', 'pending', and 'overhead' are stored."""
    response.reply(repo.root(), 'text/plain')

def repo_root_and_most_recent_docid(repo, response, params):
    """Return two items needed at mount time."""
    id = '0'  # definitely not a valid doc_id
    if len(repo.history()) > 0:    # empty (newly created) repo?
        id = repo.history()[0].id  # The first one is the most recently touched.
    response.reply(id + ' ' + repo.root(), 'text/plain')

def _first_dir(path):
    """Returns a directory name, e.g. '/var/ubidocs/jhanley'."""
    for e in sorted(os.listdir(path)):
        path1 = os.path.join(path, e)
        if os.path.isdir(path1):
            return path1
    return path

if sys.platform == "darwin":

    import xattr            # this is pre-supplied by Apple on Macs

    #import macerrors  # We would import, but for some non-ASCII encoding errors.
    resFNotFound    =   -193    #Resource file not found

    # see /System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/CarbonCore.framework/Versions/A/Headers/Finder.h
    kHasCustomIcon                = 0x0400
    kHasBundle                    = 0x2000
    kCustomIconResource           = -16455 #/* Custom icon family resource ID */

    # ee /System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/CarbonCore.framework/Versions/A/Headers/Files.h
    kFSCatInfoTextEncoding        = 0x00000001
    kFSCatInfoFinderInfo          = 0x00000800

    class FinderPoint:
        """Represents vert. & horiz. coordinates of a desktop icon."""
        def __init__(self, v, h):
            self.data = struct.pack('!hh', v, h)  # two signed 16-bit quantities

    class FInfo:
        """Represents a Finder Info structure."""
        def __init__(self):
            fdType = 0
            fdCreator = 0      # NB: OSType is 32-bits
            fdLocation = FinderPoint(0, 0).data
            fdFldr = 0
            self.data = struct.pack('!LLH', fdType, fdCreator, kHasCustomIcon) + \
                '\0' * 22  # fdLocation + struct.pack('!H', fdFldr) + ...

    def icns(doc):
        """Return first.png's ResourceFork (icons for the Finder)."""
        icon = ''
        rforkpath = os.path.join(doc.folder(), "thumbnails", "mac-icon.rsrc")
        if not os.path.exists(rforkpath):
            try:
                from uplib.macstuff import MacRipper
                MacRipper(doc.repo).rip(doc.folder(), doc.id)
                if os.path.exists(rforkpath):
                    icon = open(rforkpath, 'rb').read()
            except ImportError:
                # macstuff not there yet
                note(0, "Not using macstuff for Mac icons resource fork for %s:\n%s", doc,
                     ''.join(traceback.format_exception(*sys.exc_info())))
                if os.path.exists(doc.icon_path()) and \
                     'com.apple.ResourceFork' in xattr.listxattr(doc.icon_path()):
                    icon = xattr.getxattr(doc.icon_path(), 'com.apple.ResourceFork')
                    assert xattr.getxattr(doc.icon_path(), 'com.apple.FinderInfo') == FInfo().data
        else:
            icon = open(rforkpath, 'rb').read()
        return base64.b64encode(zlib.compress(icon, 9))

else:
    # not darwin
    def icns(doc):
        return None

def get_docids_with_categories(repo, response, params):
    response.reply(str(repo.get_docids_with_categories()), 'text/plain')

def get_categories_with_docs(repo, response, params):
    """For each category in the repo, returns 'name,id1 id2 ... idN'."""
    result = []
    for cat, ids in repo.get_categories_with_docs().iteritems():
        if cat == '':
            continue  # Is the empty category *really* a "category"?
        if ',' in cat:
            raise ValueError('comma not allowed in category name: ' + cat)
        # Relieve the caller of the burden of checking for validity.
        valid_ids = [id for id in ids  if repo.valid_doc_id(id)]
        if valid_ids:
            result.append('%s,%s' % (cat, ' '.join(valid_ids)))
    response.reply('\n'.join(sorted(result)) + '\n', 'text/plain')

def get_categories(repo, response, params):
    """Returns all categories that tag documents in the repo.

    Suppresses categories that appear only on deleted documents.
    """
    result_cats = set()  # Contains only categories which tag valid docs.
    for cat, ids in repo.get_categories_with_docs().iteritems():
        if cat == '':
            continue
        if ',' in cat:
            raise ValueError('comma not allowed in category name: ' + cat)
        s = set(ids)
        while len(s) > 0 and cat not in result_cats:
            if repo.valid_doc_id(s.pop()):
                result_cats.add(cat)

    response.reply('\n'.join(sorted(result_cats)), 'text/plain')


def get_ids_and_docnames_by_category(repo, response, params):
    """Reply with a dict mapping each category to a list of (id, name) tuples."""
    categories = repo.get_categories_with_docs()
    for cat in categories:
        docs = []
        for id in categories[cat]:
            doc = get_document_if_valid(repo, id)
            if not doc:
                continue
            if doc.get_metadata('title-is-original-filepath') == 'true':
                name = os.path.basename(doc.name())
            else:
                name = doc.name()  # Titles that mention "and/or" won't be mangled.
            docs.append((id, name))
        categories[cat] = docs
    response.reply(str(categories), 'text/plain')

def mod_time(repo, response, params):
    """Report the timestamp for the most recent change of *anything* in the repo."""
    # float, seconds since the epoch
    response.reply(str(repo.mod_time()), 'text/plain')

def patient_mod_time(repo, response, params):
    """Report a timestamp, same as mod_time(), but take perhaps a minute to do so.

    The caller must specify 'last_mod_time' and 'max_delay'.
    If mod_time is fresher than last_mod_time, it is returned at once.
    Else we wait, in case mod_time changes.  If so, the new mod_time
    is returned as soon as it changes.  If not, then max_delay seconds
    after the initial query, we return the current mod_time, which,
    of course, is identical to the last_mod_time supplied by the caller.
    """
    last = params['last_mod_time']
    max_delay = min(int(params['max_delay']), 300)  # Clamp to 5 minutes.
    epsilon = 0.009  # Add 9ms is OK, as incoming stamps have 10ms granularity.
    if repo.mod_time() > epsilon + float(last):
        return response.reply(str(repo.mod_time()))
    last = repo.mod_time()  # Avoid annoying FP roundoff.
    response.fork_request(_bg_mod_time, repo, response, last, max_delay)

def _bg_mod_time(repo, response, last, max_delay):
    """Reports mod_time to web client shortly after max_delay seconds, typically.

    Upon noticing a mod_time change, this background thread will report at once. 
    """
    deadline = time.time() + max_delay
    while repo.database() and time.time() < deadline and repo.mod_time() == last:
        time.sleep(0.080)  # human perceptual threshold
    response.reply(str(repo.mod_time()), 'text/plain')
    # At shutdown time, first __database becomes None, then hooks are called.
    # We exit immediately at shutdown time, but it would be better to register
    # a UVFS shutdown hook which simply advances mod_time.

def matching_docids(repo, response, params):
    """Search for documents matching query=terms and return zero or more ids.

    The list of document ids is whitespace delimited.
    There is no support for cutoff/narrow/widen; the intended use is mostly
    for querying unique text which will match exactly one document."""
    # This is an abbreviated version of basicPlugins.py _repo_search().
    query = params['query']
    cutoff = 0.0
    coll = PrestoCollection(repo, None, query, None, None, cutoff)
    response.reply(' '.join([doc.id for doc in coll.docs()]), 'text/plain')


INTERACTION_CHARSET = None

def matching_ids_and_filenames(repo, response, params):
    """Search for documents matching query=terms and return zero or more matches.

    Each line lists a matching document as:  doc_id ' ' filename
    """
    # This is an abbreviated version of basicPlugins.py _repo_search().
    query = params['query']
    global INTERACTION_CHARSET
    if not INTERACTION_CHARSET:
        conf = configurator.default_configurator()
        INTERACTION_CHARSET = conf.get('interaction-charset', 'UTF-8')
    query = unicode(query, INTERACTION_CHARSET, 'replace')
    cutoff = 0.0
    coll = PrestoCollection(repo, None, query, None, None, cutoff)
    result = []
    for doc in coll.docs():
        title, mtype = doc_title_and_type(doc)
        result.append('%s %s' % (doc.id, title))

    response.reply('\n'.join(result), 'text/plain')


def originals_filename(repo, response, params):
    """Return a filename (with no slashes) for a doc_id."""
    id = params['doc_id']
    filename = originals_filename_for_doc(repo.get_document(id))
    response.reply(filename, 'text/plain')


def originals_filename_for_doc(doc):
    """Return a filename (with no slashes) for a document."""
    # Typically just a single file is in originals/
    # or 'original.html' + 'original_files/' for WebPage,Complete.
    filename = doc.id
    if os.path.exists(doc.originals_path()):
        files = sorted(os.listdir(doc.originals_path()))
        if len(files) > 0:
            filename = files[0]
    return filename

def get_contenttype(doc):
    """Returns a good MIME content-type for a document, obeying its apparent-mime-type if present."""
    filename = doc.get_metadata('title') or doc.original_name() or doc.id
    ct = get_content_type(filename)
    if doc.get_metadata('content-type'):
        ct = doc.get_metadata('content-type')
    if doc.get_metadata('apparent-mime-type'):
        ct = doc.get_metadata('apparent-mime-type')
    if ct == 'application/octet-stream':
        ct = 'text/plain'
    # NB:  add_document() will get 415 HTTPCodes.UNSUPPORTED_MEDIA_TYPE
    # if we fail to pick one of the known repo.content_types(), e.g.
    # an attempt to use 'application/octet-stream'.
    return ct

def is_good_extension(ext):
    """Boolean, true if uploading with this file extension could succeed.

    That is, after mapping the extension to a content-type, we will want
    extensions/UploadDocument.py's _add_internal to find it in CONTENT_TYPES.
    """
    if ext.startswith('.'):  # e.g. might be ''
        ext = ext[1:]
    # get_content_type() punts on '.JPG' &c., letting mimetypes.guess_type() deal with it.
    ext = ext.lower()
    ct = get_content_type('foo.' + ext)
    if ct == 'application/octet-stream':
        return False  # This binary type is absolutely unacceptable to _add_internal.
    return get_extension_for_type(ct) == ext and ext in CONTENT_TYPES.values()

def title_with_good_suffix(repo, response, params):
    """Return a title for doc_id which reflects the MIME type."""
    id = params['doc_id']
    filename, mtype = doc_title_and_type(repo.get_document(id))
    response.reply(filename, 'text/plain')

def doc_title_with_good_suffix(doc):
    """Return title (perhaps unchanged) which reflects the MIME type.

    For example, a text/plain 'Readme' will be mapped to 'Readme.txt'."""
    orig_filename, orig_ext = os.path.splitext(originals_filename_for_doc(doc))
    wpc = _check_for_webpage_complete(doc.originals_path())
    if wpc:
        orig_filespec, orig_ext = os.path.splitext(wpc)     
    filename = doc.get_metadata('title') or doc.original_name() or doc.id
    filename = os.path.basename(filename).strip(' \t.,-;')
    filename = re.sub('[^A-Za-z0-9 \._-]+', '_', filename)  # sanitize charset
    assert '\r' not in filename
    assert '\n' not in filename
    orig_ext = orig_ext.lower()
    # e.g. for 'ReadMe', orig_ext == ''
    if orig_ext and \
            filename.lower().endswith(orig_ext) and \
            is_good_extension(orig_ext):
        return filename
    # Popular entries from mimetypes.common_types not found in CONTENT_TYPES:
    #  image/pict .{pct,pic,pict}, application/rtf .rtf (no uplib parser)
    # Popular entries from mimetypes.types_map not found in CONTENT_TYPES:
    #  audio .aiff + many more, video .avi + many more, text .bat .h .c .css,
    #  html .htm .xml, msword .dot, image .bmp .jpeg .tiff, postscript .eps

    # Originals lacked an extension, or had a bad extension.  Synthesize one.
    fallback_ext = get_extension_for_type(doc.get_metadata('apparent-mime-type') or \
                                          doc.get_metadata('content-type') or \
                                          'text/plain')
    ext = ((orig_ext and is_good_extension(orig_ext) and orig_ext) or fallback_ext)
    assert is_good_extension(ext)
    if not ext.startswith("."):
        ext = "." + ext
    return filename + ext

def doc_title_and_type (doc):

    """Return title (perhaps unchanged) which reflects the MIME type.

    For example, a text/plain 'Readme' will be mapped to 'Readme.txt'."""

    title = doc.get_metadata("title")
    if title:
        filename = re.sub('[^A-Za-z0-9 \._-]+', '_', title.strip(' \t.,-;'))
    elif doc.original_name():
        filename = os.path.basename(doc.original_name()).strip(' \t.,-;')
    else:
        filename = doc.id
    assert '\r' not in filename
    assert '\n' not in filename

    # OK, we have a filename, now get the MIME type
    mtype = doc.get_metadata("apparent-mime-type")
    if not mtype:
        # look at the original name
        oname = doc.original_name()
        if oname:
            mtype = get_content_type(oname.lower())
        else:
            odir = doc.originals_path()
            if os.path.isdir(odir) and _check_for_webpage_complete(odir):
                mtype = "text/html"
    if not mtype:
        # fallback to text/plain
        mtype = "text/plain"

    return filename, mtype

def get_document_if_valid(repo, id):
    """Return None, or a doc which is valid and has 1 or 2 files in originals/."""
    if not repo.valid_doc_id(id):  # Perhaps it was just a *formerly* valid ID.
        return None
    doc = repo.get_document(id)
    if len(os.listdir(doc.originals_path())) not in [1, 2]:  # regular, or WPC
        return None
    return doc

def doc_metadata_for_category(repo, response, params):
    """Return a metadata 4-tuple for each document in a category.

    The metadata items are docID, mtime, size, and a filename (with no
    slashes or odd characters); they are whitespace delimited.

    Deprecated, in favor of the XML version."""
    filenames = []
    category = params['category'].lower()
    repo._update_categories_file()  # New tags are visible faster if we do this.
    for cat, ids in repo.get_categories_with_docs().iteritems():
        if cat == category:
            for id in ids:
                doc = get_document_if_valid(repo, id)
                if not doc:
                    continue
                originals = doc.originals_path()
                orig_fspec = _check_for_webpage_complete(originals)
                if not orig_fspec:
                     orig_fspec = os.path.join(originals,
                                               os.listdir(originals)[0])
                mtime = os.stat(orig_fspec).st_mtime
                size  = os.stat(orig_fspec).st_size
                filename, mtype = doc_title_and_type(doc)
                filenames.append('%s\t%s\t%s\t%s' % (
                    id, mtime, size, filename))
    filenames.sort()
    response.reply('\n'.join(filenames), 'text/plain')

def _ends_with_html(filespec):
    return filespec.endswith('.html') or filespec.endswith('.htm')

def _check_for_webpage_complete(path):
    """Returns .html filespec, or None if not a WPC, same as the deeply-scoped method in externalAPI.py fetch_original."""
    files = sorted(os.listdir(path))
    if len(files) != 2:
        return None
    if files[0].endswith(' Files') and _ends_with_html(files[1]):
        return os.path.join(path, files[1])
    if files[1].endswith('_files') and _ends_with_html(files[0]):
        return os.path.join(path, files[0])
    return None

def _add_metadata(doc, result):
    """Append a document's metadata to a results list."""
    wpc = _check_for_webpage_complete(doc.originals_path())
    orig_fspec = wpc or os.path.join(doc.originals_path(),
                                     os.listdir(doc.originals_path())[0])
    mtime = os.stat(orig_fspec).st_mtime
    size  = os.stat(orig_fspec).st_size
    filename, mime = doc_title_and_type(doc)
    empty = 'eNoDAAAAAAE='  # This is what '' looks like after gzip & b64
    icnsdata = empty
    if sys.platform == "darwin":
        if icns(doc) == empty:
            os.system('/usr/bin/sips -i %s > /dev/null' % doc.icon_path())
        icnsdata = icns(doc)
        assert icnsdata
    md = doc.get_metadata()
    pagecount = int(md.get('page-count') or md.get('pagecount') or '1')
    fmt = 'id %s, mtime %s, sha-hash %s, is_wpc %s, pagecount %d, size %s, apparent-mime-type %s, icns %s, filename %s'
    result.append(fmt % (doc.id, mtime, doc.sha_hash(), wpc is not None,
                         pagecount, size, mime, icnsdata, filename))

def metadata_for_docs(repo, response, params):
    """Return any metadata the client might possibly want, for one doc_id."""
    result = []
    ids = params.get('id') or params.get('doc_id')
    if not ids:
        response.error(HTTPCodes.BAD_REQUEST, "No doc id specified.")
        return

    if (type(ids) in types.StringTypes) and repo.valid_doc_id(ids):
        docs = [repo.get_document(ids),]
    else:
        docs = [repo.get_document(id) for id in ids if repo.valid_doc_id(id)]
    for doc in docs:
        _add_metadata(doc, result)
    response.reply('\n'.join(result), 'text/plain')


def docs_for_category (repo, response, params):
    category_name = params.get("category")
    if not category_name:
        response.error(HTTPCodes.BAD_REQUEST, "No category parameter specified")
        return

    docs = repo.get_docs_by_category(category_name)
    fp = response.open("text/plain")
    if docs:
        for doc in docs:
            fp.write("%s %s\n" % (doc.id, doc.sha_hash()))
    fp.close()
                  

def metadata_for_category(repo, response, params):
    """Return any metadata the client might possibly want, for each document in a category."""
    filenames = {}  # maps to docs with unique filenames.
    zero = Document(repo, '0000-00-0000-000')
    category = params['category'].lower()
    repo._update_categories_file()
    for cat, ids in repo.get_categories_with_docs().iteritems():
        if cat == category:
            for id in ids:
                doc = get_document_if_valid(repo, id)
                if not doc:
                    continue
                filename, mtype = doc_title_and_type(doc)
                if filenames.get(filename, zero).id < doc.id:
                    filenames[filename] = doc  # new docs overwrite older ones
    result = []
    for doc in filenames.values():
        _add_metadata(doc, result)
    result.sort()
    response.reply('\n'.join(result), 'text/plain')

def categories_for_doc(repo, response, params):
    """Returns all category strings that doc_id is tagged with."""
    id = params.get('id') or params['doc_id']
    doc = repo.get_document(id)
    for cat in doc.get_category_strings():
        assert ',' not in cat
    response.reply(', '.join(doc.get_category_strings()), 'text/plain')
