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

import sys, os, re, datetime, time, string, struct, traceback, types

from uplib.plibUtil import read_metadata, note, DOC_ID_RE, COLL_ID_RE, id_to_time, split_categories_string, parse_date, set_verbosity
from uplib.collection import QueryCollection, PrestoCollection

def build_index_1_0 (repo):

    overhead_dir = repo.overhead_folder()
    index_file = os.path.join(overhead_dir, "index.upri")
    repo_mtime = repo.mod_time()
    note(3, "Considering rebuild of repository metadata index file...")
    if os.path.exists(index_file):
        # see if it's newer than the metadata.txt file
        mtime = os.path.getmtime(index_file)
        note(3, "repo mod time is %s, index file mod time is %s", repo_mtime, mtime)
        if mtime >= repo_mtime:
            note(3, "Index up-to-date.")
            return

    note("Re-building repository metadata index...")

    # need to rebuild index

    # some variables to keep track of categories and collections
    categories={}
    collections={}
    documents={}
    authors={}

    # read the repository metadata
    mdata = read_metadata(os.path.join(overhead_dir, "metadata.txt"))
    repo_password_hash = mdata.get('password')
    repo_password_hash = (repo_password_hash and binascii.a2b_hex(repo_password_hash)) or (20 * '\0')
    

    # List the number of documents

    def figure_author_name (basename):
        def clean_token(t):
            v = t.strip()
            if v[-1] == ",":
                v = v[:-1]
            return v
        honorifics = ("MD", "M.D.", "PhD", "Ph.D.", "Jr.", "Sr.", "II", "III", "IV", "V", "MPA")
        tokens = [clean_token(x) for x in basename.strip().split(' ') if x.strip()]
        if not tokens:
            note("Author name \"%s\" => %s", basename, tokens)
            return ""
        v = tokens[-1]
        h = ""
        while v in honorifics:
            h = h + ((h and " ") or "") + v
            tokens = tokens[:-1]
            v = tokens[-1]
        if len(tokens) > 2 and (tokens[-2] in ("van", "de", "von")):
            v = tokens[-2] + " " + v
            tokens = tokens[:-1]
        if tokens[:-1]:
            v = v + ", " + string.join(tokens[:-1])
        if h:
            v = v + ", " + h
        return v

    def read_document (doc, categories, collections, authors):

        def figure_date(datestring):
            d2 = parse_date(datestring)
            if (not d2) or (sum(d2) == 0):
                return 0
            return d2[0] * (13 * 32) + d2[1] * 13 + d2[2]

        docdata = {'id': doc.id, 'rloc': 0}
        mdata = doc.get_metadata()
        docdata['title'] = mdata.get('title', "")
        docdata['page-count'] = int(mdata.get('page-count', 1))
        date = mdata.get('date')
        if date:
            docdata['date'] = figure_date(date);
        else:
            docdata['date'] = 0
        docdata['addtime'] = int(id_to_time(doc.id))
        # we don't really know the reftime (FIXME) but we'll use the document add time as an approximation
        docdata['reftime'] = docdata['addtime']
        docdata['categories'] = []
        cstring = mdata.get('categories', "")
        if cstring:
            for category in split_categories_string(cstring):
                if not category in categories:
                    categories[category] = { 'rloc': 0, 'docs': [ doc.id, ], 'name': category }
                else:
                    categories[category]['docs'].append(doc.id)
                docdata['categories'].append(category)
        docdata['authors'] = []
        auths = mdata.get('authors', "").split(" and ")
        for auth in auths:
            if auth:
                authname = figure_author_name(auth)
                if not authname in authors:
                    authors[authname] = { 'rloc': 0, 'docs': [ doc.id, ], 'name': authname }
                else:
                    authors[authname]['docs'].append(doc.id)
                docdata['authors'].append(authname)
        return docdata

    for doc in repo.generate_docs():
        documents[doc.id] = read_document(doc, categories, collections, authors)

    note(3, "    processed documents...")

    # read the collections files
    for collname, coll in repo.list_collections():
        collections[coll.id] = { 'name': collname,
                                 'docs': [doc.id for doc in coll.docs()],
                                 'query': (isinstance(coll, QueryCollection) and coll.query) or "",
                                 'rloc': 0,
                                 'presto': isinstance(coll, PrestoCollection),
                                 'excludes': (isinstance(coll, PrestoCollection) and coll.excludes) or [],
                                 'includes': (isinstance(coll, PrestoCollection) and coll.includes) or [],
                                 'id': coll.id }

    note(3, "    processed collections...")
    
    # now figure out the layout of the index file

    def sorted_values(d, rname):
        def compare(r1, r2):
            v1 = r1.get(rname)
            v2 = r2.get(rname)
            if (type(v1) in types.StringTypes) and (type(v2) in types.StringTypes):
                return cmp(v1.lower(), v2.lower())
            else:
                return cmp(v1, v2)
        l = d.values()
        l.sort(compare)
        return l

    def document_record_size(r):
        return (2 + # offset to next document record
                2 + # page count
                2 + # number of categories
                2 + # number of authors
                4 + # date published
                4 + # date last used
                4 + # date added to repository
                4 * len(r.get('authors')) +
                4 * len(r.get('categories')) +
                2 + (len(r.get("id").encode("UTF-8")) + 1) +       # document ID
                2 + (len(r.get("title").encode("UTF-8")) + 1))

    def category_record_size(r):
        return (2 + # offset to next record
                2 + # number of documents
                4 * len(r.get("docs")) +    # positions of document records
                2 + (len(r.get("name").encode("UTF-8")) + 1))      # category name

    def author_record_size(r):
        return (2 + # offset to next record
                2 + # number of documents
                4 * len(r.get("docs")) +    # positions of document records
                2 + (len(r.get("name").encode("UTF-8")) + 1))      # author name

    def collection_record_size(r):
        return (2 + # offset to next record
                2 + # number of documents
                4 * len(r.get("docs")) +    # positions of document records
                2 + # number of explicitly included documents
                2 + # number of explicitly excluded documents
                4 * len(r.get("includes")) +    # explicitly included
                4 * len(r.get("excludes")) +    # explicitly excluded
                2 + (len(r.get("name").encode("UTF-8")) + 1) +     # collection name
                2 + (len(r.get("query").encode("UTF-8")) + 1))     # collection query

    def repository_record_size(r):
        return (4 + # number of docs in repository
                4 + # number of authors
                4 + # last-modified timem
                2 + # number of categories
                2 + # number of collections
                4 + # first document record
                4 + # first category record
                4 + # first collection record
                4 + # first authors record
                20 + # SHA hash of password
                2 + len(r.get("name", "").encode("UTF-8")) + 1)

    def round8 (v):
        return ((v + 7)/8)*8

    mdata['rsize'] = repository_record_size(mdata)
    mdata['rloc'] = 32
    first_doc_record = round8(mdata['rloc'] + mdata['rsize'])
    loc = first_doc_record
    for document in sorted_values(documents, 'id'):
        document['rsize'] = round8(document_record_size(document))
        document['rloc'] = loc
        loc += document['rsize']
        document['nextoffset'] = document['rsize']
    first_categories_record = loc
    for category in sorted_values(categories, 'name'):
        category['rsize'] = round8(category_record_size(category))
        category['rloc'] = loc
        loc += category['rsize']
        category['nextoffset'] = category['rsize']
    first_collections_record = loc
    for collection in sorted_values(collections, 'name'):
        collection['rsize'] = round8(collection_record_size(collection))
        collection['rloc'] = loc
        loc += collection['rsize']
        collection['nextoffset'] = collection['rsize']
    first_author_record = loc
    for author in sorted_values(authors, 'name'):
        author['rsize'] = round8(author_record_size(author))
        author['rloc'] = loc
        loc += author['rsize']
        author['nextoffset'] = author['rsize']

    note(3, "    figured layout...");

    # output data for debugging

    note(4, "repository name:  %s", mdata.get("name"))
    note(3, "Documents (%d) at %s:", len(documents), first_doc_record)
    for document in documents.values():
        note(4, "  %s\n      %s // %s pages // date %s // %s // %s",
             document['title'], document['authors'], document['page-count'], document['date'], document['id'], document['rloc'])
    note(3, "Categories (%d) at %s:", len(categories), first_categories_record)
    for category in categories.values():
        note(4, "  %s // %d docs // %s", category['name'], len(category['docs']), category['rloc'])
    note(3, "Collections (%d) at %s:", len(collections), first_collections_record)
    for collection in collections.values():
        note(4, "  %s // %s // %d docs // %s", collection['name'], collection['query'], len(collection['docs']), collection['rloc'])
    for author in authors.values():
        note(4, "  %s // %d docs // %s", author['name'], len(author['docs']), author['rloc'])
        for doc in author['docs']:
            r = documents.get(doc)
            note(4, "     %s \"%s\"", r['id'], r['title'])
    note(3, "total size is %s", loc)

    # output the index file

    def out4(fp, v):
        fp.write(struct.pack(">I", v & 0xFFFFFFFF))

    def out2(fp, v):
        fp.write(struct.pack(">H", v & 0xFFFF))

    def outs(fp, v):
        s = (v and v.encode('UTF-8')) or ""
        fp.write(struct.pack(">H", (len(s) + 1) & 0xFFFF) + s + '\0')

    fp = open(index_file, "wb")

    try:
        # index version header
        magic = u"UpLib Repository Index 1.0".encode('US-ASCII')
        fp.write(magic + ('\0' * (32-len(magic))))

        # write out repository information
        out4(fp, len(documents))
        out4(fp, len(authors))
        out4(fp, int(repo_mtime))      # seconds since 1/1/1970
        out2(fp, len(categories))
        out2(fp, len(collections))
        out4(fp, first_doc_record)
        out4(fp, first_categories_record)
        out4(fp, first_collections_record)
        out4(fp, first_author_record)
        fp.write(repo_password_hash)
        outs(fp, mdata.get("name", ""))

        # for each document record, write that
        for document in sorted_values(documents, 'rloc'):
            note(4, "document %s at %s [%s]", document['id'], document['rloc'], document['rsize'])
            fp.seek(document['rloc'])
            out2(fp, document['nextoffset'])
            out2(fp, document['page-count'])
            out2(fp, len(document['categories']))
            out2(fp, len(document['authors']))
            out4(fp, document['date'])
            out4(fp, document['reftime'])
            out4(fp, document['addtime'])
            for a in document['authors']:
                r = authors.get(a)
                out4(fp, (r and r.get('rloc')) or 0)
            for c in document['categories']:
                r = categories.get(c)
                out4(fp, (r and r.get('rloc')) or 0)
            outs(fp, document['id'])
            outs(fp, document['title'])
            fp.flush()

        # write out categories
        for category in sorted_values(categories, 'rloc'):
            note(4, "category %s at %s [%s]", category['name'], category['rloc'], category['rsize'])
            fp.seek(category['rloc'])
            out2(fp, category['nextoffset'])
            out2(fp, len(category['docs']))
            for docid in category['docs']:
                r = documents.get(docid)
                out4(fp, (r and r.get('rloc')) or 0)
            outs(fp, category['name'])
            fp.flush()

        # write out collections
        for collection in sorted_values(collections, 'rloc'):

            note(4, "collection %s at %s [%s] includes=%s excludes=%s", collection['name'], collection['rloc'], collection['rsize'],
                 ((not collection['presto']) and 0xFFFF) or len(collection['includes']),
                 ((not collection['presto']) and 0xFFFF) or len(collection['excludes']))

            fp.seek(collection['rloc'])
            out2(fp, collection['nextoffset'])
            out2(fp, len(collection['docs']))
            for docid in collection['docs']:
                r = documents.get(docid)
                out4(fp, (r and r.get('rloc')) or 0)
            includes = collection['includes']
            excludes = collection['excludes']
            out2(fp, ((not collection['presto']) and 0xFFFF) or len(includes))
            out2(fp, ((not collection['presto']) and 0xFFFF) or len(excludes))
            for docid in includes:
                r = documents.get(docid)
                out4(fp, (r and r.get('rloc')) or 0)
            for docid in excludes:
                r = documents.get(docid)
                out4(fp, (r and r.get('rloc')) or 0)
            outs(fp, collection['name'])
            outs(fp, collection['query'])
            fp.flush()

        # write out authors
        for author in sorted_values(authors, 'rloc'):
            note(4, "author %s at %s [%s]", author['name'], author['rloc'], author['rsize'])
            fp.seek(author['rloc'])
            out2(fp, author['nextoffset'])
            out2(fp, len(author['docs']))
            for docid in author['docs']:
                r = documents.get(docid)
                out4(fp, (r and r.get('rloc')) or 0)
            outs(fp, author['name'])
            fp.flush()

        # finished
        fp.close()
        note(3, "wrote index at %s", os.path.getmtime(index_file))

    except:
        excinfo = sys.exc_info()
        fp.close()
        os.unlink(index_file)
        note(0, "exception %s", traceback.format_exception(*excinfo))

