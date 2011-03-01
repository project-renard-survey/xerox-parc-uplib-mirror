# -*- Python -*-
#
# Code to implement the repository objects
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

import os, sys, string, time, hashlib, thread, traceback, re, types, warnings, logging, atexit, shutil

import uplib.plibUtil as plibUtil
from uplib.newFolder import create as newFolder_create
from uplib.newFolder import start_incorporation_thread, retry_folders
from uplib.createIndexEntry import index_folder, remove_from_index
from uplib.ripper import get_default_rippers
from uplib.plibUtil import note, lock_folder, unlock_folder, split_categories_string, subproc, Error, configurator, set_threaded, find_class, read_metadata, update_metadata, MutexLock, create_new_id, DOC_ID_RE, COLL_ID_RE, uthread, utf_8_encode, utf_8_decode, write_metadata, LimitedOrderedDict, HIER_DOC_ID_RE, set_verbosity, ensure_file, check_repository_in_list, set_note_sink, set_default_configuration_sections, get_fqdn, set_configuration_port
from uplib.repindex import build_index_1_0
from uplib.collection import Collection, PrestoCollection, QueryCollection, CollectionPointer, Pointer
from uplib.document import Document
from uplib.extensions import find_and_load_extension
from uplib.addDocument import MissingResource


TheRepository = None

def _compare_docs(doc1, doc2):
    # newest-first
    if doc1.id < doc2.id: return 1      # doc1 is older than doc2
    if doc1.id > doc2.id: return -1     # doc1 is newer than doc2
    return 0

def _compare_docs_by_pubdate(doc1, doc2):
    # newest-first
    if doc1.get_date() < doc2.get_date(): return 1      # doc1 is older than doc2
    if doc1.get_date() > doc2.get_date(): return -1     # doc1 is newer than doc2
    return 0

def _compare_docs_by_usage_time(repo, doc1, doc2):
    # most-recently-used first
    t1 = doc1.touch_time()
    t2 = doc2.touch_time()
    if (t1 > t2): return -1
    if (t2 > t1): return 1
    return 0

class cookie (object):
    def __init__ (self, name, value, timeout):
        self.__name = name
        self.__value = value
        self.__timeout = timeout

    def name(self):
        return self.__name

    def value(self):
        return self.__value

    def expiration_time(self):
        return self.__timeout

    def formatted_expiration_time(self):
        return time.strftime("%a, %d-%b-%Y %H:%M:%S GMT", time.gmtime(self.__timeout))

def _walk_hierarchy (topdir, level=0, prefix=None):

    if prefix is None:
        prefix = []
    for filename in os.listdir(topdir):
        fpath = os.path.join(topdir, filename)
        #print level, prefix, fpath, os.path.isdir(fpath), HIER_DOC_ID_RE[level].match(filename)
        if os.path.isdir(fpath) and HIER_DOC_ID_RE[level].match(filename):
            prefix2 = prefix + [filename,]
            if level >= (len(HIER_DOC_ID_RE) - 1):
                yield "-".join(prefix2)
            else:
                for x in _walk_hierarchy(fpath, level=level+1, prefix=prefix2):
                    yield x

