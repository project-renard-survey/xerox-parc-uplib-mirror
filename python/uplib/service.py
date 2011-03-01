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

#
# papers over differences between Medusa and Tornado and any other server framework
# we may use in the future, like Twisted
#

import sys, os, re

from uplib.plibUtil import configurator

conf = configurator.default_configurator()
service_framework = conf.get("service-framework")
if service_framework == "Medusa":
    from uplib.angelHandler import ForkRequestInNewThread, run_fn_in_new_thread
    from uplib.startAngel import darwin_launchd, daemon, unix_mainloop, start_angel

    def set_top_level_action(handler):
        if not isinstance(handler, tuple) or (len(handler) != 2):
            raise RuntimeError("toplevel handler must be tuple of ('MODULENAME', 'FUNCTIONNAME')")
        import uplib.angelHandler
        setattr(uplib.angelHandler, "TOP_LEVEL_ACTION", handler)

elif service_framework == "Tornado":
    from uplib.tornadoHandler import ForkRequestInNewThread, run_fn_in_new_thread
    from uplib.startTornado import darwin_launchd, daemon, unix_mainloop, start_angel

    def set_top_level_action(handler):
        if not isinstance(handler, tuple) or (len(handler) != 2):
            raise RuntimeError("toplevel handler must be tuple of ('MODULENAME', 'FUNCTIONNAME')")
        import uplib.tornadoHandler
        setattr(uplib.tornadoHandler, "TOP_LEVEL_ACTION", handler)

else:
    raise RuntimeError("Invalid option '%s' specified for service-framework" % service_framework)
