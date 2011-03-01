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
# A experiment -- can we use "python setup.py bdist_msi" to build the
# whole UpLib distribution?
#

import sys, os, re, tempfile, shutil, traceback, tempfile, zipfile, base64, codecs, atexit, StringIO, time, string
from distutils.core import Command
from distutils.dir_util import remove_tree
from distutils.sysconfig import get_python_version
from distutils.version import StrictVersion
from distutils.errors import DistutilsOptionError
from distutils.util import get_platform
from distutils import log
import msilib
import msilib.schema
import msilib.sequence
import msilib.text
from msilib import Feature, Dialog, add_data

PY_PREINSTALL_HEADER = r"""
// JScript to invoke the Python code
var pythonscript_base64 = "PYTHONCODE";
var WshShell = new ActiveXObject ("WScript.Shell");
var filesystem = new ActiveXObject("Scripting.FileSystemObject");
var installtemp = Session.Property("TempFolder");
var logfile = filesystem.CreateTextFile(installtemp + "%(PACKAGENAME)s-%(PACKAGEVERSION)s-preinstall.log");
var scriptfilepath = installtemp + "%(PACKAGENAME)s-%(PACKAGEVERSION)s-preinstall.py.b64";
var scriptfile = filesystem.CreateTextFile(scriptfilepath);
scriptfile.Write(pythonscript_base64);
scriptfile.Close();

var pythonDir = WshShell.RegRead ("HKEY_LOCAL_MACHINE\\Software\\Python\\PythonCore\\2.6\\InstallPath\\");
var pythonExe = pythonDir + "pythonw.exe";
if (! filesystem.FileExists(pythonExe)) {
  logfile.WriteLine("Python not found!");
 } else {
  logfile.WriteLine("python is " + pythonExe);
  WshShell.Environment("Process")("INSTALL_TARGETDIR") = Session.Property("TARGETDIR");
  var cmd = pythonExe + ' -c "import base64; exec(base64.decodestring(open(' + "r'" + scriptfilepath + "').read()))" + '"';
  logfile.WriteLine("cmd is " + cmd);
  var oExec = WshShell.Exec(cmd);
  while (oExec.Status == 0) {
    while (!oExec.StdOut.AtEndOfStream) {
      logfile.WriteLine(oExec.StdOut.ReadLine());
    }
    while (!oExec.StdErr.AtEndOfStream) {
      logfile.WriteLine(oExec.StdErr.ReadLine());
    }
    // WScript.Sleep(100);
  }
 }
filesystem.DeleteFile(scriptfilepath, true);
"""

PY_POSTINSTALL_HEADER = r"""
// JScript to invoke the Python code

var pythonscript_base64 = "PYTHONCODE";
var WshShell = new ActiveXObject ("WScript.Shell");
var filesystem = new ActiveXObject("Scripting.FileSystemObject");
var installtemp = Session.Property("TempFolder");

// tell user about this
var msiMessageTypeProgress = 0x0A000000;
var msiMessageTypeActionStart = 0x08000000;
var msiMessageTypeActionData = 0x09000000;

var record = Session.Installer.CreateRecord(3);
record.stringData(0) = "Post-install script";
record.stringData(1) = "Running post-install script...";
record.StringData(2) = "Running post-install script...";
Session.Message(msiMessageTypeActionStart, record);

var logfile = filesystem.CreateTextFile(installtemp + "%(PACKAGENAME)s-%(PACKAGEVERSION)s-postinstall.log");
var scriptfilepath = installtemp + "%(PACKAGENAME)s-%(PACKAGEVERSION)s-postinstall.py.b64";
var scriptfile = filesystem.CreateTextFile(scriptfilepath);
scriptfile.Write(pythonscript_base64);
scriptfile.Close();

var pythonDir = WshShell.RegRead ("HKEY_LOCAL_MACHINE\\Software\\Python\\PythonCore\\2.6\\InstallPath\\");
var pythonExe = pythonDir + "pythonw.exe";
if (! filesystem.FileExists(pythonExe)) {
  logfile.WriteLine("Python not found!");
 } else {
  logfile.WriteLine("python is " + pythonExe);
  WshShell.Environment("Process")("INSTALL_TARGETDIR") = Session.Property("TARGETDIR");
  var cmd = pythonExe + ' -c "import base64; exec(base64.decodestring(open(' + "r'" + scriptfilepath + "').read()))" + '"';
  logfile.WriteLine("cmd is " + cmd);
  var oExec = WshShell.Exec(cmd);
  while (oExec.Status == 0) {
    while (!oExec.StdOut.AtEndOfStream) {
      logfile.WriteLine(oExec.StdOut.ReadLine());
    }
    while (!oExec.StdErr.AtEndOfStream) {
      logfile.WriteLine(oExec.StdErr.ReadLine());
    }
    // WScript.Sleep(100);
  }
 }
filesystem.DeleteFile(scriptfilepath, true);
"""

