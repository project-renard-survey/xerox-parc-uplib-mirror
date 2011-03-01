#! /usr/local/bin/python
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
#  TODO:
#
#  * implement APPEND
#  * ESEARCH extension?  (do any clients use it?)
#
#  In this implementation, the IMAP protocol is implemented in
#  "abstractclasses".  The submodule "medusaHandler" contains an
#  asyncore/Medusa implementation of a server which actually receives
#  client connections and IMAP requests, and the submodule
#  "uplibBinding" contains UpLib implementations of
#  "abstractclasses.mailcontext", "abstractclasses.mailbox", and
#  "abstractclasses.message".
#

import sys, os
from uplib.plibUtil import note, configurator
UPLIB_MIN_VERSION = "1.7"

# simply installing the email package doesn't override the system-installed one
# So we need to see if it's installed, and if so, hack sys.path to make sure we
# load it.

testpath = os.path.join(sys.exec_prefix, "lib", "python" + str(sys.version_info[0]) + "." + str(sys.version_info[1]), "site-packages", "email")
if os.path.exists(testpath):
    oldpath = sys.path
    note(4, "hacking path to make sure %s is loaded...", testpath)
    sys.path.insert(0, os.path.split(testpath)[0])
    import email
    sys.path = oldpath
else:
    testpath = os.path.join(sys.prefix, "lib", "python" + str(sys.version_info[0]) + "." + str(sys.version_info[1]), "site-packages", "email")
    if os.path.exists(testpath):
        oldpath = sys.path
        note(4, "hacking path to make sure %s is loaded...", testpath)
        sys.path.insert(0, os.path.split(testpath)[0])
        import email
        sys.path = oldpath
    else:
        import email

versions = email.__version__.split(".")
note(4, "email version numbers are " + str(versions) + "\n")
if (not versions) or (int(versions[0]) < 4):
    raise ValueError("Need email package 4.x or higher for imapServer module")

for mname in ('abstractclasses', 'medusaHandler', 'uplibBinding'):
    d = locals().get(mname)
    if d:
        reload(d)
    else:
        __import__(mname, globals(), locals(), [])

def after_repository_instantiation (repo):
    conf = configurator.default_configurator()
    start_imap = conf.get_bool("imap-server-auto-start")
    note("start_imap is %s", start_imap)
    if start_imap:
        uplibBinding.manipulate_server_internal (repo, {"action": "Start"})

def manipulate_server(repo, response, params):
    ipaddr = response.request.channel.server.ip;
    logger = response.request.channel.server.logger;
    return uplibBinding.manipulate_server_internal(repo, params, response=response, ipaddr=ipaddr, lgr=logger)
        
def lookup_action(name):
    if name == "control":
        return manipulate_server
    return None
