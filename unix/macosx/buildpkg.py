#!/usr/bin/env python

"""buildpkg.py -- Build OS X packages for Apple's Installer.app.

This is an experimental command-line tool for building packages to be
installed with the Mac OS X Installer.app application. 

Please read the file http://python.net/~gherman/projects/buildpkg/ReadMe.txt
for more information!

Dinu C. Gherman, 
gherman@europemail.com
September 2002

!! USE AT YOUR OWN RISK !!
"""

__version__ = 0.3
__license__ = "FreeBSD"


import os, sys, glob, fnmatch, shutil, string, copy, getopt
from os.path import basename, dirname, join, islink, isdir, isfile

Error = "buildpkg.Error"

PKG_INFO_FIELDS = """\
DefaultLocation
Diskname
DeleteWarning
NeedsAuthorization
DisableStop
UseUserMask
Application
Relocatable
Required
InstallOnly
RequiresReboot
BackgroundAlignment
BackgroundScaling
InstallFat\
"""

PKG_INFO_FLAGS = """\
DefaultLocation
Diskname
DeleteWarning
AuthorizationAction
DisableStop
UseUserMask
Application
Relocatable
Required
InstallOnly
RequiresReboot
BackgroundAlignment
BackgroundScaling
InstallFat\
"""

DESCRIPTION_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>IFPkgDescriptionDeleteWarning</key>
	<string>%(DeleteWarning)s</string>
	<key>IFPkgDescriptionDescription</key>
	<string>%(Description)s</string>
	<key>IFPkgDescriptionTitle</key>
	<string>%(Title)s</string>
	<key>IFPkgDescriptionVersion</key>
	<string>%(Version)s</string>
