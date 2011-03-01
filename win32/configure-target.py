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
# This file contains a script which attempts to configure the Windows
# install before the installer puts it in place.
#
# Basically, we want to filter the file '../replacements.in' to
# another file, then invoke the Python script in the top-level
# directory called 'configure-files.py' to do the actual file changes.
#
# This should be invoked with the top-level directory for UpLib
# as the first argument, and the UpLib version as the second argument.
#

import sys, os, re, socket, shutil

UPLIB_HOME = sys.argv[1]
UPLIB_VERSION = sys.argv[2]

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
    try:
        r = WindowsRegistry(vname)
        v, t = r.get(subname)
        return v
    except:
        return None

##################
#
# Does this machine have a fully-qualified domain name?
#

import socket
fqdn = socket.getfqdn()
if fqdn: fqdn = fqdn.strip()

##################
#
# Set up the replacements dictionary
#

d = {}

d['HOSTNAME'] = socket.getfqdn()
d['OS_TARGET'] = sys.platform

##################
#
# Figure out the default language
#

import locale, re
l = locale.getdefaultlocale()[0]
if l:
   l = re.search('^[A-Za-z]+', l).group()
else:
   l = 'en'
d['DEFAULT_LANGUAGE'] = l

##################
#
# Find Java
#
version = get_registry_value(r"SOFTWARE\JavaSoft\Java Runtime Environment", "CurrentVersion")
d['JAVAHOME'] = get_registry_value(r"SOFTWARE\JavaSoft\Java Runtime Environment\%s" % version, "JavaHome")
version_parts = re.split(r'[\.\_]', version)
d['JAVA_MAJOR_VERSION'] = version_parts[0]
d['JAVA_MINOR_VERSION'] = version_parts[1]
d['JAVA_MICRO_VERSION'] = get_registry_value(r"SOFTWARE\JavaSoft\Java Runtime Environment\%s" % version, "MicroVersion")
d['JAR'] = ''                   # no jar in JRE
d['JAVA'] = os.path.join(d['JAVAHOME'], "bin", "java.exe")
d['JAVAC'] = ''                 # no JAVAC in JRE
d['JAVACLASSPATHSEP'] = ';'     # standard on Windows
d['JAVADEBUGFLAGS'] = ''        # no debugging on target
d['JAVA_COMPAT_FLAG'] = ''	# only for compiling
d['JAVA_HAS_COOKIE_HANDLING'] =	((int(d['JAVA_MAJOR_VERSION']) > 1) or (int(d['JAVA_MINOR_VERSION']) > 4)) and "yes" or "no"
d['JAVA_HOTSPOT_FLAGS'] = (version.startswith("1.6.0_") and len(version_parts) > 3 and (int(version_parts[3]) > 3) and "-Xint") or ""
keytool = os.path.join(d['JAVAHOME'], "bin", "keytool.exe")
if os.path.exists(keytool):
    d['KEYTOOL'] = keytool

##################
#
# Find OpenOffice
#
pfiles = os.listdir(os.path.join("C:", r"\\", "Program Files"))
pfiles.reverse()	# get the higher version first
for f in pfiles:
    if f.startswith("OpenOffice.org "):
        soffice = os.path.join(r"C:", r"\\", "Program Files", f, "program", "soffice.exe")
        unopkg = os.path.join(r"C:", r"\\", "Program Files", f, "program", "unopkg.exe")
        if os.path.exists(soffice) and os.path.exists(unopkg):
            d['OPENOFFICE'] = soffice
            d['UNOPKG'] = unopkg
	    break

##################
#
# Now look for programs
#

def set_value(d, vname, vloc):
    if os.path.exists(os.path.join(*vloc)):
        d[vname] = os.path.join(*vloc)

set_value(d, 'ENSCRIPT', (UPLIB_HOME, "bin", "enscript.exe"))
set_value(d, 'DIRUSE', (PROGRAM_FILES, "Resource Kit", "diruse.exe"))
set_value(d, 'GHOSTSCRIPTHOME', (UPLIB_HOME, "bin"))
set_value(d, 'PDFTOTEXT', (UPLIB_HOME, "bin", "pdftotext.exe"))
set_value(d, 'WORDBOXES_PDFTOTEXT', (UPLIB_HOME, "bin", "pdftotext.exe"))
set_value(d, 'PDFLINKS', (UPLIB_HOME, "bin", "pdflinks.exe"))
set_value(d, 'PDFINFO', (UPLIB_HOME, "bin", "pdfinfo.exe"))
# set_value(d, 'PYTHON', (UPLIB_HOME, "python", "python.exe"))
set_value(d, 'TIFFHOME', (UPLIB_HOME, "bin"))

d['USE_OPENOFFICE_FOR_WEB'] = 'false'
d['USE_OPENOFFICE_FOR_MSOFFICE'] = 'false'

d['INTERACTION_CHARSET'] = "latin_1"
d['DNS_NAMESERVER'] = ""
d['SCORETEXT'] = ""
d['SCORETEXTMODEL'] = ""
d['TAR'] = ""

