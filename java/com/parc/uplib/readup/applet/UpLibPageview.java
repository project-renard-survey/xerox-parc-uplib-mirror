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

package com.parc.uplib.readup.applet;

import javax.swing.JApplet;
import java.applet.*;
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
import java.net.*;
import java.lang.reflect.Method;

import com.parc.uplib.readup.widget.*;
import com.parc.uplib.readup.uplibbinding.*;

public class UpLibPageview extends JApplet {

    final static Color LEGEND_COLOR = new Color(.602f, .676f, .726f);
    final static Color DARK_COLOR = new Color(.439f, .475f, .490f);

    private String image_directory;
    private String document_title;
    private String document_id;
    private String page_numbers;
    private DocViewerCallback logo_url;
    private int page_count;
    private int first_page_number;
    private int current_page;
    private int selection_start;
    private int selection_end;
    private int page_width;
    private int page_height;
    private int thumbnail_width;
    private int thumbnail_height;
    private boolean show_controls;
    private boolean show_edge;
    private boolean show_two_pages;
    private boolean show_annotations;
    private boolean show_active_reading = false;
    private boolean show_rsvp = false;
    private boolean has_text;
    private int selected_inkpot;
    private String bookmark_data;
    private String password = null;
    private int right_margin = 25;
    private int pageturn_animation_milliseconds;
    private boolean has_hi_res_images;
    private int images_dpi;
    private Dimension bt_translation = null;
    private String bt_scaling_s;
    private double bt_scaling;
    private String st_scaling_s;
    private double st_scaling;

    private String scribble_source_url = null;
    private String scribble_sink_url = null;
    private String hotspot_source_url = null;
    private String hotspot_sink_url = null;
    private String activity_logger_url = null;
    private DocViewerCallback handle_action = null;
    private UpLibScribbleHandler handle_scribble = null;
    private UpLibHotspotHandler handle_hotspots = null;

    private DocViewer dv;

    private class PageOpener implements DocViewerCallback {
        private AppletContext context;
        private URL codebase;
        public PageOpener (AppletContext context_p, URL codebase) {
            this.context = context_p;
            this.codebase = codebase;
        }
        public void call (Object o) {
            try {
                URL u2 = (URL) o;
                String auth = u2.getAuthority();
                if ((auth != null) && auth.equals("-uplib-")) {
                    // make it a relative URL
                    u2 = new URL(codebase, u2.getFile());
                }
                System.err.println("Opening URL " + u2.toExternalForm());
                context.showDocument(u2, "_blank");
            } catch (Exception e) {
                System.err.println("Exception " + e + " calling showDocument");
                e.printStackTrace(System.err);
            }
        }
        public void flush() {};
    };

