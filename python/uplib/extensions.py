# -*- Python -*-
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

import os, sys, re, cgi, time, urllib, types, traceback, binascii, tempfile, base64, zipfile, zlib, pprint, socket
from StringIO import StringIO

try:
    import ssl
    _have_ssl = True
except ImportError:
    _have_ssl = False

from uplib.plibUtil import PATH_SEPARATOR, note, Error, true, find_and_load_module, false, read_metadata, update_metadata, configurator, write_metadata, UPLIB_VERSION
from uplib.plibUtil import get_fqdn, unzip, zipup
from uplib.webutils import parse_URL, https_post_multipart, htmlescape, HTTPCodes
from uplib.basicPlugins import STANDARD_BACKGROUND_COLOR, output_tools_block, output_footer, STANDARD_LEGEND_COLOR, STANDARD_DARK_COLOR, STANDARD_TOOLS_COLOR

"A utility to view and manipulate extensions local to a repository."

ORANGE_BACKGROUND_COLOR = '#ef280e'
LIGHT_ORANGE_BACKGROUND_COLOR = '#fab6ad'
LIBRARY_FRAME_COLOR = '#80a080'
LIBRARY_BACKGROUND_COLOR = '#e0f0e0'

SITE_EXTENSIONS = None
ALLOW_OLD_EXTENSIONS = False
CONTRIB_URL = None
EXTENSIONS_SERVERS_CA_CERTS = None

_HIERARCHICAL_MODULES = set()   # add module name to this to allow hierarchical function names
"""A list of modules which can have more than 3 'parts' to their path"""

# re of files to exclude from code bundle
CODE_EXCLUDES = re.compile(r"(.*~$)|(.*\.class$)|(.*\.pyc$)")

def __compare_versions(v1, v2):
    return [int(x) for x in v1.split('.')] <= [int(x) for x in v2.split('.')]

def __readdoc(fname):
    return read_metadata(fname)

def __sort_modules(m1, m2):

    name1 = m1[1]
    name2 = m2[1]
    if name1 < name2:
        return -1
    elif name1 > name2:
        return 1
    else:
        return 0

def __beginpage (fp, title, extra_metas=None):
    fp.write("<html><head><title>%s</title>\n" % htmlescape(title))
    fp.write('<link rel="shortcut icon" type="image/ico" href="/favicon.ico">\n')
    fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
    fp.write('<!--\nThe following is for buggy IE browsers\n -->')
    fp.write('<head><meta http-equiv="Pragma" content="no-cache">\n')
    fp.write('<meta http-equiv="Expires" content="-1">\n')
    if extra_metas:
        fp.write(extra_metas)
    fp.write('</head>\n')

def __endpage (fp):
    fp.write('</body><!--\nThe following is for buggy IE browsers\n -->')
    fp.write('<head><meta http-equiv="Pragma" content="no-cache">\n')
    fp.write('<meta http-equiv="Expires" content="-1"></head></html>\n')

def __has_module(list, name):
    for mod in list:
        if name == mod[1]:
            return true
    return false

def _find_info_path (basename, ext):
    if os.path.split(basename)[1].startswith("__init__.py"):
        infopath = os.path.split(basename)[0] + ext
        # also allow putting the .info file in the package
        if not os.path.exists(infopath):
            infopath = os.path.join(os.path.split(basename)[0], "__uplib__" + ext)
    elif os.path.isdir(basename) and os.path.exists(os.path.join(basename, "__init__.py")):
        infopath = basename + ext
        # also allow putting the .info file in the package
        if not os.path.exists(infopath):
            infopath = os.path.join(basename, "uplib" + ext)
    else:
        infopath = os.path.splitext(basename)[0] + ext
    if os.path.exists(infopath):
        return infopath
    else:
        return None

def __add_modules(modules_list, dirs, tag):

    for dir in dirs:
        if os.path.isdir(dir):
            filenames = os.listdir(dir)
            for filename in filenames:
                modname = None
                if filename[0] == '.':
                    continue
                if filename.endswith('--deleted'):
                    continue
                if filename.endswith('.py'):
                    modname = filename[:-3]
                elif os.path.isdir(os.path.join(dir, filename)) and os.path.exists(os.path.join(dir, filename, "__init__.py")):
                    modname = filename
                else:
                    continue
                if modname and not __has_module(modules_list, modname):
                    infopath = _find_info_path(os.path.join(dir, filename), ".info")
                    if infopath:
                        try:
                            doc = __readdoc(infopath)
                        except:
                            doc = None
                    else:
                        doc = None
                    #if ALLOW_OLD_EXTENSIONS or (doc and doc.has_key("uplib-min-version")):
                    modules_list.append((tag, modname, os.path.join(dir, filename), doc,))

_INITS_TAGS = { 0 : 'no',
                1 : 'before',
                2 : 'after',
                3 : 'before, after',
                4 : '(unknown)',
                }

def figure_inits (mdoc):
    inits = 0
    if not mdoc:
        inits = inits | 4
    else:
        if mdoc.has_key('before') and mdoc['before'] == 'on':
            inits = inits | 1
        if mdoc.has_key('after') and mdoc['after'] == 'on':
            inits = inits | 2
    return inits

def find_and_load_extension (mname, path=None, addpath=None, allow_old_extensions=False):

    def compare_versions(v1, v2):
        return [int(x) for x in v1.split('.')] <= [int(x) for x in v2.split('.')]

    if not path:
        conf = configurator.default_configurator()
        path = conf.get("actions-path", "")

    # make sure our directory is on path, for older extensions
    if allow_old_extensions:
        oldpath = sys.path
        sys.path.append(os.path.split(__file__)[0])
    try:
        m = find_and_load_module(mname, path, addpath)
        if m:
            if not allow_old_extensions:
                # is it old?
                infopath = _find_info_path(m.__file__, ".info")
                if not infopath:
                    note(3, "Can't find info for module %s", mname)
                    return None
                doc = read_metadata(infopath)
                if not doc.has_key("uplib-min-version"):
                    note(3, "No uplib-min-version in extension module %s", mname)
                    return None
                if not compare_versions(doc["uplib-min-version"], UPLIB_VERSION):
                    note(3, "uplib-min-version of %s, current version %s -- too low",
                         doc["uplib-min-version"], UPLIB_VERSION)
                    return None
            if hasattr(m, "UPLIB_MIN_VERSION"):
                v = getattr(m, "UPLIB_MIN_VERSION")
                if not compare_versions(v, UPLIB_VERSION):
                    return None
            return m
        else:
            return None
    finally:
        if allow_old_extensions:
            sys.path = oldpath

def mark_as_hierarchical_extension(ename):
    # to support extensions with hierarchical static elements, like GWT-generated UIs
    global _HIERARCHICAL_MODULES
    _HIERARCHICAL_MODULES.add(ename)

def is_hierarchical_extension(ename):
    global _HIERARCHICAL_MODULES
    return (ename in _HIERARCHICAL_MODULES)

