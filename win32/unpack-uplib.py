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
import sys, os, re, zipfile, base64, codecs, StringIO, tempfile

def rmtree(top):
    # Delete everything reachable from the directory named in 'top',
    # assuming there are no symbolic links.
    # CAUTION:  This is dangerous!  For example, if top == '/', it
    # could delete all your disk files.
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

# UpLib tree is stored in a base64-ed zipfile

print os.environ
installdir = os.environ.get("INSTALL_TARGETDIR")
uplib_version = os.environ.get("INSTALL_PACKAGEVERSION")
# create a temp directory to install from
tdir = tempfile.mktemp()
os.makedirs(tdir)
zipfilepath = os.environ.get("TREE_ZIPFILE")
sys.stdout.write("zipfilepath is %s\n" % zipfilepath)
if not os.path.exists(zipfilepath):
    sys.stderr.write("Specified tree zipfile %s doesn't exist!" % zipfilepath)
    sys.exit(1)
fp = open(zipfilepath, "r")
data = fp.read()
fp.close()
tfile = tempfile.mktemp()
sys.stdout.write("zipfile is %s\n" % tfile)
fp = open(tfile, "wb")
fp.write(base64.decodestring(data).strip())
fp.flush()
fp.close()
zf = zipfile.ZipFile(tfile, 'r')
for name in zf.namelist():
    fname = os.path.join(tdir, name)
    d = os.path.dirname(fname)
    if not os.path.exists(d):
        os.makedirs(d)
    fp = open(fname, 'wb')
    fp.write(zf.read(name))
    fp.close()
    sys.stdout.write(name + "\n")
zf.close()
os.unlink(tfile)

# Now, we have uplib unpacked.  Run "install-script.py" to install files.
os.chdir(tdir)

sys.stdout.write("running install-script.py...\n")
sys.stdout.flush()
status = os.spawnv(os.P_WAIT, sys.executable, (
    sys.executable, os.path.join(tdir, "win32", "install-script.py"), installdir, uplib_version))
if status != 0:
    sys.stdout.write("Error running install script:  %s\n" % status)
    sys.exit(1)

# Create the shortcuts
sys.stdout.write("creating UpLib shortcuts...\n")
sys.stdout.flush()
status = os.spawnv(os.P_WAIT, sys.executable, (
    sys.executable, os.path.join(tdir, "win32", "createWinShortcuts.py"), installdir))
if status != 0:
    sys.stdout.write("Error creating shortcuts:  %s\n" % status)
    sys.exit(1)

sys.stdout.write("removing temp UpLib directory %s...\n" % tdir)
if os.path.exists(tdir):
    rmtree(tdir)


