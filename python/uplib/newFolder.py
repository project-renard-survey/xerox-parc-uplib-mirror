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
# See the ARCHITECTURE document for information about the structure of document
# folders.
#

import re, os, sys, string, time, shutil, tempfile, stat, traceback, StringIO, Queue, threading

from uplib.plibUtil import false, true, Error, note, configurator, lock_folder, unlock_folder, subproc, update_metadata, read_metadata, DOC_ID_RE, unzip, uthread
from uplib.createIndexEntry import remove_from_index
# import uplib.code_timer as code_timer

############################################################
###
###  Global configuration variables
###
############################################################

CODETIMER_ON = False

TIFFINFO = None                 # the location of the tiffinfo program
TIFFSET = None                  # the location of the tiffset program
TIFFCP = None                   # the location of the tiffcp program

TAR = None
UNTAR_CMD = None

############################################################
###
###  Exception to raise to abort the processing of a folder
###
############################################################

class AbortDocumentIncorporation (Error):

    def __init__(self, id, msg):
        self.id = id
        self.message = msg

############################################################
###
###  Functions
###
############################################################

def add_description (directory, tiff_file, description_file):
    tiff_path = os.path.join(directory, tiff_file)
    tfname = tempfile.mktemp()
    os.system("%s -c none %s %s; %s -sf DESCRIPTION %s %s; %s -c g4 %s %s"
              % (TIFFCP, tiff_path, tfname,
                 TIFFSET, os.path.join(directory, description_file), tfname,
                 TIFFCP, tfname, tiff_path))
    os.unlink(tfname)

def get_possible_tiff_description (filename):

    pipeout = os.popen(TIFFINFO + " " + filename, "r")
    tiffinfo = pipeout.readlines()
    status = pipeout.close()
    desc = ""
    if status == 0:
        for line in tiffinfo:
            if re.match("^  Image Description: ", line):
                desc = re.sub(line[:-1], '^  Image Description: "', '')
                desc = re.sub(desc, '"$', '')
    return string.strip(desc)

