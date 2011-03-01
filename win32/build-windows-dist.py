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

import sys, os, re, tempfile, tarfile, shutil, time

import _winreg as wreg

class WindowsRegistry:

    # see the Python Cookbook, #146305, Dirk Holtwick

    def __init__(self, keyname):
        """
        handle registry access
        """
        self.reg = wreg.ConnectRegistry(None, wreg.HKEY_LOCAL_MACHINE)
        self.key = wreg.OpenKey(self.reg, keyname)

    def get(self, name):
        " get value out of registry "
        v, t = wreg.QueryValueEx(self.key, name)
        return v, t

    def close(self):
        " close the key finally "
        self.key.Close()
        self.reg.Close()

    def __del__(self):
        self.close()


def get_registry_value (vname, subname):
    r = WindowsRegistry(vname)
    v, t = r.get(subname)
    return v

def usage():
    sys.stderr.write("Usage:  python build-windows-dist.py UPLIB-TARFILE WINDOWS-PREREQS\n")
    sys.exit(1)

def main():

    if len(sys.argv) < 3:
        usage()

    tfile = sys.argv[1]
    winprereqs = sys.argv[2]
    dirpath = tempfile.mktemp()

    starting_dir = os.getcwd()

    os.makedirs(dirpath)

    if not os.path.exists(tfile) or (not os.path.isdir(winprereqs)):
        usage()

    # unpack the tar file
    sys.stderr.write('unpacking %s in %s...\n' % (tfile, dirpath))
    tf = tarfile.open(tfile, 'r')
    toppath = None
    for entry in tf:
        tf.extract(entry, dirpath)
        if not toppath:
            toppath = entry.name.split('/')[0]

    # copy the prereqs
    for file in os.listdir(winprereqs):
        if file == toppath:
            sys.stderr.write('skipping copy of file "%s"; same name as top level of UpLib distro\n' % toppath)
            continue
        filepath = os.path.join(winprereqs, file)
	sys.stderr.write('copying prereq %s...\n' % filepath)
        if os.path.isdir(filepath):
            shutil.copytree(filepath, os.path.join(dirpath, file))
        else:
            shutil.copy(filepath, dirpath)

    uplibpath = os.path.join(dirpath, toppath)

    # copy the icon for the installer
    shutil.copy(os.path.join(uplibpath, "images", "UpLibMultiIcon1.ico"), dirpath)
    # copy the installer script
    shutil.copy(os.path.join(uplibpath, "win32", "uplib-installer.nsi"), dirpath)

    # get the jar files
    javadir = os.path.join(starting_dir, "..", "java")
    for file in os.listdir(javadir):
	if file == "machine.config" or file.endswith(".jar"):
	    shutil.copy(os.path.join(javadir, file), os.path.join(uplibpath, "java"))

    sys.stderr.write('unpacked\n')
    sys.stderr.flush()

    # cd to the location
    os.chdir(dirpath)

    # find NSIS
    nsis_home = get_registry_value(r"SOFTWARE\NSIS", "")
    makensis = os.path.join(nsis_home, "makensis.exe")
    nsis_script = os.path.join(dirpath, "uplib-installer.nsi")

    # create the installer
    #
    uplibversion = open(os.path.join(uplibpath, "VERSION"), 'r').readline().strip()
    cmd = ('"' + makensis + '"', "/V4",
           "/DUPLIB_VERSION=" + uplibversion,
	   "/DUPLIB_FOLDER=" + '"' + toppath + '"',
           "/DOUTDIR=" + '"' + starting_dir + '"',
           '"' + nsis_script + '"')
    print cmd
    os.spawnv(os.P_WAIT, makensis, cmd)

    def unprotect_and_unlink(f, p, e):
        os.chmod(p, 0777)
        return f(p)

    # back up out of dirpath
    os.chdir(starting_dir)
    shutil.rmtree(dirpath, False, onerror=unprotect_and_unlink)

if __name__ == "__main__":
    main()