def show_extension (fp, metadata, tag, repo_name, current_uplib_version, untrusted):

    name = metadata.get("name")
    min_uplib_version = metadata.get("uplib-min-version")

    unusable = None
    if (not ALLOW_OLD_EXTENSIONS) and (not min_uplib_version):
        unusable = 'old'
    elif (min_uplib_version and not __compare_versions(min_uplib_version, current_uplib_version)):
        unusable = min_uplib_version
    if unusable:
        bgcolor = '#C0C0C0'
    else:
        bgcolor = (tag == 'inactive' and STANDARD_BACKGROUND_COLOR) or '#ffffff'
    framecolor = (tag == 'library' and LIBRARY_FRAME_COLOR) or STANDARD_LEGEND_COLOR

    filename = metadata.get("filename")
    basename = (filename and os.path.splitext(filename)[0])
    date = metadata.get("date")
    author = metadata.get("author")
    version = metadata.get("version")
    doc = metadata.get("description")
    inits = figure_inits(metadata)
    url = metadata.get("url")
    # fix historical bug
    if url == "0":
        url = ""

    fp.write('<a name="%s"><p></a>\n' % name)
    fp.write('<table width=100%% border=0 frame=box bgcolor="%s" cellpadding=5>' % framecolor)
    fp.write('<tr><td colspan=6><table width=100%% border=0><tr><td align=left><font size="+1" color="#ffffff"><tt><b>%s</b></tt></font></td>\n' % name)

    if tag == 'raw':
        fp.write('<td width=15%% align=right><form action="ext_editinfo"><input type=hidden name="basename" value="%s"><input type=submit value="Edit Info"></form></td>\n' % (urllib.quote(basename)))
    else:
        fp.write('<td width=15%% align=right>&nbsp;<td>\n');

    if tag == 'raw':
        if unusable:
            fp.write('<td width=15% align=right>&nbsp;</td>\n')
        else:
            fp.write('<td width=15%% align=right><form action="extlib_upload"><input type=hidden name="basename" value="%s"><input type=submit value="Contribute"></form></td>\n' % (urllib.quote(basename)))
    elif tag == 'library':
        if url:
            fp.write('<td width=15%% align=right><form action="%s"><input type=submit value="View Web Page"></form></td>\n' % urllib.quote(url))
        else:
            fp.write('<td width=15% align=right>&nbsp;</td>\n')
    else:
        fp.write('<td width=15%% align=right><form action="ext_showcode"><input type=hidden name="filename" value="%s"><input type=submit value="View Code"></form></td>\n' % (urllib.quote(filename)))

    if tag == 'raw':
        fp.write('<td width=15%% align=right><form action="extpath_deletedir"><input type=hidden name="directory" value="%s"><input type=submit value="Remove Dir"></form></td>\n' % (urllib.quote(os.path.dirname(filename))))

    elif tag == 'inactive':
        if unusable:
            fp.write('<td width=15% align=right>&nbsp;</td>\n')
        else:
            fp.write('<td width=15%% align=right><form action="ext_activate"><input type=hidden name="basename" value="%s"><input type=submit value="Activate"></form></td>\n' % urllib.quote(basename))
    elif tag == 'library':
        fp.write('<td width=15%% align=right><form action="extlib_showcode"><input type=hidden name="extname" value="%s"><input type=hidden name="version" value="%s"><input type=submit value="View Code"></form></td>\n' % (urllib.quote(name), urllib.quote(version)))
    else:
        fp.write('<td width=15%% align=right><form action="ext_deactivate"><input type=hidden name="basename" value="%s"><input type=submit value="Deactivate"></form></td>\n' % urllib.quote(basename))

    if tag == 'raw':
        fp.write('<td width=15%% align=center><form action="ext_deletefile"><input type=hidden name="basename" value="%s"><input type=submit value="Delete File"></form></td>\n' % urllib.quote(basename))
    elif tag == 'library':
        if unusable or untrusted:
            fp.write('<td width=15%% align=center>&nbsp;</td>\n')
        else:
            fp.write('<td width=15%% align=center><form action="extlib_download"><input type=hidden name="extname" value="%s"><input type=hidden name="version" value="%s"><input type=submit value="Install in \'%s\'"></form></td>\n' % (htmlescape(name, true), htmlescape(version, true), htmlescape(repo_name, true)))
    else:
        fp.write('<td width=15%% align=center><form action="ext_deletefile"><input type=hidden name="basename" value="%s"><input type=submit value="Delete"></form></td>\n' % urllib.quote(basename))

    fp.write('</tr></table></td></tr><tr>\n')

    if unusable:
        reason = ((unusable == 'old') and "old extension") or ("requires UpLib %s" % unusable)
        fp.write('<td width=20%% align=left bgcolor=%s><small><font color="red"><b>%s</b></font></small></td>\n' % (bgcolor, reason))
    elif (tag == 'library'):
        if url:
            fp.write('<td width=20%% align=left bgcolor="white"><small><font color="%s"><a href="%s">Web Page</a></font></small></td>\n' % ('black', htmlescape(url, true)))
        else:
            fp.write('<td width=20%% align=left bgcolor="white">&nbsp;</td>\n')
    else:
        fp.write('<td width=20%% align=left bgcolor="%s"><small><font color="%s"><i>Installed: </i></font><font color="%s">%s</font></small></td>\n' % (bgcolor, framecolor, (tag == 'raw' and 'red') or 'black', (tag == 'inactive' and 'no') or (tag == 'repo' and 'repository') or (tag == 'site' and 'site') or (tag == 'raw' and 'extensions-path') or 'yes'))

    if inits >= 0:
        fp.write('<td width=25%% align=left bgcolor="%s"><small><font color="%s"><i>Initializer: </i></font><font color="%s">%s</font></small></td>\n' % (bgcolor, framecolor, 'black', _INITS_TAGS[inits]))
    else:
        fp.write('<td width=25%% align=left bgcolor="white">&nbsp;</td>\n')

    fp.write('<td width=25%% align=left bgcolor="%s"><small><font color="%s"><i>Author: </i></font><font color="%s">%s</font></small></td>\n' % (bgcolor, framecolor, 'black', author))

    fp.write('<td width=10%% align=left bgcolor="%s"><small><font color="%s"><i>Version: </i></font><font color="%s">%s</font></small></td>\n' % (bgcolor, framecolor, 'black', version))

    fp.write('<td width=20%% align=left bgcolor="%s"><small><font color="%s"><i>Date: </i></font><font color="%s">%s</font></small></td>\n' % (bgcolor, framecolor, 'black', date))

    fp.write('</tr>\n')
    docstring = htmlescape(doc)
    docstring = re.sub('&lt;[pP]/?&gt;', '<p>', docstring)
    docstring = re.sub('&lt;(/?)[bB]&gt;', r'<\1b>', docstring)
    docstring = re.sub('&lt;(/?)[iI]&gt;', r'<\1i>', docstring)
    docstring = re.sub('&lt;(/?)[tT][tT]&gt;', r'<\1tt>', docstring)
    docstring = re.sub('&lt;[hH][rR]&gt;', '<hr>', docstring)
    if tag == 'raw':
        docstring = docstring + "<hr>\n<small><a type=\"text/plain\" target=\"_blank\" href=\"ext_showcode?filename=" + urllib.quote(filename) + "\">" + htmlescape(filename, 1) + "</a></small>"
    fp.write('<tr><td colspan=6 bgcolor="%s">%s</td></tr></table></tr>\n' % (bgcolor, docstring))