def process_folder (repo, id, directory, delete_p, replace=None):

    def _protect_files (mode, dirname, files):
        for file in files:
            thepath = os.path.join(dirname, file)
            if os.path.isdir(thepath):
                os.chmod(thepath, 0700)
            else:
                os.chmod(thepath, 0600)

    note(2, "processing folder %s...", directory)

    description = None
    contents = None
    summary = None
    metadata = None
    wordbboxes = os.path.join(directory, "wordbboxes")
    tifffile = os.path.join(directory, "document.tiff")
    pageimagesdir = os.path.join(directory, "page-images")
    images = os.path.join(directory, "images")
    originals = os.path.join(directory, "originals")
    links = os.path.join(directory, "links")

    names = os.listdir(directory)
    for name in names:
        if string.lower(name) == "contents.txt":
            contents = os.path.join(directory, name)
        elif string.lower(name) == "summary.txt":
            summary = os.path.join(directory, name)
        elif string.lower(name) == "metadata.txt":
            metadata = os.path.join(directory, name)

    if replace is None:
        newdir = os.path.join(repo.pending_folder(), id)
    else:
        newdir = replace
    if not os.path.isdir(newdir):
        raise Error("Pending directory %s does not exist!" % newdir)

    try:
        lock_folder(newdir)

        try:
            if os.path.exists(images):
                destpath = os.path.join(newdir, "images")
                if replace and os.path.exists(destpath): shutil.rmtree(destpath)
                shutil.copytree (images, destpath)
                if delete_p: shutil.rmtree (images, true)
            if os.path.exists(originals):
                destpath = os.path.join(newdir, "originals")
                if replace and os.path.exists(destpath): shutil.rmtree(destpath)
                shutil.copytree (originals, destpath)
                if delete_p: shutil.rmtree (originals, true)
            if os.path.exists(links):
                destpath = os.path.join(newdir, "links")
                if replace and os.path.exists(destpath): shutil.rmtree(destpath)
                shutil.copytree (links, destpath)
                if delete_p: shutil.rmtree (links, true)
            if metadata:
                destpath = os.path.join(newdir, "metadata.txt")
                if replace and os.path.exists(destpath): os.unlink(destpath)
                shutil.copyfile(metadata, destpath)
                m = read_metadata(metadata)
                if m.has_key("title"):
                    note("Title of uploaded folder is '%s'", m['title'])
                if delete_p: os.unlink(metadata)
            else:
                # create an empty metadata.txt
                destpath = os.path.join(newdir, "metadata.txt")
                if replace and os.path.exists(destpath): os.unlink(destpath)
                mdf = open(destpath, 'w')
                mdf.flush()
                mdf.close()

            newcontents = os.path.join(newdir, "contents.txt")
            if contents:
                if replace and os.path.exists(newcontents): os.unlink(newcontents)
                shutil.copyfile(contents, newcontents)
                if delete_p: os.unlink(contents)

            newsummary = os.path.join(newdir, "summary.txt")
            if summary:
                if replace and os.path.exists(newsummary): os.unlink(newsummary)
                shutil.copyfile(summary, newsummary)
                if delete_p: os.unlink(summary)

            if os.path.exists(wordbboxes):
                destpath = os.path.join(newdir, "wordbboxes")
                if replace and os.path.exists(destpath): os.unlink(destpath)
                shutil.copyfile(wordbboxes, destpath)
                if delete_p: os.unlink(wordbboxes)

            if os.path.exists(tifffile):
                destpath = os.path.join(newdir, "document.tiff")
                if replace and os.path.exists(destpath): os.unlink(destpath)
                shutil.copyfile(tifffile, destpath)
                if delete_p: os.unlink(tifffile)
            elif os.path.isdir(pageimagesdir):
                destpath = os.path.join(newdir, "page-images")
                if replace and os.path.exists(destpath): shutil.rmtree(destpath)
                shutil.copytree(pageimagesdir, destpath)
                if delete_p: shutil.rmtree(pageimagesdir, true)

            os.path.walk(newdir, _protect_files, None)
            os.chmod(newdir, 0700)

            return id

        finally:
            unlock_folder (newdir)

    except:
        type, value, tb = sys.exc_info()
        if os.path.exists(newdir) and not replace:
            shutil.rmtree(newdir)
        # re-raise the exception
        raise value, None, tb


def process_tarred_folder (repo, id, tarfile, metadata):
    # create a new folder, and populate it
    dirname = tempfile.mktemp()
    try:
        os.mkdir(dirname)
        os.chmod(dirname, 0700)
        cmd = UNTAR_CMD % (dirname, TAR, tarfile)
        note(2, "Untarring folder into temporary directory %s", dirname)
        status, output, signal = subproc(cmd)
        if status == 0:
            note(2, "Successfully untarred folder into %s", dirname)
            if metadata:
                update_metadata(os.path.join(dirname, "metadata.txt"), metadata)
            if (os.path.exists(os.path.join(dirname, "document.tiff")) or
                os.path.isdir(os.path.join(dirname, "page-images"))):
                return process_folder(repo, id, dirname, true)
            else:
                raise Error("invalid folder -- no page images file")
        else:
            raise Error("Problem untarring folder:\n%s" % output)
    finally:
        if os.path.exists(dirname):
            shutil.rmtree(dirname)        
    

def process_zipped_folder (repo, id, zipfile, metadata):
    # create a new folder, and populate it
    dirname = tempfile.mktemp()
    try:
        os.mkdir(dirname)
        os.chmod(dirname, 0700)
        note(2, "Unzipping folder into temporary directory %s", dirname)
        try:
            unzip(dirname, zipfile)
            note(2, "Successfully unzipped folder into %s", dirname)
            if metadata:
                update_metadata(os.path.join(dirname, "metadata.txt"), metadata)
        except:
            typ, ex, tb = sys.exc_info()
            s = string.join(traceback.format_exception(typ, ex, tb))
            raise Error("Problem unzipping folder:\n%s" % s)
        if (os.path.exists(os.path.join(dirname, "document.tiff")) or
            os.path.isdir(os.path.join(dirname, "page-images"))):
            return process_folder(repo, id, dirname, true)
        else:
            raise Error("invalid folder -- no page images")
    finally:
        if os.path.exists(dirname):
            shutil.rmtree(dirname)        
    

