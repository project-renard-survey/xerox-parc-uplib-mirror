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
#
# Code to implement the repository and document objects
#

import shelve, os, sys, time, types, traceback, re, math, weakref

from uplib.plibUtil import true, false, note, lock_folder, unlock_folder, split_categories_string, create_new_id, find_class

from uplib.document import Document

class Collection (object):

    """A Collection gathers together multiple elements from the repository,
    which may be either documents or other collections.  It's a dict, mapping
    ids or collection names to elements, and also a list (sorted by the sort
    order of the keys).
    """

    def __init__(self, repository, name=None, initial_values = ()):
        """Initialize an instance.

        :param repository: the repository we're running in
        :type repository: ``repository.Repository``
        :param name: unique ID to use as the collection name.  If not specified, one is generated.
        :type name: string
        :param initial_values: a sequence of values to start off the collection with.  Defaults to empty list.
        :type initial_values: sequence of either Document or Collection instances
        """
        self.__xitems = {}                # maps id or name to element.  Elements may be documents or other collections.
        self.scantime = repository.mod_time()   # last time looked at
        self.repository = repository
        self.id = name or create_new_id()
        self.storage_path = os.path.join(repository.collections_folder(), self.id)
        if os.path.exists(self.storage_path):
            try:
                fp = open(self.storage_path, 'rb')
                self.load(fp)
                fp.close()
            except:
                type, value, tb = sys.exc_info()
                note(2, "Couldn't load collection %s:\n%s", self.id, ''.join(traceback.format_exception(type, value, tb)))
        elif initial_values:
            for item in initial_values:
                if isinstance(item, Document):
                    self.__xitems[item.id] = DocumentPointer(item)
                elif isinstance(item, Collection):
                    self.__xitems[item.name()] = CollectionPointer(item.id, item)

    def name (self):
        """Obtain the name of the collection.

        :return: the name of the collection
        :rtype: string
        """
        return self.id

    def iterdocs (self):
        """
        Return the documents in the collection.  This recursively
        descends into sub-collections, so may be arbitrarily expensive.

        :return: iteration of docs either directly or indirectly held in this collection
        :rtype: generator
        """
        self.rescan()
        for key in self.iterkeys():
            x = self[key]
            if isinstance(x, Document):
                yield x
            elif isinstance(x, Collection):
                for x in x.iterdocs():
                    yield x
            else:
                note(0, "odd non-Document non-Collection element %s in iteration", x)

    def docs (self):
        """
        Return the documents in the collection.  This recursively
        descends into sub-collections, so may be arbitrarily expensive.

        :return: sequence of document instances
        :rtype: sequence
        """
        return [x for x in self.iterdocs()]

    # pickling methods so that this can be stored on a file

    def format_storage_line (self, fp, NAME, ELEMENT):

        """Write out a line of information about the member of the collection ELEMENT,
        which has the collection-relative NAME.  ELEMENT must have an "id" attribute."""

        fp.write("%s.%s %s %s\n" % (ELEMENT.__class__.__module__, ELEMENT.__class__.__name__, ELEMENT.id, NAME))

    def store(self, directory):

        """Store this collection to a file (or files) in the given directory.
        By default, this will call format_storage_line() once for every document
        in the collection.  Subclasses that need different behavior will need to
        override store() and load().

        Note that other instances of collection may be stored in the same directory.
        """

        filepath = os.path.join(directory, self.id)
        fp = open(filepath, 'wb')

        for name, value in self.__xitems.items():
            self.format_storage_line(fp, name, value.deref())
        fp.close()

    def parse_storage_line(self, line):

        """Read and parse a line written out by format_storage_line()."""

        m = re.match('^([^\s]+) ([^\s]+) (.*)$\n', line)
        if not m:
            note("Bad collection line <%s> found in %s", line[:-1], fp)
        return m.group(1), m.group(2), m.group(3)

    def add_storage_extras(self, line):
        # read the line again and see if there's any additional info on it
        pass

    def load(self, fp):

        """Given a file produced by "store()", read in and populate SELF
        with elements."""

        lines = fp.readlines()
        for line in lines:
            classname, id, name = self.parse_storage_line(line)

            clss = find_class(classname)

            if clss and issubclass(clss, Document):
                if self.repository.valid_doc_id(id):
                    self[name] = self.repository.get_document(id)
                else:
                    note("invalid doc ID %s found in collection file %s", id, self)
            elif clss and issubclass(clss, Collection):
                c = self.repository.get_collection(id, true)
                if not c:
                    c = clss(self.repository, id)
                    self.repository.add_collection(id, c)
                self[name] = c
                self.add_storage_extras(c, line)
            else:
                note("invalid class <%s> found in collection file %s", classname, self)

    # Display methods

    def __str__(self):
        return '<' + self.__class__.__name__ + ':' + ((self.id and (' ' + self.id)) or '') + (' %d docs>' % len(self.__xitems))

    def __repr__(self):
        return self.__str__()

    # Container methods

    def rescan (self):
        """Update the list of documents.

        This is called often, and should be as cheap as possible."""

        # call this method to update our list of entries
        pass

    def __len__(self):
        self.rescan()
        return len(self.__xitems)

    def __getitem__(self, index):
        self.rescan()
        return (self.__xitems[index].deref())

    def __setitem__(self, index, value):
        if not (isinstance(value, Document) or isinstance(value, Collection)):
            raise TypeError("value %s must be a Document or Collection" % value)
        if isinstance(value, Document):
            self.__xitems[index] = DocumentPointer(value)
        elif isinstance(value, Collection):
            self.__xitems[index] = CollectionPointer(value)
        else:
            raise ValueError("Inappropriate value %s for a collection." % repr(value))
        self.rescan()

    def __delitem__ (self, index):
        if index in self.__xitems:
            del self.__xitems[index]
            self.rescan()

    def __iter__(self):
        self.rescan()
        return self.__xitems.iterkeys()

    def __contains__(self, value):
        self.rescan()
        if not isinstance(value, (Document, Collection)):
            return False
        else:
            return (value.id in self.__xitems)

    def keys(self):
        self.rescan()
        return self.__xitems.keys()

    def values(self):
        self.rescan()
        return [x.deref() for x in self.__xitems.values()]

    def items(self):
        self.rescan()
        return [(x, self.__xitems[x].deref()) for x in self.__xitems]

    def has_key(self, key):
        self.rescan()
        return self.__xitems.has_key(key)

    def get(self, key, default=None):
        self.rescan()
        v = self.__xitems.get(key, default)
        if v:
            v = v.deref()
        return v

    def clear(self):
        return self.__xitems.clear()

    def copy(self):
        self.rescan()
        return Collection(self.__xitems.values().copy())

    def update(self, mapping):
        self.rescan()
        for key, value in mapping.items():
            self[key] = value

    def iterkeys(self):
        self.rescan()
        for k in self:
            yield k

    def itervalues(self):
        self.rescan()
        for k in self:
            yield self[k]

    def iteritems(self):
        self.rescan()
        for k in self:
            yield (k, self[k])

