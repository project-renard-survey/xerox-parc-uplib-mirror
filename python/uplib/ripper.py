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
# Code to support ripping of documents into various formats
#

import re, os, sys, string, time, shutil, tempfile, stat, traceback, thread, unicodedata, types

from uplib.plibUtil import false, true, Error, note, configurator, lock_folder, unlock_folder, subproc, update_metadata, read_metadata
from uplib.plibUtil import read_file_handling_charset_returning_bytes, read_file_handling_charset
from uplib.webutils import HTTPCodes

############################################################
###
###  Global configuration variables for SummaryRipper
###
############################################################

SUMMARY_LENGTH = None

newline_expression = re.compile(r'(\s*\n)+')
whitespace_expression = re.compile(r'\s+')
charset_pattern = re.compile(r"^Content-Type:\s*text/plain;\s*charset=([^)]*)\n", re.IGNORECASE)
alnum_chars = string.digits + string.letters

############################################################
###
###  Ripper class
###
############################################################

class Ripper (object):

    def __init__(self, repo):
        self.__repo = repo

    def name(self):
        return self.__class__.__name__

    def requires(self):
        #returns the class names of rippers which must be run before this ripper
        return ()

    def repository (self):
        return self.__repo

    def rip (self, location, doc_id):
        raise Error ("rip method not implemented for class %s!" % self.__class__)

    def rerun_after_metadata_changes(self, changed_fields=None):
        """Whether to re-run this ripper if the document metadata changes.
        Defaults to ``False``.  Should override and return True if needed.
        """
        return False

    def rerun_after_other_ripper(self, other_ripper_name):
        """Whether to re-run this ripper after the other ripper has run.
        Defaults to ``False``.  Should override and return True if needed.

        :param other_ripper_name: name of other ripper which has run
        :type other_ripper_name: string
        :return: whether or not to run the ripper
        :rtype: boolean
        """
        return False

    # some utility methods

    def folder_metadata_path (self, location):
        return os.path.join(location, "metadata.txt")

    def get_folder_metadata (self, location):
        return read_metadata(self.folder_metadata_path(location))

    def update_folder_metadata(self, location, md):
        return update_metadata(self.folder_metadata_path(location), md)

    def folder_text_path (self, location):
        return os.path.join(location, "contents.txt")
    
    def get_folder_text_bytes (self, location):
        path = self.folder_text_path(location)
        if os.path.exists(path):
            fp, charset, language = read_file_handling_charset_returning_bytes(path)
            data = fp.read()
            fp.close()
            return data, charset, language
        else:
            return None, None, None

    def get_folder_text (self, location):
        path = self.folder_text_path(location)
        if os.path.exists(path):
            text, charset, language = read_file_handling_charset(path, return_charset=True)
            return text, language
        else:
            return None, None

############################################################
###
###  SummaryRipper
###
############################################################

class SimpleSummaryRipper (Ripper):

    def __init__(self, repository, summary_length):
        Ripper.__init__(self, repository)
        self.__summary_length = summary_length

    def provides(self):
        return "SimpleSummary"

    def rip (self, location, doc_id):

        text, language = self.get_folder_text(location)
        if not text:
            return

        sum_path = os.path.join(location, "summary.txt")

        if os.path.exists(sum_path):
            # summary already there
            return

        if text.strip():
            txt = newline_expression.sub(' / ', text)
            txt = whitespace_expression.sub(' ', txt)
            while txt and not txt[0] in alnum_chars:
                # remove leading punctuation
                txt = txt[1:]
            if txt:
                txt = txt[:min(self.__summary_length, len(txt))]
        else:
            txt = u""

        f = open(sum_path, 'wb')
        f.write(txt.encode("ascii", "replace"))
        f.close()
        os.chmod(sum_path, 0600)

        self.update_folder_metadata(location, { "summary" : txt })


############################################################
###
###  rerip_generic
###
############################################################

