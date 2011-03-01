# -*- Python -*-
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

"""The documented external network API for UpLib
"""

__version__ = "$Revision: 1.59 $"
__author__ = "Bill Janssen"
__docformat__ = "restructuredtext"

import sys, os, re, string, cgi, time, traceback, urllib, types, zipfile, tempfile, base64
from xml.dom.minidom import getDOMImplementation

from uplib.plibUtil import subproc, configurator, Error, read_metadata, true, false, note, update_metadata, split_categories_string, id_to_time, read_metadata, zipup, write_metadata, header_value_encode, Job

from uplib.webutils import HTTPCodes, parse_URL, http_post_multipart, htmlescape

# for fetch_document_text
from uplib.createPageBboxes import get_page_bboxes

INTERACTION_CHARSET = "UTF-8"

def upload_document (repository, response, fields):

    """Upload a complete UpLib document folder to the repository.  Used by `uplib-add-document`.

    :Parameters:
        file
          the folder, as a zip file or tar file.  Using a tar file is considered obsolete.
        filetype
          must be either 'tarred-folder' or 'zipped-folder'
        format
          the format of the response to send back.  If 'xml', an XML document will be generated,
          containing a single text node called 'id', containing the document ID of the new document,
          but the default is to send back simply the new doc ID as a plain text string.
        title
          optionally, the title of the document
        id
          optionally, a pre-assigned doc ID to use.  If there is no folder with this ID in the
          `pending` directory, this will raise an error.
        authors
          optionally, a list of authors, each name separated from the next with the string " and ".
        source
          optionally, a string describing the source of the document.
        date
          optionally, an UpLib-format date string `[[DD/]MM/]YYYY`
        keywords
          optionally, a comma-separated list of keywords to associate with the document
        categories
          optionally, a comma-separated list of categories (tags) to associate with the document
        abstract
          optionally, an abstract for the document
        citation
          optionally, a citation in some citation format for the document
        comment
          optionally, some text giving a comment on the document
    :return: the document ID for the new document
    :rtype: plain text string, or if XML is specified, an XML ``result`` element containing an ``id`` node with the ID as its text
    """

    global INTERACTION_CHARSET

    def possibly_set (db, fields, valuename, unfold_lines=false):
        if fields.has_key(valuename):
            if unfold_lines:
                value = string.replace(string.replace(fields[valuename], '\n', ' '), '\r', ' ')
            else:
                value = fields[valuename]
            value = unicode(value, INTERACTION_CHARSET, "replace")
            db[valuename] = value

    if not INTERACTION_CHARSET:
        conf = configurator.default_configurator()
        INTERACTION_CHARSET = conf.get('interaction-charset', 'UTF-8')

    if (not fields.has_key('newfile')) or (not fields.has_key('filetype')):
        response.error(HTTPCodes.BAD_REQUEST, "Badly formed upload request.\n")
        return

    known_content_types = repository.content_types()

    msgtag = ""
    try:

        doc_bits = fields['newfile']
        doc_type = fields['filetype']

        if not doc_type in known_content_types:
            response.error(HTTPCodes.UNSUPPORTED_MEDIA_TYPE, "Can't upload files of type '%s'.\n" % doc_type)
            return

        metadata = {}
        possibly_set(metadata, fields, "title")
        possibly_set(metadata, fields, "id")
        possibly_set(metadata, fields, "authors")
        possibly_set(metadata, fields, "source")
        possibly_set(metadata, fields, "date")
        possibly_set(metadata, fields, "keywords")
        possibly_set(metadata, fields, "categories")
        possibly_set(metadata, fields, "abstract", true)
        possibly_set(metadata, fields, "citation", true)
        possibly_set(metadata, fields, "comment", true)
        possibly_set(metadata, fields, "name")

        note(2, "Adding new document; len(bits) = %d, type='%s'", len(doc_bits), doc_type)
        id = repository.create_new_document(doc_bits, doc_type, metadata)

        # update the global list of categories
        categories_value = fields.has_key('categories') and fields['categories']
        cleaned_categories = (categories_value and
                              map(lambda x: string.strip(x), string.split(categories_value, ','))) or []
        db_categories = repository.categories()
        for category in cleaned_categories:
            if not category in db_categories:
                repository.add_category(category)

        if response.xml_request or (fields.get("format") == "xml"):

            retval = getDOMImplementation().createDocument(None, "result", None)
            e = retval.createTextNode('id')
            e.data = id
            retval.documentElement.appendChild(e)
            fp = response.open("application/xml;charset=utf-8")
            fp.write(retval.toxml("UTF-8") + "\n")
            fp.close()
            return

        else:

            fp = response.open("text/plain")
            fp.write(id)
            fp.close()
            return

    except:

        typ, ex, tb = sys.exc_info()
        raise ex, None, tb

