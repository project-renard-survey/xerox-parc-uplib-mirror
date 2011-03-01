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

import java.io.File;
import java.io.IOException;
import java.net.URLDecoder;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import javax.swing.JOptionPane;
import java.util.Arrays;

/**
 * Derived from the public domain code called "Bare Bones Browser Launch for Java"
 * at http://www.centerkey.com/java/browser/, version 3, 2/7/2010
 * Author: Dem Pilafian<br>
 */
public class BrowserLauncher {

    static final String[] linux_browsers = { "firefox", "opera", "konqueror", "google-chrome",
                                             "epiphany", "seamonkey", "galeon", "kazehakase", "mozilla" };
    static final String errMsg = "Error attempting to launch web browser";

    /**
     * Opens the specified web page in the user's default browser
     * @param url A web address (URL) of a web page (ex: "http://www.google.com/")
     */
    public static void openURL(String url) throws Exception {
        try {  //attempt to use Desktop library from JDK 1.6+ (even if on 1.5)
            Class<?> d = Class.forName("java.awt.Desktop");
            d.getDeclaredMethod("browse", new Class[] {java.net.URI.class}).invoke
                (d.getDeclaredMethod("getDesktop").invoke(null),
                 new Object[] {java.net.URI.create(url)});
            //above code mimics Java 6 invocation:
            //   java.awt.Desktop.getDesktop().browse(java.net.URI.create(url));
        }
        catch (Exception ignore) {  //library not available or failed
            String osName = System.getProperty("os.name");
            if (osName.startsWith("Mac OS")) {
                Class.forName("com.apple.eio.FileManager").getDeclaredMethod
                    ("openURL", new Class[] {String.class}).invoke(null, new Object[] {url});
            }
            else if (osName.startsWith("Windows"))
                Runtime.getRuntime().exec(
                                          "rundll32 url.dll,FileProtocolHandler " + url);
            else { //assume Unix or Linux
                boolean found = false;
                for (String browser : linux_browsers)
                    if (!found) {
                        found = Runtime.getRuntime().exec
                            (new String[] {"which", browser}).waitFor() == 0;
                        if (found)
                            Runtime.getRuntime().exec(new String[] {browser, url});
                    }
                if (!found)
                    throw new Exception("Can't find any of " + Arrays.toString(linux_browsers));
            }
        }
    }
}
