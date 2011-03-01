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

import sys, os

import string, traceback, time
import win32serviceutil
import win32service
import win32event

# Remove an arbitrary service with the specified name
def restartServiceName(name):
    if (not name.lower().startswith("uplib")):
        sys.stderr.write("Only services beginning with \"Uplib\" will be restarted by this program.\n")        
        return

    manH = win32service.OpenSCManager(None,None,win32service.SC_MANAGER_ALL_ACCESS)
    try:
        servH = win32service.OpenService(manH,name,win32service.SERVICE_ALL_ACCESS)
    except:
        sys.stderr.write("No service named "+name+" exists\n")
        return

    try:

        if (win32service.QueryServiceStatus(servH)[1] == win32service.SERVICE_RUNNING):
            win32service.ControlService(servH, win32service.SERVICE_CONTROL_STOP)
            
        while (win32service.QueryServiceStatus(servH)[1] != win32service.SERVICE_STOPPED):
            time.sleep(5)

        win32service.StartService(servH, None)
    except:
        t, v, b = sys.exc_info()
        sys.stderr.write("Can't restart Windows service.  %s."% string.join(traceback.format_exception(t, v, b)))


    win32service.CloseServiceHandle(servH)
    win32service.CloseServiceHandle(manH)

    
# Remove the Uplib Service running on the specified port
def restartServiceOnPort(port):
    restartServiceName("UpLibGuardianAngel_"+str(port))

# Remove the Uplib Service whose home is the specfied directory
def restartServiceDirectory(dir):
    portFile = os.path.join(dir,"overhead","stunnel.port")
    if (os.path.exists(portFile)):
        fp = open(portFile,"rb")
        portNo = fp.read()
        fp.close()
        restartServiceOnPort(portNo.strip())

if __name__ == "__main__":
    usage = False
    for arg in sys.argv[1:]:
        if (arg.lower().startswith("--directory=")):
            restartServiceDirectory(arg[len("--directory="):])
        elif (arg.lower().startswith("--port=")):
            restartServiceOnPort(arg[len("--port="):])
        elif (arg.lower().startswith("--name=")):
            restartServiceName(arg[len("--name="):])
        else:
            usage = True

    if (usage or (len(sys.argv) != 2)):
        print "Usage: "+sys.argv[0]+" OPTION"
        print "Where OPTION includes:"
        print "--directory=DIR - The location of an Uplib repository"
        print "--name=NAME - The name of a Windows service"
        print "--port=PORT - The UpLib Repository's Port Number"