def remove_documents (repository, response, params):
    """Remove one or more documents, specified by document ID, from the repository.

    :param doc_id: The ID of the document to remove.  May be specified more than once, to remove \
           multiple documents in one call.
    :type doc_id: UpLib doc ID string
    :param check: Whether to check for ID validity before trying to delete them.  Defaults to ``False``. \
           This may cause HTTP 404 errors to be thrown; if that happens, no documents will have been deleted.
    :type check: boolean
    :return: list of documents deleted, by ID, one per line.  Note that some IDs may not appear \
             on this list if some other client deleted them while this process was running, \
             or if the ``check`` parameter was not specified and the document ID wasn't valid.
    :rtype: text/plain
    """
    ids = params.get("doc_id")
    check = params.get("check")
    if type(ids) in types.StringTypes:
        # single doc
        ids = (ids, )
    if check:
        for id in ids:
            if not repository.valid_doc_id(id):
                response.error(HTTPCodes.NOT_FOUND, id)
                return
    fp = response.open("text/plain")
    for id in ids:
        try:
            repository.delete_document(id)
        except ValueError, x:
            # invalid doc ID
            pass
        else:
            fp.write(id + "\n")
    fp.close()            


def search_repository (repository, response, params):
    """Search repository using specified query, and return hits (matching documents)
    as either a comma-separated values list of (score, ID, title) lines,
    or as an XML document, or as a zipped folder which includes the ``metadata.txt``
    file and the document icon for each hit.

    TODO:  the exact format of the XML bundle should be documented here.

    :param query: an UpLib query string
    :type query: string
    :param no-icon: optional, indicates whether to not return icons in the ziplist format, defaults to ``False``
    :type no-icon: boolean
    :param format: optional, indicates whether to return results as plain-text CSV, XML, or a Zip file. \
           if not specified, the plain-text CSV file is returned.
    :type format: string, either ``"xml"`` or ``"ziplist"``
    :return: a listing of the documents matching the query, in the specified format
    :rtype: either ``text/plain``, ``application/xml``, or ``application/x-uplib-searchresults-zipped``
    """

    from uplib.basicPlugins import get_buttons_sorted, FN_DOCUMENT_SCOPE

    if not params.has_key('query'):
        response.error(HTTPCodes.BAD_REQUEST, "No query specified.\n")
        return

    query = unicode(params.get('query'), INTERACTION_CHARSET, "replace")
    results = repository.do_query(query)
    results.sort()
    results.reverse()

    def get_doc_functions (doc):
        buttons = get_buttons_sorted(FN_DOCUMENT_SCOPE)
        retval = ""
        for button in buttons:
            if (not button[1][5]) or (button[1][5](doc)):
                url = button[1][4]
                if url is None:
                    url = "/action/basic/repo_userbutton?uplib_userbutton_key=%s&doc_id=%%s" % button[0]
                retval += "%s, %s, %s, %s\n" % (button[0], url, button[1][3], button[1][0])
        return retval

    no_icon = (params.get("no-icon") == "true")

    if response.xml_request or (params.get("format") == "xml"):

        retval = getDOMImplementation().createDocument(None, "result", None)
        e = retval.createElement('query')
        e.setAttribute('query', query)
        retval.documentElement.appendChild(e)
        for score, doc in results:
            e = retval.createElement('hit')
            e.setAttribute('doc_id', doc.id)
            e.setAttribute('score', str(score))
            title = doc.get_metadata("title") or u""
            title = title.replace("\r", " ")
            note("title is '%s'", title)
            e.setAttribute('title', title)
            retval.documentElement.appendChild(e)
        fp = response.open("application/xml;charset=utf-8")
        fp.write(retval.toxml("UTF-8") + "\n")
        fp.close()
        return

    elif params.get("format") == "ziplist":
        include_doc_functions = params.get("include-doc-functions")
        tpath = tempfile.mktemp()
        zf = zipfile.ZipFile(tpath, "w")
        try:
            try:
                for score, doc in results:
                    zf.writestr(doc.id.encode("ASCII", "strict") + "/", "")
                    zf.writestr(doc.id.encode("ASCII", "strict") + "/score", str(score))
                    if not no_icon:
                        zf.writestr(doc.id.encode("ASCII", "strict") + "/first.png", doc.document_icon())
                    if include_doc_functions:
                        zf.writestr(doc.id.encode("ASCII", "strict") + "/doc_functions.txt", get_doc_functions(doc))
                    zf.writestr(doc.id.encode("ASCII", "strict") + "/metadata.txt", doc.metadata_text())
            finally:
                zf.close()
            response.return_file("application/x-uplib-searchresults-zipped", tpath, true)
        except:
            msg = string.join(traceback.format_exception(*sys.exc_info()))
            os.remove(tpath)
            note("Exception building zipfile for search results:\n%s", msg)
            response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "Can't build zipfile for search results:\n%s\n" % htmlescape(msg))
    else:

        fp = response.open('text/plain; charset=UTF-8')
        for score, doc in results:
            title = doc.get_metadata("title") or u""
            title = title.replace("\r", " ")
            fp.write("%f,%s,%s\n" % (score, doc.id, title.encode("UTF-8", "replace")))
        fp.close()

    return