class Pointer(object):

    REPOSITORY = None

    __slots__ = ["id", "pointer"]

    def __init__(self, ref):
        if ref:
            if hasattr(ref, "id"):
                self.id = ref.id
                self.pointer = weakref.ref(ref)
            else:
                self.id = ref
                self.pointer = None
        else:
            self.id = None
            self.pointer = None

    def deref(self):
        if self.pointer:
            v = self.pointer()
        else:
            v = None
        if not v:
            self.pointer = None
            v = self.recache()
        return v

    def recache(self):
        pass

class CollectionPointer(Pointer):

    __slots__ = ["id", "collclass", "name", "pointer"]

    def __init__(self, coll):
        self.collclass = ((coll is not None) and isinstance(coll, Collection) and "%s.%s" % (coll.__class__.__module__, coll.__class__.__name__)) or None
        self.name = (coll and isinstance(coll, Collection) and coll.name()) or None
        Pointer.__init__(self, coll)

    def recache(self):
        if self.REPOSITORY:
            clss = find_class(self.collclass or "uplib.collection.Collection")
            if clss and issubclass(clss, Collection):
                d = clss(self.REPOSITORY, self.id)
                self.REPOSITORY.add_collection(self.name, d, false)
                self.pointer = weakref.ref(d)
        return d

class DocumentPointer(Pointer):

    def recache (self):
        d = None
        if self.REPOSITORY:
            d = self.REPOSITORY.get_document(self.id)
            self.pointer = weakref.ref(d)
        return d

