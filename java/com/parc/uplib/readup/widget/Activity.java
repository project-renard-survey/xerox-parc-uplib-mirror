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

import java.io.*;
import java.util.*;
import java.util.regex.*;
import java.awt.event.*;
import java.awt.image.*;
import java.awt.geom.*;
import java.awt.*;
import java.awt.datatransfer.*;
import javax.swing.*;
import javax.swing.event.*;
import javax.swing.text.*;
import javax.swing.border.*;
import javax.imageio.*;

/**
   This class is the encapsulation of an timestamped activity log entry
   for the document reader.  As new activities are defined/encountered,
   additional activity codes and toString() clauses should be added to this
   class.
*/
public class Activity {

    /**
       The document this activity has been invoked on.
    */
    public String doc_id;

    /**
       The page the reader was open to when the activity was invoked.
       May also be the page that the activity was invoked on, if
       that is appropriate.
    */
    public int page_index;

    /**
       The time when the activity was invoked.
    */
    public Date timestamp;

    /**
       A code identifying the type of the activity.
    */
    public int activity_code;

    /**
       Any additional information about the activity.  In version 1 of this
       class, only a maximum of 255 bytes are allowed.
    */
    public byte[] extension_bytes;

    public static final int AC_PAGE_TURNED = 1;        /* page_index should be new page turned to */
    public static final int AC_SCRIBBLED = 2;
    public static final int AC_HOTSPOT_CLICKED = 3;
    public static final int AC_THUMBNAILS_OPENED = 4;  /* went to thumbnails view */
    public static final int AC_THUMBNAILS_CLOSED = 5;  /* went to pages view */
    public static final int AC_OPENED_DOC = 6;         /* called once when the first page is exposed */
    public static final int AC_CLOSED_DOC = 7;         /* called when document is closed */
    public static final int AC_ANNOTATIONS_ON = 8;
    public static final int AC_ANNOTATIONS_OFF = 9;
    public static final int AC_INK_SELECTED = 10;
    public static final int AC_BOOKMARK_SET = 11;
    public static final int AC_BOOKMARK_UNSET = 12;
    public static final int AC_BOOKMARK_USED = 13;
    public static final int AC_HOTSPOTS_ON = 14;
    public static final int AC_HOTSPOTS_OFF = 15;
    public static final int AC_ADH_ON = 16;
    public static final int AC_RSVP_ON = 17;
    public static final int AC_RSVP_OFF = 18;
    public static final int AC_ADH_SPEED_UP = 19;
    public static final int AC_ADH_SLOW_DOWN = 20;
    public static final int AC_ADH_JUMP_TO = 21;
    public static final int AC_ADH_OFF = 22;
    public static final int AC_ZOOMED_IN = 23;
    public static final int AC_ZOOMED_OUT = 24;

    public Activity (String doc_id_p, int page_index_p, int activity_code_p) {
        doc_id = doc_id_p;
        page_index = page_index_p;
        timestamp = new Date();
        activity_code = activity_code_p;
        extension_bytes = null;
    }

    public Activity (String doc_id_p, int page_index_p, int activity_code_p, byte[] extensions) {
        doc_id = doc_id_p;
        page_index = page_index_p;
        timestamp = new Date();
        activity_code = activity_code_p;
        extension_bytes = extensions;
    }

    public String toString () {
        String action_name = null;

        if (activity_code == AC_THUMBNAILS_OPENED)
            action_name = "THUMBNAILS_OPENED";
        else if (activity_code == AC_THUMBNAILS_CLOSED)
            action_name = "THUMBNAILS_CLOSED";
        else if (activity_code == AC_PAGE_TURNED)
            action_name = "PAGE_TURNED";
        else if (activity_code == AC_SCRIBBLED)
            action_name = "SCRIBBLED";
        else if (activity_code == AC_HOTSPOT_CLICKED)
            action_name = "HOTSPOT_CLICKED";
        else if (activity_code == AC_OPENED_DOC)
            action_name = "OPENED";
        else if (activity_code == AC_CLOSED_DOC)
            action_name = "CLOSED";
        else if (activity_code == AC_ANNOTATIONS_ON)
            action_name = "ANNOTATIONS_ON";
        else if (activity_code == AC_ANNOTATIONS_OFF)
            action_name = "ANNOTATIONS_OFF";
        else if (activity_code == AC_INK_SELECTED)
            action_name = "INK_SELECTED";
        else if (activity_code == AC_BOOKMARK_SET)
            action_name = "BOOKMARK_SET";
        else if (activity_code == AC_BOOKMARK_UNSET)
            action_name = "BOOKMARK_UNSET";
        else if (activity_code == AC_BOOKMARK_USED)
            action_name = "BOOKMARK_USED";
        else if (activity_code == AC_HOTSPOTS_ON)
            action_name = "HOTSPOTS_ON";
        else if (activity_code == AC_HOTSPOTS_OFF)
            action_name = "HOTSPOTS_OFF";
        else if (activity_code == AC_ZOOMED_IN)
            action_name = "ZOOMED_IN";
        else if (activity_code == AC_ZOOMED_OUT)
            action_name = "ZOOMED_OUT";
        else
            action_name = "UNKNOWN";
        return "<Activity " + doc_id + "/" + page_index + ": " + action_name + "@" + timestamp.toString() + ">";
    }
}