def fetch_document_info (repository, response, params):
    """
    Return the metadata and icon for each of the specified documents.
    You can either pass a number of `doc_id` parameters, or POST a content
    which consists of a number of doc IDs, one per line, text/plain.

    :param doc_id: the document to fetch the info for.  This may be specified \
    more than once to fetch info for multiple documents in a single call.
    :type doc_id: an UpLib doc ID string
    :param format: optional, can be specified as "xml" to return the results as an XML document instead \
    of a zip file.  Or you can specify the HTTP Accept header as "application/xml" to obtain \
    the same result.
    :type format: string constant "xml"
    :return: the metadata and document icon for the specified documents
    :rtype: an XML data structure, if the "Accept: application/xml" header \
    was passed in the request, otherwise a zip file containing one folder \
    for each document, that folder being named with the document ID of that document. \
    """
    doc_ids = params.get("doc_id")
    if doc_ids:
        if type(doc_ids) in types.StringTypes:
            doclist = repository.valid_doc_id(doc_ids) and [repository.get_document(doc_ids),]
        else:
            doclist = [repository.get_document(id) for id in doc_ids if repository.valid_doc_id(id)]
    else:
        content_type = response.request.get_header('content-type')
        if content_type != "text/plain":
            note("fetch_document_info:  bad content-type %s", content_type)
            if not content_type:
                response.error(HTTPCodes.BAD_REQUEST, "IDs must be specified as a 'content' of type text/plain, one ID per line")
            else:
                response.error(HTTPCodes.BAD_REQUEST, "Invalid content-type " + str(content_type) + "; IDs must be specified as a 'content' of type text/plain, one ID per line");
            return

        if not response.content:
            note("fetch_document_info:  empty content")
            response.error(HTTPCodes.BAD_REQUEST, "No data in message")
            return

        if hasattr(response.content, "seek"):
            response.content.seek(0, 0)

        doclist = []
        id = response.content.readline().strip()
        while id:
            if repository.valid_doc_id(id):
                doclist.append(repository.get_document(id))
            else:
                response.error(HTTPCodes.NOT_FOUND, "Invalid doc-id %s specified" % id)
                return
            id = response.content.readline().strip()

    if not doclist:
            response.error(HTTPCodes.BAD_REQUEST, "No documents specified")
            return

    if response.xml_request or (params.get("format") == "xml"):

        retval = getDOMImplementation().createDocument(None, "result", None)
        for doc in doclist:
            d = retval.createElement('document')
            d.setAttribute('id', doc.id)
            title = doc.get_metadata("title") or u""
            title = title.replace("\r", " ")
            d.setAttribute('title', title)
            md = retval.createElement('metadata')
            dmd = doc.get_metadata()
            for element in dmd:
                md.setAttribute(element, dmd[element])
            d.appendChild(md)
            icon = retval.createElement('icon')
            t = retval.createTextNode(base64.encodestring(doc.document_icon()).strip())
            icon.appendChild(t)
            d.appendChild(icon)
            retval.documentElement.appendChild(d)
        fp = response.open("application/xml;charset=utf-8")
        fp.write(retval.toxml("UTF-8") + "\n")
        fp.close()
        return

    else:

        tpath = tempfile.mktemp()
        zf = zipfile.ZipFile(tpath, "w")
        try:
            try:
                for doc in doclist:
                    zf.writestr(doc.id.encode("ASCII", "strict") + "/", "")
                    zf.writestr(doc.id.encode("ASCII", "strict") + "/first.png", doc.document_icon())
                    zf.writestr(doc.id.encode("ASCII", "strict") + "/metadata.txt", doc.metadata_text())
            finally:
                zf.close()
            response.return_file("application/x-uplib-docinfo-zipped", tpath, true)
        except:
            os.remove(tpath)
            response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "Can't build zipfile for search results")
    return

