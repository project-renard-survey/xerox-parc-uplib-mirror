#!/usr/bin/env python
# -*- Mode: Python -*-
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
# This script is the "main" program for the UPLib "guardian angel",
# which watches over a repository.
#

import sys

assert sys.version_info >= (2,5,0), 'requires Python 2.5 or better'

import atexit
import os
import platform
import re
import socket
import shelve
import shutil
import string
import tempfile
import time
import traceback
import logging, logging.handlers

import tornado.httpserver
import tornado.ioloop
import tornado.web

def usage():
	sys.stderr.write("Usage:  %s DIRECTORY PORT\n" % sys.argv[0])
	sys.exit(1)

def start_angel (directory, portno, logfilename=None):

    from uplib.plibUtil import note, configurator, set_note_sink
    from uplib.tornadoHandler import ActionHandler, PingHandler, DocsHandler, LoginHandler
    from uplib.repository import Repository
    from uplib.newFolder import retry_folders

    ############################################################
    ###
    ###  create the repo and run initializers
    ###
    ############################################################

    # set up logging
    rootlogger = logging.getLogger()
    if logfilename:
        rootlogger.addHandler(logging.handlers.RotatingFileHandler(logfilename,'a', 10*1024*1024, 10*1024*1024))
    else:
        # This will log to an overhead subdirectory of the repository
        logfile_directory = os.path.join(directory, "overhead")
        if not os.path.exists(logfile_directory):
            os.makedirs(logfile_directory)
        rootlogger.addHandler(logging.handlers.RotatingFileHandler(
            os.path.join(logfile_directory, "angel.log"), 'a', 10*1024*1024, 10*1024*1024))
    # filter out logging of repo_status_json calls, which occur frequently
    class RepoStatusJsonFilter(logging.Filter):
        def filter(self, record):
            text = (record.args and str(record.msg) % record.args) or record.msg
            return ("/action/basic/repo_status_json" not in text)
    rootlogger.addFilter(RepoStatusJsonFilter())

    # make sure anything written with note() will go to the logfile
    set_note_sink(rootlogger)

    repo, use_ssl, ip_addr, conf = Repository.build_world(directory, portno, logfilename)
    note("using IP address %s, use_ssl is %s", ip_addr, use_ssl)

    ############################################################
    ###
    ###  check for pending documents, and start them
    ###
    ############################################################

    retry_folders (repo)

    ############################################################
    ###
    ###  Now create the Tornado app...
    ###
    ############################################################

    transforms = list()
    transforms.append(tornado.web.GZipContentEncoding)

    # see if we should use chunking in our server replies
    use_chunking = not conf.get_bool('no-server-chunking', False)
    if not use_chunking:
        note("disabling server HTTP 1.1 reply chunking")
    else:
        transforms.append(tornado.web.ChunkedTransferEncoding)

    handlers = list()

    # This handler handles extension requests
    handlers.append(("/action/(.*)", ActionHandler, { 'repository': repo }))
    # Redirect "/" to the top-level root
    handlers.append(("/", ActionHandler, { 'repository': repo }))

    # This handler simply replys OK to a request for /ping, to indicate that
    # the server is alive and OK, and for /login, to establish authorization
    # credentials
    handlers.append(("/ping", PingHandler, { 'repository': repo }))
    handlers.append(("/favicon.ico", PingHandler, { 'repository': repo }))
    handlers.append(("/html/signedreadup.jar", PingHandler, { 'repository': repo }))
    handlers.append(("/html/images/ReadUpJWS.gif", PingHandler, { 'repository': repo }))

    # The folder handler is the class which delivers documents from the docs
    # subdirectory requested directly, such as thumbnails.
    handlers.append(("/docs/(.*)", DocsHandler, {'repository': repo,
                                                 'allow-caching': conf.get_bool("allow-caching") }))

    # this handler serves up static HTML, jars, and images from under /html/
    handlers.append(("/html/(.*)", tornado.web.StaticFileHandler,
                     { 'path': os.path.join(repo.root(), "html") }))

    # use LoginHandler to handle login authorization
    handlers.append(("/login", LoginHandler, {'repository': repo }))

    # now set up server

    if use_ssl:
        import ssl
        ssl_options = {
            "certfile": os.path.normpath(repo.certfilename()),
            }
        root_certs_file = conf.get("root-certificates-file")
        if root_certs_file:
            if not os.path.exists(root_certs_file):
                sys.stderr.write("specified root-certificates-file %s does not exist!\n" % root_certs_file)
                sys.exit(1)
            else:
                ssl_options['ca_certs'] = root_certs_file
                ssl_options['cert_reqs'] = ssl.CERT_REQUIRED
    else:
        ssl_options = None

    try:
        http_server = tornado.httpserver.HTTPServer(
            tornado.web.Application(handlers=handlers, transforms=transforms),
            ssl_options=ssl_options,
            )
        http_server.listen(repo.port(), ip_addr)
        note("Now listening at %s://%s:%s" % (
            (ssl_options and "https") or "http", ip_addr, repo.port()))
    except:
        type, value, tb = sys.exc_info()
        s = ''.join(traceback.format_exception(type, value, tb))
        note("Can't establish HTTP server:  exception:  " + s)
        note("Abandoning attempt to start this daemon...")
        os._exit(1)

    # kill other subprocesses when exiting
    if not sys.platform.lower().startswith("win"):
        import signal
        def kill_subprocs():
            gid = os.getpgrp()
            note(0, "killing subprocesses in process group %s...", gid)
            os.killpg(-gid, signal.SIGTERM)
        atexit.register(kill_subprocs)

    # shutdown the server cleanly if things exit
    atexit.register(lambda x=http_server: x.close())

    # call the repo shutdown if the service exits
    atexit.register(lambda x=repo: x.shutdown(0))

    #
    # Catch various termination signals and save state cleanly
    #
    if not sys.platform.lower().startswith("win"):
        import signal
        signal.signal(signal.SIGTERM, lambda signum, frame: (note(0, "SIGTERM received, exiting..."), sys.exit(0)))
        signal.signal(signal.SIGUSR1, lambda signum, frame: (note(0, "SIGUSR1 received, saving..."), repo.save(true)))

    note(0, "------- Restarted at %s. ----------", time.ctime())

    # touch flag file to signal watchers...
    open(os.path.join(repo.root(), "overhead", "angel.started"), "w").write(str(time.time()))

    return repo