class QueryCollection (Collection):
    """
    A kind of collection which is populated by the results of running a query
    over the repository, a so-called "smart folder".
    """

    def __init__(self, repository, id, query=None, cutoff=0.0):
        self.query = query
        Collection.__init__(self, repository, id)
        self.xscores = {}
        self.scantime = 0
        self.cutoff = cutoff
        self.docpages = {}
        self.scanduration = 0

    def set_query(self, query):
        self.query = query
        self.scantime = 0

    def valid_in_collection (self, doc):
        return true

    def rescan (self):
        if self.repository.mod_time() > self.scantime:
            self.scantime = self.repository.mod_time()
            t1 = time.clock()
            hits = self.repository.do_full_query(self.query)
            note(4, "rescanning %s; %d hits, cutoff is %s", self, len(hits), self.cutoff)
            self.scanduration = time.clock() - t1
            self.clear()
            self.xscores.clear()
            self.docpages.clear()
            for hit in hits.values():
                # note(4, "  %s", hit)
                doc = hit.get('doc')
                score = hit.get('score')
                anypages = hit.get('pages')
                # note("  pages for %s/%f are %s", doc.id, score, anypages)
                # note(4, "   %.3f, %5s:  %s", score, self.valid_in_collection(doc), doc)
                if score >= self.cutoff and self.valid_in_collection(doc):
                    self[doc.id] = doc
                    self.xscores[doc.id] = score
                    if anypages:
                        self.docpages[doc.id] = anypages
                        

    def score(self, doc):
        self.rescan()
        return self.xscores.get(doc.id)

    def scores (self, docs=None):
        self.rescan()
        if docs:
            r = []
            for doc in docs:
                r.append((doc.id, self.xscores[doc.id]))
            return r
        else:
            return self.xscores.items()
    
    def pages (self, selector):
        if isinstance(selector, Document):
            return self.docpages.get(selector.id)
        elif (type(selector) in types.StringTypes):
            return self.docpages.get(selector)

    # Display methods

    def __str__(self):
        return '<QueryCollection: %s "%s">' % (self.id, self.query)

    def __repr__(self):
        return self.__str__()

    # pickling methods

    # pickling methods so that this can be stored on a file

    def store(self, directory):

        filepath = os.path.join(directory, self.id)
        fp = open(filepath, 'wb')
        fp.write(self.query)
        fp.close()

    def load(self, fp):

        self.query = fp.read()


class PrestoCollection (QueryCollection):

    """
    This is basically a query collection, plus explicit includes not found by the query,
    and explicit excludes which would be found by the query.
    """

    def __init__(self, repository, id, query=None, excludes=None, includes=None, cutoff=0.0):
        self.query = query
        QueryCollection.__init__(self, repository, id, query, cutoff)
        if excludes is None:
            self.excludes = list()
        else:
            self.excludes = excludes
        if includes is None:
            self.includes = list()
        else:
            self.includes = includes

    def valid_in_collection (self, doc):
        return not (self.excludes and doc.id in self.excludes)

    def rescan (self):
        QueryCollection.rescan(self)
        if self.excludes:
            for id in self.excludes:
                if id in self:
                    del self[id]
                if id in self.xscores:
                    del self.xscores[id]
        if self.includes:
            for id in self.includes:
                doc = self.repository.get_document(id)
                self[id] = doc
                self.xscores[id] = 0.0

    def store(self, directory):

        filepath = os.path.join(directory, self.id)
        fp = open(filepath, 'wb')
        fp.write("%s\n%s\n%s\n" % (self.query, self.excludes, self.includes))
        fp.close()

    def load(self, fp):
        
        self.query = fp.readline().strip()
        self.excludes = eval(fp.readline().strip())
        self.includes = eval(fp.readline().strip())

    def include_doc (self, doc):
        if doc.id in self.excludes:
            self.excludes.remove(doc.id)
        if not doc.id in self.includes:
            self.includes.append(doc.id)
        self.rescan()

    def exclude_doc (self, doc):
        if not doc.id in self.excludes:
            self.excludes.append(doc.id) 
        if doc.id in self.includes:
            self.includes.remove(doc.id)
        self.rescan()
            

def _adjust_score(score, ndocs):
    return ((score*score)/ndocs) * math.log(ndocs + math.e)

def _quote_quotes(s):
    return re.sub(r'"', r'\\"', re.sub(r'\\', r'\\\\', s))