def search_document_pages (repository, response, params):
    """
    Search the pages of the specified document for the specified query.
    Returns a list of matching pages.

    :param doc_id: the document to search.
    :type doc_id: an UpLib doc ID string
    :param query: the thing to search for
    :type query: an UpLib search query string
    :param format: optional, can be specified as "xml" to return the results as an XML \
           document instead of a zip file.  Or you can specify the HTTP Accept header as \
           "application/xml" to obtain the same result.
    :type format: string constant "xml"

    :return: the metadata and document icon for the specified documents
    :rtype: an XML data structure, if the "Accept: application/xml" header \
            was passed in the request, otherwise a zip file containing one folder \
            for each document, that folder being named with the document ID of that document.
    """
    if not params.has_key('doc_id'):
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id specified.\n")
        return
    doc_id = params.get('doc_id')
    if not repository.valid_doc_id(doc_id):
        response.error(HTTPCodes.NOT_FOUND, "Invalid doc_id %s specified.\n" % doc_id)
        return
    query = params.get("query")
    if not query:
        response.error(HTTPCodes.BAD_REQUEST, "No query specified.\n")
        return
    
    doc = repository.get_document(doc_id)
    results = doc.do_page_search(unicode(query, INTERACTION_CHARSET, "replace"))

    if response.xml_request or (params.get("format") == "xml"):

        retval = getDOMImplementation().createDocument(None, "result", None)
        e = retval.createElement('query')
        e.setAttribute('query', query)
        e.setAttribute('doc_id', doc_id)
        retval.documentElement.appendChild(e)
        for score, pageno in results:
            e = retval.createElement('hit')
            e.setAttribute('page_index', str(pageno))
            e.setAttribute('score', str(score))
            retval.documentElement.appendChild(e)
        fp = response.open("application/xml;charset=utf-8")
        fp.write(retval.toxml("UTF-8") + "\n")
        fp.close()
        return

    else:

        fp = response.open('text/plain')
        for score, pageno in results:
            fp.write("%f,%s,%d\n" % (score, doc.id, pageno))
        fp.close()
        return