def get_extension_modules(repo):

    modules = []

    global SITE_EXTENSIONS, ALLOW_OLD_EXTENSIONS

    if not SITE_EXTENSIONS:
        conf = configurator.default_configurator()
        uplib_lib = conf.get('uplib-lib')
        SITE_EXTENSIONS = os.path.join(uplib_lib, 'site-extensions')
        ALLOW_OLD_EXTENSIONS = conf.get_bool("allow-old-extensions")

    ap = repo.get_actions_path()
    if (ap and PATH_SEPARATOR in ap):
        p = ap.split(PATH_SEPARATOR)
    elif ap:
        p = (ap,)
    else:
        p = ()
    p = [os.path.expanduser(x) for x in [x.strip() for x in p] if x]
    __add_modules(modules, p, 'raw')

    __add_modules(modules, (os.path.join(repo.overhead_folder(), "extensions", "active"),), 'repo')
    __add_modules(modules, (SITE_EXTENSIONS,), 'site')
    __add_modules(modules, (os.path.join(repo.overhead_folder(), "extensions", "inactive"),), 'inactive')

    modules.sort(__sort_modules)
    return modules, p


def ext_list (repo, response, params):

    """List extensions available in the repository.  Indicate date, author, version, and docs."""

    modules, extensions_dirs = get_extension_modules(repo)
    
    note(3, "ALLOW_OLD_EXTENSIONS is %s", ALLOW_OLD_EXTENSIONS)

    fp = response.open()
    title = "Extensions in '%s'" % repo.name()

    __beginpage(fp, title)
    fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)

    output_tools_block (repo, fp, htmlescape(title), "Icon MRU", None, None)

    fp.write('<p>\n')

    url = "https://%s:%s/" % (get_fqdn(), repo.secure_port())

    if modules:
        fp.write('<table width=100%><tr><td align=left>' +
                 'The following extensions are installed in the repository "%s" at %s.' % (repo.name(), url) +
                 '<p>Extensions shown with a white background are active, and those shown ' +
                 'with a light blue background are inactive.  Those with a gray background are old,' +
                 ' and need to be updated to run with this version of UpLib.' +
                 '<p>To find new extensions in ' +
                 'the site-wide library, click on the button to the right, labelled ' +
                 '"Find New Extensions to Install".' +
                 '</td><td align=right><form action="extlib_showlib">' +
                 '<input type=submit value="Find New Extensions to Install">' +
                 '</form></td></tr></table>')

        for tag, mname, mfile, pmdoc in modules:
            if (pmdoc == None):
                mdoc = {}
            else:
                mdoc = pmdoc.copy()
            if "date" not in mdoc:
                mdoc["date"] = time.strftime("%m/%d/%y", time.localtime(os.path.getmtime(mfile)))
            if "name" not in mdoc:
                mdoc["name"] = mname
            if "filename" not in mdoc:
                mdoc["filename"] = mfile
            if "author" not in mdoc:
                mdoc["author"] = "(unknown)"
            if "version" not in mdoc:
                mdoc["version"] = "0"
            if "description" not in mdoc:
                mdoc["description"] = "(none given)"
            if "url" not in mdoc:
                mdoc["url"] = ""
            show_extension(fp, mdoc, tag, repo.name(), repo.get_version(), False)

    else:
        fp.write('<table width=100%><tr><td align=left>'
                 'No extensions are currently installed.'
                 '</td><td align=right><form action="extlib_showlib">'
                 '<input type=submit value="Find New Extensions to Install">'
                 '</form></td></tr></table>')

    if extensions_dirs:
        fp.write('<a name="extensionspath"><p></a>\n')
        fp.write('The following directories are on the <i>extensions-path</i> for "%s":<br>\n' % htmlescape(repo.name()))
        fp.write('<table width=100%>')
        for dir in extensions_dirs:
            fp.write('<tr bgcolor="white" valign=center><td><tt>%s</tt></td>' % htmlescape(dir))
            if dir == extensions_dirs[0]:
                fp.write('<td align=right>&nbsp;</td>')
            else:
                fp.write('<td valign=center align=right><form action="extpath_promotedir" method=post>' +
                         '<input type=hidden name="directory" value="%s">' % htmlescape(dir, true) +
                         '<input type=submit value="Promote Dir"></form></td>')
            fp.write('<td valign=center align=right><form action="extpath_deletedir" method=post>' +
                     '<input type=hidden name="directory" value="%s">' % htmlescape(dir, true) +
                     '<input type=submit value="Remove Dir"></form></td>')
            fp.write('</tr>')
        fp.write('</table>\n')
    fp.write('<p><form action="extpath_adddir" method=get><input type=submit value="Add New Directory to Extensions-Path"></form>\n')

    output_footer(repo, fp, None, response.logged_in)
    __endpage(fp)
    fp.close()



def ext_deletefile (repo, response, params):

    cancel = params.get('cancel')
    confirm = params.get('confirm')
    basename = params.get('basename')

    if not basename:
        response.error(HTTPCodes.BAD_REQUEST, "No 'basename' parameter specified.")
        return

    if params.get('cancel'):
        response.redirect('ext_list#%s' % os.path.basename(basename))
        return

    basename = urllib.unquote(basename)

    if (os.path.exists(basename) and os.path.isdir(basename) and os.path.exists(os.path.join(basename, "__init__.py"))):
        filename = basename
    elif (os.path.exists(basename + ".py")):
        filename = basename + ".py"
    else:
        response.error(HTTPCodes.BAD_REQUEST, "Bad 'basename' parameter ' + htmlescape(basename) + ' specified.")
        return

    if params.get('view'):
        params['filename'] = filename
        ext_showcode(repo, response, params)
        return

    if confirm:
        infopath = _find_info_path(basename, ".info")
        os.rename(filename, filename + "--deleted")
        if infopath:
            os.rename(infopath, infopath + "--deleted")
        response.redirect("ext_list")
        return

    else:
        # send back confirmer page
        fp = response.open()
        __beginpage(fp, 'Confirm Delete for "%s"' % filename)
        fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR +
                 '<table width=100% height=100%><tr align=center><td align=center>' +
                 '<form action="ext_deletefile" method=POST>\n' +
                 '<center><tt><b>%s</b></tt><p>Press "Delete" to delete the file:<p>\n' % htmlescape(filename) +
                 '<input type=hidden name="basename" value="%s">\n' % htmlescape(basename, 1) +
                 '<table><tr><td align=left><input type=submit name="cancel" value="Cancel"></td>' +
                 '<td width=50px>&nbsp;</td>' +
                 '<td align=center><input type=submit name="view" value="View File"></td>\n' +
                 '<td width=50px>&nbsp;</td>' +
                 '<td align=right><input type=submit name="confirm" value="Delete"></td></tr></table>\n' +
                 '</form>\n' +
                 '</center></form></td></tr></table>')
        __endpage(fp)
        fp.close()
        return


def samefile (fname1, fname2):
    if hasattr(os.path, "samefile"):
        return os.path.samefile(fname1, fname2)
    else:
        return os.path.abspath(fname1) == os.path.abspath(fname2)


