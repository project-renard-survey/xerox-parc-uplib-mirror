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

import sys, os, distutils.sysconfig, shutil

# make sure we can find the PyWin32 extensions
if (len(sys.argv) > 1) and os.path.isdir(sys.argv[1]):
    if os.path.exists(os.path.join(sys.exec_prefix, "python26.dll")):
        # installed privately
        todlldir = sys.exec_prefix
    elif os.path.exists('c:/WINDOWS/system32/python26.dll'):
        todlldir = "C:/WINDOWS/system32"
    else:
        sys.stderr.write("Can't find python26.dll\n")
        sys.exit(1)
    uplib_sc = distutils.sysconfig.get_python_lib(plat_specific=True, prefix=sys.argv[1])
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
    sys.argv[1:2] = []

import win32serviceutil
import win32service
import win32event

# Remove an arbitrary service with the specified name
def removeServiceName(name):
    if (not name.lower().startswith("uplib")):
        sys.stderr.write("Only services beginning with \"Uplib\" will be removed by this program.\n")        
        return

    manH = win32service.OpenSCManager(None,None,win32service.SC_MANAGER_ALL_ACCESS)
    try:
        servH = win32service.OpenService(manH,name,win32service.SERVICE_ALL_ACCESS)
    except:
        sys.stderr.write("No service named "+name+" exists\n")
        return
    
    really = raw_input("Really remove "+name+" service? ")
    if (really.lower() == "y" or really.lower() == "yes"):
        # If the service is running, then we have to stop it first
        if (win32service.QueryServiceStatus(servH)[1] == win32service.SERVICE_RUNNING):
            win32service.ControlService(servH, win32service.SERVICE_CONTROL_STOP)
        win32service.DeleteService(servH)
    
    win32service.CloseServiceHandle(servH)
    win32service.CloseServiceHandle(manH)

    
# Remove the Uplib Service running on the specified port
def removeServiceOnPort(port):
    removeServiceName("UpLibGuardianAngel_"+str(port))

# Remove the Uplib Service whose home is the specfied directory
def removeServiceDirectory(dir):
    portFile = os.path.join(dir,"overhead","stunnel.port")
    if (os.path.exists(portFile)):
        fp = open(portFile,"rb")
        portNo = fp.read()
        fp.close()
        removeServiceOnPort(portNo.strip())

if __name__ == "__main__":
    usage = False
    for arg in sys.argv[1:]:
        if (arg.lower().startswith("--directory=")):
            removeServiceDirectory(arg[len("--directory="):])
        elif (arg.lower().startswith("--port=")):
            removeServiceOnPort(arg[len("--port="):])
        elif (arg.lower().startswith("--name=")):
            removeServiceName(arg[len("--name="):])
        else:
            usage = True

    if (usage or (len(sys.argv) != 2)):
        print "Usage: "+sys.argv[0]+" OPTION"
        print "Where OPTION includes:"
        print "--directory=DIR - The location of an Uplib repository"
        print "--name=NAME - The name of a Windows service"
        print "--port=PORT - The UpLib Repository's Port Number"
