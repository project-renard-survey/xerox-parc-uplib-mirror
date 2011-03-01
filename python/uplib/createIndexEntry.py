#!/usr/bin/env python
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
#

import re, os, sys, string, time, shutil, tempfile, stat, traceback, cgi

from uplib.plibUtil import false, true, Error, note, configurator, set_verbosity, subproc, MutexLock, HAVE_PYLUCENE
from uplib.plibUtil import lock_folder, unlock_folder
import uplib.plibUtil as plibUtil
from uplib.ripper import Ripper

LUCENE = HAVE_PYLUCENE or "java"

FILE_END = 2    # for seek

JAVA = None
LUCENE_JAR = None
INDEXING_JAR = None
INDEXING_ADD_CMD = None
INDEXING_BATCHADD_CMD = None
INDEXING_REMOVE_CMD = None
INDEXING_PROPERTIES = ""
DEBUG_FLAGS = ""
SECTION_LOCK = None

# used by JCC-PyLucene to cache a context
LUCENE_CONTEXT = None

SECTION_LOCK = MutexLock('LuceneIndex')

def update_configuration():
    global JAVA, INDEXING_ADD_CMD, INDEXING_REMOVE_CMD, INDEXING_JAR, LUCENE_JAR, INDEXING_PROPERTIES, INDEXING_BATCHADD_CMD, DEBUG_FLAGS

    conf = configurator.default_configurator()
    props = conf.get("indexing-properties")

    if LUCENE == "java":

        JAVA = conf.get("java")
        LUCENE_JAR = conf.get("lucene-jarfile")
        INDEXING_JAR = conf.get("uplib-indexing-jarfile")
        INDEXING_ADD_CMD = conf.get("indexing-add-command")
        INDEXING_BATCHADD_CMD = conf.get("indexing-batch-add-command")
        INDEXING_REMOVE_CMD = conf.get("indexing-remove-command")
        if plibUtil._verbosity > 1:
            DEBUG_FLAGS = " -Dcom.parc.uplib.indexing.debugMode=true"
        else:
            DEBUG_FLAGS = ""

        if props:
            INDEXING_PROPERTIES = "\"-Dcom.parc.uplib.indexing.indexProperties=%s\"" % props
        else:
            INDEXING_PROPERTIES = ""

    elif LUCENE == 'jcc':

        import uplib.indexing
        uplib.indexing.initialize()

def get_context (repo_index_dir):

    global LUCENE_CONTEXT
    if not (LUCENE_CONTEXT and LUCENE_CONTEXT.samedir(LUCENE_CONTEXT.directorypath, repo_index_dir)):
        update_configuration()
        if LUCENE == "jcc":
            import uplib.indexing
            LUCENE_CONTEXT = uplib.indexing.LuceneContext(repo_index_dir)
    return LUCENE_CONTEXT

def index_folder (folder, repo_index_dir):

    update_configuration()

    docs_dir, doc_id = os.path.split(folder)
    SECTION_LOCK.acquire()
    try:
        try:
            if LUCENE == 'jcc':
                c = get_context(repo_index_dir)
                c.index(folder, doc_id)
            else:
                indexingcmd = INDEXING_ADD_CMD % (JAVA, DEBUG_FLAGS, INDEXING_PROPERTIES, LUCENE_JAR, INDEXING_JAR, repo_index_dir, docs_dir, doc_id)
                note(3, "  indexing with %s", indexingcmd)
                status, output, tsignal = subproc(indexingcmd)
        except:
            note(0, "Can't index folder %s:\n%s",
                 folder, ''.join(traceback.format_exception(*sys.exc_info())))
    finally:
        SECTION_LOCK.release()
    if LUCENE != 'jcc':
        note(3, "  indexing output is <%s>", output)
        if status != 0:
            raise Error ("%s signals non-zero exit status %d attempting to index %s:\n%s" % (JAVA, status, folder, output))

def index_folders (docs_dir, doc_ids, repo_index_dir):

    update_configuration()

    if not doc_ids:
        return

    if LUCENE == 'jcc':

        c = get_context(repo_index_dir)
        SECTION_LOCK.acquire()
        try:
            for id in doc_ids:
                folderpath = os.path.join(docs_dir, id)
                if os.path.isdir(folderpath):
                    lock_folder(folderpath)
                    try:
                        try:
                            c.index(folderpath, id, False)
                        except:
                            note(0, "Can't index folder %s:\n%s",
                                 folderpath, ''.join(traceback.format_exception(*sys.exc_info())))
                    finally:
                        unlock_folder(folderpath)
            c.reopen()
        finally:
            SECTION_LOCK.release()
        return

    else:

        # invoke Java to do indexing

        if len(doc_ids) > 6:

            fname = tempfile.mktemp()
            fp = open(fname, "w")
            fp.write(string.join(doc_ids, '\n'))
            fp.close()
            indexingcmd = INDEXING_BATCHADD_CMD % (JAVA, DEBUG_FLAGS, INDEXING_PROPERTIES, LUCENE_JAR, INDEXING_JAR, repo_index_dir, docs_dir, fname)
            note(3, "  indexing with %s", indexingcmd)
            SECTION_LOCK.acquire()
            try:
                status, output, tsignal = subproc(indexingcmd)
            finally:
                SECTION_LOCK.release()
                os.unlink(fname)
            note(3, "  indexing output is <%s>", output)
            if status != 0:
                raise Error ("%s signals non-zero exit status %d attempting to index %s:\n%s" % (JAVA, status, doc_ids, output))

        else:

            folders = string.join(doc_ids, ' ')
            indexingcmd = INDEXING_ADD_CMD % (JAVA, DEBUG_FLAGS, INDEXING_PROPERTIES, LUCENE_JAR, INDEXING_JAR, repo_index_dir, docs_dir, folders)
            note(3, "  indexing with %s", indexingcmd)
            SECTION_LOCK.acquire()
            try:
                status, output, tsignal = subproc(indexingcmd)
            finally:
                SECTION_LOCK.release()
            note(3, "  indexing output is <%s>", output)
            if status != 0:
                raise Error ("%s signals non-zero exit status %d attempting to index %s:\n%s" % (JAVA, status, doc_ids, output))


def remove_from_index (repo_index_dir, doc_id):

    update_configuration()

    if LUCENE == 'jcc':
        SECTION_LOCK.acquire()
        try:
            c = get_context(repo_index_dir)
            c.remove(doc_id)
        finally:
            SECTION_LOCK.release()

    else:

        indexingcmd = INDEXING_REMOVE_CMD % (JAVA, DEBUG_FLAGS, "", LUCENE_JAR, INDEXING_JAR, repo_index_dir, doc_id)
        note(3, "  de-indexing with %s", indexingcmd)
        SECTION_LOCK.acquire()
        try:
            status, output, tsignal = subproc(indexingcmd)
        finally:
            SECTION_LOCK.release()
        note(3, "  indexing output is <%s>", output)
        if status != 0:
            raise Error ("%s signals non-zero exit status %d attempting to remove %s:\n%s" % (JAVA, status, doc_id, output))

class LuceneRipper (Ripper):

    def requires (self):
        return ("SimpleSummaryRipper")

    def rip (self, location, doc_id):
        index_folder(location, self.repository().index_path())

    def rerun_after_metadata_changes(self, changed_fields=None):
        return True