    private void loadAppletParameters() {
        String tmp;
        image_directory = getParameter("IMAGE_DIR");
        System.err.println("image_directory is " + image_directory);

        tmp = getParameter("SCRIBBLE_SOURCE");
        if (tmp != null)
            scribble_source_url = tmp;
        System.err.println("scribble_source_url is " + scribble_source_url);

        tmp = getParameter("SCRIBBLE_SINK");
        if (tmp != null)
            scribble_sink_url = tmp;
        System.err.println("scribble_sink_url is " + scribble_sink_url);

        tmp = getParameter("HOTSPOTS_SOURCE");
        if (tmp != null)
            hotspot_source_url = tmp;
        System.err.println("hotspot_source_url is " + hotspot_source_url);

        tmp = getParameter("HOTSPOTS_SINK");
        if (tmp != null)
            hotspot_sink_url = tmp;
        System.err.println("hotspot_sink_url is " + hotspot_sink_url);

        tmp = getParameter("ACTIVITY_LOGGER");
        if (tmp != null)
            activity_logger_url = tmp;
        System.err.println("activity_logger_url is " + activity_logger_url);

        document_title = getParameter("DOC_TITLE");
        System.err.println("document_title is " + document_title);
        document_id = getParameter("DOC_ID");
        System.err.println("document_id is " + document_id);
        page_numbers = getParameter("PAGE_NUMBERS");
        System.err.println("page_numbers is " + page_numbers);
        tmp = getParameter("FIRST_PAGE_NUMBER");
        first_page_number = (tmp != null) ? Integer.valueOf(tmp).intValue() : 1;
        System.err.println("first_page_number is " + first_page_number);
        tmp = getParameter("CURRENT_PAGE");
        current_page = (tmp != null) ? Integer.valueOf(tmp).intValue() : 0;
        tmp = getParameter("SELECTION_START");
        selection_start = (tmp != null) ? Integer.valueOf(tmp).intValue() : -1;
        tmp = getParameter("SELECTION_END");
        selection_end = (tmp != null) ? Integer.valueOf(tmp).intValue() : -1;
        System.err.println("current_page is " + current_page);
        tmp = getParameter("PAGE_COUNT");
        page_count = (tmp != null) ? Integer.valueOf(tmp).intValue() : 1;
        System.err.println("page_count is " + page_count);
        tmp = getParameter("RIGHT_MARGIN");
        right_margin = (tmp != null) ? Integer.valueOf(tmp).intValue() : 25;
        System.err.println("right_margin is " + right_margin);
        tmp = getParameter("PAGE_WIDTH");
        page_width = (tmp != null) ? Integer.valueOf(tmp).intValue() : 660;
        System.err.println("page_width is " + page_width);
        tmp = getParameter("PAGE_HEIGHT");
        page_height = (tmp != null) ? Integer.valueOf(tmp).intValue() : 880;
        System.err.println("page_height is " + page_height);
        tmp = getParameter("PAGETURN_ANIMATION_MS");
        pageturn_animation_milliseconds = (tmp != null) ? Integer.valueOf(tmp).intValue() : 400;
        System.err.println("pageturn_animation_milliseconds is " + pageturn_animation_milliseconds);
        tmp = getParameter("THUMBNAIL_WIDTH");
        thumbnail_width = (tmp != null) ? Integer.valueOf(tmp).intValue() : 0;
        System.err.println("thumbnail_width is " + thumbnail_width);
        tmp = getParameter("THUMBNAIL_HEIGHT");
        thumbnail_height = (tmp != null) ? Integer.valueOf(tmp).intValue() : 0;
        System.err.println("thumbnail_height is " + thumbnail_height);
        tmp = getParameter("SHOW_CONTROLS");
        show_controls = (tmp != null) ? Boolean.valueOf(tmp).booleanValue() : true;
        System.err.println("show_controls is " + show_controls);

        tmp = getParameter("SHOW_ADH");
        show_active_reading = (tmp != null) ? Boolean.valueOf(tmp).booleanValue() : false;
        tmp = getParameter("SHOW_RSVP");
        show_rsvp = (tmp != null) ? Boolean.valueOf(tmp).booleanValue() : false;
        if (show_rsvp)
            show_active_reading = true;
        System.err.println("show_active_reading is " + show_active_reading);
        System.err.println("show_rsvp is " + show_rsvp);

        tmp = getParameter("IMAGES_DPI");
        images_dpi = (tmp == null) ? 300 : Integer.valueOf(tmp).intValue();
        String bt_translation_x = getParameter("PAGE_TRANSLATION_X");
        String bt_translation_y = getParameter("PAGE_TRANSLATION_Y");
        bt_translation = null;
        System.err.println("bt_translation_x is " + bt_translation_x + ", bt_translation_y is " + bt_translation_y);
        if ((bt_translation_y != null) && (bt_translation_x != null))
            bt_translation = new Dimension((int) (Float.valueOf(bt_translation_x).floatValue()),
                                           (int) (Float.valueOf(bt_translation_y).floatValue()));
        bt_scaling_s = getParameter("PAGE_SCALING");
        bt_scaling = (bt_scaling_s == null) ? 0.0D : Double.valueOf(bt_scaling_s).doubleValue();
        st_scaling_s = getParameter("THUMBNAIL_SCALING");
        st_scaling = (st_scaling_s == null) ? 0.0D : Double.valueOf(st_scaling_s).doubleValue();

        tmp = getParameter("SHOW_ANNOTATIONS");
        show_annotations = (tmp != null) ? Boolean.valueOf(tmp).booleanValue() : false;
        tmp = getParameter("HAS_HI_RES_IMAGES");
        has_hi_res_images = (tmp != null) ? Boolean.valueOf(tmp).booleanValue() : false;
        System.err.println("show_annotations is "+show_annotations);
        tmp = getParameter("SELECTED_INKPOT");
        selected_inkpot = (tmp != null) ? Integer.valueOf(tmp).intValue() : 0;
        System.err.println("selected_inkpot is " + selected_inkpot);
        bookmark_data = getParameter("BOOKMARK_DATA");
        System.err.println("bookmark_data is " + bookmark_data);
        tmp = getParameter("SHOW_EDGE");
        show_edge = (tmp != null) ? Boolean.valueOf(tmp).booleanValue() : true;
        System.err.println("show_edge is " + show_edge);
        tmp = getParameter("HAS_TEXT");
        has_text = (tmp != null) ? Boolean.valueOf(tmp).booleanValue() : true;
        System.err.println("has_text is " + has_text);
        tmp = getParameter("SHOW_TWO_PAGES");
        show_two_pages = (tmp != null) ? Boolean.valueOf(tmp).booleanValue() : false;
        System.err.println("show_two_pages is " + show_two_pages);
        tmp = getParameter("LOGO_URL");
        try {
            final URL logo_urls = new java.net.URL(tmp);
            final UpLibPageview top = this;
            logo_url = new DocViewerCallback() {
                    public void call (Object o) {
                        top.getAppletContext().showDocument(logo_urls, "_parent");
                    }
                    public void flush() {};
                };
        } catch (Exception e) {
            logo_url = null;
        }
        System.err.println("logo_url is " + logo_url);
    }