PY_PRIVATE_TREE_HEADER = r"""
// JScript to copy the private tree to a temp file, and invoke Python on it
var pythonscript_base64 = "PYTHONCODE";
var WshShell = new ActiveXObject ("WScript.Shell");
var filesystem = new ActiveXObject("Scripting.FileSystemObject");
var installtemp = Session.Property("TempFolder");
var logfile = filesystem.CreateTextFile(installtemp + "%(PACKAGENAME)s-%(PACKAGEVERSION)s-%(TREENAME)s-unpack.log");
logfile.Write("logging unpack of %(TREENAME)s...");

// tell user about this
var msiMessageTypeProgress = 0x0A000000;
var msiMessageTypeActionStart = 0x08000000;
var msiMessageTypeActionData = 0x09000000;

var record = Session.Installer.CreateRecord(3);
record.stringData(0) = "Unpack private tree";
record.stringData(1) = "Unpacking %(TREENAME)s tree...";
record.StringData(2) = "Unpacking %(TREENAME)s tree...";
Session.Message(msiMessageTypeActionStart, record);

// the Python script goes in "scriptfilename"
var scriptfilename = installtemp + "%(PACKAGENAME)s-%(PACKAGEVERSION)s-%(TREENAME)s-unpack.py.b64";
var scriptfile = filesystem.CreateTextFile(scriptfilename);
scriptfile.Write(pythonscript_base64);
scriptfile.Close();

// the tree data goes in PACKAGENAME-TREENAME.zip.b64
var record = Session.Installer.CreateRecord(1);
record.stringData(0) = "writing zip file for %(TREENAME)s...";
Session.Message(msiMessageTypeActionData, record);

var zipfilename = installtemp + "%(PACKAGENAME)s-%(PACKAGEVERSION)s-%(TREENAME)s.zip.b64";
var zipfile = filesystem.createTextFile(zipfilename);
var db = Session.Database;
var view = db.OpenView("SELECT `Data` from `Binary` WHERE `Name` = 'tree-%(TREENAME)s'");
view.Execute(null);
var record = view.Fetch();
// should only be one record
zipfile.Write(record.ReadStream(1, 100000000, 1));
zipfile.Close()

var pythonDir = WshShell.RegRead ("HKEY_LOCAL_MACHINE\\Software\\Python\\PythonCore\\2.6\\InstallPath\\");
var pythonExe = pythonDir + "pythonw.exe";
if (! filesystem.FileExists(pythonExe)) {
  logfile.WriteLine("Python not found!");
 } else {
  var record = Session.Installer.CreateRecord(1);
  record.stringData(0) = "running unpack script for %(TREENAME)s...";
  Session.Message(msiMessageTypeActionData, record);
  logfile.WriteLine("python is " + pythonExe);
  // now, run the unpack script on the zip file
  WshShell.Environment("Process")("INSTALL_TARGETDIR") = Session.Property("TARGETDIR");
  WshShell.Environment("Process")("INSTALL_PACKAGENAME") = "%(PACKAGENAME)s";
  WshShell.Environment("Process")("INSTALL_PACKAGEVERSION") = "%(PACKAGEVERSION)s";
  WshShell.Environment("Process")("TREE_ZIPFILE") = zipfilename;
  WshShell.Environment("Process")("TREE_NAME") = "%(TREENAME)s";
  cmd = pythonExe + ' -c "import base64; exec(base64.decodestring(open(' + "r'" + scriptfilename + "'" + ').read()))"';
  logfile.WriteLine("cmd is " + cmd);
  var oExec = WshShell.Exec(cmd);
  while (oExec.Status == 0) {
    while (!oExec.StdOut.AtEndOfStream) {
      logfile.WriteLine(oExec.StdOut.ReadLine());
    }
    while (!oExec.StdErr.AtEndOfStream) {
      logfile.WriteLine(oExec.StdErr.ReadLine());
    }
    // WScript.Sleep(100);
  }
 }
filesystem.DeleteFile(zipfilename, true);
filesystem.DeleteFile(scriptfilename, true);
"""

def reraise_exception(x):
    raise x

class PyDialog(Dialog):
    """Dialog class with a fixed layout: controls at the top, then a ruler,
    then a list of buttons: back, next, cancel. Optionally a bitmap at the
    left."""
    def __init__(self, *args, **kw):
        """Dialog(database, name, x, y, w, h, attributes, title, first,
        default, cancel, bitmap=False)"""
        Dialog.__init__(self, *args)
        ruler = self.h - 36
        bmwidth = 152*ruler/328
        self.has_bitmap = kw.get("bitmap", False)
        if self.has_bitmap:
            self.bitmap("Bitmap", 0, 0, bmwidth, ruler, "InstallerBitmap")
        self.line("BottomLine", 0, ruler, self.w, 0)

    def title(self, title):
        "Set the title text of the dialog at the top."
        # name, x, y, w, h, flags=Visible|Enabled|Transparent|NoPrefix,
        # text, in VerdanaBold10
        if self.has_bitmap:
            self.text("Title", 135, 10, 220, 60, 0x30003,
                      r"{\VerdanaBold10}%s" % title)
        else:
            self.text("Title", 15, 10, 320, 60, 0x30003,
                      r"{\VerdanaBold10}%s" % title)

    def back(self, title, next, name = "Back", active = 1):
        """Add a back button with a given title, the tab-next button,
        its name in the Control table, possibly initially disabled.

        Return the button, so that events can be associated"""
        if active:
            flags = 3 # Visible|Enabled
        else:
            flags = 1 # Visible
        return self.pushbutton(name, 180, self.h-27 , 56, 17, flags, title, next)

    def cancel(self, title, next, name = "Cancel", active = 1):
        """Add a cancel button with a given title, the tab-next button,
        its name in the Control table, possibly initially disabled.

        Return the button, so that events can be associated"""
        if active:
            flags = 3 # Visible|Enabled
        else:
            flags = 1 # Visible
        return self.pushbutton(name, 304, self.h-27, 56, 17, flags, title, next)

    def next(self, title, next, name = "Next", active = 1):
        """Add a Next button with a given title, the tab-next button,
        its name in the Control table, possibly initially disabled.

        Return the button, so that events can be associated"""
        if active:
            flags = 3 # Visible|Enabled
        else:
            flags = 1 # Visible
        return self.pushbutton(name, 236, self.h-27, 56, 17, flags, title, next)

    def xbutton(self, name, title, next, xpos):
        """Add a button with a given title, the tab-next button,
        its name in the Control table, giving its x position; the
        y-position is aligned with the other buttons.

        Return the button, so that events can be associated"""
        return self.pushbutton(name, int(self.w*xpos - 28), self.h-27, 56, 17, 3, title, next)

class Tree (object):
    """A tree is a tree of files to install."""
    def __init__(self, name, root, excludes=None):
        self.name = name
        self.root = root
        self.excludes = excludes

class PublicTree(Tree):
    """A tree which will form part of the files unpacked by the installer and made
    available on the target machine."""
    def __init__(self, name, root, excludes=None, destdir=None):
        Tree.__init__(self, name, root, excludes)
        self.destdir=destdir

