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

import java.io.*;

import java.lang.Class;
import java.lang.reflect.Method;

class testLucene {

    private static boolean compareArgs (Class[] args1, Class[] args2) throws Exception {
        if (args1.length != args2.length)
            return false;
        for (int i = 0;  i < args1.length;  i++) {
            if (args1[i] != args2[i])
                return false;
        }
        return true;
    }

    public static void main(String[] args) {

        try {
            Class thepackage = Class.forName("org.apache.lucene.LucenePackage");
            if (thepackage != null) {
                Method m = thepackage.getDeclaredMethod("get");
                java.lang.Package p = (java.lang.Package) m.invoke(thepackage);
                System.out.println(p.getSpecificationVersion());
                Runtime.getRuntime().exit(0);
            } else {
                System.out.println("no -- null package");
                Runtime.getRuntime().exit(0);
            }
        } catch (Exception e) {
            System.out.println("no");
            e.printStackTrace(System.err);
            Runtime.getRuntime().exit(0);
        }
    }
}
