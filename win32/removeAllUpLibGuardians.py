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

import sys, os, time, string, traceback, distutils.sysconfig, shutil

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

import win32serviceutil
import win32service
import win32event

# Remove an arbitrary service with the specified name
def removeAllUpLibGuardians():
    manH = win32service.OpenSCManager(None,None,win32service.SC_MANAGER_ALL_ACCESS)

    try:
        sStats = win32service.EnumServicesStatus(manH)
        for i in range(len(sStats)):
            if sStats[i][0].lower().startswith("uplibguardian"):
                servH = win32service.OpenService(manH,sStats[i][0],win32service.SERVICE_ALL_ACCESS)
                
                # If the service is running, then we have to stop it first
                if (win32service.QueryServiceStatus(servH)[1] == win32service.SERVICE_RUNNING):
                    win32service.ControlService(servH, win32service.SERVICE_CONTROL_STOP)

                while (win32service.QueryServiceStatus(servH)[1] != win32service.SERVICE_STOPPED):
                    time.sleep(5)
                    
                win32service.DeleteService(servH)
                win32service.CloseServiceHandle(servH)                
    except:
        t, v, b = sys.exc_info()        
        sys.stderr.write("Problem accessing UpLib service\n"+string.join(traceback.format_exception(t, v, b)))
        return 0

    
    win32service.CloseServiceHandle(manH)


if __name__ == "__main__":
    removeAllUpLibGuardians()
