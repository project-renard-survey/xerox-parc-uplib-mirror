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
# This file is run after unpacking a pre-built UpLib distribution on
# Windows (or after building UpLib from the tar file or from CVS, if
# that's what you're doing).
#
# It figures out some of the configuration parameters for the target machine,
# edits files as necessary, and puts the files in the right place.
#
# Basically, we want to filter the file '../replacements.in' to
# another file, then invoke the Python script in the top-level
# directory called 'configure-files.py' to do the actual file changes.

import sys, os, re, socket, shutil, subprocess, traceback, tarfile

UPLIB_HOME = os.path.normpath(sys.argv[1].rstrip("\\"))
UPLIB_VERSION = sys.argv[2]

SOURCE_DIR = os.path.dirname(os.path.dirname(__file__))
print "source dir is", SOURCE_DIR


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

def set_value(d, vname, vloc):
    if os.path.exists(os.path.join(*vloc)):
        d[vname] = os.path.join(*vloc)

def simple_subproc(args):
    proc = subprocess.Popen(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    for line in proc.stdout:
        print line.strip()
    status = proc.wait()
    return status

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
try:
    import guess_language
except ImportError:
    gl = False
else:
    gl = True
d['PYTHON_HAS_GUESS_LANGUAGE'] = (gl and "true") or "false"

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
# Find Python
#

# set_value(d, 'PYTHON', (UPLIB_HOME, "python", "python.exe"))
try:
    python = os.path.join(get_registry_value(r"SOFTWARE\Python\PythonCore\2.6\InstallPath", None), "pythonw.exe")
except:
    python = sys.executable
    d['PYTHON'] = os.path.join(UPLIB_HOME, "python", "pythonw.exe")
else:
    d['PYTHON'] = python
#
# We're going to need the pywin32 extensions, so install them if they're not already there
#
if os.path.exists(os.path.join(sys.exec_prefix, "python26.dll")):
    # installed privately
    todlldir = sys.exec_prefix
elif os.path.exists('c:/WINDOWS/system32/python26.dll'):
    todlldir = "C:/WINDOWS/system32"
else:
    sys.stderr.write("Can't find python26.dll\n")
    sys.exit(1)
# find them
import distutils.sysconfig
uplib_sc = distutils.sysconfig.get_python_lib(plat_specific=True, prefix=UPLIB_HOME)
fromdlldir = os.path.join(uplib_sc, "pywin32_system32")
# and install them
if not os.path.exists(os.path.join(todlldir, "pythoncom26.dll")):
    shutil.copyfile(os.path.join(fromdlldir, "pythoncom26.dll"), os.path.join(todlldir, "pythoncom26.dll"))
if not os.path.exists(os.path.join(todlldir, "pywintypes26.dll")):
    shutil.copyfile(os.path.join(fromdlldir, "pywintypes26.dll"), os.path.join(todlldir, "pywintypes26.dll"))
os.environ['PYTHONPATH'] = uplib_sc
sys.path.insert(0, os.path.join(uplib_sc, "win32"))
sys.path.insert(0, os.path.join(uplib_sc, "win32", "lib"))
sys.path.insert(0, uplib_sc)

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
# Now set up the other config parameters
#

set_value(d, 'ENSCRIPT', (UPLIB_HOME, "bin", "enscript.exe"))
set_value(d, 'NENSCRIPT', (UPLIB_HOME, "bin", "nenscript.exe"))
set_value(d, 'DIRUSE', (UPLIB_HOME, "bin", "diruse.exe"))
set_value(d, 'GHOSTSCRIPTHOME', (UPLIB_HOME,))
set_value(d, 'PDFTOTEXT', (UPLIB_HOME, "bin", "pdftotext.exe"))
set_value(d, 'WORDBOXES_PDFTOTEXT', (UPLIB_HOME, "bin", "pdftotext.exe"))
set_value(d, 'PDFLINKS', (UPLIB_HOME, "bin", "pdflinks.exe"))
set_value(d, 'PDFINFO', (UPLIB_HOME, "bin", "pdfinfo.exe"))
set_value(d, 'TIFFHOME', (UPLIB_HOME,))
set_value(d, 'JASPER', (UPLIB_HOME, "bin", "jasper.exe"))
set_value(d, 'OPENSSL', (UPLIB_HOME, "bin", "openssl.exe"))
set_value(d, 'WKHTMLTOPDF', (UPLIB_HOME, "bin", "wkhtmltopdf.exe"))
set_value(d, 'PDF2PS', (UPLIB_HOME, "bin", "pdf2ps.bat"))

if os.path.exists(os.path.normpath(os.path.join(".", "c", "findimages", "findimages.exe"))):
    d['FINDIMAGES'] = os.path.join(UPLIB_HOME, 'bin', 'findimages.exe')

if fqdn and (fqdn.endswith(".parc.com") or fqdn.endswith(".parc.xerox.com")):
    d['USE_PARC_HOSTNAME_MATCHING'] = "true"
else:
    d['USE_PARC_HOSTNAME_MATCHING'] = "false"

d['USE_OPENOFFICE_FOR_WEB'] = 'false'
d['USE_OPENOFFICE_FOR_MSOFFICE'] = 'false'
d['WEB_SERVICE_FRAMEWORK'] = 'Medusa'

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
d['UPLIB_LIB'] = os.path.join(d['UPLIB_HOME'], "lib", "UpLib-%s" % UPLIB_VERSION)
d['UPLIB_SHARE'] = os.path.join(d['UPLIB_HOME'], "share", "UpLib-%s" % UPLIB_VERSION)
d['UPLIB_CODE'] = os.path.join(d['UPLIB_SHARE'], "code")
d['UPLIB_HELP'] = os.path.join(d['UPLIB_SHARE'], "help", "html")
d['UPLIB_DOC'] = os.path.join(d['UPLIB_SHARE'], "doc")
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
if sitep and nonplat:
    sitep += os.pathsep
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

d['DIRUSE'] = os.path.join(d['UPLIB_LIB'], "diruse.exe")

##################
#
# Now transform replacements.in to replacements
#

output = open(os.path.join(SOURCE_DIR, "replacements"), "w")
for line in open(os.path.join(SOURCE_DIR, "replacements.in"), "r"):
    line = line.strip()
    if not line or (line[0] == '#'):
        continue
    parts = line.split()
    output.write(parts[0] + " " + d.get(parts[0], '') + "\n")
    #sys.stdout.write(parts[0] + " " + d.get(parts[0], '') + "\n")
output.close()

##################
#
# Filter the various files
#

print 'configuring files (UPLIB_HOME is ' + UPLIB_HOME + ')...'

args = [sys.executable,
        os.path.join(SOURCE_DIR, "configure-files.py"),
        os.path.join(SOURCE_DIR, "replacements")]
status = simple_subproc(args)
print "status from", args, "is", status
if status != 0:
    sys.exit(1)

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

status = simple_subproc([sys.executable, "win32/stopStartUpLibServices.py", "stop"])
print 'status from stopping services is', status
status = simple_subproc([sys.executable, "win32/promptClosePortal.py"])
print 'status from prompting user to close the UpLib Portal is', status

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
shutil.copy("win32/cmdprogs/uplib-topdf.bat", os.path.join(d['UPLIB_BIN'], "uplib-topdf.bat"))
shutil.copy("win32/cmdprogs/uplib-janitor.bat", os.path.join(d['UPLIB_BIN'], "uplib-janitor.bat"))
shutil.copy("win32/cmdprogs/uplib-ps2pdf.bat", os.path.join(d['UPLIB_BIN'], "uplib-ps2pdf.bat"))
shutil.copy("win32/cmdprogs/uplib-tiff-split.bat", os.path.join(d['UPLIB_BIN'], "uplib-tiff-split.bat"))
shutil.copy("win32/cmdprogs/uplib-openoffice-convert-to-pdf.bat", os.path.join(d['UPLIB_BIN'], "uplib-openoffice-convert-to-pdf.bat"))
shutil.copy("win32/cmdprogs/uplib-make-repository.bat", os.path.join(d['UPLIB_BIN'], "uplib-make-repository.bat"))
shutil.copy("win32/cmdprogs/readup.bat", os.path.join(d['UPLIB_BIN'], "readup.bat"))
shutil.copy("win32/cmdprogs/uplib-certificate.bat", os.path.join(d['UPLIB_BIN'], "uplib-certificate.bat"))
shutil.copy("win32/cmdprogs/uplib-check-windows-service-right.py", os.path.join(d['UPLIB_BIN'], "uplib-check-windows-service-right.py"))

shutil.copy("win32/removeUpLibService.py", os.path.join(d['UPLIB_BIN'], "removeUpLibService.py"))
shutil.copy("win32/restartUpLibService.py", os.path.join(d['UPLIB_BIN'], "restartUpLibService.py"))
shutil.copy("win32/removeAllUpLibGuardians.py", os.path.join(d['UPLIB_BIN'], "removeAllUpLibGuardians.py"))

for file in ("stunnel.pem", "site.config", "java/machine.config"):
    shutil.copy(file, d.get("UPLIB_LIB"))

if os.path.exists(os.path.normpath(os.path.join(".", "c", "findimages", "findimages.exe"))):
    shutil.copy(os.path.normpath(os.path.join(".", "c", "findimages", "findimages.exe")),
                os.path.join(UPLIB_HOME, 'bin', 'findimages.exe'))

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

##################
#
# install the documentation
#

for name in ("FAQ.html",
             "collections.html",
             "extensions.html",
             "info.html",
             "searching.html",
             "about.html"):
    shutil.copy(os.path.join("doc", name), d.get("UPLIB_HELP"))

docsdir = d.get("UPLIB_DOC")
for filename in os.listdir("doc"):
    if re.match(r".*\.(html|css|pdf)$", filename):
        shutil.copy(os.path.join("doc", filename), docsdir)
if os.path.exists(os.path.join("doc", "pyapidocs.tgz")):
    apidocdir = os.path.join(docsdir, "api")
    ensure_dir(apidocdir)
    tf = tarfile.open(os.path.join("doc", "pyapidocs.tgz"), "r")
    tf.extractall(apidocdir)
    tf.close()
if os.path.exists(os.path.join("doc", "javaapidocs.tgz")):
    apidocdir = os.path.join(docsdir, "java")
    ensure_dir(apidocdir)
    tf = tarfile.open(os.path.join("doc", "javaapidocs.tgz"), "r")
    tf.extractall(apidocdir)
    tf.close()
    
##################
#
# Make sure at least this user can create a Windows service
#

try:
    import win32api, win32security

    username = win32api.GetUserNameEx(win32api.NameSamCompatible)
    print 'granting "logon as a service" rights to ' + username
    policy_handle = win32security.LsaOpenPolicy(None, win32security.POLICY_ALL_ACCESS)
    sid_obj, domain, tmp = win32security.LookupAccountName(None, username)
    win32security.LsaAddAccountRights( policy_handle, sid_obj, ('SeServiceLogonRight',) )
    win32security.LsaClose( policy_handle )
except:
    print 'Exception granting user the SeServiceLogonRight:'
    print ''.join(traceback.format_exception(*sys.exc_info()))
    sys.exit(1)

##################
#
# And restart the UpLib services
#

print 'restarting all UpLib services...'

status = simple_subproc([sys.executable, "win32/stopStartUpLibServices.py", "start"])
print 'status from re-starting UpLib services is', status

print 'install done.'