# This is the main startup code

def daemon (uplib_home, uplib_code_dir, repodir, portnum, logfilename=None):

    try:
        port = int(portnum)
    except ValueError:
        port = None

    if not os.path.isdir(repodir):
        sys.stderr.write("Specified directory, %s, is not a directory!\n" % repodir)
        usage()
    elif port is None:
        sys.stderr.write("Bad port number, %s, specified.\n", portnum)
        usage()

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)     # parent
    except OSError, e:
        msg = "fork #1 failed: (%d) %s\n" % (e.errno, e.strerror)
        sys.stderr.write(msg)
        sys.exit(1)

    os.chdir(os.path.join(repodir, "overhead"))
    os.umask(0)
    # now create a new session
    os.setsid()
    # and fork into the new session

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)     # session leader exits here
    except OSError, e:
        msg = "fork #2 failed: (%d) %s\n" % (e.errno, e.strerror)
        sys.stderr.write(msg)
        sys.exit(1)

    pid = str(os.getpid())

    open(os.path.join(repodir, "overhead", "angel.pid"), "w").write("%s\n" % str(os.getpid()))
    open(os.path.join(repodir, "overhead", "angel.euid"), "w").write("%s\n" % str(os.geteuid()))

    env = os.environ.copy()
    # figure out how to invoke the actual program
    # make sure we have the Python modules on sys.path
    site_insert = ""
    # if not env.has_key("UPLIB_SITEPATH"):
    #     import distutils.sysconfig as sc
    #     nonplat = os.path.normpath(sc.get_python_lib(plat_specific=False, prefix=uplib_home))
    #     platspec = os.path.normpath(sc.get_python_lib(plat_specific=True, prefix=uplib_home))
    #     if nonplat == platspec:
    #         site_packages_dirs = [nonplat]
    #     else:
    #         site_packages_dirs = [nonplat, platspec]
    #     site_insert = ""
    #     for spdir in site_packages_dirs:

    #         sys.stderr.write("site_packages_dir is %s, %s, %s\n" % (
    #             spdir, os.path.exists(spdir) and "exists" or "doesn't exist",
    #             (spdir in sys.path) and "on sys.path" or "not on sys.path"))

    #         if os.path.exists(spdir):
    #             site_insert += " sys.path.insert(0, '%s');" % spdir
    args = [sys.executable, "-c",
            "import sys;" +
            site_insert +
            " sys.path.insert(0, '%s');" % uplib_code_dir +
            " import uplib.startTornado;" +
            " uplib.startTornado.unix_mainloop('%s', %s, %s);" % (
                repodir, port, (logfilename and repr(logfilename) or "None"))
            ]
    if env.has_key("UPLIB_SITEPATH"):
        if os.path.exists(env["UPLIB_SITEPATH"]):
            # try to duplicate the processing in the "site" module
            from site import addsitedir
            paths = addsitedir(env["UPLIB_SITEPATH"], set([env["UPLIB_SITEPATH"],]))
            env["PYTHONPATH"] = ':'.join([x for x in paths])
            args.insert(1, "-S")
        else:
            raise RuntimeError("Specified UPLIB_SITEPATH '%s' not there!" % env["UPLIB_SITEPATH"])

    os.execve(sys.executable, args, env)

                               
