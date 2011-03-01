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

package com.parc.uplib.readup.widget;

import java.util.*;

public interface Annotation {

    public static class Timestamp extends java.util.Date implements java.io.Serializable {

        public final static int CREATED = 1;
        public final static int MODIFIED = 2;
        public final static int DELETED = 3;

        private int typ;

        public Timestamp (int typ) {
            super();
            this.typ = typ;
        }

        public Timestamp (int typ, long timestamp) {
            super(timestamp);
            this.typ = typ;
        }

        public int getKind () {
            return typ;
        }
    }

    public static class Type {

        public static final Type SCRIBBLE = new Type("Scribble", 0);
        public static final Type NOTE = new Type("Note", 1);
        public static final Type LINK = new Type("Link", 2);
        public static final Type IMAGE = new Type("Image", 3);
        public static final Type TIMESTAMP = new Type("Timestamp", 4);
        public static final Type VSCRIBBLE = new Type("VariableScribble", 5);
        public static final Type ERASURE = new Type("Erasure", 6);
        public static final Type NOTESET = new Type("Noteset", 7);

        private final String name;
        private final int code;

        private Type (String name, int code) {
            this.name = name;
            this.code = code;
        }

        public String toString () {
            return name;
        }

        public int getCode() {
            return code;
        }

        public static Type getTypeForCode (int code) {
            if (code == SCRIBBLE.code)
              return SCRIBBLE;
            else if (code == NOTE.code)
              return NOTE;
            else if (code == LINK.code)
              return LINK;
            else if (code == IMAGE.code)
              return IMAGE;
            else if (code == TIMESTAMP.code)
              return TIMESTAMP;
            else if (code == VSCRIBBLE.code)
              return VSCRIBBLE;
            else if (code == ERASURE.code)
              return ERASURE;
            else
                return null;
        }
    }

    public int pageIndex();
    public String docId();
    public Timestamp timestamp();

    public Type getType ();
    public java.awt.Rectangle getBounds();
};