def _rerip_worker(response, docs, ripper, other_rippers):
    fp = response.open("text/plain")
    try:
        for doc in docs:
            location = doc.folder()
            lock_folder(location)
            try:
                try:
                    ripper.rip(location, doc.id)
                except:
                    msg = ''.join(traceback.format_exception(*sys.exc_info()))
                    note("Error running %s ripper:\n%s", ripper.name(), msg)
                    fp.write("Error running %s ripper:\n%s" % (ripper.name(), msg))
                else:
                    fp.write("ripped %s with %s\n" % (doc.id, ripper.name()))
                    reruns = [ripper.name(),]
                    for r in doc.repo.rippers():
                        if ((other_rippers and (r.name() in other_rippers)) or
                            any([r.rerun_after_other_ripper(x) for x in reruns])):
                            try:
                                r.rip(location, doc.id)
                            except:
                                msg = ''.join(traceback.format_exception(*sys.exc_info()))
                                note("Error running %s ripper:\n%s", r.name(), msg)
                                fp.write("Error running %s ripper:\n%s" % (r.name(), msg))
                            else:
                                reruns.append(r.name())
                                fp.write("ripped %s with %s\n" % (doc.id, r.name()))
                    for r in [x for x in other_rippers if isinstance(x, Ripper)]:
                        if r.name() not in reruns:
                            try:
                                r.rip(location, doc.id)
                            except:
                                msg = ''.join(traceback.format_exception(*sys.exc_info()))
                                note("Error running %s ripper:\n%s", r.name(), msg)
                                fp.write("Error running %s ripper:\n%s" % (r.name(), msg))
                            else:
                                reruns.append(r.name())
                                fp.write("ripped %s with %s\n" % (doc.id, r.name()))
            finally:
                unlock_folder(location)
    finally:
        fp.close()

def rerip_generic (repo, response, params, ripper, other_ripper_names=None, docs=None, background=False):
    """
    Generic rerip functionality, intended as an "abstract function", to be used
    to implement specific rerip functions for other rippers.

    :param repo: the repository
    :type repo: uplib.repository.Repository
    :param response: the response object to send back results with
    :type response: uplib.angelHandler.Response
    :param params: the parameters passed in the HTTP call
    :type params: dict
    :param ripper: the ripper to re-run
    :type ripper: uplib.ripper.Ripper
    :param other_ripper_names: the names of other rippers from the standard ripper chain to rerun after running ripper
    :type other_ripper_names: list(string)
    """

    if not docs:
        coll = params.get("coll")
        if coll:
            coll = repo.get_collection(params.get('coll'), true)
        docs = coll and coll.docs()
    if not docs:
        doc_ids = params.get('doc_id')
        if type(doc_ids) in types.StringTypes:
            if doc_ids == "all":
                docs = repo.generate_docs()
            else:
                doc_ids = ( doc_ids, )
        if (not docs) and doc_ids:
            docs = [repo.get_document(id) for id in doc_ids if repo.valid_doc_id(id)]

    if not docs:
        response.error(HTTPCodes.BAD_REQUEST, "No documents specified to rerip.")
        return

    if background:
        response.fork_request(_rerip_worker, response, docs, ripper, other_ripper_names)
    else:
        _rerip_worker(response, docs, ripper, other_ripper_names)

############################################################
###
###  get_default_rippers
###
############################################################

def get_default_rippers(repo):
    """Returns a default set of Ripper instances.

    :param repo: the repository instance
    :type repo: uplib.repository.Repository
    :return: the default set of rippers, in order
    :rtype: list(uplib.ripper.Ripper)
    """

    from uplib import createThumbnails, createHTML, createIndexEntry, createPageBboxes, paragraphs

    conf = configurator.default_configurator()

    default = [SimpleSummaryRipper(repo, int(repo.get_param("summary-length") or conf.get_int("summary-length") or 250)),
               paragraphs.ParagraphRipper(repo),
               createThumbnails.ThumbnailRipper(repo),
               createPageBboxes.BboxesRipper(repo),
               createHTML.HTMLRipper(repo),
               createIndexEntry.LuceneRipper(repo),
               ]

    if (sys.platform == "darwin") and conf.get_bool("install-finder-icon-ripper", True):
        from macstuff import MacRipper
        # add the Mac ripper just before the Lucene ripper
        default.insert(-2, MacRipper(repo))

    # if we have language support, add that ripper, too
    try:
        from uplib.language import GuessLanguageRipper
    except ImportError:
        pass
    else:
        default.insert(0, GuessLanguageRipper(repo))

    return default