def update_configuration():
    global TIFFINFO, TIFFCP, TIFFSET, TAR, UNTAR_CMD, SUMMARY_LENGTH, CODETIMER_ON

    conf = configurator.default_configurator()

    TIFFINFO = conf.get("tiffinfo")
    TIFFCP = conf.get("tiffcp")
    TIFFSET = conf.get("tiffset")
    TAR = conf.get("tar")
    UNTAR_CMD = conf.get("untar-command")
    SUMMARY_LENGTH = conf.get_int("summary-length")
    CODETIMER_ON = conf.get_bool("codetimer-on", False)



def note_error (folderpath, e):
    fp = open(os.path.join(folderpath, 'ERROR'), 'w')
    rippingpath = os.path.join(folderpath, 'RIPPING')
    if os.path.exists(rippingpath):
        ripper = open(rippingpath, 'rb').read()
        fp.write("While running ripper class '%s', the following exception occurred:\n" % ripper)
    fp.write(''.join(traceback.format_exception(*e)))
    fp.close()    


def _run_rippers (folderpath, repo, id):

    rippers = repo.rippers()
    lock_folder(folderpath)
    try:
        which_ripper = os.path.join(folderpath, "RIPPING")
        try:
            for ripper in rippers:
                note("%s:  running ripper %s", id, str(ripper))
                fp = open(which_ripper, 'wb')
                fp.write(ripper.__class__.__name__)
                fp.close()
                try:
    #                 if CODETIMER_ON:
    #                     code_timer.StartInt("newFolder$ripping-%s" % ripper.name(), "uplib")

                    ripper.rip(folderpath, id)

                finally:

                    pass
    #                 if CODETIMER_ON:
    #                     code_timer.StopInt("newFolder$ripping-%s" % ripper.name(), "uplib")

        except AbortDocumentIncorporation:
            type, value, tb = sys.exc_info()
            raise value, None, tb

        except:
            type, value, tb = sys.exc_info()
            note("Running document rippers raised the following exception:\n%s",
                 string.join(traceback.format_exception(type, value, tb)))
            note("Fixing the problem and restarting the UpLib angel will cause this document to be added to the repository.")
            # re-raise the exception
            raise value, None, tb

        else:
            if os.path.exists(which_ripper):
                os.unlink(which_ripper)
    finally:
        unlock_folder(folderpath)

def _finish_inclusion (repo, folderpath, id):

    if (os.path.exists(os.path.join(folderpath, "UNPACKED")) and
        not os.path.exists(os.path.join(folderpath, "RIPPED"))):

#         if CODETIMER_ON:
#             code_timer.StartInt("newFolder$ripping", "uplib")

        _run_rippers(folderpath, repo, id)

        fp = open(os.path.join(folderpath, "RIPPED"), 'w')
        fp.flush()
        fp.close()

        which_ripper = os.path.join(folderpath, "RIPPING")
        if os.path.exists(which_ripper):
            os.unlink(which_ripper)
        os.unlink(os.path.join(folderpath, "UNPACKED"))

#         if CODETIMER_ON:
#             code_timer.StopInt("newFolder$ripping", "uplib")

    if os.path.exists(os.path.join(folderpath, "RIPPED")):

#         if CODETIMER_ON:
#             code_timer.StartInt("newFolder$register", "uplib")

        # OK, the infrastructure is established, now put it in place
        newfolderpath = repo.doc_location(id)
        d = os.path.split(newfolderpath)[0]
        if not os.path.exists(d):
            os.makedirs(d)
        os.rename(folderpath, newfolderpath)
        note("moved %s to docs", id)

        os.unlink(os.path.join(newfolderpath, "RIPPED"))

        repo.register_new_document(id)
        note("%s now registered with repository %s", id, repo)

#         if CODETIMER_ON:
#             code_timer.StopInt("newFolder$register", "uplib")

    folderpath = repo.doc_location(id)
    if os.path.exists(os.path.join(folderpath, "ERROR")):
        os.unlink(os.path.join(folderpath, "ERROR"))