d['GHOSTSCRIPT'] = os.path.join(d['GHOSTSCRIPTHOME'], "bin", "gswin32c.exe")
d['PS2PDF'] = os.path.join(d['GHOSTSCRIPTHOME'], "lib", "ps2pdf.bat")

d['TIFF2PS'] = os.path.join(d['TIFFHOME'], "bin", "tiff2ps.exe")
d['TIFFCP'] = os.path.join(d['TIFFHOME'], "bin", "tiffcp.exe")
d['TIFFINFO'] = os.path.join(d['TIFFHOME'], "bin", "tiffinfo.exe")
d['TIFFSET'] = os.path.join(d['TIFFHOME'], "bin", "tiffset.exe")
d['TIFFSPLIT'] = os.path.join(d['TIFFHOME'], "bin", "tiffsplit.exe")

d['UPLIB_HOME'] = UPLIB_HOME
d['UPLIB_EXEC'] = d['UPLIB_HOME']
d['UPLIB_BIN'] = os.path.join(d['UPLIB_HOME'], "bin")
d['UPLIB_LIB'] = os.path.join(d['UPLIB_HOME'], "lib")
d['UPLIB_SHARE'] = os.path.join(d['UPLIB_HOME'], "share")
d['UPLIB_CODE'] = os.path.join(d['UPLIB_HOME'], "share", "code")
d['UPLIB_HELP'] = os.path.join(d['UPLIB_HOME'], "share", "help", "html")
d['UPLIB_DOC'] = os.path.join(d['UPLIB_HOME'], "share", "doc")
d['UPLIB_VERSION'] = UPLIB_VERSION
d['PACKAGE_VERSION'] = UPLIB_VERSION
d['EXTENSIONSDIR'] = os.path.join(d['UPLIB_LIB'], "site-extensions")
d['IMAGESDIR'] = os.path.join(d['UPLIB_SHARE'], "images")

import distutils.sysconfig as sc
platlib = sc.get_python_lib(plat_specific=True, prefix=UPLIB_HOME)
if not os.path.isdir(platlib):
    platlib = ""
nonplat = sc.get_python_lib(plat_specific=False, prefix=UPLIB_HOME)
if not os.path.isdir(nonplat):
    nonplat = ""
sitep = platlib
if sitep: sitep += os.pathsep
sitep += nonplat
d['UPLIB_SITE_PACKAGES_PLAT'] = platlib
d['UPLIB_SITE_PACKAGES_NONPLAT'] = nonplat
d['UPLIB_SITE_PACKAGES'] = sitep

d['USE_PYLUCENE'] = 'jcc'
d['USE_STUNNEL'] = 'false'

d['UPLIB_GET_PROGRAM'] = os.path.join(d['UPLIB_HOME'], "bin", "uplib-get-document")
d['UPLIB_ADD_PROGRAM'] = os.path.join(d['UPLIB_HOME'], "bin", "uplib-add-document")
d['UPLIB_CHECK_ANGEL_PROGRAM'] = os.path.join(d['UPLIB_HOME'], "bin", "uplib-check-angel")

d['NAUTILUS'] = ""
d['KONQUEROR'] = ""

d['BOURNE_SHELL'] = ""

d['DIRUSE'] = os.path.join(d['UPLIB_BIN'], "diruse.exe")
d['GRANT'] = os.path.join(d['UPLIB_BIN'], "grant.exe")

PYTHON = d.get("PYTHON")

##################
#
# Now transform replacements.in to replacements
#

output = open("replacements", "w")
for line in open("replacements.in", "r"):
    line = line.strip()
    if not line or (line[0] == '#'):
        continue
    parts = line.split()
    output.write(parts[0] + " " + d.get(parts[0], '') + "\n")
output.close()

##################
#
# Filter the various files
#

print 'configuring files (UPLIB_HOME is ' + UPLIB_HOME + ')...'

os.spawnv(os.P_WAIT, PYTHON, (PYTHON, "configure-files.py", "replacements"))

##################
#
# Make sure the install directories exist
#

def ensure_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)

ensure_dir(d.get("UPLIB_HOME"))
ensure_dir(d.get("UPLIB_SHARE"))
ensure_dir(d.get("UPLIB_DOC"))
ensure_dir(d.get("UPLIB_CODE"))
ensure_dir(d.get("UPLIB_HELP"))
ensure_dir(d.get("UPLIB_LIB"))
ensure_dir(d.get("UPLIB_BIN"))
ensure_dir(d.get("EXTENSIONSDIR"))
ensure_dir(d.get("IMAGESDIR"))

##################
#
# Stop the UpLib services, if any
#

print 'stopping all UpLib services...'

os.spawnv(os.P_WAIT, PYTHON, (PYTHON, "win32/stopStartUpLibServices.py", "stop"))
os.spawnv(os.P_WAIT, PYTHON, (PYTHON, "win32/promptClosePortal.py"))

##################
#
# And put everything in its place
#

print 'copying files...'

shutil.copy("win32/windows-service-template", d.get("UPLIB_SHARE"))