def find_likely_collections (doc, collections=None, score_adjust=None, count=None):

    """
    Return a list of category suggestions for the given document.

    :param doc: the document under consideration
    :type doc: document.Document
    :param collections: the collections to consider.  If not specified, defaults to all collections registered with the repository.
    :type collections: set of collection.Collection
    :param score_adjust: a function taking two arguments, the raw score and the number of documents, which will produce a floating point number which is the adjusted score.
    :type score_adjust: fn(float, int) => float
    :param count: number of results to return, defaults to all
    :type count: int
    :return: list of likely collections, and scores for each collection.  Each score consists of three values:  the raw score, the number of documents which contributed to that score, and the adjusted score
    :rtype: list(collection.Collection, (float, int, float))
    """

    note(4, "find_likely_collections:  getting search context (%s)", time.ctime())
    c = doc.repo.search_context()
    note(4, "find_likely_collections:  have search context (%s)", time.ctime())
    if not c:
        return None
    if not collections:
        collections = [x[1] for x in doc.repo.list_collections()]

    # accumulate some representative text about the document
    t = doc.text()
    if (not t) or (len(t.strip()) < 20):
        t = doc.get_metadata("summary")
    else:
        t = t.strip()
    if (not t) or (len(t.strip()) < 20):
        t = doc.get_metadata("abstract")
    else:
        t = t.strip()
    if (not t) or (len(t.strip()) < 20):
        t = ""
    t2 = doc.get_metadata("comments")
    if t2 and t2.strip():
        t = t + "\n" + t2.strip()
    # notes
    ann = doc.get_notes()
    for page in ann:
        notetext = ""
        notes = ann[page]
        for n in notes:
            if n[1]:
                notetext +=  ' '.join([x for x in n[1] if x])
        ann[page] = notetext
    t2 = '\n'.join(ann.values())
    if t2 and t2.strip():
        t = t + "\n" + t2.strip()

    qstring, hits = c.like_this(t, fieldnames=["contents", "notes", "comments", "abstract"])
    note(4, "find_likely_collections:  have %d hits (%s)", len(hits), time.ctime())
    keywords = doc.get_metadata("keywords")
    if keywords:
        keywords = " OR ".join([('keywords:"' + _quote_quotes(x.strip()) + '"') for x in keywords.split(',')])
        note(4, "find_likely_collections:  searching for keywords... (%s)", time.ctime())
        keywords = c.search(keywords)
        note(4, "find_likely_collections:  found %d keywords... (%s)", len(keywords), time.ctime())
    title = doc.get_metadata("title")
    if title:
        title = [x.strip() for x in title.split() if x.strip()]
        if title:
            title = " OR ".join([('title:"' + _quote_quotes(x) + '"') for x in title if ((len(x) > 5) or
                                                                                        ((len(x) > 2) and x.strip().isupper()))])
            if title:
                note(4, "find_likely_collections:  searching for title words %s... (%s)", repr(title), time.ctime())
                title = c.search(title)
                note(4, "find_likely_collections:  found %d title words... (%s)", len(title), time.ctime())
    if not hits and not title and not keywords:
        return None

    note(4, "find_likely_collections:  creating colls...  (%s)", time.ctime())
    colls = {}

    # create mapping of doc ID to collection
    id_to_collection_mapping = {}
    for coll in collections:
        ids = coll.keys()
        for id in coll.keys():
            if id in id_to_collection_mapping:
                id_to_collection_mapping[id].append(coll)
            else:
                id_to_collection_mapping[id] = [coll,]

    for id, score, pageno in hits:
        if pageno != '*':
            continue
        if id == doc.id:
            continue
        for coll in id_to_collection_mapping.get(id, []):
            if coll in colls:
                colls[coll][0] += score
                colls[coll][1] += 1
            else:
                colls[coll] = [score, 1]
    if title:
        for id, score in title:
            if id == doc.id:
                continue
            for coll in id_to_collection_mapping.get(id, []):
                if coll in colls:
                    colls[coll][0] += score
                    colls[coll][1] += 1
                else:
                    colls[coll] = [score, 1]
    if keywords:
        for id, score in title:
            if id == doc.id:
                continue
            for coll in id_to_collection_mapping.get(id, []):
                if coll in colls:
                    colls[coll][0] += score * 2
                    colls[coll][1] += 1
                else:
                    colls[coll] = [score * 2, 1]
    if not colls:
        return None
    colls = colls.items()       # map dict to list(coll, (score, count))
    colls = [x for x in colls if x[1][1] > 0]
    # now sort by score, adjusted for ndocs
    note(4, "find_likely_collections:  sorting colls by score...  (%s)", time.ctime())
    if score_adjust is None:
        score_adjust = _adjust_score
    for tag in colls:
        tag[1].append(score_adjust(*tag[1]))
    colls.sort(lambda x, y: cmp(y[1][2], x[1][2]))
    if colls and isinstance(count, int):
        colls = colls[:min(len(colls), count)]
    note(4, "find_likely_collections:  returning %d colls  (%s)", len(colls), time.ctime())
    return colls

def suggest_collections (repo, response, params):
    """
    Given a doc, find the collections it might fit into.

    :param doc_id: the document to look at
    :type doc_id: UpLib doc ID string
    :param coll: the collection(s) to look at.  May be specified more than once.
    :type coll: UpLib collection ID string
    :return: a list of collections and scores
    :rtype: text/plain
    """
    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return
    doc = repo.valid_doc_id(doc_id) and repo.get_document(doc_id)
    if not doc:
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter '%s' specified." % doc_id)
        return
    colls = params.get("coll")
    if colls and (type(colls) in types.StringTypes):
        colls = (colls,)
    if not colls:
        colls = [x[1] for x in repo.list_collections()]
    else:
        colls = [repo.get_collection(x) for x in colls]
    suggestions = find_likely_collections(doc, colls)
    fp = response.open("text/plain")
    for (coll, (rawscore, count, adjscore)) in suggestions:
        fp.write("%6.3f  %s  (%d, %.3f)\n" % (adjscore, str(coll), count, rawscore))
    fp.close()
        
        