    private String joinURLParts (String p1, String p2) {
        String retval;

        if (p1.endsWith("/") && (p2.startsWith("/")))
            retval = p1 + p2.substring(1);
        else
            retval = p1 + p2;
        System.err.println("URL formed is " + retval);
        return retval;
    }

    public void setPage(int pageno) {
        dv.setPage(pageno);
    }

    public void init () {

        try {
            // on Macs, use Quartz for drawing instead of Sun's slow code
            System.setProperty("apple.awt.graphics.UseQuartz","true");
        } catch (Exception x) {
        }

        Scribble[] scribbles = null;
        HotSpot[] hotspots = null;
        String image_url_prefix = null;
        String codebase = getCodeBase().toExternalForm();
        URL sink_u = null;
        URL source_u = null;
        DocViewerCallback page_opener = null;

        setBackground(LEGEND_COLOR);

        loadAppletParameters();

        image_url_prefix = joinURLParts(codebase, image_directory);
        System.err.println("codebase is " + codebase + ", scribble_source_url is " + scribble_source_url);

        if ((scribble_sink_url != null) || (scribble_source_url != null)) {
            try {
                if (scribble_sink_url != null)
                    sink_u = new URL(joinURLParts(codebase, scribble_sink_url));
                if (scribble_source_url != null)
                    source_u = new URL(joinURLParts(codebase, scribble_source_url));
                handle_scribble = new UpLibScribbleHandler(document_id, password, sink_u, source_u);
            } catch (MalformedURLException e) {
                System.err.println("Bad URL formed from " + codebase + " and either " + scribble_sink_url + " or " + scribble_source_url);
            }
        } else {
            handle_scribble = null;
        }

        if ((scribble_source_url != null) && (handle_scribble != null)) {
            scribbles = handle_scribble.readScribbles();
        }

        final AppletContext context = this.getAppletContext();

        page_opener = (DocViewerCallback) new PageOpener(context, getCodeBase());

        if (hotspot_source_url != null) {
            try {
                source_u = new URL(joinURLParts(codebase, hotspot_source_url));
                if (hotspot_sink_url != null) {
                    try {
                        sink_u = new URL(joinURLParts(codebase, hotspot_sink_url));
                        handle_hotspots = new UpLibHotspotHandler(document_id, password, sink_u, source_u, page_opener);
                    } catch (MalformedURLException e) {
                        System.err.println("Bad URL formed from " + codebase + " and " + hotspot_sink_url);
                        handle_hotspots = null;
                    }
                }
                hotspots = UpLibHotSpot.readHotspots(source_u, password, null, page_opener);
            } catch (MalformedURLException e) {
                System.err.println("Bad URL formed from " + codebase + " and " + hotspot_source_url);
            }
        }

        if (activity_logger_url != null) {
            URL u;
            try {
                u = new URL(joinURLParts(codebase, activity_logger_url));
                handle_action = new UpLibActivityLogger(document_id, u, password);
            } catch (MalformedURLException e) {
                System.err.println("Bad URL formed from " + codebase + " and " + activity_logger_url);
            }
        } else {
            handle_action = new DocViewerCallback() {
                    public void call (Object o) {
                        Activity a = (Activity) o;
                        System.err.println("Action:  " + a);
                    }
                    public void flush() {};
                };
        }            

        System.err.println("OS is " + System.getProperty("os.name"));

        UpLibNoteHandler nh = null;
        UpLibPageImageLoader pl = null;
        UpLibPageImageLoader hl = null;
        UpLibPageTextLoader tl = null;
        UpLibPageImageLoader zl = null;
        URL codebase_URL = null;
        try {
            codebase_URL = new URL(codebase);
            pl = new UpLibPageImageLoader("page image", codebase_URL, password, right_margin);
            hl = new UpLibPageImageLoader("page thumbnail", codebase_URL, password, 0);
            if (has_hi_res_images) {
                zl = new UpLibPageImageLoader(codebase_URL, password, 0);
                zl.setPageImageType("hi-res page image");
            }
            if (has_text)
                tl = new UpLibPageTextLoader("page text", codebase_URL, password);
            nh = new UpLibNoteHandler(codebase_URL, password, (1 << 10));
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }

        setFocusable(false);
        getContentPane().setFocusable(false);
        getRootPane().setFocusable(false);
        getGlassPane().setFocusable(false);
        getLayeredPane().setFocusable(false);
        System.err.println("instantiating DocViewer");

        dv = new DocViewer(new SoftReferenceCache(pl, 50),
                           new SoftReferenceCache(hl, 200),
                           document_title,
                           document_id,
                           logo_url,
                           page_count,
                           first_page_number,
                           page_numbers,
                           current_page,
                           new Dimension(page_width, page_height),
                           new Dimension(thumbnail_width, thumbnail_height),
                           show_controls,
                           DocViewer.PAGEEDGE_3D_PROGRESS_BAR_TOP,
                           DocViewer.PAGEEDGE_3D_PROGRESS_BAR_BOTTOM,
                           show_two_pages,
                           scribbles,
                           handle_scribble,
                           hotspots,
                           handle_action,
                           true,
                           show_annotations,
                           selected_inkpot,
                           bookmark_data,
                           pageturn_animation_milliseconds,
                           0,
                           has_text ? new SoftReferenceCache(tl, 10) : null,
                           page_opener,
                           nh,
                           (nh == null) ? null : new SoftReferenceCache(nh, 100));
        dv.setBackground(LEGEND_COLOR);
        dv.setRepositoryURL(codebase_URL);
        dv.setHotspotSaver(handle_hotspots);
        if (has_text) {
            dv.setShowActiveReading(show_active_reading, show_rsvp);
            dv.setADHState(400);
            dv.setLocateHandler(new LocateHandler(context, codebase, document_id));
            dv.setGoogleHandler(new LocateHandler(context));
        }
        if ((bt_scaling_s != null) && (bt_translation != null) && (st_scaling_s != null)) {
            dv.setThumbnailSizeFactors(bt_translation, bt_scaling, st_scaling);
            if (zl != null)
                dv.setHiResPageImageLoader(new SoftReferenceCache(zl, 0), bt_scaling, bt_translation, images_dpi);
        }
        if ((selection_start >= 0) && (selection_end >= 0)) {
            dv.setSelection(current_page, selection_start, selection_end);
        }
        dv.setTopLevelWindow(this);
        System.err.println("DocViewer is " + dv);
        getContentPane().add(dv);
        System.err.println("Added DocViewer " + dv);
    }