def darwin_launchd (repodir, port):
    """
    This is designed to work with a Darwin launchd plist, keeping this daemon
    alive, owned by root.  It never really stops; if you kill it, launchd will
    restart it.  So to "stop" it, instead we first put a file in the overhead
    directory, LAUNCHD_BLOCKED, then kill the existing process.  The new process
    will see the file, and just loop without initializing till the file disappears,
    in which case it will exit, and launchd will restart it.  Complicated.
    """

    if not os.path.isdir(repodir):
        sys.stderr.write("Invalid root directory %s specified!")
        sys.exit(1)

    open(os.path.join(repodir, "overhead", "angel.pid"), "w").write("%s\n" % str(os.getpid()))
    open(os.path.join(repodir, "overhead", "angel.euid"), "w").write("%s\n" % str(os.geteuid()))

    flagfile = os.path.join(repodir, "overhead", "LAUNCHD_BLOCKED")
    if os.path.exists(flagfile):
        fp = open(os.path.join(repodir, "overhead", "angel.log"), "a")
        fp.write("*** UpLib (%s, port %s):  block file " % (repodir, port) +
                 flagfile + " exists; waiting for it to be removed\n")
        fp.close()
        while True:
            time.sleep(1)
            if not os.path.exists(flagfile):
                break
        sys.exit(0)

    # make sure angel.port is correct
    fp = open (os.path.join(repodir, "overhead", "angel.port"), "w")
    fp.write(str(port))
    fp.close()

    angelout_log_path = os.path.join(repodir, "overhead", "angelout.log")
    if not os.path.exists(angelout_log_path):
        fp = open(angelout_log_path, "w")
        fp.flush()
        fp.close()

    unix_mainloop(repodir, port, None)


def unix_mainloop(repodir, port, logfilename):

    try:
        port = int(port)
    except ValueError:
        port = None

    if not os.path.isdir(repodir):
        sys.stderr.write("Specified directory, %s, is not a directory!\n" % repodir)
        usage()
    elif port is None:
        sys.stderr.write("Bad port number, %s, specified.\n", portnum)
        usage()

    try:
        repo = start_angel(repodir, port, logfilename)
    except:
        sys.stderr.write("%s: exception initializing angel:\n%s" % (
            time.ctime(), ''.join(traceback.format_exception(*sys.exc_info()))))
        sys.exit(1)

    # Finally, start up the server loop!  This loop will not exit until
    # all clients and servers are closed.  You may cleanly shut the system
    # down by sending SIGINT (a.k.a. KeyboardInterrupt).

    from uplib.plibUtil import note
    while True:
        try:
            tornado.ioloop.IOLoop.instance().start()
        except (KeyboardInterrupt, SystemExit), x:
            note(4, "Exited from main loop due to exception:\n%s", ''.join(traceback.format_exception(*sys.exc_info())))
            raise
        except:
            note(0, "Exited from main loop due to exception:\n%s", ''.join(traceback.format_exception(*sys.exc_info())))


if __name__ == "__main__" and (not sys.platform.lower().startswith("win")):
    if (len(sys.argv) < 3) or (len(sys.argv) > 4):
        sys.stderr.write("Wrong number of arguments.\n")
        usage()
    unix_mainloop(*sys.argv[1:])

# on Windows this module is loaded from a WindowsService wrapper,
# which calls start_angel(), then runs its own event-processing loop
