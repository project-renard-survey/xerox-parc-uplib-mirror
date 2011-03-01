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

import socket, sys, os, tempfile, urllib

def find_unused_port(family=socket.AF_INET, socktype=socket.SOCK_STREAM, host="127.0.0.1"):
    tempsock = socket.socket(family, socktype)
    tempsock.bind((host, 0))
    port = tempsock.getsockname()[1]
    tempsock.close()
    del tempsock
    return port

def setup_uplib(uplib_home, uplib_version):
    uplib_lib = os.path.join(uplib_home, "lib", "UpLib-%s" % uplib_version)
    if not os.path.isdir(uplib_lib):
        sys.stderr.write("Can't find UpLib lib dir at %s.\n" % uplib_lib)
        return False
    os.environ["PATH"] = os.path.join(uplib_home, "bin") + ":" + os.environ["PATH"]
    os.environ["UPLIB_LIB"] = uplib_lib
    sys.path.insert(0, os.path.join(uplib_home, "share", "UpLib-%s" % uplib_version, "code"))
    return True

def setup_uplibrc(settings):

    if os.environ.has_key("UPLIBRC"):
        from uplib.plibUtil import configurator
        conf = configurator(filename=os.environ.get("UPLIBRC"))
        default_settings = dict(conf.dump().get("default"))
        #sys.stderr.write("default_settings are %s\n" % str(default_settings))
        #sys.stderr.write("settings are %s\n" % str(settings))
        default_settings.update(settings)
        settings = default_settings
        #sys.stderr.write("updated settings are %s\n" % str(settings))

    tconffile = tempfile.mktemp()
    fp = open(tconffile, "w")
    fp.write("[default]\n")
    for name, value in settings.items():
        fp.write("%s: %s\n" % (name, value))
    fp.close()
    os.environ["UPLIBRC"] = tconffile

def topdf_available_p (conf=None):
    if conf is None:
        from uplib.plibUtil import configurator
        conf = configurator()
    topdf_port = conf.get_int("topdf-port")
    topdf_host = conf.get("topdf-binding-ip-address") or "127.0.0.1"
    if topdf_port > 0:
        # see if it's running
        url = "http://%s:%s/ping" % (topdf_host, topdf_port)
        try:
            response = urllib.urlopen(url).read()
        except:
            return topdf_host, topdf_port, []
        else:
            return topdf_host, topdf_port, response.strip().split()
    else:
        return topdf_host, topdf_port, []


def use_topdf(settings):

    topdf_host, topdf_port, capabilities = topdf_available_p()

    if sys.platform == "darwin":
        settings["wkpdf"] = ""                      # can't use this directly -- window server issues
        settings["wkhtmltopdf"] = ""                # ditto
        settings["soffice"] = ""                    # ditto
        settings["use-openoffice-for-web-page-to-pdf"] = "false"
        settings["use-openoffice-for-msoffice-to-pdf"] = "false"

    if topdf_port > 0:
        if capabilities:
            settings["push-documents-to-topdf-service"] = "true"
            settings["use-topdf-service-for-msoffice-to-pdf"] = "true" if ("office" in capabilities) else "false"
            settings["use-topdf-service-for-web-page-to-pdf"] = "true" if ("office" in capabilities) else "false"
            settings["topdf-port"] = topdf_port
            settings["topdf-binding-ip-address"] = topdf_host
            return True
        else:
            settings["use-topdf-service-for-msoffice-to-pdf"] = "false"
            settings["use-topdf-service-for-web-page-to-pdf"] = "false"
            settings["topdf-port"] = "-1"
            return False
    else:
        return False

        