shutil.copy("win32/diruse.exe", os.path.join(d['UPLIB_LIB'], "diruse.exe"))

shutil.copy("commandline/uplib-make-repository", os.path.join(d['UPLIB_BIN'], "uplib-make-repository.py"))
shutil.copy("commandline/uplib-add-document", os.path.join(d['UPLIB_BIN'], "uplib-add-document.py"))
shutil.copy("commandline/uplib-get-document", os.path.join(d['UPLIB_BIN'], "uplib-get-document.py"))
shutil.copy("commandline/uplib-check-angel", os.path.join(d['UPLIB_BIN'], "uplib-check-angel.py"))
shutil.copy("commandline/uplib-ps2pdf", os.path.join(d['UPLIB_BIN'], "uplib-ps2pdf.py"))
shutil.copy("commandline/uplib-certificate", os.path.join(d['UPLIB_BIN'], "uplib-certificate.py"))
shutil.copy("win32/cmdprogs/uplib-add-document.bat", os.path.join(d['UPLIB_BIN'], "uplib-add-document.bat"))
shutil.copy("win32/cmdprogs/uplib-get-document.bat", os.path.join(d['UPLIB_BIN'], "uplib-get-document.bat"))
shutil.copy("win32/cmdprogs/uplib-check-angel.bat", os.path.join(d['UPLIB_BIN'], "uplib-check-angel.bat"))
shutil.copy("win32/cmdprogs/uplib-portal.bat", os.path.join(d['UPLIB_BIN'], "uplib-portal.bat"))
shutil.copy("win32/cmdprogs/uplib-janitor.bat", os.path.join(d['UPLIB_BIN'], "uplib-janitor.bat"))
shutil.copy("win32/cmdprogs/uplib-ps2pdf.bat", os.path.join(d['UPLIB_BIN'], "uplib-ps2pdf.bat"))
shutil.copy("win32/cmdprogs/uplib-tiff-split.bat", os.path.join(d['UPLIB_BIN'], "uplib-tiff-split.bat"))
shutil.copy("win32/cmdprogs/uplib-openoffice-convert-to-pdf.bat", os.path.join(d['UPLIB_BIN'], "uplib-openoffice-convert-to-pdf.bat"))
shutil.copy("win32/cmdprogs/uplib-make-repository.bat", os.path.join(d['UPLIB_BIN'], "uplib-make-repository.bat"))
shutil.copy("win32/cmdprogs/readup.bat", os.path.join(d['UPLIB_BIN'], "readup.bat"))
shutil.copy("win32/cmdprogs/uplib-certificate.bat", os.path.join(d['UPLIB_BIN'], "uplib-certificate.bat"))

shutil.copy("win32/removeUpLibService.py", os.path.join(d['UPLIB_BIN'], "removeUpLibService.py"))
shutil.copy("win32/restartUpLibService.py", os.path.join(d['UPLIB_BIN'], "restartUpLibService.py"))
shutil.copy("win32/removeAllUpLibGuardians.py", os.path.join(d['UPLIB_BIN'], "removeAllUpLibGuardians.py"))

for file in ("stunnel.pem", "site.config", "java/machine.config"):
    shutil.copy(file, d.get("UPLIB_LIB"))

UPLIB_CODE = d.get("UPLIB_CODE")
for filename in os.listdir(UPLIB_CODE):
    if filename.endswith(".pyc") or filename.endswith(".js"):
        os.unlink(os.path.join(UPLIB_CODE, filename))
for filename in os.listdir("java"):
    if filename.endswith(".jar") or (filename == "machine.config"):
        shutil.copy(os.path.join("java", filename), UPLIB_CODE)
for filename in os.listdir(os.path.join("python", "uplib")):
    uplib_pkg_dir = os.path.join(UPLIB_CODE, "uplib")
    ensure_dir(uplib_pkg_dir)
    if filename.endswith(".py"):
        shutil.copy(os.path.join("python", "uplib", filename), uplib_pkg_dir)

for filename in os.listdir("."):
    if filename.endswith(".js"):
        shutil.copy(filename, UPLIB_CODE)

shutil.rmtree(d.get("IMAGESDIR"))
shutil.copytree("images", d.get("IMAGESDIR"))

shutil.rmtree(d.get("EXTENSIONSDIR"))
shutil.copytree("extensions", d.get("EXTENSIONSDIR"))

for name in ("FAQ.html",
             "collections.html",
             "extensions.html",
             "info.html",
             "searching.html",
             "about.html"):
    shutil.copy(os.path.join("doc", name), d.get("UPLIB_HELP"))

for filename in os.listdir("doc"):
    if re.match(r".*\.(html|css|pdf)$", filename):
        shutil.copy(os.path.join("doc", filename), d.get("UPLIB_DOC"))
    
##################
#
# And restart the UpLib services
#

print 'restarting all UpLib services...'

os.spawnv(os.P_WAIT, PYTHON, (PYTHON, "win32/stopStartUpLibServices.py", "start"))

print 'install done.'