</dict>
</plist>
"""

SCRIPT_NAMES = {
    "postinstall": "post_install",
    "preinstall": "pre_install",
    "postflight": "post_flight",
    "preflight": "pre_flight",
    "preupgrade": "pre_upgrade",
    "postupgrade": "post_upgrade",
    }


######################################################################
# Helpers
######################################################################

# Convenience class, as suggested by /F.

class GlobDirectoryWalker:
    "A forward iterator that traverses files in a directory tree."

    def __init__(self, directory, pattern="*"):
        self.stack = [directory]
        self.pattern = pattern
        self.files = []
        self.index = 0


    def __getitem__(self, index):
        while 1:
            try:
                file = self.files[self.index]
                self.index = self.index + 1
            except IndexError:
                # pop next directory from stack
                self.directory = self.stack.pop()
                self.files = os.listdir(self.directory)
                self.index = 0
            else:
                # got a filename
                fullname = join(self.directory, file)
                if isdir(fullname) and not islink(fullname):
                    self.stack.append(fullname)
                if fnmatch.fnmatch(file, self.pattern):
                    return fullname


######################################################################
# The real thing
######################################################################

class PackageMaker:
    """A class to generate packages for Mac OS X.

    This is intended to create OS X packages (with extension .pkg)
    containing archives of arbitrary files that the Installer.app 
    (Apple's OS X installer) will be able to handle.

    As of now, PackageMaker instances need to be created with the 
    title, version and description of the package to be built. 
    
    The package is built after calling the instance method 
    build(root, resources, **options). The generated package is 
    a folder hierarchy with the top-level folder name equal to the 
    constructor's title argument plus a '.pkg' extension. This final
    package is stored in the current folder.
    
    The sources from the root folder will be stored in the package
    as a compressed archive, while all files and folders from the
    resources folder will be added to the package as they are.

    Example:
    
    With /my/space being the current directory, the following will
    create /my/space/distutils-1.0.2.pkg/:

      PM = PackageMaker
      pm = PM("distutils-1.0.2", "1.0.2", "Python distutils.")
      pm.build("/my/space/sources/distutils-1.0.2")
      
    After a package is built you can still add further individual
    resource files or folders to its Contents/Resources subfolder
    by using the addResource(path) method: 

      pm.addResource("/my/space/metainfo/distutils/")
    """

    packageInfoDefaults = {
        'Title': None,
        'Version': None,
        'Description': '',
        'DefaultLocation': '/',
        'Diskname': '(null)',
        'DeleteWarning': '',
        'NeedsAuthorization': 'NO',
        'DisableStop': 'NO',
        'UseUserMask': 'YES',
        'Application': 'NO',
        'Relocatable': 'YES',
        'Required': 'NO',
        'InstallOnly': 'NO',
        'OutputDir': '.',
        'RequiresReboot': 'NO',
        'BundleIdentifier': '',
        'BackgroundAlignment': 'left',
        'BackgroundScaling': 'tofit',
        'Packages': None,
        'InstallFat': 'NO'}


    def __init__(self, title, version, desc):
        "Init. with mandatory title/version/description arguments."

        info = {"Title": title, "Version": version, "Description": desc}
        self.packageInfo = copy.deepcopy(self.packageInfoDefaults)
        self.packageInfo.update(info)
        
        # variables set later
        self.packageRootFolder = None
        self.packageContentsFolder = None
        self.packageResourceFolder = None
        self.sourceFolder = None
        self.resourceFolder = None

        versions = string.split(version, ".")
        self.packageInfo['MajorVersion'] = int(versions[0])
        if len(versions) > 1:
            self.packageInfo['MinorVersion'] = int(versions[1])
        else:
            self.packageInfo['MinorVersion'] = 0


    def _escapeBlanks(self, s):
        "Return a string with escaped blanks."
        
        return s.replace(' ', '\ ')
                

    def build(self, root, resources=None, **options):
        """Create a package for some given root folder.

        With no 'resources' argument set it is assumed to be the same 
        as the root directory. Option items replace the default ones 
        in the package info.
        """

        # set folder attributes
        if options.get('Packages') and not resources:
            resources = root
            root = None

        self.sourceFolder = root
        self.resourceFolder = resources

        # replace default option settings with user ones if provided
        fields = self.packageInfoDefaults.keys()
        for k, v in options.items():
            if k in fields:
                self.packageInfo[k] = v
            elif not k in ["OutputDir"]:
                raise Error, "Unknown package option: %s" % k
        
        if self.packageInfo.has_key("NeedsAuthorization") and self.packageInfo["NeedsAuthorization"].lower() == "yes":
            self.packageInfo["AuthorizationAction"] = "RootAuthorization"

        # Check where we should leave the output. Default is current directory
        outputdir = options.get("OutputDir", os.getcwd())
        packageName = self.packageInfo["Title"]
        packageVersion = self.packageInfo["Version"]
        extension = (options.get('Packages') and ".mpkg") or ".pkg"
        self.packageRootFolder = os.path.join(outputdir, packageName + "-" + packageVersion + extension)
        # self.packageRootFolder = os.path.join(outputdir, packageName + extension)
 
        # do what needs to be done
        self._makeFolders()
        self._addPkgInfo()
        self._addInfo()
        self._addInfoPlist()
        self._addDescription()
        if options.get('Packages'):
            self._addPackages()
        else:
            self._addArchive()
            self._addBom()
            self._addSizes()
        self._addResources()
        self._addScripts()


    def addResource(self, path):
        "Add arbitrary file or folder to the package resource folder."
        
        # Folder basenames become subfolders of Contents/Resources.
        # This method is made public for those who wknow what they do!
   
        prf = self.packageResourceFolder
        if isfile(path) and not isdir(path):
            shutil.copy(path, prf)
        elif isdir(path):
            path = self._escapeBlanks(path)
            prf = self._escapeBlanks(prf)
            os.system("cp -r %s %s" % (path, prf))
        

    def _makeFolders(self):
        "Create package folder structure."

        # Not sure if the package name should contain the version or not...
        # packageName = "%s-%s" % (self.packageInfo["Title"], 
        #                          self.packageInfo["Version"]) # ??

        self.packageContentsFolder = join(self.packageRootFolder, "Contents")
        self.packageResourceFolder = join(self.packageContentsFolder, "Resources")
        os.mkdir(self.packageRootFolder)
        os.mkdir(self.packageContentsFolder)
        os.mkdir(self.packageResourceFolder)
        if self.packageInfo['Packages']:
            self.packagePackagesFolder = os.path.join(self.packageResourceFolder, "packages")
            os.mkdir(self.packagePackagesFolder)
        

    def _addPkgInfo(self):
        "Make PkgInfo file in Contents folder"

        fp = open(os.path.join(self.packageContentsFolder, "PkgInfo"), "wb")
        if self.packageInfo['Packages']:
            fp.write("pmkrmpkg")
        else:
            fp.write("pmkrpkg1")
        fp.close()


    def _addInfoPlist(self):
        "Write Info.plist file containing installing options."

        # Not sure if options in PKG_INFO_FIELDS are complete...

        def getValue (d, key):
            v = d.get(key, '')
            if v and (v.lower() == 'yes' or v.lower() == 'true'):
                return "<true/>"
            elif v and (v.lower() == 'no' or v.lower() == 'false'):
                return "<false/>"
            else:
                return "<string>" + v + "</string>"

        info = """<?xml version="1.0" encoding="UTF-8"?>
                  <!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
                  <plist version="1.0">
                  <dict>
                  <key>CFBundleGetInfoString</key>
                  <string>UpLib %(Version)s</string>
                  <key>CFBundleIdentifier</key>
                  <string>%(BundleIdentifier)s</string>
                  <key>CFBundleName</key>
                  <string>%(Title)s</string>
                  <key>CFBundleShortVersionString</key>
                  <string>%(Version)s</string>
                  <key>IFMajorVersion</key>
                  <integer>%(MajorVersion)s</integer>
                  <key>IFMinorVersion</key>
                  <integer>%(MinorVersion)s</integer>
                  """ % self.packageInfo

        for f in string.split(PKG_INFO_FLAGS, "\n"):
            info = info + "\t<key>IFPkgFlag%s</key>\n\t%s\n" % (f, getValue(self.packageInfo, f))

        info = info + """<key>IFPkgFormatVersion</key>
                <real>0.10000000149011612</real>
                </dict>
                </plist>
                """
        path = os.path.join(self.packageRootFolder, "Contents", "Info.plist")
        f = open(path, "w")
        f.write(info)


    def _addInfo(self):
        "Write .info file containing installing options."

        # Not sure if options in PKG_INFO_FIELDS are complete...

        info = ""
        for f in string.split(PKG_INFO_FIELDS, "\n"):
            info = info + "%s %%(%s)s\n" % (f, f)
        info = info % self.packageInfo
        if self.packageInfo['Packages']:
            info += "PackageLocation: ./packages\n"
        base = self.packageInfo["Title"] + ".info"
        path = join(self.packageResourceFolder, base)
        f = open(path, "w")
        f.write(info)


    def _addBom(self):
        "Write .bom file containing 'Bill of Materials'."

        # Currently ignores if the 'mkbom' tool is not available.

        try:
            bomPath = join(self.packageContentsFolder, "Archive.bom")
            bomPath = self._escapeBlanks(bomPath)
            sourceFolder = self._escapeBlanks(self.sourceFolder)
            cmd = "mkbom %s %s" % (sourceFolder, bomPath)
            res = os.system(cmd)
            cwd = os.getcwd()
            os.chdir(self.packageResourceFolder)
            os.symlink("../Archive.bom", "./" + self.packageInfo["Title"] + ".bom")
            os.chdir(cwd)
        except:
            pass


    def _addArchive(self):
        "Write .pax.gz file, a compressed archive using pax/gzip."

        # Currently ignores if the 'pax' tool is not available.

        cwd = os.getcwd()

        # create archive
        os.chdir(self.sourceFolder)
        self.archPath = join(self.packageContentsFolder, "Archive.pax.gz")
        archPath = self._escapeBlanks(self.archPath)
        cmd = "pax -x cpio -w -z -f %s %s" % (archPath, ".")
        res = os.system(cmd)
        
        # add symlink
        os.chdir(self.packageResourceFolder)
        os.symlink("../Archive.pax.gz", self.packageInfo["Title"] + ".pax.gz")

        os.chdir(cwd)


    def _addDescription(self):

        text = DESCRIPTION_TEXT % self.packageInfo
        path = os.path.join(self.packageResourceFolder, "Description.plist")
        f = open(path, "w")
        f.write(text)
        f.close()

    def _addResources(self):
        "Add all files and folders inside a resources folder to the package."

        # This folder normally contains Welcome/ReadMe/License files, 
        # .lproj folders and scripts.

        if not self.resourceFolder:
            return

        files = glob.glob("%s/*" % self.resourceFolder)
        for f in files:
            if not (f.endswith("~") or f.endswith("/CVS")):
                self.addResource(f)
        

    def _addSizes(self):
        "Write .sizes file with info about number and size of files."

        # Not sure if this is correct, but 'installedSize' and 
        # 'zippedSize' are now in Bytes. Maybe blocks are needed? 
        # Well, Installer.app doesn't seem to care anyway, saying 
        # the installation needs 100+ MB...

        numFiles = 0
        installedSize = 0
        zippedSize = 0

        files = GlobDirectoryWalker(self.sourceFolder)
        for f in files:
            numFiles = numFiles + 1
            installedSize = installedSize + os.lstat(f)[6]

        try:
            zippedSize = os.stat(self.archPath+ ".gz")[6]
        except OSError: # ignore error 
            pass
        base = self.packageInfo["Title"] + ".sizes"
        f = open(join(self.packageResourceFolder, base), "w")
        format = "NumFiles %d\nInstalledSize %d\nCompressedSize %d\n"
        f.write(format % (numFiles, installedSize, zippedSize))

    def _addScripts(self):

        title = self.packageInfo["Title"]

        cwd = os.getcwd()
        os.chdir(self.packageResourceFolder)

        for f in SCRIPT_NAMES.keys():
            path = join(".", f)
            print "checking", path, "=>", os.path.exists(path)
            if os.path.exists(path):
                os.chmod(path, 0555)
                os.symlink(path, join(".", title + "." + SCRIPT_NAMES[f]))
                print "   added " + join(".", title + "." + SCRIPT_NAMES[f])

        os.chdir(cwd)


    def _addPackages(self):

        title = self.packageInfo["Title"]
        packages = self.packageInfo["Packages"].split(",")
        package_list = []

        cwd = os.getcwd()
        os.chdir(self.packagePackagesFolder)

        for path in packages:
            print "checking", path, "=>", os.path.exists(path)
            if os.path.exists(path):
                package_filename = os.path.split(path)[1]
                cmd = 'ditto "%s" "%s"' % (path, os.path.join(self.packagePackagesFolder, package_filename))
                os.system(cmd)
                print "   added " + path
                package_list.append(package_filename)
            else:
                raise ValueError("No such package %s" % path)
        fp = open(os.path.join(self.packageResourceFolder, title + ".list"), "w")
        fp.write("\n".join([("%s:Required" % x) for x in package_list]))
        fp.close()

        os.chdir(cwd)


# Shortcut function interface

def buildPackage(*args, **options):
    "A shortcut function for building a package."
    
    o = options
    title, version, desc = o["Title"], o["Version"], o["Description"]
    pm = PackageMaker(title, version, desc)
    apply(pm.build, list(args), options)

    return pm


######################################################################
# Command-line interface
######################################################################

def printUsage():
    "Print usage message."

    format = "Usage: %s <opts1> [<opts2>] <root> [<resources>]"
    print format % basename(sys.argv[0])
    print
    print "       with arguments:"
    print "           (mandatory) root:         the package root folder"
    print "           (optional)  resources:    the package resources folder"
    print
    print "       and options:"
    print "           (mandatory) opts1:"
    mandatoryKeys = string.split("Title Version Description", " ")
    for k in mandatoryKeys:
        print "               --%s" % k
    print "           (optional) opts2: (with default values)"

    pmDefaults = PackageMaker.packageInfoDefaults
    optionalKeys = pmDefaults.keys()
    for k in mandatoryKeys:
        optionalKeys.remove(k)
    optionalKeys.sort()
    maxKeyLen = max(map(len, optionalKeys))
    for k in optionalKeys:
        format = "               --%%s:%s %%s"
        format = format % (" " * (maxKeyLen-len(k)))
        print format % (k, repr(pmDefaults[k]))


def main():
    "Command-line interface."

    shortOpts = ""
    keys = PackageMaker.packageInfoDefaults.keys()
    longOpts = map(lambda k: k+"=", keys)

    try:
        opts, args = getopt.getopt(sys.argv[1:], shortOpts, longOpts)
    except getopt.GetoptError, details:
        print details
        printUsage()
        return

    optsDict = {}
    for k, v in opts:
        optsDict[k[2:]] = v

    ok = optsDict.keys()
    if not (1 <= len(args) <= 2):
        print "No argument given!"
    elif not ("Title" in ok and \
              "Version" in ok and \
              "Description" in ok):
        print "Missing mandatory option!"
    else:
        pm = apply(buildPackage, args, optsDict)
        return

    printUsage()

    # sample use:
    # buildpkg.py --Title=distutils \
    #             --Version=1.0.2 \
    #             --Description="Python distutils package." \
    #             /Users/dinu/Desktop/distutils


if __name__ == "__main__":
    main()