def __restart(modname, repo, response):

    spinner = os.path.join(repo.root(), "html", "images", "rotating-uplib-logo.gif")
    if os.path.exists(spinner):
        imagetag = '<p><img src="/html/images/rotating-uplib-logo.gif" width=20 height=20>'
    else:
        imagetag = ''
    
    fp = response.open()
    fp.write('<head><title>Re-starting UpLib Guardian Angel</title>\n' +
             ('<meta http-equiv="Refresh" content="60; url=ext_list#%s"></head>\n' % modname) +
             ('<body bgcolor="%s">\n' % STANDARD_TOOLS_COLOR) +
             '<table width=100% height=100%><tr align=center><td align=center>' +
             ('<table bgcolor="%s" cellpadding=50><tr><td>' % STANDARD_BACKGROUND_COLOR) +
             '<center>Now re-starting the UpLib Guardian Angel<br>' +
             'to enable the extension\'s startup actions.' +
             '<p>This may take up to 60 seconds.' +
             '<p>Please wait...' + imagetag +
             '</center></td></tr></table></td></tr></table></body>')
    fp.close()
    # response.request.version = None

    # fork off uplib-check-angel
    conf = configurator.default_configurator()
    if sys.platform.startswith("win"):
        classname = 'UpLibGuardianAngel_%d' % repo.secure_port()
        
        pyExe = sys.executable
        sPath = "lib\\site-packages\\win32\\pythonservice.exe"
        if pyExe.lower().endswith(sPath):
            pyExe = pyExe[:len(pyExe)-len(sPath)]+"python.exe"
        arg1 = "\""+conf.get("uplib-bin")+"\\restartUpLibService.py\""
        arg2 = "--port="+str(repo.secure_port())
        note("command is %s %s %s", pyExe, arg1, arg2)
        response.request.channel.server.close()

        # Must use spawn so this happens outside the repository
        os.spawnl(os.P_NOWAIT, pyExe, pyExe, arg1, arg2)
    else:
        uplib_check_angel = os.path.join(conf.get("uplib-bin"), "uplib-check-angel")
        cmd = "/bin/sh -c '(sleep 5 ; %s --restart %s > /dev/null 2>&1) &'" % (uplib_check_angel, repo.root())
        note("command is %s", cmd)
        response.request.channel.server.close()
        os.system(cmd)


def ext_activate(repo, response, params):

    basename = params.get('basename')
    if not basename:
        response.error(HTTPCodes.BAD_REQUEST, "No 'basename' parameter specified.")
        return
    basename = urllib.unquote(basename)
    if (os.path.exists(basename) and os.path.isdir(basename) and os.path.exists(os.path.join(basename, "__init__.py"))):
        filename = basename
    elif (os.path.exists(basename + ".py")):
        filename = basename + ".py"
    else:
        response.error(HTTPCodes.BAD_REQUEST, "Bad 'basename' parameter ' + htmlescape(basename) + ' specified.")
        return

    dir = os.path.dirname(filename)
    file = os.path.basename(filename)
    if not (samefile(dir, os.path.join(repo.overhead_folder(), "extensions", "inactive"))):
        response.error(HTTPCodes.BAD_REQUEST, 'Extension ' + htmlescape(basename) + ' not in the repository\'s "inactive" directory.')
        return
    activedir = os.path.join(repo.overhead_folder(), "extensions", "active")
    os.rename(filename, os.path.join(activedir, file))
    infopath = _find_info_path(filename, ".info")
    if infopath:
        os.rename(infopath, os.path.join(activedir, os.path.basename(infopath)))

    mod = find_and_load_extension(os.path.basename(basename), os.path.join(repo.overhead_folder(), "extensions", "active"), None,
                                  allow_old_extensions=ALLOW_OLD_EXTENSIONS)
    if hasattr(mod, "after_repository_instantiation") or hasattr(mod, "before_repository_instantiation"):
        # restart the server!
        __restart(os.path.basename(basename), repo, response)
    else:
        response.redirect('ext_list#%s' % os.path.basename(basename))


def ext_deactivate(repo, response, params):

    basename = params.get('basename')
    if not basename:
        response.error(HTTPCodes.BAD_REQUEST, "No 'basename' parameter specified.")
        return
    basename = urllib.unquote(basename)
    if (os.path.exists(basename) and os.path.isdir(basename) and os.path.exists(os.path.join(basename, "__init__.py"))):
        filename = basename
    elif (os.path.exists(basename + ".py")):
        filename = basename + ".py"
    else:
        response.error(HTTPCodes.BAD_REQUEST, "Bad 'basename' parameter ' + htmlescape(basename) + ' specified.")
        return

    dir = os.path.dirname(filename)
    file = os.path.basename(filename)
    if not (samefile(dir, os.path.join(repo.overhead_folder(), "extensions", "active"))):
        response.error(HTTPCodes.BAD_REQUEST, 'Extension ' + htmlescape(basename) + ' not in the repository\'s "active" directory.')
        return

    mod = find_and_load_extension(os.path.basename(basename), os.path.join(repo.overhead_folder(), "extensions", "active"), None,
                                  allow_old_extensions=ALLOW_OLD_EXTENSIONS)
    has_starters = hasattr(mod, "after_repository_instantiation") or hasattr(mod, "before_repository_instantiation")

    inactivedir = os.path.join(repo.overhead_folder(), "extensions", "inactive")
    note("renaming %s to %s", filename, os.path.join(inactivedir, file))
    infopath = _find_info_path(filename, ".info")
    os.rename(filename, os.path.join(inactivedir, file))
    if infopath:
        os.rename(infopath, os.path.join(inactivedir, os.path.basename(infopath)))

    if has_starters:
        __restart(os.path.basename(basename), repo, response)
    else:
        response.redirect('ext_list#%s' % os.path.basename(basename))



def extpath_adddir (repo, response, params):

    directory = params.get('directory')
    if not directory:

        # send back a form to fill out

        fp = response.open()
        __beginpage(fp, 'Adding Directory to Extensions-Path for Repository "%s"' % repo.name(),
                    '<meta http-equiv="Content-Script-Type" content="text/javascript">\n'
                    '<script type="text/javascript">\n'
                    'function sf(){document.adddir.directory.focus();}\n'
                    '</script>\n')
        fp.write('<body bgcolor="%s" onload="sf()">\n' % STANDARD_BACKGROUND_COLOR)
        fp.write('<table width=100% height=100%><tr align=center><td align=center>'+
                 '<form action="extpath_adddir" method=POST name="adddir">\n' +
                 'Enter the directory you wish to add to the <i>Extensions-Path</i> ' +
                 'for repository \'%s\'\n' % htmlescape(repo.name()) +
                 '<p><input type=text size=60 name="directory" value="">\n' +
                 '<p><input type=submit value="Submit">\n' +
                 '</form></td></tr></table>')
        __endpage(fp)
        return

    directory = urllib.unquote(directory)

    if not os.path.exists(os.path.expanduser(directory)) or not os.path.isdir(os.path.expanduser(directory)):
        response.error(HTTPCodes.BAD_REQUEST, "Specified directory, " + directory + ", is not a valid directory.")
        return

    else:
        # OK, we've got the directory:  add it

        dirs = repo.get_actions_path()
        if dirs:
            dirs = dirs + PATH_SEPARATOR + directory
        else:
            dirs = directory
        repo.set_actions_path(dirs)
        response.redirect('ext_list#extensionspath')


