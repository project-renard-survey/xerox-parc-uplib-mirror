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

import java.util.logging.*;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

public class LogStackTrace {

    private static String produceLogMsg (Exception t) {
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        t.printStackTrace(new PrintStream(b, true));
        try {
            return b.toString("UTF-8");
        } catch (java.io.UnsupportedEncodingException x) {
            // won't happen
            return null;
        }
    }

    public static void info (Logger l, Exception t) {
        l.info(produceLogMsg(t));
    }

    public static void warning (Logger l, Exception t) {
        l.warning(produceLogMsg(t));
    }

    public static void severe (Logger l, Exception t) {
        l.severe(produceLogMsg(t));
    }

    public static void info (Logger l, String msg, Exception t) {
        l.info(msg + "\n" + produceLogMsg(t));
    }

    public static void warning (Logger l, String msg, Exception t) {
        l.warning(msg + "\n" + produceLogMsg(t));
    }

    public static void severe (Logger l, String msg, Exception t) {
        l.severe(msg + "\n" + produceLogMsg(t));
    }
}
