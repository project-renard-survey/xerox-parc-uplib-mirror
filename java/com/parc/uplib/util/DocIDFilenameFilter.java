/*
  This file is part of the "UpLib 1.7.11" release.
  Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
  
  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*/

package com.parc.uplib.util;

import java.util.regex.Pattern;
import java.util.regex.Matcher;

public class DocIDFilenameFilter implements java.io.FilenameFilter {

    private static String ID_PATTERN = "[0-9]{5}-[0-9]{2}-[0-9]{4}-[0-9]{3}";
    private Matcher pattern = null;

    public DocIDFilenameFilter () {
        // note that this isn't thread-safe.  Each thread should create its
        // own instance of DocIDFilenameFilter.
        pattern = Pattern.compile(ID_PATTERN).matcher("");
    }

    public boolean accept (java.io.File dir, String name) {
        pattern.reset(name);
        return pattern.matches();
    }
}