def extpath_promotedir (repo, response, params):

    directory = params.get('directory')
    if not directory or not os.path.exists(os.path.expanduser(directory)) or not os.path.isdir(os.path.expanduser(directory)):
        response.error(HTTPCodes.BAD_REQUEST, "Specified directory, " + directory + ", is not a valid directory.")
        return

    else:
        # OK, we've got the directory:  add it

        directory = urllib.unquote(directory)

        dirs = repo.get_actions_path()
        if dirs:
            dirs = dirs.split(PATH_SEPARATOR)
        else:
            dirs = []
        found = -1
        for i in range(len(dirs)):
            if directory == os.path.expanduser(dirs[i]):
                found = i
                break

        if found > 0:
            dirs[found - 1], dirs[found] = dirs[found], dirs[found - 1]
            repo.set_actions_path(PATH_SEPARATOR.join(dirs))

        response.redirect('ext_list#extensionspath')


def extpath_deletedir (repo, response, params):

    directory = params.get('directory')
    if not directory:
        response.error(HTTPCodes.BAD_REQUEST, 'Required parameter "directory" not provided.')
        return

    directory = urllib.unquote(directory)

    dirs = repo.get_actions_path()
    if not dirs:
        response.redirect('ext_list#extensionspath')
        return

    dirs = dirs.split(PATH_SEPARATOR)
    found = None
    for testdir in dirs:
        if directory == os.path.expanduser(testdir):
            found = testdir
            break
    
    if not found:
        response.reply('Directory "' + directory + '" doesn\'t seem to be in the extensions-path:<p>' + '<p>'.join(dirs))
        return

    dirs.remove(found)
    repo.set_actions_path(PATH_SEPARATOR.join(dirs))
    response.redirect('ext_list#extensionspath')
    return



def ext_editinfo (repo, response, params):

    base = params.get('basename')
    if not base:
        response.error(HTTPCodes.BAD_REQUEST, 'Required parameter "basename" not provided.')
        return

    base = urllib.unquote(base)
    if (os.path.exists(base) and os.path.isdir(base) and os.path.exists(os.path.join(base, "__init__.py"))):
        filename = base
    elif (os.path.exists(base + ".py")):
        filename = base + ".py"
    else:
        response.error(HTTPCodes.BAD_REQUEST, "Bad 'basename' parameter ' + htmlescape(base) + ' specified.")
        return

    infopath = base + '.info'

    if params.has_key('description'):
        newdb = {'before': 'off', 'after': 'off'}
        for key in ('name', 'author', 'version', 'url', 'before', 'after', 'description', 'uplib-min-version'):
            if params.has_key(key):
                newdb[key] = params[key].replace('\n', ' ').replace('\r', ' ')
        try:
            update_metadata(infopath, newdb)
        except:
            type, value, tb = sys.exc_info()
            msg = ''.join(traceback.format_exception(type, value, tb))
            note(0, "Exception trying to update " + infopath + ":\n" + msg)
            response.error(HTTPCodes.INTERNAL_SERVER_ERROR, 'Couldn\'t write info file ' + infopath + '.\n')
            return
        response.redirect('ext_list#%s' % os.path.basename(base))

    else:

        if os.path.exists(infopath):
            try:
                info = read_metadata(infopath)
            except:
                response.error(HTTPCodes.BAD_REQUEST, 'Existing info file ' + infopath + ' not readable.');
                return
        else:
            info = {}

        descr = info.get('description')
        if descr:
            descr = re.sub(r'\s(<[pP]/?>)', '\n\n\\1', descr)
        else:
            descr = ''

        fp = response.open()
        __beginpage(fp, "Editing Info for %s" % os.path.basename(base))
        fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
        fp.write('<table width=100% height=100%><tr align=center><td align=center>\n')
        fp.write('<center><H3>Editing Information for Extension "%s"</H3>\n' % htmlescape(os.path.basename(base)) +
                 '<p><small>(<a type="text/plain" target="_blank" href="ext_showcode?filename=' + urllib.quote(filename) + '">' + htmlescape(filename, 1) + '</a>)</small>\n')
        fp.write('<p><form action="ext_editinfo" method=POST enctype="multipart/form-data">\n')
        fp.write('<input type=hidden name="basename" value="%s">\n' % htmlescape(base, true))
        fp.write('<table>\n')
        fp.write('<tr><td align=right>Author:</td><td><input type=text size=60 name="author" value="%s"></td></tr>' % htmlescape(info.get('author') or os.environ.get('NAME') or ""))
        fp.write('<tr><td align=right>Version:  </td><td><input type=text name="version" value="%s"></td></tr>' % htmlescape(info.get('version') or ''))
        fp.write('<tr><td align=right>Initializers:  </td><td>' +
                 '<input type=checkbox %s name="before">Before' % ((info.get('before') == 'on' and "checked") or "") +
                 '&nbsp;&nbsp;&nbsp;&nbsp;' +
                 '<input type=checkbox %s name="after">After' % ((info.get('after') == 'on' and "checked") or "") +
                 '</td></tr>')
        fp.write('<tr><td align=right>Description:  </td><td><textarea rows=20 cols=60 name="description">%s</textarea></td></tr>' % htmlescape(descr))
        fp.write('<tr><td align=right>URL (if any):  </td><td><input type=text name="url" value="%s"></td></tr>' % htmlescape(info.get('url') or ''))
        fp.write('<tr><td align=right>Minimum UpLib version:  </td><td><input type=text name="uplib-min-version" value="%s"></td></tr>' % htmlescape(info.get('uplib-min-version') or repo.get_version()))
        fp.write('</table><p><input type=submit value="Enter"></form></center>\n')
        fp.write('<p><blockquote>The <i>description</i> field is really a limited form of HTML.<br>'
                 'Only the &lt;p&gt, &lt;i&gt, &lt;b&gt, &lt;tt&gt, and &lt;hr&gt tags can be used.<br>'
                 'Any other tags used will just show up as literals in the text.\n</blockquote>')
        fp.write('</td></tr></table>')
        __endpage(fp);
        fp.close()
        return

def ext_showcode (repo, response, params):

    filename = params.get('filename')
    if not filename:
        response.error(HTTPCodes.BAD_REQUEST, 'Required parameter "filename" not provided.')
        return
    filename = urllib.unquote(filename)

    if not os.path.exists(filename):
        response.error(HTTPCodes.BAD_REQUEST, 'File "%s" doesn\'t exist.' % htmlescape(filename))
        return

    if os.path.isdir(filename):

        files = os.listdir(filename)
        ename = os.path.basename(filename)
        fp = response.open()
        __beginpage(fp, 'Extension "%s"' % ename)
        fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
        fp.write('<b>Extension \'%s\'</b> (in directory %s)\n<hr>\n<p><ul>\n' % (htmlescape(ename), htmlescape(filename)))
        for fname in files:
            if fname.endswith('.py'):
                fp.write('<li><a href="ext_showcode?filename=%s">%s</a>\n' % (htmlescape(os.path.join(filename, fname), true), htmlescape(fname)))
        fp.write('</ul>')
        __endpage(fp)
        return

    else:

        ename = os.path.splitext(os.path.basename(filename))[0]
        try:
            f = open(filename, 'r')
        except:
            response.error(HTTPCodes.BAD_REQUEST, htmlescape('Can\'t open specified file ' + filename + '.'));
            return

        fp = response.open()
        if filename:
            __beginpage(fp, 'Extension "%s":  %s' % (ename, filename))
        else:
            __beginpage(fp, 'Extension "%s"' % ename)
        fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
        if filename:
            fp.write('<b>Extension "%s":  %s</b>\n' % (htmlescape(ename), htmlescape(filename)))
        else:
            fp.write('<b>Extension "%s"</b>\n' % htmlescape(ename))
        fp.write('<hr><pre>\n')
        fp.write(htmlescape(f.read()))
        f.close()
        fp.write('</pre>\n')
        __endpage(fp)
        fp.close()
        return