def fetch_folder (repository, response, params):
    """
    Return a document's UpLib folder as a zip file.

    :param doc_id: the document to fetch
    :type doc_id: UpLib doc ID string

    :return: a zipped UpLib document folder
    :rtype: zipped directory tree, as MIME type "application/x-uplib-folder-zipped"
    """
    if not params.has_key('doc_id'):
        response.error(HTTPCodes.BAD_REQUEST, "No query specified.\n")
        return
    doc_id = params.get('doc_id')
    if not repository.valid_doc_id(doc_id):
        response.error(HTTPCodes.NOT_FOUND, "Invalid doc_id %s specified.\n" % doc_id)
        return
    location = repository.doc_location(doc_id)
    tfilename = zipup(location)
    response.return_file("application/x-uplib-folder-zipped", tfilename, true)

def repo_index (repository, response, params):
    """
    Fetch the repository index of the document.  This may have the usually harmless side-effect
    of saving the repository, if no index for the repository has been created yet.

    :param modtime: Optional.  If supplied, and if the repository has not been modified since this time, this call wil return an HTTP "not modified" code, instead of the repository index.
    :type modtime: a string containing a floating point number giving seconds past the Python (UNIX) epoch.

    :return: the repository index
    :rtype: a binary structure containing a 'sketch' of the current state of the repository. See the ARCHITECTURE document for more information on the structure of this data. Uses MIME type "application/x-uplib-repository-index".

    """

    modtime = params.get("modtime")
    if modtime is not None:
        modtime = float(modtime.strip())
        note("modtime is %s, repository.mod_time() is %s", modtime, repository.mod_time())
        if repository.mod_time() <= modtime:
            response.error(HTTPCodes.NOT_MODIFIED, "Not modified since %s" % time.ctime(modtime))
            return

    fname = os.path.join(repository.overhead_folder(), "index.upri")
    if not os.path.exists(fname):
        repository.save(force = True)
    if os.path.exists(fname):
        response.return_file("application/x-uplib-repository-index", fname, false)
    else:
        response.error(HTTPCodes.NOT_FOUND, "No index file for this repository.")

def fetch_original (repository, response, params):
    """
    Return the original bits of the document.  If the document original is multi-file,
    a zipfile containing all the parts is returned, with MIME type "application/x-folder-zipped".
    With one exception -- if the document is multi-file and a Web page,
    and if the user has specified the "browser" parameter,
    the response is an HTTP redirect to the stored version of the Web page,
    rather than an actual value.

    :param doc_id: the document to retrieve
    :type doc_id: an UpLib doc ID string
    :param browser: optional, indicates whether the result is for display in browser
    :type browser: boolean
    :return: the document original
    :rtype: bits or possibly a redirect
    """

    def check_for_webpage_complete(d):
        files = os.listdir(d)
        files.sort()
        if len(files) != 2:
            return None
        if files[0].endswith(" Files") and (files[1].endswith(".html") or files[1].endswith(".htm")):
            return files[1]
        if files[1].endswith("_files") and (files[0].endswith(".html") or files[0].endswith(".htm")):
            return files[0]
        return None

    if not params.has_key('doc_id'):
        response.error(HTTPCodes.BAD_REQUEST, "No query specified.\n")
        return
    doc_id = params.get('doc_id')
    if not repository.valid_doc_id(doc_id):
        response.error(HTTPCodes.NOT_FOUND, "Invalid doc_id %s specified.\n" % doc_id)
        return

    doc = repository.get_document(doc_id)
    originals_dir = doc.originals_path()
    format = doc.get_metadata("apparent-mime-type") or "application/octet-stream"
    if os.path.isdir(originals_dir):
        files = os.listdir(originals_dir)
        master = check_for_webpage_complete(originals_dir)
        if not files:
            response.error(HTTPCodes.NOT_FOUND, "No originals for that document %s.\n" % doc_id)
        if len(files) == 1:
            #note("returning single file %s (%s)", os.path.join(originals_dir, files[0]), format)
            response.return_file(format, os.path.join(originals_dir, files[0]))
        elif params.has_key("browser") and os.path.exists(os.path.join(originals_dir, "original.html")):
            #note("redirecting to /docs/%s/originals/original.html" % doc_id)
            response.redirect("/docs/%s/originals/original.html" % doc_id)
        elif params.has_key("browser") and master:
            #note("redirecting to /docs/%s/originals/%s" ,doc_id, master)
            response.redirect("/docs/%s/originals/%s" % (doc_id, master))
        else:
            tfilename = zipup(originals_dir)
            #note("returning zipfile %s", tfilename)
            response.return_file("application/x-folder-zipped", tfilename, true)
    else:
        response.error(HTTPCodes.NOT_FOUND, "No originals for that document %s.\n" % doc_id)