def flesh_out_folder(id, tmpfilename, metadata, repo, unpack_fn, counter):
    try:
        try:
#             note(3, "CODETIMER_ON is %s", CODETIMER_ON)
#             if CODETIMER_ON:
#                 code_timer.Init()
#                 code_timer.CreateTable("uplib")
#                 code_timer.CodeTimerOn()
#                 code_timer.StartInt("newFolder$unpack", "uplib")
#             else:
#                 code_timer.CodeTimerOff()

            if unpack_fn and tmpfilename and os.path.exists(tmpfilename):
                unpack_fn(repo, id, tmpfilename, metadata)

#             if CODETIMER_ON:
#                 code_timer.StopInt("newFolder$unpack", "uplib")
            folderpath = repo.pending_location(id)
            try:
                note("unpacked new folder in %s", folderpath)
                if not sys.platform.lower().startswith("win"):
                    s, o, t = subproc("ls -Rl %s" % folderpath)
                    note("%s\n" % o)

                fp = open(os.path.join(folderpath, "UNPACKED"), 'w')
                fp.flush()
                fp.close()

                # as of this point, we can restart the inclusion of the document

                md = read_metadata(os.path.join(folderpath, "metadata.txt"))
                replacement_id = md.get("replacement-contents-for")
                if replacement_id:
                    if repo.valid_doc_id(replacement_id):
                        # contents to replace another document
                        md["replacement-contents-for"] = ""
                        update_metadata(os.path.join(folderpath, "metadata.txt"), md)
                        note(2, "replacing contents of %s with this data...", replacement_id)
                        existing_document = repo.get_document(replacement_id)
                        new_folder = existing_document.folder()
                        process_folder(repo, replacement_id, folderpath, false, new_folder)
                        _run_rippers(new_folder, repo, replacement_id)
                        existing_document.recache()
                        repo.touch_doc(existing_document)
                        raise AbortDocumentIncorporation(id, "replacement for existing document %s" % replacement_id)
                    else:
                        raise AbortDocumentIncorporation(id, "replacement for non-existent document %s" % replacement_id)

                _finish_inclusion (repo, folderpath, id)

#                 if CODETIMER_ON:
#                     noteOut = StringIO.StringIO()
#                     noteOut.write("\nCode Timer statistics (what took time, in milliseconds):\n")
#                     code_timer.PrintTable(noteOut, "uplib")
#                     noteOut.write("\n")
#                     noteOutString = noteOut.getvalue()
#                     note(3, noteOutString)

            except:
                type, value, tb = sys.exc_info()
                note("%s", ''.join(traceback.format_exception(type, value, tb)))
                note_error(folderpath, (type, value, tb))
                raise value, None, tb

        except AbortDocumentIncorporation, x:
            # ripper signalled to stop adopting this document, for good
            note(2, "AbortDocumentIncorporation exception on %s:  %s", x.id, x.message)
            if (x.id == id):
                shutil.rmtree(folderpath)
            remove_from_index(repo.index_path(), id)

        except:
            type, value, tb = sys.exc_info()
            note("Exception processing new folder:\n%s", ''.join(traceback.format_exception(type, value, tb)))
    finally:
        if tmpfilename and os.path.exists(tmpfilename):
            os.unlink(tmpfilename)
        if isinstance(counter, threading._BoundedSemaphore):
            try:
                counter.release()
            except:
                note("Exception releasing incorporation semaphore %s:\n%s", counter,
                     ''.join(traceback.format_exception(*sys.exc_info())))

def _incorporate_document(repo, incoming_queue, counter):
    # it's a bit tricky to shut this down cleanly, so we do
    # some extra checking
    import sys, Queue, traceback, threading
    while True:
        try:
            value = incoming_queue.get(True, 60)
            # value contains:  (id, tmpfilename, metadata, unpack_fn)
            id, tmpfilename, metadata, unpack_fn = value
            if isinstance(counter, threading._BoundedSemaphore):
                # blocks until below max number of threads
                counter.acquire()
            uthread.start_new_thread(flesh_out_folder,
                                     (id, tmpfilename, metadata, repo, unpack_fn, counter),
                                     name="incorporating-%s" % id)
        except Queue.Empty:
            pass
        except:
            if sys and traceback and note:
                note("%s", ''.join(traceback.format_exception(*sys.exc_info())))

