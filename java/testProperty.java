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

class testProperty {

    public static void main(String[] args) {

        try {
            System.out.println(System.getProperty(args[0]));
            Runtime.getRuntime().exit(0);
        } catch (Exception x) {
            System.out.println("1");
            Runtime.getRuntime().exit(1);
        }
    };
}