class Repository (object):

    def __init__ (self, version, root, db, inc_threads=True):

        global TheRepository
        if TheRepository:
            raise Error("a repository object, %s, already exists!" % TheRepository)
        TheRepository = self
        Pointer.REPOSITORY = self

        __conf = configurator.default_configurator()

        # both categories and documents may be updated by multiple threads, so
        #  we create these locks to protect the data
        set_threaded(True)
        self.categories_lock = MutexLock('RepoCategories')
        self.document_lock = MutexLock('RepoDocuments')

        self.__database = None
        self.__root = root
        self.__version = version or "unknown"
        self.__metadata_filename = os.path.join(root, "overhead", "metadata.txt")
        if os.path.exists(self.__metadata_filename):
            try:
                self.__metadata = read_metadata(self.__metadata_filename)
            except:
                note(0, "%s\n*** Removing bad metadata.txt file",
                     "".join(traceback.format_exception(*sys.exc_info())))
                os.unlink(self.__metadata_filename)
                self.__metadata = {}
        else:
            self.__metadata = {}

        try:
            self.__categories = (os.path.exists(os.path.join(root, "overhead", "categories.txt")) and
                                 read_metadata(os.path.join(root, "overhead", "categories.txt"))) or {}
        except:
            note(0, "%s\n*** Removing bad categories.txt file",
                 "".join(traceback.format_exception(*sys.exc_info())))
            os.unlink(os.path.join(root, "overhead", "categories.txt"))
            self.__categories = {}

        for key, value in self.__categories.items():
            try:
                if type(value) in types.StringTypes:
                    value = eval(value)
            except:
                note("for value %s %s:\n%s", key, repr(value), ''.join(traceback.format_exception(*sys.exc_info())))
                raise
            self.__categories[key] = value

        try:
            self.__authors = (os.path.exists(os.path.join(root, "overhead", "authors.txt")) and
                              read_metadata(os.path.join(root, "overhead", "authors.txt"))) or {}
        except:
            note(0, "%s\n*** Removing bad authors.txt file",
                 "".join(traceback.format_exception(*sys.exc_info())))
            os.unlink(os.path.join(root, "overhead", "authors.txt"))
            self.__authors = {}

        for key, value in self.__authors.items():
            try:
                if type(value) in types.StringTypes:
                    value = eval(value)
            except:
                note("for value <<%s: %s>>:\n%s", repr(key), repr(value), ''.join(traceback.format_exception(*sys.exc_info())))
                raise
            self.__authors[key] = value
        self.__certfilename = os.path.join(root, "overhead", "stunnel.pem")

        for key in db.keys():
            self.__metadata[key] = str(db[key])
        update_metadata(self.__metadata_filename, self.__metadata)
        if self.__metadata.has_key("password-hash") and not self.__metadata["password-hash"]:
            del self.__metadata["password-hash"]
        self.has_password = self.__metadata.has_key("password-hash")
        if "verbosity" in self.__metadata:
            set_verbosity(int(self.__metadata["verbosity"]))

        self.__uses_hierarchical_directories = self.__metadata.get("use-hierarchical-directories", "false").lower() == "true"

        # list of (on_addition, on_deletion) function pairs to call when a document is added or deleted
        # each function takes one parameter, the document object
        self.__doc_watchers = []

        self.__rippers = None

        self.__valid_cookies = {}
        self.__cookie_timeout = int(self.__metadata.get("cookie-timeout", 60 * 60 * 9))    # 9 hours
        # last time modified
        self.__modtime = time.time()
        # last time a document was added or deleted
        self.__doctime = time.time()
        # zero-parameter shutdown functions to call when shutting down the repo
        self.__shutdown_hooks = []

        default_history_size = __conf.get_int("mru-history-maxsize", 10000)
        if self.__metadata.has_key("history-length"):
            v = self.__metadata["history-length"]
            try:
                vi = int(v)
            except:
                vi = default_history_size
            self.__history_limit = vi
        else:
            self.__history_limit = default_history_size
        # maps doc ID to Document instance
        self.__history = LimitedOrderedDict(self.__history_limit)
        self.__read_history()

        # check the categories -- they can be zeroed if the metadata file is deleted
        if (not self.__categories) or (not self.__authors):
            # could be OK, but rescan anyway just in case
            note(3, "rescanning categories and authors...")
            self.rescan_indices()

        # finally, restore the collections

        # maps collection name to Collection instance
        self.__collections = {}
        self.__read_collections()
        self.__search_context = None
        self.__save_time = 0

        # create a thread to deal with new documents
        if inc_threads:
            n_incorporation_threads = self.__metadata.get("max-simultaneous-incorporation-threads")
            if not n_incorporation_threads:
                n_incorporation_threads = __conf.get("max-simultaneous-incorporation-threads")
            if n_incorporation_threads:
                n_incorporation_threads = int(n_incorporation_threads)
            else:
                n_incorporation_threads = -1        # no limit
            self.__incorporation_queue = start_incorporation_thread(self, n_incorporation_threads)

        self.start_time = time.time()


    def __str__(self):
        return '<' + str(self.__class__) + ' ' + self.name() + '>'

    def __repr__(self):
        return self.__str__()

    def add_shutdown_hook(self, hook):
        self.__shutdown_hooks.append(hook)

    def run_shutdown_hooks(self):
        if self.__database is not None:
            self.__database.close()
            self.__database = None
        for hook in self.__shutdown_hooks:
            try:
                hook()
            except:
                pass

    def shutdown(self, exitvalue):
        self.save(True)
        self.run_shutdown_hooks()
        os._exit(exitvalue)

    def save(self, force=False):
        if (self.__save_time > self.__modtime and not force):
            return
        self.__save_metadata()
        self.__save_collections()
        self.__save_history()
        try:
            if force: build_index_1_0(self)
        except:
            note(0, string.join(traceback.format_exception(*sys.exc_info())))
        self.__save_time = time.time()
        note("Saved repository at %s" % time.ctime(self.__save_time))

    def history(self):
        return [self.__history[key] for key in reversed(self.__history)]

    def __save_metadata(self):
        update_metadata(self.__metadata_filename, self.__metadata)

    def __save_history(self):
        history_path = os.path.join(self.overhead_folder(), "history.txt")
        fp = open(history_path, 'w')
        for key in reversed(self.__history):
            fp.write(key + "\n")
        fp.close()

    def __read_history(self):
        # read in a list of the lastest docs touched
        history_path = os.path.join(self.overhead_folder(), "history.txt")
        if os.path.exists(history_path):
            for did in reversed([line.strip() for line in open(history_path, 'r')]):
                if self.valid_doc_id(did):
                    self.__history[did] = Document(self, did)

    def __read_collections(self):

        path = os.path.join(self.overhead_folder(), "collections.txt")

        if not os.path.exists(path):
            return

        coll_list_file = open(path, 'r')
        lines = coll_list_file.readlines()
        coll_list_file.close()

        for line in lines:

            try:
                m = re.match('^([^\s]+)\s+([^\s]+)\s*(.*)$\n', line)
                if not m:
                    raise ValueError("bad collection line \"%s\"" % line)
                classname = m.group(1)
                id = m.group(2)
                name = m.group(3)

                note(3, "...restoring %s %s (%s)", classname, id, name)

                clss = find_class(classname)

                if clss and issubclass(clss, Collection):
                    c = self.get_collection(id, True)
                    if not c:
                        c = clss(self, id)
                        self.add_collection(name, c, False)
                else:
                    raise ValueError("invalid class <%s> found in collections.txt" % classname)
            except:
                note("while reading collection:\n%s", string.join(traceback.format_exception(*sys.exc_info())))


    def __save_collections (self):

        coll_list_file = open(os.path.join(self.overhead_folder(), "collections.txt"), 'w')
        for key, c in self.__collections.items():
            try:
                c.store(self.collections_folder())
                coll_list_file.write("%s.%s %s %s\n" % (c.__class__.__module__, c.__class__.__name__, c.id, key))
            except:
                note("while saving collection %s:\n%s", key, string.join(traceback.format_exception(*sys.exc_info())))
        coll_list_file.close()        

    def rippers(self):
        if self.__rippers == None:
            self.__rippers = get_default_rippers(self)
        return self.__rippers

    def update_indices(self, doc, authors=None, categories=None):
        if categories is not None:
            cs = doc.get_category_strings()
            cats = []
            for cat in cs:
                c = [x.strip().lower() for x in cat.split('/')]
                for i in range(len(c)):
                    cname = '/'.join(c[:i+1])
                    if cname not in cats:
                        cats.append(cname)
            for cat in cats:
                if cat in categories:
                    if doc.id not in categories[cat]:
                        categories[cat].append(doc.id)
                else:
                    categories[cat] = [doc.id,]
            for cat in categories:
                if (doc.id in categories[cat]) and (cat not in cats):
                    categories[cat].remove(doc.id)
        if authors is not None:
            auts = doc.get_metadata("authors")
            if auts:
                auts = [x.strip() for x in auts.split(' and ')]
                for aut in auts:
                    if aut in authors:
                        if doc.id not in authors[aut]:
                            authors[aut].append(doc.id)
                    else:
                        authors[aut] = [doc.id,]
            else:
                auts = []
            for aut in authors:
                if (doc.id in authors[aut]) and (aut not in auts):
                    authors[aut].remove(doc.id)

    def reindex(self, docs=None, categories=None, authors=None):
        if docs is None:
            docids = self._generate_doc_ids()
        else:
            docids = [doc.id for doc in docs]
        for docid in docids:
            index_folder(self.doc_location(docid), self.index_path())
        if categories or authors:
            if categories is not None:
                categories.clear()
            if authors is not None:
                authors.clear()
            self.categories_lock.acquire()
            try:
                for doc in docs:
                    self.update_indices(doc, authors, categories)
            finally:
                self.categories_lock.release()

    def get_param (self, param_name, default_value=None):
        return self.__metadata.get(param_name, default_value)

    def port(self):
        return int(self.__metadata.get('http-port'))

    def secure_port(self):
        return int(self.__metadata.get('https-port'))

    def mod_time(self):
        """
        Get the last-modified-time of the repository.

        :return: last-modified timestamp, as seconds past the Python epoch
        :rtype: float
        """
        return self.__modtime

    def up_time(self):
        return time.time() - self.start_time

    def check_cookie(self, value):
        if self.__valid_cookies.has_key(value):
            c = self.__valid_cookies[value]
            now = time.time()
            if c.expiration_time() > now:
                return True
            else:
                del self.__valid_cookies[value]
        return False

    def new_cookie(self, stri):
        # first, expire old cookies
        for c in self.__valid_cookies.keys():
            self.check_cookie(c)
        # now, create a new cookie and return it
        value = hashlib.sha1(stri + str(time.time())).hexdigest()
        c = cookie("uplibnonce%d" % self.secure_port(), hashlib.sha1(stri).hexdigest(), time.time() + self.__cookie_timeout)
        self.__valid_cookies[c.value()] = c
        return c

    def create_document_folder (self, directory):
        # this should be atomic, or at least hold some lock
        self.document_lock.acquire()
        try:
            while 1:
                s = "%014ld" % (long(time.time() * 1000))
                outbase = s[:5] + '-' + s[5:7] + '-' + s[7:11] + '-' + s[11:]
                for dir in ("docs", "pending", "deleted"):
                    newdir = os.path.join(self.root(), dir, outbase)
                    if os.path.exists(newdir):
                        time.sleep(1)
                        continue
                newdir = os.path.join(directory, outbase)
                if os.path.exists(newdir):
                    time.sleep(1)
                    continue
                break
            os.mkdir(newdir)
            os.chmod(newdir, 0700)
        finally:
            self.document_lock.release()
        return newdir

    def create_new_document (self, doc_bits, doc_type, metadata=None):
        return newFolder_create(self, self.__incorporation_queue,
                                doc_bits, doc_type, metadata)

    def register_document_watcher(self, on_add, on_delete, on_touch):
        self.__doc_watchers.append((on_add, on_delete, on_touch))

    def register_new_document (self, did):
        newdoc = Document(self, did)
        c = split_categories_string(newdoc.get_metadata('categories'))

        self.categories_lock.acquire()
        for category in c:
            if category and category not in self.__categories:
                self.add_category(category, True)
        self.categories_lock.release()

        self.document_lock.acquire()
        self.__modtime = time.time()
        self.__doctime = self.__modtime
        self.document_lock.release()
        self.save()

        for on_add, on_delete, on_touch in self.__doc_watchers:
            if on_add:
                on_add(newdoc)

        self.touch_doc(newdoc, notify=False)


    def delete_document (self, did):
        if not self.valid_doc_id(did):
            raise ValueError("Invalid document id %s" % did)
        else:
            location = self.doc_location(did)
            deleted_folder = os.path.join(self.__root, "deleted")
            if not os.path.isdir(deleted_folder):
                os.mkdir(deleted_folder)
                os.chmod(deleted_folder, 0700)

            doc = self.get_document(did)
            for on_add, on_delete, on_touch in self.__doc_watchers:
                if on_delete:
                    on_delete(doc)

            self.document_lock.acquire()
            try:
                if did in self.__history:
                    self.__history.pop(did)
                remove_from_index(self.index_path(), did)
                os.rename(location, os.path.join(deleted_folder, did))
                doc.setfolder(os.path.join(deleted_folder, did))
                self.__modtime = time.time()
                self.__doctime = self.__modtime
            finally:
                self.document_lock.release()

    def doc_mod_time(self):
        return self.__doctime

    def valid_doc_id (self, doc_id):
        return os.path.isdir(self.doc_location(doc_id))

    def root (self):
        return self.__root

    def doc_location (self, doc_id):
        if self.__uses_hierarchical_directories:
            return os.path.join(self.docs_folder(), *doc_id.split("-"))
        else:
            return os.path.join(self.docs_folder(), doc_id)

    def pending_location (self, doc_id):
        return os.path.join(self.pending_folder(), doc_id)

    def collections_folder (self):
        return os.path.join(self.__root, "overhead", "collections")

    def docs_folder (self):
        return os.path.join(self.__root, "docs")

    def html_folder (self):
        return os.path.join(self.__root, "html")

    def overhead_folder (self):
        return os.path.join(self.__root, "overhead")

    def pending_folder (self):
        return os.path.join(self.__root, "pending")

    def deleted_folder (self):
        return os.path.join(self.__root, "deleted")

    def certfilename(self):
        return self.__certfilename

    def set_certfilename(self, name):
        self.__certfilename = name

    def initialize_database(self):
        # anything we need to do to initialize the DB
        pass

    def database(self):
        if self.__database is None:
            try:
                import sqlite3 as sqlite
            except ImportError:
                try:
                    from pysqlite2 import dbapi2 as sqlite
                except ImportError:
                    note("No sqlite support found!")
                    return None
            path = os.path.join(self.overhead_folder(), "sqlitedb")
            if os.path.exists(path):
                # just open it
                self.__database = sqlite.connect(path)
            else:
                # need to create any initial tables
                self.__database = sqlite.connect(path)
                self.initialize_database()
        return self.__database

    def list_pending(self, full=False):
        """
        Returns a a list of which documents are currently in pending.
        If optional argument 'full' is True, also includes status (which ripper)
        and some metadata, such as 'title', 'authors', and 'pagecount'.

        :param full: whether or not to include details for each document
        :type full: boolean
        :return: list of dicts, one for each document in 'pending'.  If 'full' is True, \
                 dict will include 'status' and 'ripper' fields, otherwise just 'id'.
        :rtype: list(dict(id: doc_id [, 'status': ('unpacking' or 'error' or 'moving' or 'ripping'), \
                                      'ripper': name of ripper, 'error': error traceback, \
                                      'title': title, 'authors': authors, 'page_count', page count, \
                                      'pubdate': date]))
        """
        pendings = []
        pending_filenames = os.listdir(self.pending_folder())
        for filename in pending_filenames:
            if filename.startswith("."):
                continue
            pdir = os.path.join(self.pending_folder(), filename)
            if not os.path.isdir(pdir) or len(os.listdir(pdir)) == 0:
                continue
            current = { 'id' : filename }
            pendings.append(current)
            if full:
                files = os.listdir(pdir)
                current['status'] = "unpacking"
                current['ripper'] = ""
                ripper_index = 0
                if "ERROR" in files:
                    current['status'] = "error"
                    current['error'] = unicode(open(os.path.join(pdir, "ERROR"), 'rb').read(), "UTF-8", "replace")
                    if "RIPPING" in files:
                        current['ripper'] = unicode(open(os.path.join(pdir, "RIPPING"), 'rb').read(), "UTF-8", "replace")
                elif "RIPPED" in files:
                    current['status'] = "moving"
                elif "UNPACKED" in files:
                    current['status'] = "ripping"
                    if "RIPPING" in files:
                        current['ripper'] = unicode(open(os.path.join(pdir, "RIPPING"), 'rb').read(), "UTF-8", "replace")
                current['title'] = filename
                current['page_count'] = 0
                current['authors'] = ''
                current['pubdate'] = ''
                if "metadata.txt" in files:
                    d = read_metadata(os.path.join(pdir, "metadata.txt"))
                    if d.has_key("title"):
                        k = d.get("title").strip()
                        if k:
                            current['title'] = d.get("title")
                    if d.has_key("page-count"):
                        current['page_count'] = int(d.get("page-count"))
                    if d.has_key("authors"):
                        current['authors'] = d.get("authors")
                    if d.has_key("date"):
                        current['pubdate'] = d.get("date")
                    else:
                        page_images_dir = os.path.join(pdir, "page-images")
                        if os.path.exists(page_images_dir):
                            current['page_count'] = len(os.listdir(page_images_dir))
        return pendings


    def sort_doclist_by_pubdate(self, doclist):
        doclist.sort(_compare_docs_by_pubdate)
        return doclist

    def sort_doclist_by_mru (self, doclist):
        doclist.sort(lambda x, y, z=self: _compare_docs_by_usage_time(z, x, y))
        return doclist

    def sort_doclist_by_lru (self, doclist):
        doclist.sort(lambda x, y, z=self: _compare_docs_by_usage_time(z, x, y))
        doclist.reverse()
        return doclist

    def sort_doclist_by_adddate (self, doclist):
        doclist.sort(_compare_docs)
        return doclist

    def list_docs (self, order=None):
        warnings.warn("The 'list_docs()' method will be removed in a future release!  Try generate_docs() instead.",
                      DeprecationWarning)
        docs = [x for x in self.generate_docs()]
        if (order == 'pubdate'):
            docs.sort(_compare_docs_by_pubdate)
        elif (order == 'lastused'):
            docs.sort(lambda x, y, z=self: _compare_docs_by_usage_time(z, x, y))
        elif (order == 'adddate'):
            docs.sort(_compare_docs)
        else:
            docs.sort(_compare_docs)
        return docs

    def _generate_doc_ids (self, count=0):
        if self.__uses_hierarchical_directories:
            counter = 0
            for doc_id in _walk_hierarchy(self.docs_folder()):
                counter += 1
                if count and (counter > count):
                    break
                yield doc_id
        else:
            if sys.version_info < (2,6):
                # bug in os.listdir (http://bugs.python.org/issue1608818) till 2.6
                retries = 0
                while retries < 10:
                    retries += 1
                    try:
                        filenames = os.listdir(self.docs_folder())
                        break
                    except MemoryError:
                        continue
                if retries >= 10:
                    raise RuntimeError("Can't operate os.listdir to enumerate docs subdirectory!")
                counter = 0
                for filename in filenames:
                    if count and (counter >= count):
                        return
                    if DOC_ID_RE.match(filename):
                        yield filename
                        counter += 1
                return
            else:
                counter = 0
                for filename in os.listdir(self.docs_folder()):
                    if count and (counter >= count):
                        return
                    if DOC_ID_RE.match(filename):
                        yield filename
                        counter += 1

    def generate_docs (self, count=0):
        """Return an iterator over all the docs of the repository, in no particular order.

        :param count: a keyword param giving the max number of docs to return
        :type count: int
        :return: an interator listing ``count`` (if specified) or all the documents of the repository
        :rtype: iterator of Document instances
        """
        if sys.version_info < (2,6):
            # bug in os.listdir (http://bugs.python.org/issue1608818) till 2.6
            retries = 0
            while retries < 10:
                retries += 1
                try:
                    filenames = [x for x in self._generate_doc_ids(count=count)]
                    break
                except MemoryError:
                    continue
            if retries >= 10:
                raise RuntimeError("Can't operate os.listdir to enumerate docs subdirectory!")
            counter = 0
            for filename in filenames:
                if count and (counter >= count):
                    return
                if DOC_ID_RE.match(filename):
                    d = self.__history.get(filename)
                    if d:
                        yield d
                    else:
                        yield Document(self, filename)
                    counter += 1
            return
        else:
            counter = 0
            for doc_id in self._generate_doc_ids(count=count):
                if count and (counter >= count):
                    return
                d = self.__history.get(doc_id)
                if d:
                    yield d
                else:
                    yield Document(self, doc_id)
                counter += 1

    def docs_count(self):
        count = 0
        if sys.version_info < (2,6):
            # bug in os.listdir (http://bugs.python.org/issue1608818) till 2.6
            retries = 0
            while retries < 10:
                retries += 1
                try:
                    doc_ids = self._generate_doc_ids()
                    break
                except MemoryError:
                    continue
            if retries >= 10:
                raise RuntimeError("Can't operate os.listdir to enumerate docs subdirectory!")
            for doc_id in doc_ids:
                if DOC_ID_RE.match(doc_id):
                    count += 1
        else:
            for doc_id in self._generate_doc_ids():
                count += 1
        return count

    def touch_doc(self, doc_or_id, bury=False, notify=True):
        if type(doc_or_id) in types.StringTypes:
            d = self.get_document(doc_or_id)
        elif isinstance(doc_or_id, Document):
            d = doc_or_id
        else:
            raise ValueError("Parameter 'doc_or_id', %s, must be a document ID string or a Document instance" % repr(doc_or_id))
        d.touch()
        oldcathash = hash(unicode(self.__categories))
        oldauthash = hash(unicode(self.__authors))
	self.update_indices(d, self.__authors, self.__categories)
	if (oldcathash != hash(unicode(self.__categories))):
            self._update_categories_file()
        if (oldauthash != hash(unicode(self.__authors))):
            self._update_authors_file()
        found = None
        if d.id in self.__history:
            del self.__history[d.id]
        if not bury:
            self.__history[d.id] = d
        self.__modtime = time.time()
        if notify:
            for on_add, on_delete, on_touch in self.__doc_watchers:
                if on_touch:
                    on_touch(d)

    def get_touched_since(self, t):
        return [self.__history[x] for x in reversed(self.__history) if (self.__history[x].touch_time() > t)]

    def index_path (self):
        return os.path.join(self.__root, "index")

    def name(self):
        return self.__metadata.get('name') or self.__root

    def set_name(self, newname):
        self.__metadata['name'] = newname
        update_metadata(self.__metadata_filename, self.__metadata)
        self.__modtime = time.time()

    def content_types(self):
        ctypes = eval(self.__metadata.get("content-types", "{}"))
        if type(ctypes) == type({}):
            return ctypes.keys()
        else:
            return []

    def categories(self):
        l = self.__categories.keys()
        l.sort()
        return l

    def get_docs_by_category(self, cat):
        x = self.__categories.get(cat.strip().lower())
        if x:
            return tuple([self.get_document(id) for id in x if self.valid_doc_id(id)])

    def get_docids_with_categories(self):
        ids_to_categories_mapping = {}
        for cat, ids in self.__categories.iteritems():
            for id in ids:
                if id not in ids_to_categories_mapping:
                    ids_to_categories_mapping.setdefault(id, [])
                ids_to_categories_mapping[id].append(cat)
        return ids_to_categories_mapping

    def get_categories_with_docs(self):
        return self.__categories.copy()

    def get_docs_by_author(self, author):
        x = self.__authors.get(author.strip().lower())
        if x:
            return tuple([get_document(id) for id in x])

    def get_authors_with_docs(self):
        return self.__authors.copy()

    def add_category(self, new_category, holds_lock=False):
        if not holds_lock:
            self.categories_lock.acquire()
        try:
            if new_category.strip().lower() not in self.__categories:
                self.__categories[new_category.strip().lower()] = []
                self._update_categories_file()
                self.__modtime = time.time()
        finally:
            if not holds_lock:
                self.categories_lock.release()

    def _update_authors_file(self, d=None):
        if d is None:
            d = self.__authors.copy()
            #note("self.__authors yields %d (%d) values", len(self.__authors), len(d))
        for key, value in d.items():
            value = str(value)
            if isinstance(key, unicode):
                key2 = utf_8_encode(key)
                if key2 != key:
                    del d[key]
                    #note("replacing authors key '%s' with '%s'", key, key2)
                    d[key2] = value
                else:
                    d[key] = value
            else:
                d[key] = value
        for key in d.keys()[:]:
            if key == "":
                # empty string, somehow
                del d[key]
                continue
        write_metadata(open(os.path.join(self.__root, "overhead", "authors.txt"), 'w'), d)

    def _update_categories_file(self, d=None):
        if d is None:
            d = self.__categories.copy()
            # note("self.__categories yields %d (%d) values", len(self.__categories), len(d))
        for key, value in d.items():
            value = str(value)
            if isinstance(key, unicode):
                key2 = utf_8_encode(key)
                if key2 != key:
                    del d[key]
                    #note("replacing categories key '%s' with '%s'", key, key2)
                    d[key2] = value
                else:
                    d[key] = value
            else:
                d[key] = value
        for key in d.keys()[:]:
            if key == "":
                # empty string, somehow
                del d[key]
                continue
        write_metadata(open(os.path.join(self.__root, "overhead", "categories.txt"), 'w'), d)

    def rescan_categories(self):
        self.categories_lock.acquire()
        categories = {}
        for doc in self.generate_docs():
            self.update_indices(doc, None, categories)
        self.__categories = categories
        self._update_categories_file()
        self.__modtime = time.time()
        self.categories_lock.release()

    def rescan_indices(self):
        self.categories_lock.acquire()
        try:
            newcats = {}
            newauts = {}
            for doc in self.generate_docs():
                self.update_indices(doc, newauts, newcats)
            self.__categories = newcats
            self.__authors = newauts
            self._update_categories_file()
            self._update_authors_file()
        finally:
            self.categories_lock.release()

    def get_document(self, doc_id):
        d = self.__history.get(doc_id)
        if d:
            return d
        elif self.valid_doc_id(doc_id):
            return Document(self, doc_id)
        else:
            raise ValueError("Invalid doc_id '%s'" % doc_id)
        
    def change_password(self, oldpassword, newpassword):
        oldhash = self.__metadata.get("password-hash")
        if not oldhash or hashlib.sha1(oldpassword).hexdigest() == oldhash:
            if len(newpassword) == 0:
                # remove the password
                self.__metadata["password-hash"] = ""
                self.has_password = False
            else:
                self.__metadata["password-hash"] = hashlib.sha1(newpassword).hexdigest()
                self.has_password = True
            update_metadata(self.__metadata_filename, self.__metadata)
            return True
            self.__modtime = time.time()
            self.save()
        else:
            return False

    def check_password(self, testpassword):
        if not self.has_password and len(testpassword) == 0:
            return True
        hash = self.__metadata.get("password-hash")
        return (hashlib.sha1(testpassword).hexdigest() == hash)

    def get_version(self):
        return self.__version

    def get_favicon(self):
        try:
            fp = open(os.path.join(self.__root, "html", "images", "favicon.ico"), 'rb')
            data = fp.read()
            fp.close()
            return data
        except:
            note(0, "Can't read favicon:\n%s", ''.join(traceback.format_exception(*sys.exc_info())))
            return None

    def list_collections(self):
        """
        Get a list of all the collections known to the repository.

        :return: list of collections
        :rtype: list(collection.Collection)
        """
        return self.__collections.items()

    def get_collection (self, name, byid=False):
        if not byid:
            return self.__collections.get(name)
        else:
            for c in self.__collections.values():
                if c.id == name:
                    return c
        return None

    def get_collection_name (self, c):
        if type(c) in types.StringTypes:
            for name, coll in self.__collections.items():
                if c == coll.id:
                    return name
        elif isinstance(c, Collection):
            for name, coll in self.__collections.items():
                if c.id == coll.id:
                    return name
        return None

    def delete_collection (self, id):
        if isinstance(id, Collection):
            id = id.name()
        for name, coll in self.__collections.items():
            if (coll.name() == id):
                del self.__collections[name]
                self.__save_collections()
                return True
        return False

    def rename_collection(self, oldname, newname):
        c = self.__collections.get(oldname)
        if c:
            del self.__collections[oldname]
            self.__collections[newname] = c
            self.__save_collections()
            return True
        else:
            return False        

    def add_collection (self, name, objects, checkpoint=False):
        note(4, "add_collection:  isinstance(%s, Collection) => %s",
             objects, (isinstance(objects, Collection) and "true") or "false")
        if isinstance(objects, Collection):
            c = objects
        else:
            c = Collection(self, create_new_id(), objects)
        self.__collections[name or c.name()] = c
        self.__modtime = time.time()
        if checkpoint: self.save()
        return c

    def add_query_collection (self, name, query):
        if isinstance(query, Collection):
            c = query
        else:
            c = PrestoCollection(self, None, query)
        self.__collections[name or c.name()] = c
        self.__save_collections()
        return c

    def set_lucene_jarfile(self, jarfile):
        if jarfile:
            self.__metadata['lucene-jarfile'] = str(jarfile)
        else:
            self.__metadata['lucene-jarfile'] = None
        update_metadata(self.__metadata_filename, self.__metadata)

    def set_actions_path (self, path):
        self.__metadata['extensions-path'] = path or "(none)"
        update_metadata(self.__metadata_filename, self.__metadata)
        note("extensions-path is now %s", self.get_param("extensions-path"))

    def get_actions_path (self):
        path = self.__metadata.get('extensions-path')
        if path == "(none)":
            return None
        else:
            return path

    def search_context (self):

        if (plibUtil.HAVE_PYLUCENE and (plibUtil.THREADING == "python") and uthread.JAVA_ENV and os.path.exists(self.index_path())):
            from uplib import indexing
            if not self.__search_context:
                self.__search_context = indexing.LuceneContext(self.index_path())
        return self.__search_context

    def pylucene_search (self, search_operation, query_string):

        note(4, "plibUtil.HAVE_PYLUCENE is %s, and plibUtil.THREADING is %s, and \"use-pylucene\" is %s",
             plibUtil.HAVE_PYLUCENE, plibUtil.THREADING, self.get_param("use-pylucene"))

        if (plibUtil.HAVE_PYLUCENE and
            os.path.exists(self.index_path())):
            if (plibUtil.HAVE_PYLUCENE == 'jcc') and (plibUtil.THREADING == 'python'):
                from uplib import indexing
                if not self.__search_context:
                    self.__search_context = indexing.LuceneContext(self.index_path())
            if self.__search_context:
                v = None
                try:
                    if search_operation == "search":
                        v = self.__search_context.search(query_string)
                    elif search_operation == "pagesearch":
                        v = self.__search_context.pagesearch(query_string)
                    elif search_operation == "bothsearch":
                        v = self.__search_context.bothsearch(query_string)
                    else:
                        raise ValueError("specified search operation \"%s\" not understood" % search_operation)
                    note(4, "   search results are %s", v)
                    return v
                finally:
                    note(4, "finished search \"%s\" with %d results", query_string, (v and len(v)) or 0);
            else:
                raise Error("Can't create SearchContext for repository!")
        else:
            return None

    def javalucene_search (self, search_operation, query_string):

        # self.save()           # don't think we need this, and it speeds things up
        conf = configurator.default_configurator()
        INDEXING_SEARCH_CMD = conf.get("indexing-search-command")
        JAVA = conf.get("java")
        LUCENE_JAR = conf.get("lucene-jarfile")
        INDEXING_JAR = conf.get("uplib-indexing-jarfile")
        search_terms = conf.get("search-properties");
        search_operator = conf.get("search-default-operator");
        search_abbrevs = conf.get("search-abbreviations");
        if search_terms:
            if sys.platform.lower().startswith("win"):
                searchterms = "-Dcom.parc.uplib.indexing.defaultSearchProperties=%s" % search_terms
            else:
                searchterms = "'-Dcom.parc.uplib.indexing.defaultSearchProperties=%s'" % search_terms
        else:
            searchterms = ""
        if search_abbrevs:
            if sys.platform.lower().startswith("win"):
                searchterms += " -Dcom.parc.uplib.indexing.userAbbrevs=%s" % search_abbrevs
            else:
                searchterms += " '-Dcom.parc.uplib.indexing.userAbbrevs=%s'" % search_abbrevs
        if search_operator and (search_operator.lower() in ("or", "and")):
            if sys.platform.lower().startswith("win"):
                searchops = " -Dcom.parc.uplib.indexing.defaultSearchOperator=%s" % search_operator
                searchops += " -Dcom.parc.uplib.indexing.defaultPageSearchOperator=%s" % search_operator
            else:
                searchops = " '-Dcom.parc.uplib.indexing.defaultSearchOperator=%s'" % search_operator
                searchops += " '-Dcom.parc.uplib.indexing.defaultPageSearchOperator=%s'" % search_operator
        else:
            searchops = ""

        if sys.platform.lower().startswith("win"):
            quoted_query_string = re.sub(r'"', r'\"', query_string)
            quoted_query_string = re.sub('&', '^&', quoted_query_string)
        else:
            quoted_query_string = re.sub(r"'", r"'\''", query_string)

        try:
          command = INDEXING_SEARCH_CMD % (JAVA, searchterms, searchops, INDEXING_JAR, LUCENE_JAR, self.index_path(), search_operation, quoted_query_string)
        except TypeError:
          raise Error("Unable to format the search command.  "
                      "INDEXING_SEARCH_CMD = " + INDEXING_SEARCH_CMD + ".  "
                      "8 arguments provided.  Perhaps the "
                      "'indexing-search-command' parameter in your configuration file is out of date?")
      
        note(3, "Running search command: %s" % command)
        status, output, tsignal = subproc(command)
        if status != 0:
            raise Error ("%s signals non-zero exit status %d attempting to run query <%s> in %s:\n%s\ncommand is <%s>" % (JAVA, status, query_string, self.name(), output, command))
        if output and output[0] == '*':
            raise Error ("%s signals error attempting to run query <%s> in %s:\n%s\ncommand is <%s>" % (JAVA, query_string, self.name(), output, command))

        return command, output


    def do_query (self, query_string, searchtype=None):
        """
        Run a query on the repository's collection, and return the matching documents.  Simplified version of :see #do_full_query:.

        :param query_string: an UpLib/Lucene query
        :type query_string: string
        :param searchtype: either "search", to search just documents, "pagesearch", to search just pages,\
               and "bothsearch", to search both.  Defaults to "search".
        :type searchtype: string
        :return: matching docs, as a list of score,document tuples
        :rtype: list(tuple(float,Document))
        """
        if not os.path.isdir(self.index_path()):
            return []

        if searchtype is None:
            searchtype = "search"

        results = self.do_full_query(query_string, searchtype)

        return [(x['score'], x['doc']) for x in results.values()]


    def do_full_query (self, query_string, searchtype=None):
        """
        Run a query on the repository's collection, and return the matching documents.

        :param query_string: an UpLib/Lucene query
        :type query_string: string
        :param searchtype: either "search", to search just documents, "pagesearch", to search just pages, \
               and "bothsearch", to search both.  Default is "search".
        :type searchtype: string
        :return: matching documents and/or pages, and their scores.  This is a mapping from doc IDs to result dictionaries.  Each result dictionary has the keys "doc" (mapped to an UpLib Document instance) and "score", mapped to a floating point value.  In addition, if pages are searched, each result dictionary will also have the key "pages", which maps to a list of page indices.
        :rtype: dict(id: dict(doc: <Document instance>, score: float, [pages: list(int)]))
        """

        if not os.path.isdir(self.index_path()):
            return {}

        if searchtype is None:
            searchtype = "bothsearch"

        results = self.pylucene_search(searchtype, query_string)

        # note(4, "results of pylucene_search are %s", results)

        if results is not None:
            results2 = {}
            for result in results:
                id = result[0]
                score = result[1]
                if len(result) == 2 and self.valid_doc_id(id):
                    # new document mentioned
                    results2[id] = { 'doc' : self.get_document(id), 'score' : float(score) }
                    note(4, "*-  %10s %.4f:  %s", score, results2[id]['score'], results2[id]['doc'])
                elif len(result) == 3 and id in results2:
                    # new page of a document -- add if the doc is in the results
                    pages = results2[id].get('pages', {})
                    pages[int(result[2])] = float(score)
                    results2[id]['pages'] = pages

            # note("results of pylucene_search('%s', '%s') is %s", searchtype, query_string, results2)

            return results2

        command, output = self.javalucene_search(searchtype, query_string)

        try:
            results = {}
            if string.strip(output):
                lines = string.split(output, '\n')
                for line in lines:
                    if line:
                        pageno = None
                        doc_id, scorestring = line.split()
                        if "/" in doc_id:
                            doc_id, pageno = doc_id.split("/")
                        if self.valid_doc_id(doc_id):
                            # "bothsearch" returns document matches before page matches, so
                            # we only want to add records if there are no page numbers in the
                            # current hit (that is, there's a document match)
                            record = results.get(doc_id)
                            if not record and not pageno:
                                record = { 'doc' : self.get_document(doc_id) }
                                record['score'] = float(scorestring)
                                results[doc_id] = record
                            elif record and not pageno:
                                note(0, "Pre-existing search hit %s (score %s) hit again in search results (score %s)!  Ignoring it.",
                                     doc_id, record.get('score'), scorestring)
                            if record and pageno:
                                # if we've already created a record, there was a previous
                                # document match, so keep track of page matches, as well
                                pages = record.get('pages')
                                if not pages:
                                    record['pages'] = { int(pageno) : float(scorestring) }
                                else:
                                    pages[int(pageno)] = float(scorestring)
            return results
        except:
            raise Error ("Error parsing output of search command.\nCommand was:  %s\nOutput was:\n%s\nException was:\n%s" %
                         (command, output, traceback.format_exception(*sys.exc_info())))

    STUNNEL_CONF_BOILERPLATE = """
    debug = 7

    cert = %(overhead-dir)s/%(certfilename)s
    output = %(overhead-dir)s/stunnel.log
    %(pid-line)s

    [uplib]
    accept = %(accept-addr)s
    connect = %(connect-addr)s
    """

    def build_world (directory, portno=None, logfilename=None, inc_threads=True):

        # figure out what we have to work with

        try:
            import ssl
        except:
            _have_ssl = False
        else:
            _have_ssl = True

        if hasattr(os, 'uname'):
            osname = os.uname()[0]
        else:
            osname = sys.platform
        hostname = get_fqdn()

        machineid = None
        if sys.platform in ('darwin', 'linux2') and os.path.exists('/etc/uplib-machine-id'):
            fp = open('/etc/uplib-machine-id', 'r')
            machineid = fp.read().strip()
            fp.close()

        if portno is None and os.path.exists(os.path.join(directory, "overhead", "angel.port")):
            portno = int(open(os.path.join(directory, "overhead", "angel.port")).read().strip()) + 1

        set_configuration_port(portno - 1);
        if machineid:
            sections = (machineid + ":" + str(portno-1),
                        hostname+":"+str(portno-1),
                        machineid,
                        hostname,
                        osname,
                        "server",
                        "default",)
        else:
            sections = (hostname+":"+str(portno-1),
                        hostname,
                        osname,
                        "server",
                        "default",)

        set_default_configuration_sections(sections)
        conf = configurator(sections=sections)
        use_stunnel = conf.get_bool("use-stunnel", True)
        if not use_stunnel:
            # affects our port number
            if machineid:
                sections = (machineid + ":" + str(portno),
                            hostname+":"+str(portno),
                            machineid,
                            hostname,
                            osname,
                            "server",
                            "default",)
            else:
                sections = (hostname+":"+str(portno),
                            hostname,
                            osname,
                            "server",
                            "default",)
            set_default_configuration_sections(sections)
            conf = configurator(sections=sections)
        configurator.set_default_configurator(conf)

        version = conf.get("UPLIB_VERSION")
        lucene_jarfile = conf.get("use-pylucene") + ':' + conf.get("lucene-jarfile")
        button_addition_enabled = conf.get_bool("allow-extensions-to-add-buttons", True)

        # process a few convenient arguments
        PUBLISHING_ROOT = directory
        IP_ADDRESS = "127.0.0.1"
        HTTP_PORT = portno
        HTTPS_PORT = ((use_stunnel or not _have_ssl) and (portno-1)) or portno
        MONITOR_PORT = HTTP_PORT + 1

        # set our umask appropriately
        os.umask(0077)

        note("....... Restarting at %s. ...........", time.ctime())
        note("sys.path is %s", sys.path)
        note("Default configurator is %s", conf)

        repositoryData = { 'root' : PUBLISHING_ROOT,
                           'http-port' : HTTP_PORT,
                           'https-port' : HTTPS_PORT,
                           'monitor_port' : MONITOR_PORT,
                           'content-types': { 'tarred-folder' : "application/x-uplib-folder-tarred",
                                              'zipped-folder' : "application/x-uplib-folder-zipped" },
                           }

        # make sure threads work (and initialize JVM)
        from uplib.plibUtil import uthread
        uthread.initialize()

        ############################################################
        ###
        ###  update older versions
        ###
        ############################################################

        def ensure_directory(dir):
            if not os.path.exists(dir):
                os.makedirs(dir)
            elif not os.path.isdir(dir):
                raise Error("File %s specified as directory is not a directory!" % dir)

        def remove_file (fpath):
            if os.path.islink(fpath) or os.path.exists(fpath):
                os.unlink(fpath)

        ensure_directory(os.path.join(PUBLISHING_ROOT, "overhead"))
        ensure_directory(os.path.join(PUBLISHING_ROOT, "docs"))

        mdpath = os.path.join(PUBLISHING_ROOT, "overhead", "metadata.txt")

        if (not os.path.exists(mdpath) and
            os.path.exists(os.path.join(PUBLISHING_ROOT, "overhead", "metadata"))):
            # this is a 1.0 system
            db = shelve.open(os.path.join(PUBLISHING_ROOT, "overhead", "metadata"), 'c')
            newdb = {}
            for key in db.keys():
                if key == 'collections':
                    continue
                newdb[key] = str(db[key])
            update_metadata(mdpath, newdb)
            db.close()

        if os.path.exists(mdpath):
            testdb = read_metadata(mdpath)
            if not testdb.has_key('extensions-path'):
                testdb['extensions-path'] = conf.get('actions-path', '')
                update_metadata(mdpath, testdb)
            ct = testdb.get('content-types')
            if ct:
                ct = eval(ct)
                if not ct.has_key('zipped-folder'):
                    testdb['content-types'] = str({ 'tarred-folder' : "application/x-uplib-folder-tarred",
                                                    'zipped-folder' : "application/x-uplib-folder-zipped" })
                    update_metadata(mdpath, testdb)
            if ("http-port" not in testdb) or ("https-port" not in testdb):
                update_metadata(mdpath, {"http-port": str(HTTP_PORT), "https-port": str(HTTPS_PORT)})

        if not os.path.exists(os.path.join(PUBLISHING_ROOT, "overhead", "collections")):
            os.mkdir(os.path.join(PUBLISHING_ROOT, "overhead", "collections"))

        uplib_share = conf.get('uplib-share')
        imageroot = os.path.join(PUBLISHING_ROOT, "html", "images")
        ensure_directory(imageroot)
        ensure_file(os.path.join(imageroot, "delete.gif"), os.path.join(uplib_share, "images", "delete.gif"), False)
        ensure_file(os.path.join(imageroot, "icon16.png"), os.path.join(uplib_share, "images", "icon16.png"), True)
        ensure_file(os.path.join(imageroot, "favicon-ipod.png"), os.path.join(uplib_share, "images", "favicon-ipod.png"), False)
        ensure_file(os.path.join(imageroot, "favicon.ico"), os.path.join(uplib_share, "images", "favicon.ico"), False)
        ensure_file(os.path.join(imageroot, "info.png"), os.path.join(uplib_share, "images", "info.png"), True)
        ensure_file(os.path.join(imageroot, "swirl.gif"), os.path.join(uplib_share, "images", "animated-swirl-24.gif"), True)
        ensure_file(os.path.join(imageroot, "transparent.png"), os.path.join(uplib_share, "images", "transparent.png"), True)
        ensure_file(os.path.join(imageroot, "ReadUpJWS.gif"), os.path.join(uplib_share, "images", "ReadUpJWS.gif"), True)

        javascriptdir = os.path.join(PUBLISHING_ROOT, "html", "javascripts")
        ensure_directory(javascriptdir)
        for file in os.listdir(javascriptdir):
            fullpath = os.path.join(javascriptdir, file)
            if os.path.islink(fullpath) or os.path.exists(fullpath):
                os.unlink(fullpath)
        # copy over latest version of javascript code
        scriptsinstallation = os.path.join(uplib_share, "code")
        for file in os.listdir(scriptsinstallation):
            if file.endswith(".js"):
                ensure_file(os.path.join(javascriptdir, file), os.path.join(scriptsinstallation, file), True)

        tempdir = os.path.join(PUBLISHING_ROOT, "html", "temp")
        ensure_directory(tempdir)
        for file in os.listdir(tempdir):
            fullpath = os.path.join(tempdir, file)
            if os.path.islink(fullpath) or os.path.exists(fullpath):
                os.unlink(fullpath)

        helproot = os.path.join(PUBLISHING_ROOT, "html", "helppages")
        ensure_directory(helproot)
        note(2, "Copying new help files and images from %s to old repository location", uplib_share)
        dist_helpfiles_dir = os.path.join(uplib_share, "help", "html")
        helpfiles = os.listdir(dist_helpfiles_dir)
        for helpfile in helpfiles:
            if helpfile.endswith('.html'):
                ensure_file(os.path.join(helproot, helpfile), os.path.join(dist_helpfiles_dir, helpfile), True)

        note("Updating documentation pages from %s...", uplib_share)
        docroot = os.path.join(PUBLISHING_ROOT, "html", "doc")
        apiroot = os.path.join(PUBLISHING_ROOT, "html", "doc", "api")
        ensure_directory(docroot)
        ensure_directory(apiroot)
        dist_docfiles_dir = os.path.join(uplib_share, "doc")

        def update_directory_tree(sourced, targetd, pattern):
            for f in os.listdir(sourced):
                fullpath = os.path.join(sourced, f)
                destpath = os.path.join(targetd, f)
                if os.path.isdir(fullpath):
                    ensure_directory(destpath)
                    update_directory_tree(fullpath, destpath, pattern)
                elif pattern.match(f):
                    ensure_file(destpath, fullpath, True)

        update_directory_tree(dist_docfiles_dir, docroot, re.compile(r'.*\.pdf$|.*\.html$|.*\.css$|.*\.png$|.*\.js$|.*\.txt$'))

        if not os.path.exists(os.path.join(PUBLISHING_ROOT, "overhead", "extensions")):
            # 1.0 or 1.1, needs extensions hierarchy
            extensions_root = os.path.join(PUBLISHING_ROOT, "overhead", "extensions")
            ensure_directory(os.path.join(extensions_root, "inactive"))
            ensure_directory(os.path.join(extensions_root, "active"))

        if os.path.exists(os.path.join(PUBLISHING_ROOT, "html", "UpLibPageview.jar")):
            # may be obsolete version of the jar, so remove symlink
            os.unlink(os.path.join(PUBLISHING_ROOT, "html", "UpLibPageview.jar"))

        ensure_file(os.path.join(PUBLISHING_ROOT, "html", "ebookbase.jar"),
                    os.path.join(uplib_share, "code", "ebookbase.jar"), True)

        # we introduced month names as images in 1.4
        images_dir = os.path.join(PUBLISHING_ROOT, "html", "images")
        images_src = os.path.join(uplib_share, "images")
        for monthname in ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"):
            ensure_file (os.path.join(images_dir, monthname + ".png"), os.path.join(images_src, "monthnames", monthname + ".png"), True)

        ensure_file(os.path.join(images_dir, "rotating-uplib-logo.gif"),
                    os.path.join(images_src, "rotating-uplib-logo.gif"))

        # check to make sure stunnel config file exists if stunnel version is 4 or greater
        if use_stunnel:
            stunnel_version = int(conf.get("stunnel-version", 4))
            stunnel_conf_file = os.path.join(PUBLISHING_ROOT, "overhead", "stunnel.conf")
            if ((stunnel_version >= 4) and not os.path.exists(stunnel_conf_file)):
                fp = open(stunnel_conf_file, "w")
                fp.write('cert = %s\n' % os.path.join(conf.get("uplib-lib"), "stunnel.pem") +
                         'output = %s\n' % os.path.join(PUBLISHING_ROOT, "overhead", "stunnel.log"))
                if not sys.platform.startswith("win"):
                    fp.write('pid = %s\n' % os.path.join(PUBLISHING_ROOT, "overhead", "stunnel.pid"))
                fp.write('\n' +
                         '[uplib]\n' +
                         'accept = %d\n' % (HTTP_PORT - 1) +
                         'connect = %d\n' % HTTP_PORT)
                fp.close()

        # create a signed readup jar file for remote use
        signedjarpath = os.path.join(PUBLISHING_ROOT, "html", "signedreadup.jar")
        if os.path.exists(signedjarpath):
            os.unlink(signedjarpath)
        if os.path.exists(os.path.join(uplib_share, "code", "signedreadup.jar")):
            ensure_file(signedjarpath,
                        os.path.join(uplib_share, "code", "signedreadup.jar"))
        else:
            note("Creating new signed ReadUp jar for use with Java Web Start...")
            tpath = os.path.join(PUBLISHING_ROOT, "overhead", hostname + ".pem")
            if os.path.exists(tpath):
                certfile = tpath
            else:
                certfile = os.path.join(PUBLISHING_ROOT, "overhead", "stunnel.pem")
            openssl = conf.get("openssl")
            jarsigner = os.path.join(conf.get("javahome"), "bin", "jarsigner")
            if os.path.exists(certfile) and openssl and os.path.exists(jarsigner):
                # sign the jar file with the repository's certificate
                tmpcertfile = tempfile.mktemp()
                cmd = "%s pkcs12 -export -passout pass:foobar -out %s -in %s -name myrepo" % (openssl, tmpcertfile, certfile)
                status, output, tsignal = subproc(cmd)
                if status != 0:
                    note("can't sign jar file %s with certificate %s:  %s\n", tfilename, repocertfile, output)
                else:
                    ensure_file(signedjarpath,
                                os.path.join(uplib_share, "code", "ShowDoc.jar"))
                    cmd = "%s -keystore %s -storetype pkcs12 -storepass foobar %s myrepo" % (jarsigner, tmpcertfile, signedjarpath)
                    status, output, tsignal = subproc(cmd)
                    if status != 0:
                        note("can't sign jar file %s with certificate %s:  %s\n", tfilename, repocertfile, output)
                if os.path.exists(tmpcertfile): os.unlink(tmpcertfile)


        ############################################################
        ###
        ###  remove any LOCK files hanging around
        ###
        ############################################################

        docsdir = os.path.join(PUBLISHING_ROOT, "docs")
        if os.path.isdir(docsdir):
            for foldername in os.listdir(docsdir):
                lockfile = os.path.join(docsdir, foldername, "LOCK")
                if os.path.exists(lockfile):
                    note(2, "Removing lock file in folder %s...", foldername)
                    os.unlink(lockfile)

        ############################################################
        ###
        ###  remove any empty directories in pending
        ###
        ############################################################

        pendingdir = os.path.join(PUBLISHING_ROOT, "pending")
        if os.path.isdir(pendingdir):
            for foldername in os.listdir(pendingdir):
                fpath = os.path.join(pendingdir, foldername)
                if os.path.isdir(fpath) and (not os.listdir(fpath)):
                    note(2, "Removing empty folder %s in pending...", foldername)
                    os.rmdir(fpath)

        ############################################################
        ###
        ###  see if clients need certificates
        ###
        ############################################################

        root_certs_file = conf.get("root-certificates-file")
        if root_certs_file and (not os.path.exists(root_certs_file)):
            sys.stderr.write("specified root-certificates-file %s does not exist!\n" % root_certs_file)
            sys.exit(1)

        ############################################################
        ###
        ###  check for new repository, and initialize if necessary
        ###
        ############################################################

        if not os.path.exists(mdpath):
            # fresh start with a new repository
            params = {'default-listing-format' : conf.get('default-listing-format', "Icon MRU"),
                      'default-listing-count' : conf.get_int('default-listing-count', 50),
                      'default-listing-order' : conf.get('default-listing-order', 'lastused'),
                      'thumbnail-strategy': conf.get('thumbnail-strategy', "log-area"),
                      'summary-length' : conf.get_int('summary-length', 250),
                      'overview-refresh-period' : conf.get_int('overview-refresh-period', 60 * 2),
                      'extensions-path' : conf.get('actions-path', ''),
                      }
            repositoryData.update(params)
            update_metadata(mdpath, repositoryData)

        ############################################################
        ###
        ###  read the repository metadata
        ###
        ############################################################

        repo_metadata = read_metadata(mdpath)
        use_http = (repo_metadata.get("use-http") == "true") or conf.get_bool("use-http")
        allow_old_extensions = ((repo_metadata.get("allow-old-extensions") == "true")
                                or conf.get_bool("allow-old-extensions", False))

        ############################################################
        ###
        ###  load any user initialization modules
        ###
        ############################################################

        from uplib.basicPlugins import set_button_addition_allowed

        set_button_addition_allowed(button_addition_enabled)

        user_init_modules = []
        user_inits = conf.get("user-initialization-modules")
        if user_inits:
            if repo_metadata.has_key("extensions-path"):
                user_init_dirs = repo_metadata["extensions-path"]
            else:
                user_init_dirs = None
            user_init_names = user_inits.split(':')
            user_init_modules = []
            for name in user_init_names:
                try:
                    m = find_and_load_extension(name, user_init_dirs, allow_old_extensions=allow_old_extensions)
                except MissingResource, x:
                    note("Can't load %s:  %s", name, x)
                else:
                    user_init_modules.append(m)
            note("user init modules are %s, dirs are %s", user_init_modules, user_init_dirs)

        sys_init_modules = []
        repo_init_paths = []
        repo_init_dirs = repo_metadata.get("autoinit-extension-dirs")
        if repo_init_dirs:
            repo_init_paths = [x.strip() for x in repo_init_dirs.split(";") if os.path.exists(x.strip())]
        repo_init_paths.append(os.path.join(PUBLISHING_ROOT, "overhead", "extensions", "active"))
        for repo_init_path in repo_init_paths:
            if os.path.isdir(repo_init_path):
                files = os.listdir(repo_init_path)
                for filename in files:
                    if (filename.endswith('.py') or
                        (os.path.isdir(os.path.join(repo_init_path, filename)) and
                         os.path.exists(os.path.join(repo_init_path, filename, "__init__.py")))):
                        try:
                            mod = find_and_load_extension(os.path.splitext(filename)[0], repo_init_path,
                                                          allow_old_extensions=allow_old_extensions)
                        except MissingResource, x:
                            note("Can't load %s:  %s", filename, x)
                        else:
                            if mod and (hasattr(mod, "before_repository_instantiation") or
                                        hasattr(mod, "after_repository_instantiation")):
                                sys_init_modules.append(mod)

        sys_inits_path = os.path.join(conf.get('uplib-lib'), 'site-extensions')
        if os.path.isdir(sys_inits_path):
            files = os.listdir(sys_inits_path)
            for filename in files:
                if (filename.endswith('.py') or
                    (os.path.isdir(os.path.join(sys_inits_path, filename)) and
                     os.path.exists(os.path.join(sys_inits_path, filename, "__init__.py")))):
                    try:
                        mod = find_and_load_extension(os.path.splitext(filename)[0], sys_inits_path,
                                                      allow_old_extensions=allow_old_extensions)
                    except MissingResource, x:
                        note("Can't load %s:  %s", filename, x)
                    else:
                        if mod and (hasattr(mod, "before_repository_instantiation") or
                                    hasattr(mod, "after_repository_instantiation")):
                            sys_init_modules.append(mod)

        init_modules = user_init_modules + sys_init_modules

        for mod in init_modules:
            if mod:
                if hasattr(mod, "before_repository_instantiation"):
                    note(2, "Calling before method in module '%s'", mod)
                    try:
                        mod.before_repository_instantiation(repositoryData)
                    except:
                        type, value, tb = sys.exc_info()
                        note(2, "Can't invoke before_repository_instantiation method of module %s:\n%s",
                             mod, string.join(traceback.format_exception(type, value, tb)))

        set_button_addition_allowed(True)

        ############################################################
        ###
        ###  Now build the repository obj, and load any stored state
        ###
        ############################################################

        repo = Repository(version, PUBLISHING_ROOT, repositoryData, inc_threads=inc_threads)

        # Save our PID in the right place
        fp = open(os.path.join(repo.root(), "overhead", "angel.pid"), 'w')
        fp.write(str(os.getpid()))
        fp.close()

        check_repository_in_list (PUBLISHING_ROOT, True)

        tpath = os.path.join(repo.overhead_folder(), hostname + ".pem")
        if os.path.exists(tpath):
            certfile = tpath
            repo.set_certfilename(certfile)
        else:
            certfile = repo.certfilename()

        use_ssl = _have_ssl and (not use_http or use_stunnel) and os.path.exists(certfile)

        if use_ssl:
            # Save our certificate file path in the right place
            fp = open(os.path.join(PUBLISHING_ROOT, "overhead", "angel.certpath"), 'w')
            fp.write(certfile)
            fp.close()

        if use_stunnel and (stunnel_version >= 4):
            ip_addr = repo.get_param("ip-address")
            bind_external = (repo.get_param("bind-to-hostname-if-no-password", "false").lower() == "true")
            if (ip_addr is None) and bind_external and repo.check_password("") and ("." in hostname):
                ip_addr = hostname
            if not ip_addr:
                ip_addr = "127.0.0.1"
            if ip_addr != "127.0.0.1":
                connect_addr = ip_addr + ":" + str(repo.port())
            else:
                connect_addr = str(repo.port())
            if not sys.platform.startswith("win"):
                pidline = "pid = %s/stunnel.pid" % os.path.join(PUBLISHING_ROOT, "overhead")
            else:
                pidline = ""
            fp = open(stunnel_conf_file, "w")
            fp.write(Repository.STUNNEL_CONF_BOILERPLATE.strip() % {
                "certfilename": os.path.split(certfile)[1],
                "pid-line" : pidline,
                "overhead-dir": os.path.join(PUBLISHING_ROOT, "overhead"),
                "accept-addr": str(repo.secure_port()),
                "connect-addr": connect_addr } + "\n")
            fp.close()
        elif not use_stunnel:
            ip_addr = "0.0.0.0"
        else:
            ip_addr = "127.0.0.1"

        ############################################################
        ###
        ###  If the lucene jarfile has changed, re-index the repo
        ###
        ############################################################

        old_jarfile = repo.get_param("lucene-jarfile")
        write_lock = os.path.join(repo.index_path(), "write.lock")
        if (not old_jarfile) or (old_jarfile != lucene_jarfile):
            note("old Lucene jarfile was %s, new jarfile is %s.", old_jarfile, lucene_jarfile)
            p = repo.index_path()
            if os.path.exists(p):
                note("removing old index...")
                shutil.rmtree(p)
            note("re-indexing all documents to be compatible with %s...", lucene_jarfile)
            repo.reindex()
            repo.set_lucene_jarfile(lucene_jarfile)
            note("done reindexing.")

        elif os.path.exists(write_lock):
            os.unlink(write_lock)

        elif not os.path.exists(repo.index_path()):
            # no index!  generate it
            note("generating Lucene index for repository...")
            repo.reindex()
            note("done indexing.")

        ############################################################
        ###
        ###  now do the after-instantiation routines, if any
        ###
        ############################################################

        set_button_addition_allowed(button_addition_enabled)

        for mod in init_modules:
            if mod and hasattr(mod, "after_repository_instantiation"):
                note(2, "Calling after method in module '%s'", mod)
                try:
                    mod.after_repository_instantiation(repo)
                except:
                    type, value, tb = sys.exc_info()
                    note(2, "Can't invoke after_repository_instantiation method of module %s:\n%s",
                         mod, string.join(traceback.format_exception(type, value, tb)))

        # count the # of docs and pages...
        if conf.get_bool("immediately-calculate-repository-statistics", True):
            from uplib.basicPlugins import figure_stats
            uthread.start_new_thread(figure_stats, (repo,), "Calculating repo stats")

        set_button_addition_allowed(True)

        # wonder what the ripper chain looks like now?
        note(3, "Rippers now %s", [x.__class__.__name__ for x in repo.rippers()])

        ############################################################
        ###
        ###  if email support is desired, add it
        ###
        ############################################################

        if (conf.get_bool("email-supported", True)):
            try:
                from uplib import emailParser
                emailParser.initialize(repo, conf)
            except:
                note("couldn't initialize email:\n%s", string.join(traceback.format_exception(*sys.exc_info())))

        return repo, use_ssl, ip_addr, conf

    build_world=staticmethod(build_world)