def repo_properties (repo, response, params):
    """
    Return the properties of the repository.  These include values like
    `name`, `port`, `uplib-home`, `uplib-bin`, `uplib-lib`, `uplib-version`,
    `categories` (a comma-separated list of category names),
    `docs` (a comma-separated list of doc IDs), `collections` (a comma-separated list
    of collection IDs), `last-modified-time` (a timestamp with the last-modified
    time of the repository, as a floating point string giving seconds past the Unix epoch).

    :return: the repository properties specified above
    :rtype: either an XML-formatted data set, if "Accept: application/xml" is specified, \
            or a plain text list of properties, with one per line (lines can be very long)
    """
    d = {}
    d['name'] = repo.name()
    d['port'] = repo.port()
    d['uplib-home'] = configurator.default_configurator().get("uplib-home")
    d['uplib-bin'] = configurator.default_configurator().get("uplib-bin")
    d['uplib-lib'] = configurator.default_configurator().get("uplib-lib")
    d['uplib-version'] = configurator.default_configurator().get("UPLIB_VERSION")
    c = repo.categories()
    c.sort(lambda x, y: cmp(string.lower(x), string.lower(y)))
    d['categories'] = ','.join(c)
    d['docs'] = ','.join([doc.id for doc in repo.generate_docs()])
    d['collections'] = ','.join([x.id for x in repo.list_collections()])
    d['last-modified-time'] = str(repo.mod_time())

    if response.xml_request or (params.get("format") == "xml"):

        retval = getDOMImplementation().createDocument(None, "repository", None)
        e = retval.createElement('properties')
        for element in d:
            e.setAttribute(element, str(d[element]))
        retval.documentElement.appendChild(e)
        fp = response.open("application/xml;charset=utf-8")
        fp.write(retval.toxml("UTF-8") + "\n")
        fp.close()
        return

    else:

        fp = response.open("text/plain")
        write_metadata(fp, d)
        fp.close()

def doc_metadata (repo, response, params):
    """
    Return the metadata for the specified document.

    :param doc_id: the document to fetch the info for.
    :type doc_id: an UpLib doc ID string
    :param format: optional, can be specified as "xml" to return the results as \
           an XML document instead of a zip file.  Or you can specify the \
           HTTP Accept header as "application/xml" to obtain the same result.
    :type format: string constant "xml"
    :return: the metadata for the specified documents
    :rtype: an XML data structure, if the "Accept: application/xml" header \
            was passed in the request, otherwise a value of MIME type "text/rfc822-headers".
    """

    id = params.get("doc_id");
    if not id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified for request.\n")
        return

    if not repo.valid_doc_id(id):
        response.error(HTTPCodes.NOT_FOUND, "Invalid doc_id parameter %s specified for request.\n" % params.get("doc_id"))
        return

    doc = repo.get_document(id)

    if response.xml_request or (params.get("format") == "xml"):

        retval = getDOMImplementation().createDocument(None, "result", None)
        d = retval.createElement('document')
        d.setAttribute('id', doc.id)
        title = doc.get_metadata("title") or u""
        title = title.replace("\r", " ")
        d.setAttribute('title', title)
        md = retval.createElement('metadata')
        dmd = doc.get_metadata()
        for element in dmd:
            md.setAttribute(element, dmd[element])
        d.appendChild(md)
        retval.documentElement.appendChild(d)
        fp = response.open("application/xml;charset=utf-8")
        fp.write(retval.toxml("UTF-8") + "\n")
        fp.close()
        return

    else:

        fp = response.open("text/rfc822-headers")
        write_metadata(fp, doc.get_metadata())
        fp.close()