def _extlib_checksite (repo, url):

    # validate a particular site, and return the certificates to use with it
    host, port, path = parse_URL(url)
    certfilepath = os.path.join(repo.overhead_folder(), "extensions", "%s.%s.pem" % (host, port))
    note("looking for '%s' -- %s", certfilepath, os.path.exists(certfilepath))
    if os.path.exists(certfilepath):
        clientcertpath = os.path.join(repo.overhead_folder(), "extensions", "%s.%s.client.pem" % (host, port))
        if os.path.exists(clientcertpath):
            return (certfilepath, clientcertpath)
        else:
            return (certfilepath, None)
    else:
        return None

def _extlib_acceptsite (repo, url, servercert_pem, clientcertandkey_pem=None):

    # store the certificates to use with a particular site
    host, port, path = parse_URL(url)
    certfilepath = os.path.join(repo.overhead_folder(), "extensions", "%s.%s.pem" % (host, port))
    fp = open(certfilepath, 'w')
    fp.write(servercert_pem)
    fp.close()
    if clientcertandkey_pem:
        clientcertpath = os.path.join(repo.overhead_folder(), "extensions", "%s.%s.client.pem" % (host, port))
        fp = open(clientcertpath, 'w')
        fp.write(clientcertandkey_pem)
        fp.close()

def _extlib_get_server_identity (url, fullcert=False):

    """Retrieve the certificate from the server at the specified address,
    validate it, and return its identity string."""
    
    note("url is %s, EXTENSIONS_SERVERS_CA_CERTS is %s", url, EXTENSIONS_SERVERS_CA_CERTS)
    host, port, path = parse_URL(url)
    s = ssl.wrap_socket(socket.socket(),
                        cert_reqs=ssl.CERT_REQUIRED,
                        ca_certs=EXTENSIONS_SERVERS_CA_CERTS)
    s.connect((host, port))
    certdict = s.getpeercert(fullcert)
    s.close()
    return certdict

def extlib_allowsite(repo, response, params):

    url = params.get("url")
    if not url:
        response.error(HTTPCodes.BAD_REQUEST, "No 'url' parameter specified.")
        return
    cert = _extlib_get_server_identity(url, True)
    if cert:
        pem = ssl.DER_cert_to_PEM_cert(cert)
        _extlib_acceptsite (repo, url, pem)
    referer = response.request.get_header('referer')
    response.redirect(referer or "extlib_showlib")

def extlib_download (repo, response, params):

    global CONTRIB_URL, EXTENSIONS_SERVERS_CA_CERTS

    def copyvalue (db, line):
        colon_pos = line.find(':')
        if colon_pos > 0:
            key = line[:colon_pos]
            val = line[colon_pos+1:].strip()
            db[key] = val

    extname = params.get('extname')
    if not extname:
        response.error(HTTPCodes.BAD_REQUEST, "No 'extname' parameter specified.")
        return

    if CONTRIB_URL == None:
        # initialize contrib-url from site.config
        conf = configurator.default_configurator()
        CONTRIB_URL = conf.get('extensions-library-url')
        if not CONTRIB_URL:
            response.error(HTTPCodes.BAD_REQUEST, "No Extensions Library URL available.")
            return
        if EXTENSIONS_SERVERS_CA_CERTS is None:
            EXTENSIONS_SERVERS_CA_CERTS = conf.get("extensions-sites-ca-certs-file")

    host, port, path = parse_URL(CONTRIB_URL)
    parms = [ ('name', extname), ('code', "true"), ('info', "true") ]
    if params.get('version'):
        parms.append(('version', params.get('version')))

    certs = _extlib_checksite(repo, CONTRIB_URL)

    status, status_msg, headers, msg = https_post_multipart(host, port, None, "/get", parms, [],
                                                            ca_certs=EXTENSIONS_SERVERS_CA_CERTS,
                                                            certfile=(certs and certs[1]) or None)
    if status != 200:
        note("Download of extension %s from %s signalled %s -- %s.  Message was:\n%s\n", extname, CONTRIB_URL, status, status_msg, msg)
        fp = response.open('text/plain')
        fp.write("Download of extension %s from %s signalled %s -- %s.  Message was:\n%s\n" % (extname, CONTRIB_URL, status, status_msg, msg))
        fp.close()
        return

    db = {}
    z = zipfile.ZipFile(StringIO(msg), 'r')
    i = z.infolist()
    # should be two entries, one for the info and one for the code
    if len(i) != 2:
        note("Odd results from extlib_download of '%s':  %s", extname, [x.filename for x in i])
        fp = response.open('text/plain')
        fp.write("Odd results from extlib_download of '%s':  %s" % (extname, [x.filename for x in i]))
        fp.close()
        return
        
    infopath = None
    codepath = None
    for entry in i:
        if entry.filename.endswith("/info"):
            infopath = os.path.join(repo.overhead_folder(), "extensions", "inactive", extname + ".info")
            open(infopath, 'wb').write(zlib.decompress(z.read(entry.filename)))
        elif entry.filename.endswith("/code"):
            codepath = os.path.join(repo.overhead_folder(), "extensions", "inactive", extname)
            bytes = z.read(entry.filename)
            zc = zipfile.ZipFile(StringIO(bytes), 'r')
            ic = zc.infolist()
            if len(ic) == 1:
                # just a single file
                codepath += ".py"
                open(codepath, 'wb').write(zc.read(ic[0].filename))
                zc.close()
            else:
                zc.close()
                unzip(codepath, StringIO(bytes))
        else:
            note("Odd entry in zipfile from extlib_download of '%s':  %s", extname, [x.filename for x in i])
            fp = response.open('text/plain')
            fp.write("Odd entry in zipfile returned from download of '%s' from '%s':  %s" % (extname, CONTRIB_URL, nentry.filename))
            fp.close()
            return

    if not infopath:
        note("No info in results from extlib_download of '%s' from '%s':  %s", extname, CONTRIB_URL, [x.filename for x in i])
        fp = response.open('text/plain')
        fp.write("No info in results from extlib_download of '%s' from '%s': %s" % (extname, CONTRIB_URL, [x.filename for x in i]))
        fp.close()
        return
        
    if not codepath:
        note("No code in results from extlib_download of '%s' from '%s':  %s", extname, CONTRIB_URL, [x.filename for x in i])
        fp = response.open('text/plain')
        fp.write("No code in results from extlib_download of '%s' from '%s': %s" % (extname, CONTRIB_URL, [x.filename for x in i]))
        fp.close()
        return
        
    response.redirect('ext_list#%s' % extname)