class PrivateTree(Tree):
    """A tree which will be unpacked by the installer in a temporary directory.  It may
    optionally include a post-unpack script, which may be JScript or VBScript."""
    def __init__(self, name, root, excludes=None, unpack_script=None):
        Tree.__init__(self, name, root, excludes)
        self.unpack_script = unpack_script

def _showmedia(db):
    def _showrecord(r):
        return [r.GetString(i) for i in range(1, r.GetFieldCount()+1)]
    v = db.OpenView("SELECT * FROM `Media`")
    v.Execute(None)
    print _showrecord(v.GetColumnInfo(msilib.MSICOLINFO_NAMES))
    v.Close()

class _Directory (msilib.Directory):
    """We subclass Directory so that we can clean up the instance, and release
    the storage it's holding on to.  Otherwise, there may be too many files
    to package without errors.
    """

    def __del__(self):
        self.db.Commit()
        self.db = None
        self.keyfiles = None
        self.cab = None
        self.ids = None

class _CAB (msilib.CAB):
    """We subclass CAB to add a class variable "diskId", so that multiple
    CAB instances can be added to a single installer.
    """

    diskId = 1

    def commit(self, db):
        filename = tempfile.mktemp()
        msilib.FCICreate(filename, self.files)
        print filename, os.path.getsize(filename)
        sys.stderr.write(str((self.diskId, self.index, None, "#"+self.name, None, None)) + "\n")
        msilib.add_data(db, "Media",
                        [(self.diskId, self.index, None, "#"+self.name, None, None)])
        msilib.add_stream(db, self.name, filename)
        self.diskId += 1
        db.Commit()
        os.unlink(filename)