def start_incorporation_thread(repo, n_simultaneous_threads):
    incoming_queue = Queue.Queue()
    name = "process_incoming_documents"
    counter = None
    if (n_simultaneous_threads > 0):
        name += "_in_at_most_%d_threads" % n_simultaneous_threads
        counter = threading.BoundedSemaphore(n_simultaneous_threads)
    uthread.start_new_thread(_incorporate_document, (repo, incoming_queue, counter), name=name)
    return incoming_queue

def retry_folder (repo, folderpath, id):
    try:
        if os.path.exists(os.path.join(folderpath, "LOCK")):
            os.unlink(os.path.join(folderpath, "LOCK"))

#         if CODETIMER_ON:
#             code_timer.Init()
#             code_timer.CreateTable("uplib")
#             code_timer.CodeTimerOn()
#         else:
#             code_timer.CodeTimerOff()

        _finish_inclusion (repo, folderpath, id)

#         if CODETIMER_ON:
#             noteOut = StringIO.StringIO()
#             noteOut.write("\nCode Timer statistics (what took time, in milliseconds):\n")
#             code_timer.PrintTable(noteOut, "uplib")
#             noteOut.write("\n")
#             noteOutString = noteOut.getvalue()
#             note(3, noteOutString)

    except AbortDocumentIncorporation, x:
        # ripper signalled to stop adopting this document, for good
        note(2, "AbortDocumentIncorporation exception on %s:  %s", x.id, x.message)
        if (x.id == id):
            shutil.rmtree(folderpath)
        remove_from_index(repo.index_path(), id)

    except:
        type, value, tb = sys.exc_info()
        note_error(folderpath, (type, value, tb))
        note("Exception re-processing new folder:\n%s", string.join(traceback.format_exception(type, value, tb)))

def retry_folders (repo):
    def _retry_folders_thread_fn (repo):
        directory = repo.pending_folder()
        pending_docs = [x for x in os.listdir(directory) if DOC_ID_RE.match(x)]
        note(3, "%d docs in 'pending' folder", len(pending_docs))
        for filename in pending_docs:
            try:
                # retry this document
                folderpath = os.path.join(directory, filename)
                if (os.path.exists(os.path.join(folderpath, "UNPACKED")) or os.path.exists(os.path.join(folderpath, "RIPPED"))):
                    note(2, "Attempting to salvage pending folder %s", filename)
                    retry_folder (repo, folderpath, filename)
                else:
                    note("Files in %s may be salvageable, but not automatically.  Please check.", folderpath)
            except:
                note("retry_folders:  %s", ''.join(traceback.format_exception(*sys.exc_info())))
    uthread.start_new_thread(_retry_folders_thread_fn, (repo,), name="retry_pending_folders")

def create (repo, queue, doc_bits, doc_type, metadata):

    note(4, "in newFolder.create")

    # make sure we have the user's current configuration
    update_configuration()

    note(4, "updated configuration data")

    tmpfilename = tempfile.mktemp()
    f = open(tmpfilename, 'wb')
    f.write(doc_bits)
    f.close()

    note(3, "wrote packed file to temporary file %s", tmpfilename)

    if metadata and metadata.has_key("id"):
        id = metadata['id']
        note(2, "document metadata specifies an ID of %s", id)
        # use existing directory (if it's there)
        folder = os.path.join(repo.pending_folder(), id)
        del metadata["id"]
        if not os.path.isdir(folder):
            note("specified document ID of %s does not exist; creating new folder for document", id)
            folder = repo.create_document_folder(repo.pending_folder())
    else:
        folder = repo.create_document_folder(repo.pending_folder())
    id = os.path.basename(folder)

    if doc_type == 'tarred-folder':
        queue.put((id, tmpfilename, metadata, process_tarred_folder))
    elif doc_type == 'zipped-folder':
        queue.put((id, tmpfilename, metadata, process_zipped_folder))
    else:
        raise Error("Can only add documents of type 'tarred-folder' or 'zipped-folder'")

    return id

