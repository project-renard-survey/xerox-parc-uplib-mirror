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
import sys, os, re

POSSIBLE_LOCATIONS = ("/usr/java/", "/usr/lib", "/usr/lib/jvm")

possibilities = []

for d in POSSIBLE_LOCATIONS:

    if not os.path.isdir(d):
        # not using Sun Java
        continue

    possibilities += [os.path.join(d, x) for x in os.listdir(d) if (os.path.isdir(os.path.join(d, x)) and
                                                                    (x.startswith("jdk1.4.2") or
                                                                     x.startswith("j2sdk1.5-sun") or
                                                                     x.startswith("java-1.5.0-sun") or
                                                                     x.startswith("jdk-1.5") or
                                                                     x.startswith("jdk1.5.") or
                                                                     x.startswith("java-1.6") or
                                                                     x.startswith("java-6-sun") or
                                                                     x.startswith("java-6-openjdk") or
                                                                     x.startswith("jdk1.6") or
                                                                     x.startswith("java")
                                                                     ))
                      ]

for possibility in possibilities[:]:
    # need compiler
    if not os.path.exists(os.path.join(possibility, "bin", "javac")):
        possibilities.remove(possibility)
        continue
        
    # need jar
    if not os.path.exists(os.path.join(possibility, "bin", "jar")):
        possibilities.remove(possibility)
        continue

    # need jarsigner
    if not os.path.exists(os.path.join(possibility, "bin", "jarsigner")):
        possibilities.remove(possibility)
        continue


if len(possibilities) < 1:
    # no jdk directoriees found
    sys.stderr.write("No JDK directories found under %s.\n" % repr(POSSIBLE_LOCATIONS))
    sys.exit(1)

possibilities.sort()
# take latest one, which should sort to the end of the list
sys.stdout.write(possibilities[-1])
sys.exit(0)