def build_index_1_1 (repo):

    overhead_dir = repo.overhead_folder()
    index_file = os.path.join(overhead_dir, "index.upri")
    repo_mtime = repo.mod_time()
    note(3, "Considering rebuild of repository metadata index file...")
    if os.path.exists(index_file):
        # see if it's newer than the metadata.txt file
        mtime = os.path.getmtime(index_file)
        note(3, "repo mod time is %s, index file mod time is %s", repo_mtime, mtime)
        if mtime >= repo_mtime:
            note(3, "Index up-to-date.")
            return

    note("Re-building repository metadata index...")

    # need to rebuild index

    # some variables to keep track of categories and collections
    categories={}
    collections={}
    documents={}
    authors={}

    # read the repository metadata
    mdata = read_metadata(os.path.join(overhead_dir, "metadata.txt"))
    repo_password_hash = mdata.get('password')
    repo_password_hash = (repo_password_hash and binascii.a2b_hex(repo_password_hash)) or (20 * '\0')
    

    # List the number of documents

    def figure_author_name (basename):
        def clean_token(t):
            v = t.strip()
            if v[-1] == ",":
                v = v[:-1]
            return v
        honorifics = ("MD", "M.D.", "PhD", "Ph.D.", "Jr.", "Sr.", "II", "III", "IV", "V", "MPA")
        tokens = [clean_token(x) for x in basename.strip().split(' ') if x.strip()]
        if not tokens:
            note("Author name \"%s\" => %s", basename, tokens)
            return ""
        v = tokens[-1]
        h = ""
        while v in honorifics:
            h = h + ((h and " ") or "") + v
            tokens = tokens[:-1]
            v = tokens[-1]
        if len(tokens) > 2 and (tokens[-2] in ("van", "de", "von")):
            v = tokens[-2] + " " + v
            tokens = tokens[:-1]
        if tokens[:-1]:
            v = v + ", " + string.join(tokens[:-1])
        if h:
            v = v + ", " + h
        return v

    def read_document (doc, categories, collections, authors):

        def figure_date(datestring):
            d2 = parse_date(datestring)
            if (not d2) or (sum(d2) == 0):
                return 0
            return d2[0] * (13 * 32) + d2[1] * 13 + d2[2]

        docdata = {'id': doc.id, 'rloc': 0}
        mdata = doc.get_metadata()
        docdata['title'] = mdata.get('title', "")
        docdata['page-count'] = int(mdata.get('page-count', 1))
        date = mdata.get('date')
        if date:
            docdata['date'] = figure_date(date);
        else:
            docdata['date'] = 0
        docdata['addtime'] = int(id_to_time(doc.id))
        # we don't really know the reftime (FIXME) but we'll use the document add time as an approximation
        docdata['reftime'] = docdata['addtime']
        docdata['categories'] = []
        cstring = mdata.get('categories', "")
        if cstring:
            for category in split_categories_string(cstring):
                if not category in categories:
                    categories[category] = { 'rloc': 0, 'docs': [ doc.id, ], 'name': category }
                else:
                    categories[category]['docs'].append(doc.id)
                docdata['categories'].append(category)
        docdata['authors'] = []
        auths = mdata.get('authors', "").split(" and ")
        for auth in auths:
            if auth:
                authname = figure_author_name(auth)
                if not authname in authors:
                    authors[authname] = { 'rloc': 0, 'docs': [ doc.id, ], 'name': authname }
                else:
                    authors[authname]['docs'].append(doc.id)
                docdata['authors'].append(authname)
        return docdata

    for doc in repo.generate_docs():
        documents[doc.id] = read_document(doc, categories, collections, authors)

    note(3, "    processed documents...")

    # read the collections files
    for collname, coll in repo.list_collections():
        collections[coll.id] = { 'name': collname,
                                 'docs': [doc.id for doc in coll.docs()],
                                 'query': (isinstance(coll, QueryCollection) and coll.query) or "",
                                 'rloc': 0,
                                 'presto': isinstance(coll, PrestoCollection),
                                 'excludes': (isinstance(coll, PrestoCollection) and coll.excludes) or [],
                                 'includes': (isinstance(coll, PrestoCollection) and coll.includes) or [],
                                 'id': coll.id }

    note(3, "    processed collections...")
    
    # now figure out the layout of the index file

    def sorted_values(d, rname):
        def compare(r1, r2):
            v1 = r1.get(rname)
            v2 = r2.get(rname)
            if (type(v1) in types.StringTypes) and (type(v2) in types.StringTypes):
                return cmp(v1.lower(), v2.lower())
            else:
                return cmp(v1, v2)
        l = d.values()
        l.sort(compare)
        return l

    def document_record_size(r):
        return (2 + # offset to next document record
                2 + # page count
                2 + # number of categories
                2 + # number of authors
                4 + # date published
                4 + # date last used
                4 + # date added to repository
                4 * len(r.get('authors')) +
                4 * len(r.get('categories')) +
                2 + (len(r.get("id").encode("UTF-8")) + 1) +       # document ID
                2 + (len(r.get("title").encode("UTF-8")) + 1))

    def category_record_size(r):
        return (2 + # offset to next record
                2 + # number of documents
                4 * len(r.get("docs")) +    # positions of document records
                2 + (len(r.get("name").encode("UTF-8")) + 1))      # category name

    def author_record_size(r):
        return (2 + # offset to next record
                2 + # number of documents
                4 * len(r.get("docs")) +    # positions of document records
                2 + (len(r.get("name").encode("UTF-8")) + 1))      # author name

    def collection_record_size(r):
        return (2 + # offset to next record
                2 + # number of documents
                4 * len(r.get("docs")) +    # positions of document records
                2 + # number of explicitly included documents
                2 + # number of explicitly excluded documents
                4 * len(r.get("includes")) +    # explicitly included
                4 * len(r.get("excludes")) +    # explicitly excluded
                2 + (len(r.get("name").encode("UTF-8")) + 1) +     # collection name
                2 + (len(r.get("query").encode("UTF-8")) + 1))     # collection query

    def repository_record_size(r):
        return (4 + # number of docs in repository
                4 + # number of authors
                4 + # last-modified timem
                2 + # number of categories
                2 + # number of collections
                4 + # first document record
                4 + # first category record
                4 + # first collection record
                4 + # first authors record
                20 + # SHA hash of password
                2 + len(r.get("name", "").encode("UTF-8")) + 1)

    def round8 (v):
        return ((v + 7)/8)*8

    mdata['rsize'] = repository_record_size(mdata)
    mdata['rloc'] = 32
    first_doc_record = round8(mdata['rloc'] + mdata['rsize'])
    loc = first_doc_record
    for document in sorted_values(documents, 'id'):
        document['rsize'] = round8(document_record_size(document))
        document['rloc'] = loc
        loc += document['rsize']
        document['nextoffset'] = document['rsize']
    first_categories_record = loc
    for category in sorted_values(categories, 'name'):
        category['rsize'] = round8(category_record_size(category))
        category['rloc'] = loc
        loc += category['rsize']
        category['nextoffset'] = category['rsize']
    first_collections_record = loc
    for collection in sorted_values(collections, 'name'):
        collection['rsize'] = round8(collection_record_size(collection))
        collection['rloc'] = loc
        loc += collection['rsize']
        collection['nextoffset'] = collection['rsize']
    first_author_record = loc
    for author in sorted_values(authors, 'name'):
        author['rsize'] = round8(author_record_size(author))
        author['rloc'] = loc
        loc += author['rsize']
        author['nextoffset'] = author['rsize']

    note(3, "    figured layout...");

    # output data for debugging

    note(4, "repository name:  %s", mdata.get("name"))
    note(3, "Documents (%d) at %s:", len(documents), first_doc_record)
    for document in documents.values():
        note(4, "  %s\n      %s // %s pages // date %s // %s // %s",
             document['title'], document['authors'], document['page-count'], document['date'], document['id'], document['rloc'])
    note(3, "Categories (%d) at %s:", len(categories), first_categories_record)
    for category in categories.values():
        note(4, "  %s // %d docs // %s", category['name'], len(category['docs']), category['rloc'])
    note(3, "Collections (%d) at %s:", len(collections), first_collections_record)
    for collection in collections.values():
        note(4, "  %s // %s // %d docs // %s", collection['name'], collection['query'], len(collection['docs']), collection['rloc'])
    for author in authors.values():
        note(4, "  %s // %d docs // %s", author['name'], len(author['docs']), author['rloc'])
        for doc in author['docs']:
            r = documents.get(doc)
            note(4, "     %s \"%s\"", r['id'], r['title'])
    note(3, "total size is %s", loc)

    # output the index file

    def out4(fp, v):
        fp.write(struct.pack(">I", v & 0xFFFFFFFF))

    def out2(fp, v):
        fp.write(struct.pack(">H", v & 0xFFFF))

    def outs(fp, v):
        s = (v and v.encode('UTF-8')) or ""
        fp.write(struct.pack(">H", (len(s) + 1) & 0xFFFF) + s + '\0')

    fp = open(index_file, "wb")

    try:
        # index version header
        magic = u"UpLib Repository Index 1.1".encode('US-ASCII')
        fp.write(magic + ('\0' * (32-len(magic))))

        # write out repository information
        out4(fp, len(documents))
        out4(fp, len(authors))
        out4(fp, int(repo_mtime))      # seconds since 1/1/1970
        out2(fp, len(categories))
        out2(fp, len(collections))
        out4(fp, first_doc_record)
        out4(fp, first_categories_record)
        out4(fp, first_collections_record)
        out4(fp, first_author_record)
        fp.write(repo_password_hash)
        outs(fp, mdata.get("name", ""))

        # for each document record, write that
        for document in sorted_values(documents, 'rloc'):
            note(4, "document %s at %s [%s]", document['id'], document['rloc'], document['rsize'])
            fp.seek(document['rloc'])
            out2(fp, document['nextoffset'])
            out2(fp, document['page-count'])
            out2(fp, len(document['categories']))
            out2(fp, len(document['authors']))
            out4(fp, document['date'])
            out4(fp, document['reftime'])
            out4(fp, document['addtime'])
            for a in document['authors']:
                r = authors.get(a)
                out4(fp, (r and r.get('rloc')) or 0)
            for c in document['categories']:
                r = categories.get(c)
                out4(fp, (r and r.get('rloc')) or 0)
            outs(fp, document['id'])
            outs(fp, document['title'])
            fp.flush()

        # write out categories
        for category in sorted_values(categories, 'rloc'):
            note(4, "category %s at %s [%s]", category['name'], category['rloc'], category['rsize'])
            fp.seek(category['rloc'])
            out2(fp, category['nextoffset'])
            out2(fp, len(category['docs']))
            for docid in category['docs']:
                r = documents.get(docid)
                out4(fp, (r and r.get('rloc')) or 0)
            outs(fp, category['name'])
            fp.flush()

        # write out collections
        for collection in sorted_values(collections, 'rloc'):

            note(4, "collection %s at %s [%s] includes=%s excludes=%s", collection['name'], collection['rloc'], collection['rsize'],
                 ((not collection['presto']) and 0xFFFF) or len(collection['includes']),
                 ((not collection['presto']) and 0xFFFF) or len(collection['excludes']))

            fp.seek(collection['rloc'])
            out2(fp, collection['nextoffset'])
            out2(fp, len(collection['docs']))
            for docid in collection['docs']:
                r = documents.get(docid)
                out4(fp, (r and r.get('rloc')) or 0)
            includes = collection['includes']
            excludes = collection['excludes']
            out2(fp, ((not collection['presto']) and 0xFFFF) or len(includes))
            out2(fp, ((not collection['presto']) and 0xFFFF) or len(excludes))
            for docid in includes:
                r = documents.get(docid)
                out4(fp, (r and r.get('rloc')) or 0)
            for docid in excludes:
                r = documents.get(docid)
                out4(fp, (r and r.get('rloc')) or 0)
            outs(fp, collection['name'])
            outs(fp, collection['query'])
            fp.flush()

        # write out authors
        for author in sorted_values(authors, 'rloc'):
            note(4, "author %s at %s [%s]", author['name'], author['rloc'], author['rsize'])
            fp.seek(author['rloc'])
            out2(fp, author['nextoffset'])
            out2(fp, len(author['docs']))
            for docid in author['docs']:
                r = documents.get(docid)
                out4(fp, (r and r.get('rloc')) or 0)
            outs(fp, author['name'])
            fp.flush()

        # finished
        fp.close()
        note(3, "wrote index at %s", os.path.getmtime(index_file))

    except:
        excinfo = sys.exc_info()
        fp.close()
        os.unlink(index_file)
        note(0, "exception %s", traceback.format_exception(*excinfo))

def main (argv):

    if len(argv) < 1 or (not os.path.isdir(argv[0])):
        sys.stderr.write("Invalid directory specified.\n")
        sys.exit(1)

    set_verbosity(4)
    files = os.listdir(argv[0])
    if ("docs" in files) and ("overhead" in files):
        from uplib.repository import Repository
        from uplib.plibUtil import configurator

        uplib_version = configurator().get("UPLIB_VERSION")
        r = Repository(uplib_version, argv[0], read_metadata(os.path.join(argv[0], "overhead", "metadata.txt")))

        build_index_1_0(r)

if __name__ == "__main__":
    main(sys.argv[1:])
