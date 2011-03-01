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

import java.io.IOException;

/**
 * This interface is used to fetch an instance of some resource -- a
 * PageText object, a page thumbnail, whatever, from storage.
 */
public interface ResourceLoader {

    public class TemporaryFailure extends IOException {
        public TemporaryFailure (String msg) {
            super(msg);
        }
    };
    public class PrivilegeViolation extends IOException {
        public PrivilegeViolation (String msg) {
            super(msg);
        }
    };
    public class CommunicationFailure extends TemporaryFailure {
        public CommunicationFailure (String msg) {
            super(msg);
        }
    };
    public class ResourceNotFound extends IOException {
        public ResourceNotFound (String msg) {
        }
    }
    public class ResourceTooLarge extends IOException {
        int maxsize;
        public ResourceTooLarge (String msg, int size) {
            maxsize = size;
        }
    }

    public Object getResource(String document_id, int pageno, int selector) throws IOException;
}

