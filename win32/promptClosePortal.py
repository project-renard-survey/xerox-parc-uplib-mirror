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
import sys, os, os.path, time
from Tkinter import *
import tkMessageBox

def main(argv):
    uHome = os.path.expanduser(r"~\.uplib-portal-running")

    root = None
    root = Tk()
    root.withdraw()

    while (os.path.exists(uHome)):
        tkMessageBox.showwarning("UpLib Install Warning...","To continue with the installation, please close the UpLib Portal.\n\nIf the UpLib Portal is not running, please delete the file:\n   "+uHome)
        if (os.path.exists(uHome)):
            time.sleep(15)
        
    del root

if __name__ == "__main__":
    main(sys.argv)