    public Dimension getPreferredSize () {
        return dv.getPreferredSize();
    }

    public Dimension getMaximumSize () {
        return dv.getPreferredSize();
    }

    public Dimension getMinimumSize () {
        return dv.getPreferredSize();
    }

    public void setSize (int width, int height) {
        super.setSize(width, height);
        validate();
    }

    public void start() {
        System.err.println("UpLibPageview Start is called");
    }

    public void stop() {
        System.err.println("UpLibPageview Stop is called");
    }

    public void destroy() {
        System.err.println("UpLibPageview Destroy is called");
        try {
            dv.finalize();
        } catch (Throwable x) {
            x.printStackTrace(System.err);
        }
    }

    public String getAppletInfo() {
        return "Title: com.parc.uplib.UpLibPageview $Revision: 1.45 $, $Date: 2008/10/01 02:11:33 $\n"
               + "Author: Bill Janssen\n"
               + "A simple page viewing and marking application.";
    }

    public String[][] getParameterInfo() {
        String[][] info = {
          {"IMAGE_DIR", "string", "the directory containing the page images"},
          {"SCRIBBLE_SINK", "string", "the URL to call to deposit scribbles"},
          {"SCRIBBLE_SOURCE", "string", "the URL to call to load scribbles"},
          {"HOTSPOTS_SOURCE", "string", "the URL to call to load hotspots info"},
          {"ACTIVITY_LOGGER", "string", "the URL to call to log activities" },
          {"DOC_TITLE", "string", "the name of the document (may be null)"},
          {"FIRST_PAGE_NUMBER", "int", "the number for the first page, if it isn't 1"},
          {"CURRENT_PAGE", "int", "zero-based page index for which page to show first"},
          {"SELECTION_START", "int", "zero-based character index for where to start the selection (whole document)"},
          {"SELECTION_END", "int", "zero-based character index for where to end the selection (whole document)"},
          {"PAGE_COUNT", "int", "the number of page images"},
          {"PAGE_WIDTH", "int", "the width of the page images"},
          {"PAGE_HEIGHT", "int", "the height of the page images"},
          {"PAGETURN_ANIMATION_MS", "int", "the number of milliseconds to animate in a page turn"},
          {"SHOW_CONTROLS", "boolean", "whether to show the right-hand controls panel"},
          {"SHOW_EDGE", "boolean", "whether to show the edges on top and bottom"},
          {"SHOW_TWO_PAGES", "boolean", "whether to show two pages at once"},
          {"HAS_TEXT", "boolean", "whether the page text is available"},
          {"LOGO_URL", "string", "a URL to switch to if the logo icon is clicked on"},
        };
        return info;
    }
}
