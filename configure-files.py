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

import sys, os, re, socket, pprint

def read_substitutions_file (filepath):

    substitutions = {}
    linecounter = 0
    fp = open(filepath)
    for line in fp:
        linecounter += 1
        line = line.strip()
        if (not line) or (line[0] == '#'):
            # blank or comment line
            continue
        values = re.split(r"\s+", line, 1)
        if (len(values) < 1) or not values[0].strip():
            sys.stderr.write("Bad value on line %d in file %s:  '%s'!\n" % (linecounter, filepath, line.strip()))
            sys.exit(1)
        name = values[0].strip()
        if len(values) > 1:
            value = values[1].strip()
        else:
            value = None
        if value and (value[0] != '@' or value[-1] != '@'):
            substitutions[name] = value.replace("\\", "\\\\")
        else:
            substitutions[name] = ''
    fp.close()
    return substitutions


FILES_TO_CONFIGURE = [
    "site.config",
    "Makefile",
    "python/Makefile",
    "python/uplib/plibUtil.py",
    "java/Makefile",
    "java/build-topdf-library.sh",
    "java/machine.config",
    "c/Makefile",
    "c/findimages/Makefile",
    "commandline/Makefile",
    "commandline/uplib-check-angel",
    "commandline/uplib-make-repository",
    "commandline/uplib-ps2pdf",
    "commandline/uplib-pdf2ps",
    "commandline/uplib-openoffice-convert-to-pdf",
    "commandline/uplib-openoffice-convert-to-pdf-via-server",
    "commandline/uplib-add-document",
    "commandline/uplib-get-document",
    "commandline/uplib-portal",
    "commandline/uplib-version",
    "commandline/uplib-janitor",
    "commandline/uplib-certificate",
    "commandline/readup",
    "commandline/uplib-setup-openoffice",
    "commandline/uplib-cache-url",
    "commandline/mount_uvfs",
    "commandline/mount_uvfs2",
    "commandline/uplib-topdf",
    "commandline/uplib-webkit2pdf",
    "extensions/Makefile",
    "doc/Makefile",
    "doc/info.html",
    "doc/collections.html",
    "doc/searching.html",
    "doc/extensions.html",
    "doc/FAQ.html",
    "doc/about.html",
    "doc/index.html",
    "doc/manual.txt",
    ]

if sys.platform == 'win32':
    FILES_TO_CONFIGURE += [
        "win32/Makefile",
        "win32/cmdprogs/Makefile",
        "win32/cmdprogs/uplib-check-angel.bat",
        "win32/cmdprogs/uplib-make-repository.bat",
        "win32/cmdprogs/uplib-ps2pdf.bat",
        "win32/cmdprogs/uplib-add-document.bat",
        "win32/cmdprogs/uplib-get-document.bat",
        "win32/cmdprogs/uplib-portal.bat",
        "win32/cmdprogs/uplib-topdf.bat",
        "win32/cmdprogs/uplib-janitor.bat",
        "win32/cmdprogs/uplib-certificate.bat",
        "win32/cmdprogs/readup.bat",
        "win32/cmdprogs/uplib-tiff-split.bat",
        "win32/cmdprogs/uplib-openoffice-convert-to-pdf.bat",
        "win32/cmdprogs/uplib-check-windows-service-right.py",
        "win32/createWinShortcuts.py",
        ]
else:
    FILES_TO_CONFIGURE += [
        "unix/Makefile",
        "unix/linux/Makefile",
        "unix/macosx/Makefile",
        "unix/macosx/uplib-print-pdf-to-repository",
        "unix/macosx/com.parc.uplib.ToPDFAgent.plist",
        ]

# optional files -- might be there, might not
for pathname in ["tests/Makefile",]:
    if os.path.exists(pathname + ".in"):
        FILES_TO_CONFIGURE.append(pathname)

if len(sys.argv) < 2:
    sys.stderr.write("Usage: REPLACEMENTS-FILE\n")
    sys.exit(2)

if not os.path.exists(sys.argv[1]):
    sys.stderr.write("Replacements file %s does not exist!\n" % sys.argv[1])
    sys.exit(3)

# read the substitutions
substitutions = {}
for filename in sys.argv[1:]:
    sys.stderr.write("reading %s...\n" % filename)
    newsubs = read_substitutions_file(filename)    
    substitutions.update(newsubs)

for key, value in substitutions.items():
    if not value:
	sys.stderr.write("No value for %s...\n" % key)
    substitutions[re.compile('@' + key + '@')] = value
    del substitutions[key]

# now apply them

for filename in FILES_TO_CONFIGURE:
    if not os.path.exists(filename + ".in"):
        sys.stderr.write("No such file %s!\n" % filename)
        sys.exit(5)
    else:
        sys.stderr.write("Doing %s...\n" % filename)
        infp = open(filename + ".in")
        outfp = open(filename, 'w')
        for line in infp:
            for expression, replacement in substitutions.items():
		try:
	            line = expression.sub(replacement, line, 0)
	        except:
                    sys.stderr.write("Exception processing line <%s> with expr <%s> and replacement <%s>\n" % (line.strip(), expression.pattern, replacement))
		    sys.exit(6)
            outfp.write(line)
        outfp.close()
        infp.close()
sys.stderr.write("Done.\n")
sys.exit(0)
            