def reserve_document_id (repo, response, params):
    """Reserve and return an UpLib document ID.

    :param format: optional parameter to select XML return value
    :type format: string constant "xml" to select XML return value
    :return: either text/plain document ID string, or XML "result" element \
             containing a text string which is the reserved doc ID.
    """

    folder = repo.create_document_folder(repo.pending_folder())
    id = os.path.basename(folder)

    if response.xml_request or (params.get("format") == "xml"):

        retval = getDOMImplementation().createDocument(None, "result", None)
        e = retval.createTextNode('id')
        e.data = id
        retval.documentElement.appendChild(e)
        fp = response.open("application/xml;charset=utf-8")
        fp.write(retval.toxml("UTF-8") + "\n")
        fp.close()

    else:

        fp = response.open("text/plain")
        fp.write(id + "\n")
        fp.close()

def fetch_job_output (repo, response, params):

    jobid = params.get("jobid");
    if not jobid:
        note("fetch_job_output:  no jobid specified in call")
        response.error(HTTPCodes.BAD_REQUEST, "No jobid specified.")
        return

    j = Job.find_job(jobid)
    if not j:
        note("fetch_job_output:  bad jobid %s specified in call, known jobs are %s" % (jobid, str(Job.JOB_TABLE)))
        response.error(HTTPCodes.NOT_FOUND, "Invalid jobid %s specified." % jobid)
        return

    fp = response.open("application/json")
    t = '{ finished: %s, percentage: %s, output: "%s" }\n' % (
        (j.running() and "false") or "true",
        j.get_percent_done(),
        string.replace(string.replace(j.get_output(), '"', '\\"'), '\n', '\\n'))
    fp.write(t)
    if not j.running():
        Job.finish_job(jobid)
    fp.close()

def _accum_generator(doc, pages):
    pagecount = int(doc.get_metadata("page-count") or doc.get_metadata("pagecount"))
    first_page = True
    for page_index in range(pagecount):
        if pages and (page_index not in pages):
            continue
        if (not first_page):
            yield 0          # signal pagebreak
        pagedata = get_page_bboxes(os.path.join(doc.folder(), "thumbnails"), page_index)
        if pagedata:
            first_page = False
            accum = None
            for box in pagedata.boxes:
                if accum:
                    accum.append(box)
                else:
                    accum = [box]
                if not (box.ends_word or (box.ends_line and not box.inserted_hyphen)):
                    continue
                yield accum
                accum = None