def extlib_upload (repo, response, params):

    global CONTRIB_URL, EXTENSIONS_SERVERS_CA_CERTS

    base = params.get('basename')
    if not base:
        response.error(HTTPCodes.BAD_REQUEST, 'Required parameter "basename" not provided.')
        return

    base = urllib.unquote(base)
    if (os.path.exists(base) and os.path.isdir(base) and os.path.exists(os.path.join(base, "__init__.py"))):
        filename = base
    elif (os.path.exists(base + ".py")):
        filename = base + ".py"
    else:
        response.error(HTTPCodes.BAD_REQUEST, "Bad 'basename' parameter ' + htmlescape(base) + ' specified.")
        return

    infopath = _find_info_path(filename, ".info")
    if not infopath:
        response.error(HTTPCodes.BAD_REQUEST, "No info file for extension '%s'." % base)
        return
    db = read_metadata(infopath)

    tfname = None
    try:
        if os.path.isdir(filename):
            tfname = zipup(filename, EXCLUDES=CODE_EXCLUDES, COMPRESSION=zipfile.ZIP_DEFLATED)
            tfbits = None
        else:
            s = StringIO()
            z = zipfile.ZipFile(s, 'w')
            z.writestr(os.path.split(filename)[1], open(filename, 'r').read())
            z.close()
            tfbits = s.getvalue()

        s = StringIO()
        write_metadata(s, db)
        info = zlib.compress(s.getvalue(), 8)

        if CONTRIB_URL == None:
            # initialize contrib-url from site.config
            conf = configurator.default_configurator()
            CONTRIB_URL = conf.get('extensions-library-url')
            if not CONTRIB_URL:
                response.error(HTTPCodes.BAD_REQUEST, "No Extensions Library URL available.")
                return
            if EXTENSIONS_SERVERS_CA_CERTS is None:
                EXTENSIONS_SERVERS_CA_CERTS = conf.get("extensions-sites-ca-certs-file")

        host, port, path = parse_URL(CONTRIB_URL)
        parms = [ ('name', os.path.basename(base)),
                  ('version', (db.has_key('version') and db['version']) or '0'),
                  ('info', info),]
        if tfname:
            files = [ ('code', tfname), ]
        else:
            files = []
            parms.append(('code', tfbits))

        certs = _extlib_checksite(repo, CONTRIB_URL)
            
        status, status_msg, headers, msg = https_post_multipart(host, port, None, "/upload", parms, files,
                                                                ca_certs=EXTENSIONS_SERVERS_CA_CERTS,
                                                                certfile=(certs and certs[1]) or None)
        if status != 200:
            note("Post of extension to %s signalled %s -- %s.  Message was:\n%s\n", CONTRIB_URL, status, status_msg, msg)
            fp = response.open('text/plain')
            fp.write("Post of extension to %s signalled %s -- %s.  Message was:\n%s\n" % (CONTRIB_URL, status, status_msg, msg))
            fp.close()
        else:
            response.redirect('ext_list#%s' % os.path.basename(base))

    finally:
        if tfname:
            os.unlink(tfname)

def extlib_showlib (repo, response, params):

    """List extensions available in the Library.  Indicate date, author, version, and docs."""
    
    global CONTRIB_URL, EXTENSIONS_SERVERS_CA_CERTS
    global SITE_EXTENSIONS

    if not SITE_EXTENSIONS or not CONTRIB_URL:
        conf = configurator.default_configurator()
        if not SITE_EXTENSIONS:
            uplib_lib = conf.get('uplib-lib')
            SITE_EXTENSIONS = os.path.join(uplib_lib, 'site-extensions')

        if CONTRIB_URL == None:
            # initialize contrib-url from site.config
            CONTRIB_URL = conf.get('extensions-library-url')
            if not CONTRIB_URL:
                response.error(HTTPCodes.BAD_REQUEST, "No Extensions Library URL available.")
                return
        if EXTENSIONS_SERVERS_CA_CERTS is None:
            EXTENSIONS_SERVERS_CA_CERTS = conf.get("extensions-sites-ca-certs-file")

    host, port, path = parse_URL(CONTRIB_URL)

    certs = _extlib_checksite(repo, CONTRIB_URL)

    try:
        status, status_msg, headers, msg = https_post_multipart(host, port, None, "/list", [], [],
                                                                ca_certs=EXTENSIONS_SERVERS_CA_CERTS,
                                                                certfile=(certs and certs[1]) or None)
    except socket.error:
        msg = ''.join(traceback.format_exception(*sys.exc_info()))
        note("Exception signalled connecting to %s:\n%s", CONTRIB_URL, msg)
        fp = response.open('text/plain')
        fp.write("Exception connecting to %s:\n%s\n" % (CONTRIB_URL, msg))
        fp.close()
        return
        
    modules = []
    if status != 200:
        note("Post of extension to %s signalled %s -- %s.  Message was:\n%s\n", CONTRIB_URL, status, status_msg, msg)
        fp = response.open('text/plain')
        fp.write("Post of extension to %s signalled %s -- %s.  Message was:\n%s\n" % (CONTRIB_URL, status, status_msg, msg))
        fp.close()
        return
    elif len(msg) == 0:
        # no modules
        pass
    else:
        # zipfile
        z = zipfile.ZipFile(StringIO(msg), 'r')
        for entry in z.infolist():
            metadata = read_metadata(StringIO(zlib.decompress(z.read(entry.filename))))
            metadata["name"] = entry.filename.split('/')[0]
            modules.append(metadata)
        #note("modules are %s", modules)
        modules.sort(lambda m1, m2: cmp(m1.get("name"), m2.get("name")))

    # return an HTML view of the documents in the collection

    fp = response.open()
    if certs:
        title = "Extensions Available for Download"
    else:
        title = "Extensions in %s" % CONTRIB_URL

    __beginpage(fp, title)
    fp.write('<body bgcolor="%s">\n' % LIBRARY_BACKGROUND_COLOR)

    fp.write('<p><table width=100%% bgcolor="%s"><tr><td>' % LIBRARY_FRAME_COLOR +
             '<font color=white><center><h1>%s</h1></center></font></td></tr></table>\n' % htmlescape(title))
    fp.write('<p>The following UpLib extensions' +
             ' are available for download from the library at<br>%s.' % htmlescape(CONTRIB_URL))
    if certs:
        fp.write('<p>Click on the button labelled "Install in \'%s\'" to install '
                 'any of them in the repository.' % htmlescape(repo.name()))
        fp.write('<p>Note that if you install any of them, that installation will only '
                 'be for this repository (%s).\n' % htmlescape(repo.name()))
        fp.write('If you want them to be present in any other repositories, '
                 'you must either install them separately in each of those repositories, '
                 'install them in the site-local extensions directory (%s), '
                 'or add a directory to the <i>extensions-path</i> of each repository, '
                 'and copy them to that directory (not recommended).' % htmlescape(SITE_EXTENSIONS))

    elif _have_ssl and EXTENSIONS_SERVERS_CA_CERTS and os.path.exists(EXTENSIONS_SERVERS_CA_CERTS):
        identity = _extlib_get_server_identity(CONTRIB_URL)
        fp.write('<p><font color=red>Remember that extensions run as you, on your machine, '
                 'and can do anything you can do on that machine.</font><br>Be very careful '
                 'about what you install.</p>\n')
        fp.write('<p>This extensions site has not been certified by you as a trusted source '
                 'of extensions.  It runs with a certificate which identifies it as the '
                 'following:<br>\n<pre>%s</pre>\n' % htmlescape(pprint.pformat(identity)))
        fp.write('<p>This identification has been verified against the root certificates in '
                 '<tt>%s</tt>.\n' % htmlescape(EXTENSIONS_SERVERS_CA_CERTS))
        fp.write('<form action="extlib_allowsite" method=get name=allowsite enctype="multipart/form-data">\n')
        fp.write('<input type=hidden name="url" value="%s">\n' % htmlescape(CONTRIB_URL, True))
        fp.write('To certify this repository as a source of trusted extensions for this '
                 'repository, press this button: ')
        fp.write('<input type=submit name="Certify Site" value="Certify Site"></form>\n<hr>\n')

    else:
        if not _have_ssl:
            fp.write('<p><font color=red>You must have the SSL module installed in your Python on this '
                     'machine to download extensions from extensions sites.</font>')
        elif not EXTENSIONS_SERVERS_CA_CERTS:
            fp.write('<p><font color=red>You must have a file containing CA certs to validate the '
                     'the certificate from the extension site.</font>  Right now, you have no such file, so '
                     'you will be unable to install any extension from this site (or any other site).  The value of '
                     '<tt>extensions-sites-ca-certs-file</tt> in your site.config file, '
                     'or your <tt>~/.uplibrc</tt> file, '
                     'should be set to the full pathname of the file containing the CA certs '
                     '(as a concatenation of PEM-format certificates).')
        elif not os.path.exists(EXTENSIONS_SERVERS_CA_CERTS):
            fp.write('<p><font color=red>You must have a file containing CA certs to validate the '
                     'the certificate from the extension site.  You have specified '
                     '<tt>%s</tt> as this file, but it doesn\'t exist.' % htmlescape(EXTENSIONS_SERVERS_CA_CERTS))

    fp.write('<p>')

    if modules:

        for md in modules:
            name = md.get("name")
            date = md.get("date")
            author = md.get("author")
            version = md.get("version")
            description = md.get("description")
            url = md.get("url")
            if url == "0":
                url = None
            inits = figure_inits(md)
            min_uplib_version = md.get("uplib-min-version")
            show_extension(fp, md, 'library', repo.name(), repo.get_version(), not certs)

    else:
        fp.write('<p><table width=100%% bgcolor="%s"><tr><td><font color=white>' % LIBRARY_FRAME_COLOR +
                 'No extensions are registered.</font></td></tr></table>\n')

    __endpage(fp)
    fp.close()
    