class Packager (object):

    def __init__ (self, package_name, package_version,
                  author=None, email=None, url=None,
                  trees=None, pre_install=None, post_install=None,
                  keep_temp=False, package_file=None, package_uuid=None,
                  default_install_location=None, install_location_hint=None,
                  directory_combo = None,
                  bitmap=None):

        if trees and not isinstance(trees, (list, tuple, set)):
            raise ValueError("trees much be specified as a list")
        if pre_install and not os.path.exists(pre_install):
            raise ValueError("Specified pre_install script %s does not exist!" % pre_install)
        if post_install and not os.path.exists(post_install):
            raise ValueError("Specified post_install script %s does not exist!" % post_install)
        self.author = author
        self.email = email
        self.url = url
        self.package_name = package_name
        self.package_version = package_version
        self.trees = []
        self.pre_install = pre_install
        self.post_install = post_install
        self.keep_temp = keep_temp
        if not package_file:
            package_file = os.path.join(os.getcwd(), "%s-%s.msi" % (package_name, package_version))
        self.package_file = os.path.abspath(package_file)
        self.uuid = package_uuid
        if trees:
            for tree in trees:
                if not os.path.isdir(tree.root):
                    if not os.path.exists(tree.root):
                        raise ValueError("Specified tree root, %s, does not exist!" % tree.root)
                    else:
                        raise ValueError("Specified tree root, %s, is not a directory!" % tree.root)
                self.add_tree(tree)
        self.install_location = default_install_location or ""
        self.install_location_hint = install_location_hint
        if bitmap:
            if not os.path.exists(bitmap):
                raise ValueError("Specified bitmap file %s doesn't exist!" % bitmap)
            elif not bitmap.lower().endswith(".bmp"):
                raise ValueError("Specified bitmap must be a BMP file.")
        self.bitmap = bitmap
        self.show_directory_combo = directory_combo

    def add_tree (self, tree):
        if tree.name in [x.name for x in self.trees]:
            raise ValueError("duplicate tree name %s; all trees in a package must have different names" % repr(tree.name))
        self.trees.append(tree)

    def run (self):

        self.initialize_db()
        self.add_files()
        self.add_scripts()
        self.add_ui()
        self.db.Commit()

    def initialize_db(self):
        dirpath, filepath = os.path.split(self.package_file)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        if os.path.exists(self.package_file):
            os.unlink(self.package_file)
        print self.package_file

        if not self.author:
            author = "UNKNOWN"
        else:
            author = (isinstance(self.author, (list, tuple, set)) and " and ".join([x for x in self.author])) or str(self.author)

        product_name = "%s %s" % (self.package_name, self.package_version)

        self.db = msilib.init_database(self.package_file, msilib.schema,
                                       product_name, self.uuid or msilib.gen_uuid(),
                                       self.package_version, author)
        msilib.add_tables(self.db, msilib.sequence)
        props = [('DistVersion', self.package_version)]
        if self.email:
            props.append(("ARPCONTACT", self.email))
        if self.url:
            props.append(("ARPURLINFOABOUT", self.url))
        print 'install_location', self.install_location
        props.append(("TARGETDIR", self.install_location.replace('/', '\\')))
        if props:
            add_data(self.db, 'Property', props)

        # for some reason, we need to add our own error icon, so do that
        add_data(self.db, "Binary", [
            ("dlgerror.ico", msilib.Binary("./dialog-error.ico")),     # 22x22
            ])
        if self.bitmap:
            add_data(self.db, "Binary", [
                ("InstallerBitmap", msilib.Binary(self.bitmap)),     # 22x22
                ])            
        self.db.Commit()

    def add_files(self):
        f = Feature(self.db, "default", "Default Feature", "Everything", 1, directory="TARGETDIR")
        f.set_current()
        # each tree is represented by a CAB
        for tree in self.trees:
            if isinstance(tree, PublicTree):
                cab = _CAB(tree.name)
                rootdir = os.path.abspath(tree.root)
                root = _Directory(self.db, cab, None, rootdir, "TARGETDIR", "SourceDir")
                self.db.Commit()
                todo = [root]
                while todo:
                    dir = todo.pop()
                    #sys.stderr.write("processing %s\n" % dir.physical)
                    for file in os.listdir(dir.absolute):
                        if tree.excludes and tree.excludes.match(file):
                            continue
                        afile = os.path.join(dir.absolute, file)
                        if os.path.isdir(afile):
                            newdir = _Directory(self.db, cab, dir, file, file, "%s|%s" % (dir.make_short(file), file))
                            todo.append(newdir)
                        else:
                            try:
                                key = dir.add_file(file)
                                #sys.stderr.write('added %s\n' % file)
                            except AssertionError:
                                print "Exception adding", file
                                print ''.join(traceback.format_exception(*sys.exc_info()))
                                print "dir.short_names is", dir.short_names
                #_showmedia(self.db)
                cab.commit(self.db)
            elif isinstance(tree, PrivateTree):
                # private trees are represented as a zip file contained as a binary blob
                files = []
                todo = [(os.path.abspath(tree.root), "")]
                while todo:
                    dir, rdir = todo.pop()
                    for file in os.listdir(dir):
                        if tree.excludes and tree.excludes.match(file):
                            print 'excluding', (rdir and os.path.join(rdir, file)) or file
                            continue
                        afile = os.path.join(dir, file)
                        rfile = (rdir and os.path.join(rdir, file)) or file
                        if os.path.isdir(afile):
                            todo.append((afile, rfile))
                        else:
                            files.append((afile, rfile))
                tfile = tempfile.mktemp()
                zfile = None
                try:
                    # we base64 the zip file for better use with Scripting.FileSystemObject
                    buffer = StringIO.StringIO()
                    zfile = zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED)
                    for afile, rfile in files:
                        zfile.write(afile, rfile)
                    zfile.close()
                    zfile = None
                    data = buffer.getvalue()
                    print tree.name + ' zipfile', len(data)
                    data = base64.encodestring(data)
                    tfileobj = open(tfile, "w")
                    tfileobj.write(data + '\n')
                    tfileobj.close()
                    # tfileobj = open(tfile, "r")
                    # for line in tfileobj:
                    #     print line.strip()
                    # tfileobj.close()
                    print tfile, os.path.getsize(tfile)
                    add_data(self.db, "Binary", [
                        ("tree-" + tree.name, msilib.Binary(tfile)),
                        ])
                finally:
                    if zfile and isinstance(zfile, zipfile.ZipFile):
                        zfile.close()
                    if os.path.exists(tfile):
                        try:
                            os.unlink(tfile)
                        except:
                            pass
                # handle unpack script
                if tree.unpack_script:
                    script_key = "tree-%s-unpack" % tree.name
                    action_script = tree.unpack_script
                    if tree.unpack_script.lower().endswith(".exe"):
                        action_type = 2
                    if tree.unpack_script.lower().endswith(".js"):
                        action_type = 5
                    elif tree.unpack_script.lower().endswith(".vbs"):
                        action_type = 6
                    elif tree.unpack_script.lower().endswith(".py"):
                        action_script, action_type = self._wrap_unpack_script(tree)
                    else:
                        raise ValueError("Can't handle unpack script of unknown type:  %s" % tree.unpack_script)
                    add_data(self.db, "Binary",
                        [(script_key, msilib.Binary(action_script)),
                        ])
                    # fp = open(action_script, "rb")
                    # data = fp.read()
                    # fp.close()
                    # print '------------------- unpack script for tree "%s" ----------------------' % tree.name
                    # print data
                    # print '----------------------------------------------------------------------'
                    if action_script != tree.unpack_script:
                        atexit.register(lambda x=action_script: os.path.exists(x) and os.unlink(x))
                    add_data(self.db, "CustomAction",
                            [(script_key, action_type, script_key, None)])
                    add_data(self.db, "InstallExecuteSequence",
                            [(script_key, "NOT Installed", 6799)])
            else:
                raise ValueError("Can't process tree <%s: %s> -- unknown subtype of Tree" % (tree.__class__.__name__, tree.name))

    def add_scripts(self):
        # now add any pre- or post- install scripts
        if self.pre_install:
            action_script = self.pre_install
            if self.pre_install.lower().endswith(".js"):
                action_type = 5
            elif self.pre_install.lower().endswith(".vbs"):
                action_type = 6
            elif self.pre_install.lower().endswith(".exe"):
                action_type = 2
            elif self.pre_install.lower().endswith(".py"):
                action_script, action_type = self._wrap_install_script(self.pre_install, PY_PREINSTALL_HEADER)
            else:
                raise ValueError("Can't use pre-install scripts of this type:  %s", self.pre_install)
            add_data(self.db, "Binary",
                [("PreInstall", msilib.Binary(action_script)),
                ])
            if action_script != self.pre_install:
                atexit.register(lambda x=action_script: os.path.exists(x) and os.unlink(x))
            # fp = open(action_script, "rb")
            # data = fp.read()
            # fp.close()
            # print '------------------- pre-install script ----------------------'
            # print data
            # print '--------------------------------------------------------------'
            add_data(self.db, "CustomAction",
                [("PreInstall", action_type, "PreInstall", None)
                ])
            add_data(self.db, "InstallExecuteSequence",
                    [("PreInstall", "NOT Installed", 450)])

        if self.post_install:
            action_script = self.post_install
            if self.post_install.lower().endswith(".js"):
                action_type = 5
            elif self.post_install.lower().endswith(".vbs"):
                action_type = 6
            elif self.post_install.lower().endswith(".exe"):
                action_type = 2
            elif self.post_install.lower().endswith(".py"):
                action_script, action_type = self._wrap_install_script(self.post_install, PY_POSTINSTALL_HEADER)
            else:
                raise ValueError("Can't use post-install scripts of this type:  %s", self.post_install)
            add_data(self.db, "Binary",
                [("PostInstall", msilib.Binary(action_script)),
                ])
            if action_script != self.post_install:
                atexit.register(lambda x=action_script: os.path.exists(x) and os.unlink(x))
            # fp = open(action_script, "rb")
            # data = fp.read()
            # fp.close()
            # print '------------------- post-install script ----------------------'
            # print data
            # print '--------------------------------------------------------------'
            add_data(self.db, "CustomAction",
                    [("PostInstall", action_type, "PostInstall", None)])
            add_data(self.db, "InstallExecuteSequence",
                    [("PostInstall", "NOT Installed", 6800)])


    def _wrap_unpack_script (self, tree):
        # wrap a Python unpack script
        fp = open(tree.unpack_script, 'rb')
        data = fp.read()
        fp.close()
        tfile = tempfile.mktemp() + ".js"
        outfile = open(tfile, "w")
        header = PY_PRIVATE_TREE_HEADER.replace("PYTHONCODE", '\\n\\\n'.join(base64.encodestring(data).split('\n')))
        outfile.write(header % { 'TREENAME': tree.name, 'PACKAGENAME': self.package_name, 'PACKAGEVERSION': self.package_version })
        outfile.close()
        return tfile, 5

    def _wrap_install_script (self, script_file, header):
        # wrap a Python unpack script
        fp = open(script_file, 'rb')
        data = fp.read()
        fp.close()
        tfile = tempfile.mktemp() + ".js"
        outfile = open(tfile, "w")
        header = header.replace("PYTHONCODE", '\\n\\\n'.join(base64.encodestring(data).split('\n')))
        outfile.write(header % { 'PACKAGENAME': self.package_name, 'PACKAGEVERSION': self.package_version })
        outfile.close()
        return tfile, 5

    def add_ui(self):
        db = self.db
        x = y = 50
        w = 370
        h = 300
        title = "[ProductName] Setup"

        # see "Dialog Style Bits"
        modal = 3      # visible | modal
        modeless = 1   # visible
        track_disk_space = 32

        # UI customization properties
        add_data(db, "Property",
                 # See "DefaultUIFont Property"
                 [("DefaultUIFont", "DlgFont8"),
                  # See "ErrorDialog Style Bit"
                  ("ErrorDialog", "ErrorDlg"),
                  ("Progress1", "Install"),   # modified in maintenance type dlg
                  ("Progress2", "installs"),
                  ("MaintenanceForm_Action", "Repair"),
                  # possible values: ALL, JUSTME
                  ("WhichUsers", "ALL")
                 ])

        # Fonts, see "TextStyle Table"
        add_data(db, "TextStyle",
                 [("DlgFont8", "Tahoma", 9, None, 0),
                  ("DlgFontBold8", "Tahoma", 8, None, 1), #bold
                  ("VerdanaBold10", "Verdana", 10, None, 1),
                  ("VerdanaRed9", "Verdana", 9, 255, 0),
                 ])

        # UI Sequences, see "InstallUISequence Table", "Using a Sequence Table"
        # Numbers indicate sequence; see sequence.py for how these action integrate
        add_data(db, "InstallUISequence",
                 [("PrepareDlg", "Not Privileged or Windows9x or Installed", 140),
                  # can only install for all users for the moment
                  #("WhichUsersDlg", "Privileged and not Windows9x and not Installed", 141),
                  # In the user interface, assume all-users installation if privileged.
                  ("SelectDirectoryDlg", "Not Installed", 1230),
                  # XXX no support for resume installations yet
                  #("ResumeDlg", "Installed AND (RESUME OR Preselected)", 1240),
                  ("MaintenanceTypeDlg", "Installed AND NOT RESUME AND NOT Preselected", 1250),
                  ("ProgressDlg", None, 1280)])

        add_data(db, 'ActionText', msilib.text.ActionText)
        add_data(db, 'UIText', msilib.text.UIText)
        #####################################################################
        # Standard dialogs: FatalError, UserExit, ExitDialog
        fatal=PyDialog(db, "FatalError", x, y, w, h, modal, title,
                     "Finish", "Finish", "Finish", bitmap=self.bitmap)
        fatal.title("[ProductName] Installer ended prematurely")
        fatal.back("< Back", "Finish", active = 0)
        fatal.cancel("Cancel", "Back", active = 0)
        fatal.text("Description1", self.bitmap and 135 or 15, 70,
                   self.bitmap and 220 or 320, 80, 0x30003,
                   "[ProductName] setup ended prematurely because of an error.  "
                   "Your system has not been modified.  To install this program at a "
                   "later time, please run the installation again.")
        fatal.text("Description2", self.bitmap and 135 or 15, 155,
                   self.bitmap and 220 or 320, 20, 0x30003,
                   "Click the Finish button to exit the Installer.")
        c=fatal.next("Finish", "Cancel", name="Finish")
        c.event("EndDialog", "Exit")

        user_exit=PyDialog(db, "UserExit", x, y, w, h, modal, title,
                     "Finish", "Finish", "Finish", bitmap=self.bitmap)
        user_exit.title("[ProductName] Installer was interrupted")
        user_exit.back("< Back", "Finish", active = 0)
        user_exit.cancel("Cancel", "Back", active = 0)
        user_exit.text("Description1", self.bitmap and 135 or 15, 70,
                       self.bitmap and 220 or 320, 80, 0x30003,
                   "[ProductName] setup was interrupted.  Your system has not been modified.  "
                   "To install this program at a later time, please run the installation again.")
        user_exit.text("Description2", self.bitmap and 135 or 15, 155,
                       self.bitmap and 220 or 320, 20, 0x30003,
                   "Click the Finish button to exit the Installer.")
        c = user_exit.next("Finish", "Cancel", name="Finish")
        c.event("EndDialog", "Exit")

        exit_dialog = PyDialog(db, "ExitDialog", x, y, w, h, modal, title,
                             "Finish", "Finish", "Finish", bitmap=self.bitmap)
        exit_dialog.title("Completing the [ProductName] Installer")
        exit_dialog.back("< Back", "Finish", active = 0)
        exit_dialog.cancel("Cancel", "Back", active = 0)
        exit_dialog.text("Description", self.bitmap and 135 or 15, 235,
                         self.bitmap and 220 or 320, 20, 0x30003,
                   "Click the Finish button to exit the Installer.")
        c = exit_dialog.next("Finish", "Cancel", name="Finish")
        c.event("EndDialog", "Return")

        #####################################################################
        # Required dialog: FilesInUse, ErrorDlg
        inuse = PyDialog(db, "FilesInUse",
                         x, y, w, h,
                         19,                # KeepModeless|Modal|Visible
                         title,
                         "Retry", "Retry", "Retry", bitmap=self.bitmap)
        inuse.text("Title", 15, 6, 200, 15, 0x30003,
                   r"{\DlgFontBold8}Files in Use")
        inuse.text("Description", 20, 23, 280, 20, 0x30003,
               "Some files that need to be updated are currently in use.")
        inuse.text("Text", 20, 55, 330, 50, 3,
                   "The following applications are using files that need to be updated by this setup. Close these applications and then click Retry to continue the installation or Cancel to exit it.")
        inuse.control("List", "ListBox", 20, 107, 330, 130, 7, "FileInUseProcess",
                      None, None, None)
        c=inuse.back("Exit", "Ignore", name="Exit")
        c.event("EndDialog", "Exit")
        c=inuse.next("Ignore", "Retry", name="Ignore")
        c.event("EndDialog", "Ignore")
        c=inuse.cancel("Retry", "Exit", name="Retry")
        c.event("EndDialog","Retry")

        # See "Error Dialog". See "ICE20" for the required names of the controls.
        error = Dialog(db, "ErrorDlg",
                       50, 10, 330, 101,
                       65543,       # Error|Minimize|Modal|Visible
                       title,
                       "ErrorText", None, None)
        error.text("ErrorText", 50,9,280,48,3, "")
        error.control("ErrorIcon", "Icon", 16, 10, 22, 22, 5242881, None, "dlgerror.ico", None, None)
        error.pushbutton("N",120,72,81,21,3,"No",None).event("EndDialog","ErrorNo")
        error.pushbutton("Y",240,72,81,21,3,"Yes",None).event("EndDialog","ErrorYes")
        error.pushbutton("A",0,72,81,21,3,"Abort",None).event("EndDialog","ErrorAbort")
        error.pushbutton("C",42,72,81,21,3,"Cancel",None).event("EndDialog","ErrorCancel")
        error.pushbutton("I",81,72,81,21,3,"Ignore",None).event("EndDialog","ErrorIgnore")
        error.pushbutton("O",159,72,81,21,3,"Ok",None).event("EndDialog","ErrorOk")
        error.pushbutton("R",198,72,81,21,3,"Retry",None).event("EndDialog","ErrorRetry")

        #####################################################################
        # Global "Query Cancel" dialog
        cancel = Dialog(db, "CancelDlg", 50, 10, 260, 85, 3, title,
                        "No", "No", "No")
        cancel.text("Text", 48, 15, 194, 30, 3,
                    "Are you sure you want to cancel [ProductName] installation?")
        #cancel.control("Icon", "Icon", 15, 15, 24, 24, 5242881, None,
        #               "py.ico", None, None)
        c=cancel.pushbutton("Yes", 72, 57, 56, 17, 3, "Yes", "No")
        c.event("EndDialog", "Exit")

        c=cancel.pushbutton("No", 132, 57, 56, 17, 3, "No", "Yes")
        c.event("EndDialog", "Return")

        #####################################################################
        # Global "Wait for costing" dialog
        costing = Dialog(db, "WaitForCostingDlg", 50, 10, 260, 85, modal, title,
                         "Return", "Return", "Return")
        costing.text("Text", 48, 15, 194, 30, 3,
                     "Please wait while the installer finishes determining your disk space requirements.")
        c = costing.pushbutton("Return", 102, 57, 56, 17, 3, "Return", None)
        c.event("EndDialog", "Exit")

        #####################################################################
        # Preparation dialog: no user input except cancellation
        prep = PyDialog(db, "PrepareDlg", x, y, w, h, modeless, title,
                        "Cancel", "Cancel", "Cancel", bitmap=self.bitmap)
        prep.text("Description", 15, 70, 320, 40, 0x30003,
                  "Please wait while the Installer prepares to guide you through the installation.")
        prep.title("Welcome to the [ProductName] Installer")
        c=prep.text("ActionText", 15, 110, 320, 20, 0x30003, "Pondering...")
        c.mapping("ActionText", "Text")
        c=prep.text("ActionData", 15, 135, 320, 30, 0x30003, None)
        c.mapping("ActionData", "Text")
        prep.back("Back", None, active=0)
        prep.next("Next", None, active=0)
        c=prep.cancel("Cancel", None)
        c.event("SpawnDialog", "CancelDlg")

        #####################################################################
        # Target directory selection
        seldlg = PyDialog(db, "SelectDirectoryDlg", x, y, w, h, modal, title,
                        "Next", "Next", "Cancel", bitmap=self.bitmap)
        seldlg.title("Select Destination Directory")

        if self.install_location_hint:
            seldlg.text("Hint", 15, 30, 300, 40, 3, self.install_location_hint)

        seldlg.back("< Back", None, active=0)
        c = seldlg.next("Next >", "Cancel")
        c.event("SetTargetPath", "TARGETDIR", ordering=1)
        c.event("SpawnWaitDialog", "WaitForCostingDlg", ordering=2)
        c.event("EndDialog", "Return", ordering=3)

        c = seldlg.cancel("Cancel", (self.show_directory_combo and "DirectoryCombo") or "PathEdit")
        c.event("SpawnDialog", "CancelDlg")

        if self.show_directory_combo:
            seldlg.control("DirectoryCombo", "DirectoryCombo", self.bitmap and 135 or 15, 70,
                           self.bitmap and 172 or 272, 80, 393219,
                           "TARGETDIR", None, "DirectoryList", None)
            seldlg.control("DirectoryList", "DirectoryList", self.bitmap and 135 or 15, 90,
                           self.bitmap and 208 or 308, 136, 3, "TARGETDIR",
                           None, "PathEdit", None)
        seldlg.control("PathEdit", "PathEdit", self.bitmap and 135 or 15, 230,
                       self.bitmap and 206 or 306, 16, 3, "TARGETDIR", None, "Next", None)
        c = seldlg.pushbutton("Up", 306, 70, 18, 18, 3, "Up", None)
        c.event("DirectoryListUp", "0")
        c = seldlg.pushbutton("NewDir", 324, 70, 30, 18, 3, "New", None)
        c.event("DirectoryListNew", "0")

        #####################################################################
        # Disk cost
        cost = PyDialog(db, "DiskCostDlg", x, y, w, h, modal, title,
                        "OK", "OK", "OK", bitmap=self.bitmap)
        cost.text("Title", 15, 6, 200, 15, 0x30003,
                  "{\DlgFontBold8}Disk Space Requirements")
        cost.text("Description", 20, 20, 280, 20, 0x30003,
                  "The disk space required for the installation of the selected features.")
        cost.text("Text", 20, 53, 330, 60, 3,
                  "The highlighted volumes (if any) do not have enough disk space "
                  "available for the currently selected features.  You can either "
                  "remove some files from the highlighted volumes, or choose to "
                  "install less features onto local drive(s), or select different "
                  "destination drive(s).")
        cost.control("VolumeList", "VolumeCostList", 20, 100, 330, 150, 393223,
                     None, "{120}{70}{70}{70}{70}", None, None)
        cost.xbutton("OK", "Ok", None, 0.5).event("EndDialog", "Return")

        #####################################################################
        # WhichUsers Dialog. Only available on NT, and for privileged users.
        # This must be run before FindRelatedProducts, because that will
        # take into account whether the previous installation was per-user
        # or per-machine. We currently don't support going back to this
        # dialog after "Next" was selected; to support this, we would need to
        # find how to reset the ALLUSERS property, and how to re-run
        # FindRelatedProducts.
        # On Windows9x, the ALLUSERS property is ignored on the command line
        # and in the Property table, but installer fails according to the documentation
        # if a dialog attempts to set ALLUSERS.
        whichusers = PyDialog(db, "WhichUsersDlg", x, y, w, h, modal, title,
                              "AdminInstall", "Next", "Cancel", bitmap=self.bitmap)
        whichusers.title("Select whether to install [ProductName] for all users of this computer.")
        # A radio group with two options: allusers, justme
        g = whichusers.radiogroup("AdminInstall", 15, 60, 260, 50, 3,
                                  "WhichUsers", "", "Next")
        g.add("ALL", 0, 5, 150, 20, "Install for all users")
        g.add("JUSTME", 0, 25, 150, 20, "Install just for me")

        whichusers.back("Back", None, active=0)

        c = whichusers.next("Next >", "Cancel")
        c.event("[ALLUSERS]", "1", 'WhichUsers="ALL"', 1)
        c.event("EndDialog", "Return", ordering = 2)

        c = whichusers.cancel("Cancel", "AdminInstall")
        c.event("SpawnDialog", "CancelDlg")

        #####################################################################
        # Installation Progress dialog (modeless)
        progress = PyDialog(db, "ProgressDlg", x, y, w, h, modeless, title,
                            "Cancel", "Cancel", "Cancel", bitmap=self.bitmap)
        progress.text("Title", self.bitmap and 135 or 20, 15, self.bitmap and 100 or 200, 15, 0x30003,
                      "{\DlgFontBold8}[Progress1] [ProductName]")
        progress.text("Text", self.bitmap and 135 or 35, 65, self.bitmap and 200 or 300, 30, 3,
                      "Please wait while the Installer [Progress2] [ProductName]. "
                      "This may take several minutes.")
        progress.text("StatusLabel", self.bitmap and 135 or 35, 100, 35, 20, 3, "Status:")

        c=progress.text("ActionText", self.bitmap and 170 or 70, 100, w-70, 20, 3, "Pondering...")
        c.mapping("ActionText", "Text")

        #c=progress.text("ActionData", 35, 140, 300, 20, 3, None)
        #c.mapping("ActionData", "Text")

        c=progress.control("ProgressBar", "ProgressBar", self.bitmap and 135 or 35, 120,
                           self.bitmap and 200 or 300, 10, 65537,
                           None, "Progress done", None, None)
        c.mapping("SetProgress", "Progress")

        progress.back("< Back", "Next", active=False)
        progress.next("Next >", "Cancel", active=False)
        progress.cancel("Cancel", "Back").event("SpawnDialog", "CancelDlg")

        ###################################################################
        # Maintenance type: repair/uninstall
        maint = PyDialog(db, "MaintenanceTypeDlg", x, y, w, h, modal, title,
                         "Next", "Next", "Cancel", bitmap=self.bitmap)
        maint.title("Welcome to the [ProductName] Setup Wizard")
        maint.text("BodyText", self.bitmap and 135 or 15, 63,
                   self.bitmap and 230 or 320, 42, 3,
                   "Select whether you want to repair or remove [ProductName].")
        g=maint.radiogroup("RepairRadioGroup", self.bitmap and 135 or 15, 108,
                           self.bitmap and 220 or 330, 60, 3,
                            "MaintenanceForm_Action", "", "Next")
        #g.add("Change", 0, 0, 200, 17, "&Change [ProductName]")
        g.add("Repair", 0, 18, 200, 17, "&Repair [ProductName]")
        g.add("Remove", 0, 36, 200, 17, "Re&move [ProductName]")

        maint.back("< Back", None, active=False)
        c=maint.next("Finish", "Cancel")
        # Change installation: Change progress dialog to "Change", then ask
        # for feature selection
        #c.event("[Progress1]", "Change", 'MaintenanceForm_Action="Change"', 1)
        #c.event("[Progress2]", "changes", 'MaintenanceForm_Action="Change"', 2)

        # Reinstall: Change progress dialog to "Repair", then invoke reinstall
        # Also set list of reinstalled features to "ALL"
        c.event("[REINSTALL]", "ALL", 'MaintenanceForm_Action="Repair"', 5)
        c.event("[Progress1]", "Repairing", 'MaintenanceForm_Action="Repair"', 6)
        c.event("[Progress2]", "repairs", 'MaintenanceForm_Action="Repair"', 7)
        c.event("Reinstall", "ALL", 'MaintenanceForm_Action="Repair"', 8)

        # Uninstall: Change progress to "Remove", then invoke uninstall
        # Also set list of removed features to "ALL"
        c.event("[REMOVE]", "ALL", 'MaintenanceForm_Action="Remove"', 11)
        c.event("[Progress1]", "Removing", 'MaintenanceForm_Action="Remove"', 12)
        c.event("[Progress2]", "removes", 'MaintenanceForm_Action="Remove"', 13)
        c.event("Remove", "ALL", 'MaintenanceForm_Action="Remove"', 14)

        # Close dialog when maintenance action scheduled
        c.event("EndDialog", "Return", 'MaintenanceForm_Action<>"Change"', 20)
        #c.event("NewDialog", "SelectFeaturesDlg", 'MaintenanceForm_Action="Change"', 21)

        maint.cancel("Cancel", "RepairRadioGroup").event("SpawnDialog", "CancelDlg")


