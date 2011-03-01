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
"""
Adds DocumentParser for vCard format, which is our standard representation
for address book entries.

:author: Bill Janssen
"""
__docformat__ = "restructuredtext"
__version__ = "$Revision: 1.12 $"

# see RFC 2425 and 2426

try:
    from parser import vCards, add_vcards_file
except ImportError:
    pass

def after_repository_instantiation(repo):
    from uplib.addDocument import CONTENT_TYPES
    import mimetypes
    CONTENT_TYPES["text/x-vcard"] = "vcf"
    mimetypes.add_type("text/x-vcard", ".vcf")