def extlib_showcode (repo, response, params):

    """Show the code file of an extension in the library.  If a multifile directory, show list of subfiles."""
    
    global CONTRIB_URL
    global SITE_EXTENSIONS

    if not SITE_EXTENSIONS or not CONTRIB_URL:
        conf = configurator.default_configurator()
        if not SITE_EXTENSIONS:
            uplib_lib = conf.get('uplib-lib')
            SITE_EXTENSIONS = os.path.join(uplib_lib, 'site-extensions')

        if CONTRIB_URL == None:
            # initialize contrib-url from site.config
            CONTRIB_URL = conf.get('extensions-library-url')
            if not CONTRIB_URL:
                response.error(HTTPCodes.BAD_REQUEST, "No Extensions Library URL available.")
                return

    host, port, path = parse_URL(CONTRIB_URL)

    extname = params.get('extname')
    version = params.get('version')
    if not extname:
        response.error(HTTPCodes.BAD_REQUEST, "No 'extname' parameter specified, so no way to know which extension to display.")
        return

    p = [('name', extname),
         ('code', "true") ]
    if version:
        p.append(('version', version))
    filename = params.get('filename')
    if filename:
        p.append(('subfile', filename))

    certs = _extlib_checksite(repo, CONTRIB_URL)
    status, status_msg, headers, msg = https_post_multipart(host, port, None, "/get", p, [],
                                                            ca_certs=EXTENSIONS_SERVERS_CA_CERTS,
                                                            certfile=(certs and certs[1]) or None)

    if status != 200:
        note("Request for file to %s signalled %s -- %s.  Message was:\n%s\n", CONTRIB_URL, status, status_msg, msg)
        fp = response.open('text/plain')
        fp.write("Request for file to %s signalled %s -- %s.  Message was:\n%s\n" % (CONTRIB_URL, status, status_msg, msg))
        fp.close()
        return
    else:
        # multiple packings here; might be multiple zipfiles, one for each extension, inside an outer zipfile
        # so, first get the extension's code zipfile
        z = zipfile.ZipFile(StringIO(msg))
        f = z.infolist()
        #note("outer f for '%s' is %s", extname, f)
        d = z.read(f[0].filename)
        z.close()
        # now read the code out of that zipfile
        z = zipfile.ZipFile(StringIO(d))
        f = z.infolist()
        #note("inner f for '%s' is %s", extname, f)
        if len(f) > 1:
            # multipart file, following lines are in HTML
            #note("Got multipart back for %s %s -- length %s", extname, f, len(f))
            fp = response.open()
            __beginpage(fp, 'Extension "%s", version %s' % (extname, version))
            fp.write('<body bgcolor="%s"><!-- \n-->' % LIBRARY_BACKGROUND_COLOR)
            fp.write('<table width=100%% bgcolor="%s"><tr><td><font color=white><!--\n-->' % LIBRARY_FRAME_COLOR)
            fp.write('<b>Extension "%s", version %s</b>' % (htmlescape(extname), htmlescape(version)))
            fp.write('</font></td><td align=right><font color=white>(in Library)</font></td></tr></table><p>\n')
            for part in f:
                fp.write('<p><b>%s</b>:<br><pre>\n' % htmlescape(part.filename))
                if part.filename.endswith(".py") or part.filename.endswith(".txt"):
                    fp.write(htmlescape(z.read(part.filename)))
                else:
                    fp.write(' &middot; <i>%d bytes</i>\n' % len(z.read(part.filename)))
                fp.write('</pre></p>\n')
            __endpage(fp)
            fp.close()
            return
        else:
            # single file, lines are contents of file
            #note("Got singlefile back for %s %s -- length %s", extname, (filename or ''), len(msg)-1)
            fp = response.open()
            if filename:
                title = 'Extension "%s", version %s:  %s' % (extname, version, filename)
            else:
                title = 'Extension "%s", version %s' % (extname, version)
            __beginpage(fp, title)
            fp.write('<body bgcolor="%s"><!-- \n-->' % LIBRARY_BACKGROUND_COLOR)
            fp.write('<table width=100%% bgcolor="%s"><tr><td><font color=white><!--\n-->' % LIBRARY_FRAME_COLOR)
            if filename:
                fp.write('<b>Extension "%s", version %s:  %s</b><!-- \n-->' % (htmlescape(extname), htmlescape(version), htmlescape(filename)))
            else:
                fp.write('<b>Extension "%s", version %s</b><!-- \n-->' % (htmlescape(extname), htmlescape(version)))
            fp.write('</font></td><td align=right><font color=white>(in Library)</font></td></tr></table><p><pre>\n')
            fp.write(htmlescape(z.read(f[0].filename)))
            fp.write('</pre>\n')
            __endpage(fp)
            fp.close()
            return

eview_actions = {
    'ext_list': ext_list,

    'ext_deletefile' : ext_deletefile,
    'ext_activate': ext_activate,
    'ext_deactivate': ext_deactivate,
    'ext_editinfo': ext_editinfo,
    'ext_showcode': ext_showcode,

    'extlib_upload': extlib_upload,
    'extlib_showlib' : extlib_showlib,
    'extlib_download': extlib_download,
    'extlib_showcode' : extlib_showcode,
    'extlib_allowsite' : extlib_allowsite,

    'extpath_deletedir': extpath_deletedir,
    'extpath_promotedir': extpath_promotedir,
    'extpath_adddir': extpath_adddir,
    }
