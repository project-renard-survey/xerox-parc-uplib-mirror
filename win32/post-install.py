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
# post-install script to run after the MSI installer has unpacked the files
#

import sys, os, re, distutils.sysconfig, shutil

targetdir = os.environ.get("INSTALL_TARGETDIR")

def copydll(source, dest):
    if os.path.exists(dest):
        os.unlink(dest)
    shutil.copyfile(source, dest)

# make sure the win32 DLLs are there
dlldir = os.path.join(distutils.sysconfig.get_python_lib(plat_specific=True, prefix=targetdir), "pywin32_system32")
try:
    copydll(os.path.join(dlldir, "pythoncom26.dll"), "C:\WINDOWS\system32\pythoncom26.dll")
    copydll(os.path.join(dlldir, "pywintypes26.dll"), "C:\WINDOWS\system32\pywintypes26.dll")
except:
    traceback.print_exc(None, sys.stderr)
    sys.exit(1)
