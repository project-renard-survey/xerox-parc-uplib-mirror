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

def get_registry_value (vname, subname):
    k = wreg.OpenKey(wreg.HKEY_LOCAL_MACHINE, vname)
    v, t = wreg.QueryValueEx(k, subname)
    k.Close()
    return v

if __name__ == "__main__":
    try:
        javaversion = get_registry_value(r"SOFTWARE\JavaSoft\Java Development Kit", "CurrentVersion")
        javahome = get_registry_value(r"SOFTWARE\JavaSoft\Java Development Kit\%s" % javaversion, "JavaHome")
        if len(sys.argv) > 1:
            if sys.argv[1] == "--msys":
                if javahome[0].isalpha() and (javahome[1] == ':'):
                    javahome = "/" + javahome[0] + javahome[2:]
                javahome = javahome.replace(r"\\", "/")
        sys.stdout.write(javahome + "\n")
    except:
        raise
