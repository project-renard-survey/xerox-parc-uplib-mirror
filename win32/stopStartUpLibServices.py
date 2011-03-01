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

import sys, os, string, traceback, time

import win32serviceutil
import win32service
import win32event

# Stop all uplib services
def stopUplibServices():
    try:
        manH = win32service.OpenSCManager(None,None,win32service.SC_MANAGER_ALL_ACCESS)
        sList = win32service.EnumServicesStatus(manH,win32service.SERVICE_WIN32,win32service.SERVICE_ACTIVE)
        for svc in sList:
            name = svc[0]
            if (name.lower().startswith("uplib")):
                serveH = win32service.OpenService(manH,name,win32service.SERVICE_ALL_ACCESS)
                if (win32service.QueryServiceStatus(serveH)[1] == win32service.SERVICE_RUNNING):
                    win32service.ControlService(serveH, win32service.SERVICE_CONTROL_STOP)

                while (win32service.QueryServiceStatus(serveH)[1] != win32service.SERVICE_STOPPED):
                    time.sleep(5)

                win32service.CloseServiceHandle(serveH)


        win32service.CloseServiceHandle(manH)        
    except:
        t, v, b = sys.exc_info()
        sys.stderr.write("Problem Stopping UpLib Services.  %s."% string.join(traceback.format_exception(t, v, b)))


# Start all uplib services
def startUplibServices():
    try:
        manH = win32service.OpenSCManager(None,None,win32service.SC_MANAGER_ALL_ACCESS)
        sList = win32service.EnumServicesStatus(manH,win32service.SERVICE_WIN32,win32service.SERVICE_INACTIVE)
        for svc in sList:
            name = svc[0]
            if (name.lower().startswith("uplib")):
                serveH = win32service.OpenService(manH,name,win32service.SERVICE_ALL_ACCESS)
                
                if (win32service.QueryServiceStatus(serveH)[1] == win32service.SERVICE_STOPPED and win32service.QueryServiceConfig(serveH)[1] == win32service.SERVICE_AUTO_START):
                    win32service.StartService(serveH, None)
                win32service.CloseServiceHandle(serveH)

        win32service.CloseServiceHandle(manH)        
    except:
        t, v, b = sys.exc_info()
        sys.stderr.write("Problem Starting UpLib Services.  %s."% string.join(traceback.format_exception(t, v, b)))
    
if __name__ == "__main__":
    usage = False
    if (len(sys.argv) == 2):
        if (sys.argv[1].lower() == "stop"):
            stopUplibServices()
        elif (sys.argv[1].lower() == "start"):
            startUplibServices()
        else:
            usage = True
    else:         
        usage = True

    if (usage):
        print "Usage: "+sys.argv[0]+" OPTION"
        print "Where OPTION includes:"
        print "stop - Stop All UpLib services"
        print "start - Start All UpLib services"