def fetch_document_text (repo, response, params):
    """
    Return the text of the specified document.

    :param doc_id: the document to fetch the text of.
    :type doc_id: an UpLib doc ID string
    :param page_index: which page to retrieve the text of.  This can be specified multiple \
           times to retrieve the text of all pages.  If not specified, all pages \
           are returned.  Indices which don't actually exist in the document are ignored.       
    :type page_index: integer
    :param show_pos_tags: whether to include the part-of-speech tags for the text, \
           if available.  Uses the Xerox LinguistX POS tag set \
           (http://www.cis.upenn.edu/~cis639/docs/inxight/tagging.html).  This is \
           off by default.
    :type show_pos_tags: string constant "true"
    :param format: optional, can be specified as "xml" to return the results as \
           an XML document instead of plain text.  Or you can specify the \
           HTTP Accept header as "application/xml" to obtain the same result.
    :type format: string constant "xml"
    :return: the text of specified pages the document, or all pages if not explicitly \
             specified.  Either as plain text, one sentence per line, with formfeeds between \
             different pages and vertical tabs between paragraphs, or as an XHTML data \
             structure.    
    :rtype: an XHTML data structure, if the "Accept: application/xml" header \
            was passed in the request, otherwise "text/plain".
    """
    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id specified.")
        return
    if type(doc_id) not in types.StringTypes:
        response.error(HTTPCodes.BAD_REQUEST, "Too many doc_id parameters specified.  Only one is allowed.")
        return
    if not repo.valid_doc_id(doc_id):
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id specified.")
        return
    doc = repo.get_document(doc_id)
    postags = (params.get("show_pos_tags") == "true")
    page = params.get("page_index")
    if page:
        if type(page) in types.StringTypes:
            pages = [int(page)]
        else:
            pages = [int(x) for x in page]
    else:
        pages = None

    if response.xml_request or (params.get("format") == "xml"):
        impl = getDOMImplementation()
        retval = impl.createDocument("http://www.w3.org/1999/xhtml", "html",
                                     impl.createDocumentType('html',
                                                             '-//W3C//DTD XHTML 1.0 Strict//EN',
                                                             'http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd'))
        retval.documentElement.setAttribute("xmlns", "http://www.w3.org/1999/xhtml")
        retval.documentElement.setAttribute("uplib-doc-id", doc.id)
        body = retval.createElement('body')
        retval.documentElement.appendChild(body)

        current_para = None
        current_sentence = None
        page_top = 0
        pts_per_page = (int(doc.get_metadata("images-height")) * 72.0) / (int(doc.get_metadata("images-dpi") or 300))
        for accum in _accum_generator(doc, pages):
            if (accum == 0):         # new page
                page_top += pts_per_page
                page_top += 36
                continue
            box = accum[0]
            if box.begins_paragraph:
                current_para = retval.createElement('p')
                current_para.setAttribute("page", u"" + doc.page_index_to_page_number_string(box.page.page_index))
                body.appendChild(current_para)
            if current_para and box.begins_sentence:
                current_sentence = retval.createElement('span')
                current_sentence.setAttribute("class", u"sentence")
                current_para.appendChild(current_sentence)
            if current_sentence:
                if not box.begins_paragraph:
                    current_sentence.appendChild(retval.createTextNode(u' '));
                text = u''.join([x.string() for x in accum])
                if not text.strip():
                    continue
                span = retval.createElement('span')
                span.setAttribute("class", u"word")
                span.appendChild(retval.createTextNode(text.strip()))
                current_sentence.appendChild(span)
                if postags:
                    part_of_speech = box.part_of_speech_tag()
                    if part_of_speech:
                        span.setAttribute("part-of-speech", u"" + part_of_speech)
                face = (box.italic and "Italic") or "Regular"
                family = (box.fixed_width and "Monospace") or (box.serif_font and "Serif") or "Sans-Serif"
                weight = (box.bold and "Bold") or "Regular"
                span.setAttribute(
                    "style",
                    u"font-family:%s;font-style:%s;font-weight:%s;font-size:%spt;" % (
                        family, face, weight, box.font_size,))
                span.setAttribute("content-position", str(box.text_position + box.page.start_pos))
        fp = response.open("application/xhtml+xml;charset=utf-8")
        fp.write(retval.toxml("UTF-8") + "\n")
        fp.close()
    else:
        fp = response.open("text/plain;charset=UTF-8")
        first_on_page = True
        for accum in _accum_generator(doc, pages):

            if accum == 0:
                fp.write("\n\f")
                first_on_page = True
                continue

            if accum[0].begins_paragraph:
                if first_on_page:
                    fp.write("\n")
                else:
                    fp.write("\n\x0b\n")
                first_on_page = False
            elif accum[0].begins_sentence:
                fp.write("\n")
            else:
                fp.write(" ")
            text = u''.join([x.string() for x in accum])
            fp.write(text.strip().encode("UTF-8", "replace"))
            if postags:
                part_of_speech = accum[0].part_of_speech_tag()
                if part_of_speech:
                    fp.write("/" + part_of_speech)
        fp.close()
