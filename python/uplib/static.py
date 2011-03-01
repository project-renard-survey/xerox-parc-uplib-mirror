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
# static.py
#

import string

"""Namespaces for static variables to provide thread-safe global access.

Contains a function _get() for getting or creating new namespaces
and also serves as a place to store the namespaces themselves.  Even
though the namespaces can be imported anywhere and appear global, they
are thread-safe because they are internally indexed by thread ID.

To create a namespace:

    import static
    g = static._get('g')

To use it later in any module:

    from static import g
    g.foo = 3
    print g.bar

Namespace instances (such as 'g' in the example) can also be treated
as dictionaries: g.foo and g['foo'] are equivalent.  The keys(), values()
and items() methods are all available as well."""


from uplib.plibUtil import uthread
_ident = uthread.get_ident              # import just one private name
del uthread

class _Namespace:
    """A dictionary of static variables specific to the current thread.
    Implemented as a dictionary of dictionaries indexed by thread ID.
    Behaves like both a dictionary and an attributed object for convenience."""

    def __repr__(self):
        if self.__dict__.has_key(_ident()):
            return '<namespace ' + repr(self.__dict__[_ident()]) + '>'
        else:
            return '<namespace {}>'

    # pickle/unpickle only the current thread's view of the namespace

    def __getstate__(self):
        try: return self.__dict__[_ident()]
        except KeyError: return {}

    def __setstate__(self, dict):
        self.__dict__[_ident()] = dict

    # translate KeyErrors to AttributeErrors so pickle works properly

    def __getattr__(self, key):
        try: return self.__dict__[_ident()][key]
        except KeyError: raise AttributeError, key
    
    def __setattr__(self, key, value):
        if not self.__dict__.has_key(_ident()):
            self.__dict__[_ident()] = {}
        self.__dict__[_ident()][key] = value

    def __delattr__(self, key):
        try: del self.__dict__[_ident()][key]
        except KeyError: raise AttributeError, key

    # for convenience, also behave like a dictionary

    def __getitem__(self, key):
        try: return self.__dict__[_ident()][key]
        except KeyError: raise KeyError, key

    __setitem__ = __setattr__          # hopefully no exceptions to worry about

    def __delitem__(self, key):
        try: del self.__dict__[_ident()][key]
        except KeyError: raise KeyError, key

    def has_key(self, key):
        if not self.__dict__.has_key(_ident()): return 0
        return self.__dict__[_ident()].has_key(key)

    def keys(self):
        if not self.__dict__.has_key(_ident()): return []
        return self.__dict__[_ident()].keys()

    def values(self):
        if not self.__dict__.has_key(_ident()): return []
        return self.__dict__[_ident()].values()

    def items(self):
        if not self.__dict__.has_key(_ident()): return []
        return self.__dict__[_ident()].items()

    # for getting a value which may not be set

    def get(self, key, default):
        try: return self.__dict__[_ident()][key]
        except KeyError: return default

    # for clearing out the namespace

    def clear(self):
        if self.__dict__.has_key(_ident()):
            del self.__dict__[_ident()]
        self.__dict__[_ident()] = {}
        return self

def _get(name):
    """Get a particular static namespace by name."""

    if name[:1] == '_':                          # prevent collisions
        raise ValueError, "'%s' is not an allowed name for a namespace" % name

    import sys
    module = sys.modules[__name__]               # get this module
    if not hasattr(module, name):
        setattr(module, name, _Namespace())      # create new in this module
    return getattr(module, name)

def _put(name, value):
    """Store a dictionary as a namespace in this module."""

    if name[:1] == '_':
        raise ValueError, "'%s' is not an allowed name for a namespace" % name

    ns = _get(name)
    if hasattr(value, '__getstate__'):
        ns.__setstate__(value.__getstate__())
    else:
        ns.__setstate__(value)
    return ns

stop_dict = {"JAVA_ENABLED": 1, "JAVASCRIPT_ENABLED": 1, "thispage": 1, "WW_NEXT_PAGE": 1, "thispage": 1, "lastpage": 1, "buttonName": 1, "nextpage": 1, "complete": 1, "ww_status": 1, "ww_status_len": 1, "action": 1, "needsRefresh": 1, "auth_username": 1, "auth_password": 1, "auth_domain": 1, "auth_doccom_uid": 1}

def namespace_to_hidden_fields(space):
    for key, val in space.items():
        if stop_dict.has_key(key) or string.find(key, ".x")!=-1 or string.find(key, ".y")!=-1:
            continue
        if type(val)==type([]):
            for sub_val in val:
                print '<input type="hidden" name="%s" value="%s">' % (key, sub_val)
        else:
            print '<input type="hidden" name="%s" value="%s">' % (key, val)

    