UPLIB_PREINSTALL_SCRIPT = r"""
// JScript to invoke the Python code
var WshShell = new ActiveXObject ("WScript.Shell");
var filesystem = new ActiveXObject("Scripting.FileSystemObject");
var installtemp = Session.Property("TempFolder");
var logfile = filesystem.CreateTextFile(installtemp + "UpLib-1.7.9-preinstall.log");

var pythonInstalled = true;
var pythonDir = null;
var pythonExe = null;
try {
    pythonDir = WshShell.RegRead ("HKEY_LOCAL_MACHINE\\Software\\Python\\PythonCore\\2.6\\InstallPath\\");
    pythonExe = pythonDir + "pythonw.exe";
} catch (x) {
    pythonInstalled = false;
};
if (! (pythonInstalled && filesystem.FileExists(pythonExe))) {
  logfile.WriteLine("Python not found!");
  var rec = Installer.CreateRecord(1);
  rec.StringData(1) = "Python 2.6 must be installed on your system before running the UpLib installer.";
  var v = Session.Message(0x01000010, rec);
  logfile.WriteLine("User message returned " + v);
  throw new Error(0, "Python not installed!");
}

var javaInstalled = true;
var javaHome = null;
try {
    javaHome = WshShell.RegRead ("HKEY_LOCAL_MACHINE\\Software\\JavaSoft\\Java Runtime Environment\\1.6\\JavaHome");
} catch (x) {
  javaInstalled = false;
};
if (! (javaInstalled && filesystem.FolderExists(javaHome))) {
  logfile.WriteLine("Java not found!");
  var rec = Installer.CreateRecord(1);
  rec.StringData(1) = "Java 6 must be installed on your system before running the UpLib installer.";
  var v = Session.Message(0x01000010, rec);
  logfile.WriteLine("User message returned " + v);
  throw new Error(0, "Java not installed!");
};
"""

def better_make_id(str):
    #str = str.replace(".", "_") # colons are allowed
    str = str.replace(" ", "_")
    str = str.replace("-", "_")
    str = str.replace("+", "_")
    str = str.replace("$", "_")
    if str[0] in string.digits:
        str = "_"+str
    assert re.match("^[A-Za-z_][A-Za-z0-9_.]*$", str), "BETTER"+str
    return str

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stderr.write("Usage:  %s TARGET-DIR UPLIB-DIR [MSI-FILENAME]\n" % sys.argv[0])
        sys.exit(1)

    msilib.make_id = better_make_id

    prereqexcludes = re.compile(r"CVS$|\.cvsignore$|\.svn$|.*~$|\._.*$")
    uplibexcludes = re.compile(r"CVS$|\.cvsignore$|\.cvspass$|\.settings$|scripts$|debian$|"
                               r"FOSS$|fuse-old$|\.svn$|.*~$|\._.*$|.*\.class$|.*\.pyc$|.*\.dvi$|"
                               r"tests$|unix$|misc$|fuse$|email$|clib$|prefuse$|htmldoc.*\.tgz$|"
                               r".*\.msi$")

    target_dir = sys.argv[1]
    uplib_dir = sys.argv[2]
    uplib_version = None
    for line in open(os.path.join(uplib_dir, "site.config")):
        if re.search("UPLIB_VERSION", line):
            uplib_version = line.strip().split("=")[1].strip()
            break
    if not uplib_version and os.path.exists(os.path.join(uplib_dir, "VERSION")):
        fp = open(os.path.join(uplib_dir, "VERSION"))
        uplib_version = fp.read().strip()
        fp.close()
    if not uplib_version:
        sys.stderr.write("Can't figure UpLib version.  Please configure source directory.\n")
        sys.exit(1)

    if len(sys.argv) > 3:
        install_filename = sys.argv[3]
    else:
        install_filename = "uplib-" + uplib_version + ".msi"

    pre_install_script_path = tempfile.mktemp() + ".js"
    fp = open(pre_install_script_path, "w")
    fp.write(UPLIB_PREINSTALL_SCRIPT)
    fp.close()
    post_install_script_path = os.path.join(uplib_dir, "win32", "post-install.py")
    uplib_unpack_script_path = os.path.join(uplib_dir, "win32", "unpack-uplib.py")

    prereqs = PublicTree("prereqs", target_dir, excludes=prereqexcludes)
    uplibfiles = PrivateTree("UpLib", uplib_dir, excludes=uplibexcludes,
                             unpack_script=uplib_unpack_script_path)

    sys.stderr.write("creating packager...\n")
    p = Packager("UpLib", uplib_version,
                 author=["Bill Janssen", "Lance Good", "Christiaan Royer", "Ashok Popat"],
                 email="uplib-feedback@parc.com",
                 url="http://uplib.parc.com",
                 trees=[prereqs, uplibfiles],
                 default_install_location=target_dir,
                 pre_install=pre_install_script_path,
                 post_install=post_install_script_path,
                 package_file=os.path.abspath(install_filename),
                 bitmap="installer-label.bmp",
                 directory_combo=True,
                 )
    start = time.time()
    sys.stderr.write("building %s...\n" % install_filename)
    p.run()
    end = time.time()
    sys.stderr.write("%s seconds.\n" % (end - start))
