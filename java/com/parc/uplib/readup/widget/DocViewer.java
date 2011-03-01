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

import javax.swing.JApplet;
import java.io.*;
import java.awt.dnd.*;
import java.util.*;
import java.util.regex.*;
import java.awt.event.*;
import java.awt.image.*;
import java.awt.geom.*;
import java.awt.font.*;
import java.awt.*;
import java.awt.dnd.*;
import java.awt.datatransfer.*;
import javax.swing.*;
import javax.swing.event.*;
import javax.swing.text.*;
import javax.swing.text.html.*;
import javax.swing.border.*;
import javax.imageio.*;
import java.net.URL;
import java.lang.reflect.*;
import java.lang.ref.SoftReference;
import java.text.SimpleDateFormat;
import java.security.MessageDigest;

import com.parc.uplib.util.EmacsKeymap;
import com.parc.uplib.util.Base64;
import com.parc.tablet.PenEvent;        // from JPen.jar
import com.parc.tablet.PenSupport;      // from JPen.jar

public class DocViewer extends JPanel
  implements KeyListener, FocusListener, ActionListener {

    protected final static Color BACKGROUND_COLOR = new Color(.878f, .941f, .973f);
    protected final static Color TOOLS_COLOR = new Color(.754f, .848f, .910f);
    protected final static Color HALF_TOOLS_COLOR = new Color(.754f, .848f, .910f, 0.5f);
    protected final static Color BARELY_TOOLS_COLOR = new Color(.754f, .848f, .910f, 0.3f);
    protected final static Color TRANSPARENT = new Color(0, 0, 0, 0);
    protected final static Color TRANSPARENT_TOOLS_COLOR = new Color(.754f, .848f, .910f, .8f);
    protected final static Color LEGEND_COLOR = new Color(.602f, .676f, .726f);
    protected final static Color HALF_LEGEND_COLOR = new Color(.602f, .676f, .726f, 0.5f);
    protected final static Color DARK_COLOR = new Color(.439f, .475f, .490f);
    protected final static Color UPLIB_ORANGE = new Color(.937f, .157f, .055f);
    protected final static Color UPLIB_ORANGE_WASH = new Color(.937f, .157f, .055f, 0.50f);
    protected final static Color CLEAR = new Color(1.0f, 1.0f, 1.0f, 0.0f);
    protected final static Color WHITE = new Color(1.0f, 1.0f, 1.0f);
    protected final static Color HALF_WHITE = new Color(1.0f, 1.0f, 1.0f, 0.5f);
    protected final static Color NOTE_BACKGROUND = new Color(1.0f, 1.0f, 0.8f, 0.9f);
    protected final static Color HALF_YELLOW = new Color(1.0f, 1.0f, 0.0f, 0.5f);
    protected final static Color WHITE80 = new Color(1.0f, 1.0f, 1.0f, 0.8f);
    protected final static Color BLACK = new Color(0.0f, 0.0f, 0.0f);
    protected final static Color HALF_BLACK = new Color(0.0f, 0.0f, 0.0f, 0.5f);
    protected final static Color GRAY = new Color(0.5f, 0.5f, 0.5f);
    // protected final static Color HOT_SPOT_COLOR = new Color(0.8f, 0.8f, 0.0f, 0.1f);
    protected final static Color HOT_SPOT_COLOR = HALF_TOOLS_COLOR;
    public final static Color HIGHLIGHT_COLOR = new Color(1.0f, 0.0f, 1.0f, 0.2f);
    protected final static Color DIM_CYAN = new Color(0.0f, 1.0f, 1.0f, 0.2f);

    protected final static Color PHRASE_COLOR_1 = new Color(1.0f, 1.0f, 0.0f, 0.10f);
    protected final static Color PHRASE_COLOR_2 = new Color(0.0f, 1.0f, 1.0f, 0.08f);
    protected final static Color PHRASE_COLOR_3 = new Color(1.0f, 0.0f, 1.0f, 0.10f);

    protected final static Color GREEN_MARKER_COLOR = new Color(0.0f, 0.7f, 0.0f, 0.2f);
    protected final static Color PINK_MARKER_COLOR = new Color(0.7f, 0.0f, 0.0f, 0.2f);
    protected final static Color BLUE_MARKER_COLOR = new Color(0.0f, 0.0f, 0.7f, 0.2f);

    protected final static Color BLUE_INK_COLOR = new Color(0.0f, 0.0f, 1.0f);
    protected final static Color RED_INK_COLOR = new Color(1.0f, 0.0f, 0.0f);

    protected final static Font   NOTE_NUMBER_FONT = new Font(null, Font.PLAIN, 18);

    protected final static int    LEFT_PAGE_OFFSET = 0;
    protected final static int    RIGHT_PAGE_OFFSET = 1;

    protected final static int    PAGEEDGE_NONE = 0;
    public final static int    PAGEEDGE_PROGRESS_BAR = 1;
    public final static int    PAGEEDGE_BOOK_HALVES = 2;
    public final static int    PAGEEDGE_3D_PROGRESS_BAR_TOP = 3;
    public final static int    PAGEEDGE_3D_PROGRESS_BAR_BOTTOM = 4;

    protected final static char   ESCAPE = '\u001b';
    protected final static char   BACKSPACE = '\u0008';
    protected final static char   DELETE = '\u007f';
    protected final static char   CONTROL_C = '\u0003';
    protected final static char   CONTROL_D = '\u0004';
    protected final static char   CONTROL_F = '\u0006';
    protected final static char   CONTROL_G = '\u0007';
    protected final static char   CONTROL_I = '\u0009';
    protected final static char   CONTROL_J = '\n';
    protected final static char   CONTROL_K = '\u000b';
    protected final static char   CONTROL_L = '\u000c';
    protected final static char   CONTROL_M = '\r';
    protected final static char   CONTROL_N = '\u000e';
    protected final static char   CONTROL_O = '\u000f';
    protected final static char   CONTROL_P = '\u0010';
    protected final static char   CONTROL_Q = '\u0011';
    protected final static char   CONTROL_R = '\u0012';
    protected final static char   CONTROL_S = '\u0013';
    protected final static char   CONTROL_T = '\u0014';
    protected final static char   CONTROL_U = '\u0015';
    protected final static char   CONTROL_V = '\u0016';
    protected final static char   CONTROL_W = '\u0017';
    protected final static char   CONTROL_X = '\u0018';
    protected final static char   CONTROL_Y = '\u0019';
    protected final static char   CONTROL_Z = '\u001a';
    protected final static char   SPACE = ' ';

    protected static RenderingHints high_quality_rendering_mode;
    protected static RenderingHints low_quality_rendering_mode;

    public final static Point ORIGIN_POINT = new Point(0, 0);

    static Pattern PAGERANGES = Pattern.compile("^(\\d+)(-|--)(\\d+)$");

    static BasicStroke HOTSPOT_BORDER = new BasicStroke(6.0f,
                                                        BasicStroke.CAP_ROUND,
                                                        BasicStroke.JOIN_ROUND);
    static int HOTSPOT_BORDER_WIDTH = 7;        /* slightly larger than stroke width */
    protected final static String INTERNAL_LINK_PREFIX = new String("#uplibpage=");

    static protected boolean    avoid_imageio = false;

    static {

        high_quality_rendering_mode = new RenderingHints(null);
        low_quality_rendering_mode = new RenderingHints(null);

        high_quality_rendering_mode.put (RenderingHints.KEY_ANTIALIASING,
                          RenderingHints.VALUE_ANTIALIAS_ON);
        high_quality_rendering_mode.put (RenderingHints.KEY_ALPHA_INTERPOLATION,
                          RenderingHints.VALUE_ALPHA_INTERPOLATION_QUALITY);
        high_quality_rendering_mode.put (RenderingHints.KEY_RENDERING,
                          RenderingHints.VALUE_RENDER_QUALITY);
        high_quality_rendering_mode.put (RenderingHints.KEY_INTERPOLATION,
                          RenderingHints.VALUE_INTERPOLATION_BICUBIC);
        
        low_quality_rendering_mode.put (RenderingHints.KEY_ANTIALIASING,
                         RenderingHints.VALUE_ANTIALIAS_OFF);
        low_quality_rendering_mode.put (RenderingHints.KEY_ALPHA_INTERPOLATION,
                         RenderingHints.VALUE_ALPHA_INTERPOLATION_SPEED);
        low_quality_rendering_mode.put (RenderingHints.KEY_RENDERING,
                         RenderingHints.VALUE_RENDER_SPEED);
        low_quality_rendering_mode.put (RenderingHints.KEY_INTERPOLATION,
                         RenderingHints.VALUE_INTERPOLATION_NEAREST_NEIGHBOR);

        System.err.println("high_quality_rendering_mode is " + high_quality_rendering_mode);
        System.err.println("low_quality_rendering_mode is " + low_quality_rendering_mode);

        try {
            String imageio_broken = System.getProperty("com.parc.uplib.imageIO-broken");
            avoid_imageio = (imageio_broken != null) && imageio_broken.toLowerCase().equals("true");
        } catch (java.lang.SecurityException x) {
            // don't have privilege to look at this...
            avoid_imageio = false;
        }
    }

    protected static int  splash_page_period = 0;
    protected BufferedImage splash_image = null;

    static protected String     os_name = null;

    protected AnnotationStreamHandler scribble_handler;
    protected DocViewerCallback   activity_logger;
    protected DocViewerCallback   page_opener = null;

    protected URL         theRepositoryURL;
    protected boolean     show_controls;
    protected int         top_edge_type;
    protected int         bottom_edge_type;
    protected BufferedImage       next_arrow;
    protected BufferedImage       back_arrow;
    protected BufferedImage       small_uplib_logo;
    protected BufferedImage       eyeball_image;
    protected BufferedImage       grayed_eyeball_image;
    protected BufferedImage       link_icon;
    protected BufferedImage       link_icon_translucent;
    protected BufferedImage       hotspots_image;
    protected BufferedImage       snapback_left_image;
    protected BufferedImage       snapback_right_image;
    protected BufferedImage       zoom_in_image;
    protected BufferedImage       thumbnails_image;
    protected BufferedImage       search_icon_image;
    protected BufferedImage       search_again_label;
    protected BufferedImage       note_corner_image;
    protected BufferedImage       doccontrol_top;
    protected BufferedImage       doccontrol_bottom;
    protected BufferedImage       doccontrol_center;
    protected BufferedImage       postit_image;
    protected BufferedImage       page_edge_slider_top_center;
    protected BufferedImage       page_edge_slider_top_right_end;
    protected BufferedImage       page_edge_slider_bottom_center;
    protected BufferedImage       page_edge_slider_bottom_right_end;
    protected BufferedImage       page_edge_background_right_end;
    protected BufferedImage       page_edge_background_center;
    protected BufferedImage       bookmark_drop_shadow;
    static protected BufferedImage       button_up_background;
    static protected BufferedImage       button_down_background;
    static protected BufferedImage       big_inkpot;
    static protected BufferedImage       small_inkpot_with_quill;
    static protected BufferedImage       smalltext_image;
    protected BufferedImage               red_bookmark = null;
    protected BufferedImage               purple_bookmark = null;
    protected BufferedImage               green_bookmark = null;
    protected DocViewerCallback   logo_url;
    protected DocViewerCallback   locate_handler = null;
    protected DocViewerCallback   google_handler = null;
    protected DocViewerCallback   seturl_handler = null;
    protected Cursor      our_cursor;
    protected Class       scaled_jcomponent_class = null;
    protected Class       content_pane_class = null;
    protected AnnotationStreamHandler       note_saver = null;
    protected AnnotationStreamHandler       hotspot_saver = null;
    protected SoftReferenceCache  note_loader = null;

    protected int         first_page_number;
    protected int         page_count;
    protected String      document_id;
    protected String      document_title;
    protected ArrayList   page_number_data;
    protected int         page_width;
    protected int         page_height;
    protected int         thumbnail_width;
    protected int         thumbnail_height;

    protected String      image_directory;

    protected Container   top_level_ancestor;
    protected Pageview    left_pageview;
    protected Pageview    right_pageview;
    protected Box         pageview_holder;
    protected boolean     two_page = false;
    protected PageControl controls;
    protected PageEdge    top_page_edge;
    protected PageEdge    bottom_page_edge;
    protected JLabel      page_indicator;
    protected boolean     gui_created = false;
    protected int         current_page_index = 0;
    protected int         snapback_page;
    protected boolean     first_page_expose = true;
    protected int         default_pageturn_animation_time = 0;
    protected JLabel      status_label;
    protected ArrayList   strokes;                // contains an ArrayList of Scribbles for each page
    protected ArrayList   hotspots = null;
    protected Inkpots     widget_inkpots = null;
    protected ArrayList   note_sheets;            // contains an ArrayList of Notes for each page
    protected SoftReferenceCache  page_image_loader;
    protected SoftReferenceCache  thumbnail_image_loader;
    protected SoftReferenceCache  hires_page_image_loader;
    protected JPanel      views_flipper;
    protected DocThumbnails       thumbnails = null;
    protected JViewport   thumbnails_viewport = null;
    protected Component   focus_window = null;

    protected boolean     show_scribbles;
    protected boolean     show_hotspots;
    protected boolean     show_parts_of_speech;
    protected HotSpot     drag_hotspot = null;
    protected boolean     page_rotated = false;
    protected boolean     shift_key_pressed = false;
    protected boolean     control_key_pressed = false;
    protected boolean     thumbnails_showing = false;
    protected boolean     zoom_in_showing = false;
    protected Date        annotation_span_start;
    protected Date        annotation_span_end;
    protected AnnotationTimeControl annotation_span_controls = null;
    protected int         initial_selected_inkpot;
    protected boolean     activities_on;
    protected boolean     doc_closed = false;
    protected boolean     decompress_images_on_load = true;
    protected boolean	  clickForPageTurn = true;
    protected boolean     show_dialog_on_drop = false;
    protected Clipboard   clipboard = null;
    protected LinkDescrDialog     link_description_dialog = null;

    protected Bookmark[]  bookmarks = null;
    protected String      initial_bookmark_data;

    protected double              page_image_scaling = java.lang.Double.NaN;
    protected AffineTransform     big_to_small_transform = null;
    protected AffineTransform     small_to_big_transform = null;

    protected ZoomedViewer        zoomed_viewer = null;

    protected SoftReferenceCache  pagetext_loader;
    protected int[]               page_texts_starts = null;

    protected boolean             show_phrases = false;

    protected SearchState         search_state = null;

    protected SelectionState      selection = null;

    protected ADHState            active_reading = null;
    protected boolean             show_active_reading = false;
    protected boolean             rsvp_mode = false;
    protected boolean             current_drag_source = false;
    protected Point               current_drop_point = null;
    protected BufferedImage       cached_link_image = null;

    protected TreeMap             document_properties = null;

    public static int max(int v1, int v2) {
        return ((v1 > v2) ? v1 : v2);
    }

    public static int min(int v1, int v2) {
        return ((v1 < v2) ? v1 : v2);
    }

    public static float max(float v1, float v2) {
        return ((v1 > v2) ? v1 : v2);
    }

    public static float min(float v1, float v2) {
        return ((v1 < v2) ? v1 : v2);
    }

    private static class LinkDescrDialog extends JDialog implements ActionListener {

        private JTextArea textarea;
        public boolean cancelled;
        private JButton ok_button;

        public LinkDescrDialog (JPanel owner) {
            super((JFrame) null, null, true, owner.getGraphicsConfiguration());
            setBackground(TOOLS_COLOR);
            initComponents();
            setDefaultCloseOperation(JDialog.HIDE_ON_CLOSE);
            cancelled = false;
        }

        protected void initComponents() {

            setTitle("description for link ");

            Box b = Box.createVerticalBox();
            b.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));

            Container contents = getContentPane();
            contents.add(b);

            JScrollPane a = new JScrollPane(textarea = new JTextArea(""));
            b.add(a);

            b.add(Box.createVerticalStrut(5));

            Box s = Box.createHorizontalBox();
            b.add(s);

            JButton but = new JButton("Cancel");
            but.addActionListener(this);
            s.add(but);

            s.add(Box.createHorizontalGlue());

            ok_button = new JButton("OK");
            ok_button.addActionListener(this);
            s.add(ok_button);

            b.add(s);

            pack();
        }

        public Point getOKButtonLocation() {
            Point p = new Point();
            java.awt.Component c = ok_button;
            while (c != this) {
                // System.err.println("***** " + c);
                Point l = c.getLocation();
                p.x += l.x;
                p.y += l.y;
                c = c.getParent();
            }
            return p;
        }

        public void actionPerformed (ActionEvent e) {
            if (e.getActionCommand().equals("Cancel")) {
                cancelled = true;
                setVisible(false);
            }
            else if (e.getActionCommand().equals("OK"))
                setVisible(false);
        }

        public void setDescription(String d) {
            textarea.setText(d);
        }

        public String getDescription () {
            return textarea.getText();
        }
    }

    public class Notesheets extends java.util.ArrayList implements Annotation {

        protected Annotation.Timestamp timestamp;
        private Rectangle bounds;
        private int page_index;

        public Notesheets (int capacity, int pageIndex) {
            super(capacity);
            timestamp = new Annotation.Timestamp(Annotation.Timestamp.CREATED);
            page_index = pageIndex;
            bounds = null;
        }

        public int pageIndex() {
            return page_index;
        }

        public String docId() {
            return document_id;
        }

        public Timestamp timestamp() {
            return timestamp;
        }

        public Type getType () {
            return Annotation.Type.NOTESET;
        }

        public java.awt.Rectangle getBounds() {
            return bounds;
        }

        public boolean add (Object o) {
            if (o instanceof NoteFrame) {
                NoteFrame nf = (NoteFrame) o;
                if (bounds == null)
                    bounds = new Rectangle(nf.x, nf.y, nf.width, nf.height);
                else {
                    bounds.add((double) nf.x, (double) nf.y);
                    bounds.add((double) (nf.x + nf.width), (double) (nf.y + nf.height));
                }
                return super.add(o);
            } else {
                return false;
            }
        }
    }

    public class NoteFramesSetter implements DocViewerCallback {
        private int pageno;
        public NoteFramesSetter(int i) {
            pageno = i;
        }
        public void call (Object o) {
            // System.err.println("@@@ value arrived for page " + pageno + " note frames:  " + o);
            if (o == null)
                return;
            else if (o instanceof Exception) {
                if (!(o instanceof ResourceLoader.ResourceNotFound)) {
                    System.err.println("Couldn't fetch note pages for " + document_id + " page " + pageno + ":");
                    ((Exception)o).printStackTrace(System.err);
                }
            } else if (o instanceof NoteFrame[]) {
                NoteFrame[] notes = (NoteFrame[]) o;
                Notesheets sheets = new Notesheets (notes.length, pageno);
                for (int j = 0;  j < notes.length;  j++) {
                    sheets.add(notes[j]);
                }
                note_sheets.set(pageno, sheets);
                if ((current_page_index == pageno) || (two_page && ((current_page_index + 1) == pageno)))
                    repaintPageview();
            }
        }
        public void flush() {};
    }

    public class PageTextSetter implements DocViewerCallback {

        private int pageno;
        private boolean redraw;
        private SearchState search;

        public PageTextSetter (int pageno, boolean redraw, SearchState searching) {
            this.pageno = pageno;
            this.redraw = redraw;
            this.search = searching;
        }

        public PageTextSetter (int pageno, boolean redraw) {
            this.pageno = pageno;
            this.redraw = redraw;
            this.search = null;
        }

        public void call (Object o) {
            if (o instanceof PageText) {
                PageText ptext = (PageText) o;
                page_texts_starts[pageno] = ptext.getTextLocation();

                // System.err.println("*** loaded page text for " + pageno + " => " + ptext);
                if (pageno == (two_page ? (current_page_index + 1) : current_page_index)) {
                    if (active_reading != null) {
                        active_reading.pagetextDelivered(pageno);
                    }
                }
                if (search != null)
                    synchronized(search) {
                        search.notifyAll();
                    }
                if (redraw)
                    repaintPageview();
            } else if (o instanceof Exception) {
                System.err.println("Exception fetching pagetext for page " + pageno + ": " + o);
            }
        }

        public void flush() {};
    }

    public class PageImageSetter implements DocViewerCallback {

        private int pageno;
        private JPanel component;

        public PageImageSetter (int pageno, JPanel component) {
            this.pageno = pageno;
            this.component = component;
        }

        public PageImageSetter (int pageno) {
            this.pageno = pageno;
            this.component = null;
        }

        public void call (Object o) {
            if (o instanceof Image) {
                if (component != null)
                    component.repaint();
                else if ((pageno == current_page_index) || (two_page && (pageno == (current_page_index + 1))))
                    repaintPageview();
            } else if (o instanceof Exception) {
                System.err.println("Exception fetching page image for page " + pageno + ": " + o);
            }
        }

        public void flush() {};
    }

    protected class DVTransferHandler extends TransferHandler implements Icon {

        private BufferedImage dragImage;
        private Transferable transferable;

        public DVTransferHandler () {
            super();
        }
        
        public Transferable createTransferable (JComponent comp) {
            System.err.println("createTransferable(" + comp + ")");
            return transferable;
        }

        public void setTransferData (Transferable t, BufferedImage i) {
            transferable = t;
            dragImage = i;
        }

        public boolean importData (JComponent comp, Transferable t) {
            boolean status;

            if (comp instanceof Pageview) {
                Pageview pv = (Pageview) comp;
                DataFlavor f = pv.desiredFlavor(t.getTransferDataFlavors());
                try {
                    Object o = t.getTransferData(f);
                    status = pv.doDrop (o, ((Pageview)comp).getDropPoint());
                } catch (UnsupportedFlavorException x) {
                    // shouldn't happen, because we checked the flavor, but...
                    x.printStackTrace(System.err);
                    status = false;
                } catch (IOException x) {
                    x.printStackTrace(System.err);
                    status = false;
                }
            } else {
                status = super.importData(comp, t);
            }
            System.err.println("importData => " + status);
            return status;
        }

        public boolean canImport (JComponent comp, DataFlavor[] transferFlavors) {
            boolean status;
            if (comp instanceof Pageview)
                status = ((Pageview)comp).canImport(transferFlavors);
            else
                status = super.canImport(comp, transferFlavors);
            System.err.println("canImport(" + comp + ") => " + status);
            return status;
        }

        public int getSourceActions (JComponent c) {
            if (transferable == null)
                return TransferHandler.NONE;
            else
                return TransferHandler.COPY;
        }

        public int getIconHeight () {
            if (dragImage != null)
                return dragImage.getHeight();
            else
                return 0;
        }

        public int getIconWidth () {
            if (dragImage != null)
                return dragImage.getWidth();
            else
                return 0;
        }

        public void paintIcon (Component c, Graphics g, int x, int y) {
            if (dragImage != null) {
                g.drawImage(dragImage, x, y, null);
            }
        }

        public Icon getVisualRepresentation (Transferable t) {
            if ((t == transferable) && (dragImage != null))
                return this;
            return null;
        }

        protected void exportDone (JComponent source,
                                   Transferable data,
                                   int action) {
            super.exportDone(source, data, action);
            if (data == transferable) {
                transferable = null;
                dragImage = null;
            }
            System.err.println("export done.");
        }
    }

    protected static class RomanNumerals {

        private String roman_version;
        private int    integer_version;

        static RomanNumerals[] values = null;

        private RomanNumerals (String rv, int iv) {
            roman_version = rv;
            integer_version = iv;
        }

        public static String toRoman (int n) {

            String retval = "";

            if (values == null) {
                values = new RomanNumerals[13];
                values[0] = new RomanNumerals("m", 1000);
                values[1] = new RomanNumerals("cm", 900);
                values[2] = new RomanNumerals("d",  500);
                values[3] = new RomanNumerals("cd", 400);
                values[4] = new RomanNumerals("c",  100);
                values[5] = new RomanNumerals("xc", 90);
                values[6] = new RomanNumerals("l",  50);
                values[7] = new RomanNumerals("xl", 40);
                values[8] = new RomanNumerals("x",  10);
                values[9] = new RomanNumerals("ix", 9);
                values[10] = new RomanNumerals("v",  5);
                values[11] = new RomanNumerals("iv", 4);
                values[12] = new RomanNumerals("i",  1);
            }
            if ((n < 1) || (n >= 5000))
                return null;
            for (int i = 0;  i < values.length;  i++) {
                while (n >= values[i].integer_version) {
                    retval += values[i].roman_version;
                    n -= values[i].integer_version;
                }
            }
            return retval;
        }
    }

    public class PageEdge extends JPanel
        implements MouseInputListener, MouseWheelListener, InkpotsListener {

        public DocViewer topl;
        private int     display_style = 0;
        private Point   click_point;
        private TexturePaint tiled_page_edge_slider_bottom_center;
        private TexturePaint tiled_page_edge_slider_top_center;
        private TexturePaint tiled_page_edge_background_top_center;

        public PageEdge (DocViewer toplevel, int page_width, int page_height, int style) {
            super(new BorderLayout());
            topl = toplevel;
            Dimension d = new Dimension(two_page ? (2 * page_width) : page_width, 5);
            setPreferredSize(d);
            setBackground(BACKGROUND_COLOR);
            setOpaque(true);
            setFocusable(false);
            addMouseListener(this);
            addMouseWheelListener(this);
            if (document_title != document_id)
                setToolTipText(document_title + " (" + document_id + ")");
            else
                setToolTipText(document_title);
            display_style = style;
            tiled_page_edge_slider_top_center = null;
            tiled_page_edge_slider_bottom_center = null;
        }

        public void setBounds (int x, int y, int width, int height) {
            super.setBounds(x, y, width, height);
            // System.err.println("DocThumbnails.setBounds(" + width + ", " + height + ") called");
            if (height != 5) {
                setPreferredSize(new Dimension(two_page ? (2 * page_width) : page_width, 5));
                invalidate();
            }
        }

        public void mousePressed(MouseEvent e) {
            // System.err.println("Mouse event " + e);
            click_point = e.getPoint();
            if (!topl.focusOnOurApp())
                topl.requestFocusInWindow();
        }

        public void mouseDragged(MouseEvent e) {
            // System.err.println("Mouse event " + e);
        }

        public void mouseReleased(MouseEvent e) {
            // System.err.println("Mouse event " + e);
            if (click_point != null) {
                if ((active_reading != null) && (show_active_reading || !active_reading.paused())) {
                    float page_div = getWidth() / page_count;
                    int xpos = e.getX();
                    int pageno = (int) Math.floor(xpos / page_div);
                    int bits = xpos - Math.round(pageno * page_div);
                    float page_percentage = ((float) bits) / page_div;
                    PageText pt = (PageText) pagetext_loader.get(document_id, pageno, 0, null);
                    if (pt != null) {
                        int pos = Math.round(page_percentage * pt.getTextBytes().length);
                        PageText.WordBox box = pt.getWordBox(pos);
                        active_reading.jumpTo(box);
                    }
                } else if (click_point.distance(e.getPoint()) < 5.0)
                    topl.setPage((int)((e.getPoint().getX() * page_count) / getWidth()));
                click_point = null;
            }
        }
        
        public void mouseEntered(MouseEvent e) {
            // System.err.println("pageedge size is " + getWidth() + "x" + getHeight());
            click_point = null;
        }

        public void mouseExited(MouseEvent e) {
            // System.err.println("Mouse event " + e);
            click_point = null;
        }

        public void mouseClicked(MouseEvent e) {
            // System.err.println("Mouse event " + e);
            int page = (int)((e.getX() * page_count) / getWidth());
        }

        public void mouseMoved(MouseEvent e) {
            // System.err.println("Mouse event " + e);
            if (!topl.focusOnOurApp())
                topl.requestFocusInWindow();
        }

        public void mouseWheelMoved (MouseWheelEvent e) {
            // System.err.println("PageEdge mouse wheel event " + e);
            if (!topl.isFocusOwner())
                topl.requestFocusInWindow();
            int pages = e.getWheelRotation();
            topl.setPage(max(0, min(current_page_index + pages, (page_count - (two_page ? 2 : 1)))));
        }

        public String getToolTipText (MouseEvent e) {
            return "Page " + getPageNumberString((int)((e.getX() * page_count) / getWidth()));
        }

        public void inkpotChanged (boolean active, Inkpots.Pot current) {
            repaint();
        }
        
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            int ourwidth = getWidth();
            int ourheight = getHeight();
            ((Graphics2D)g).setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            ((Graphics2D)g).setStroke(new BasicStroke(1.0F, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            try {
                if (display_style == PAGEEDGE_PROGRESS_BAR) {
                    float percentage = ((float)min(page_count, current_page_index+(two_page ? 2 : 1)))/page_count;
                    g.setColor(TOOLS_COLOR);
                    g.fillRect(0, 0, (int)(ourwidth * percentage), ourheight);
                    if (topl.showScribbles()) {
                        g.setColor(UPLIB_ORANGE_WASH);
                        for (int j = 0;  j < page_count;  j++) {
                            ArrayList s = (ArrayList) strokes.get(j);
                            if (s != null && s.size() > 0) {
                                int x = (int)(ourwidth * (j/(float)page_count));
                                int width = (int)(ourwidth / (float)page_count) - 1;
                                g.fillOval(x + width/2 - 2, 0, 4, 4);
                            }
                        }
                    }
                } else if (display_style == PAGEEDGE_BOOK_HALVES) {
                    Graphics2D g2 = (Graphics2D) g;
                    if (page_count > 1) {
                        g2.setColor(TOOLS_COLOR);
                        float percentage_read = ((float)current_page_index)/(page_count - 1);
                        float percentage_unread = ((float)(page_count - (current_page_index + (two_page?2:1)))) / (page_count - 1);
                        float leftheight = percentage_read * ourheight;
                        float rightheight = percentage_unread * ourheight;
                        if (leftheight > 0)
                            g2.fill(new Rectangle2D.Float(0, ourheight - leftheight, ourwidth / 2.0F, leftheight));
                        if (rightheight > 0)
                            g2.fill(new Rectangle2D.Float(ourwidth / 2.0F, ourheight - rightheight, ourwidth / 2.0F, rightheight));
                    }

                } else if ((display_style == PAGEEDGE_3D_PROGRESS_BAR_TOP) ||
                           (display_style == PAGEEDGE_3D_PROGRESS_BAR_BOTTOM)) {

                    if (tiled_page_edge_background_top_center == null)
                        tiled_page_edge_background_top_center =
                            new TexturePaint(page_edge_background_center,
                                             new Rectangle(0, 0,
                                                           page_edge_background_center.getWidth(null),
                                                           page_edge_background_center.getHeight(null)));
                    if (tiled_page_edge_slider_top_center == null)
                        tiled_page_edge_slider_top_center =
                            new TexturePaint(page_edge_slider_top_center,
                                             new Rectangle(0, 0,
                                                           page_edge_slider_top_center.getWidth(null),
                                                           page_edge_slider_top_center.getHeight(null)));
                    if (tiled_page_edge_slider_bottom_center == null)
                        tiled_page_edge_slider_bottom_center =
                            new TexturePaint(page_edge_slider_bottom_center,
                                             new Rectangle(0, 0,
                                                           page_edge_slider_bottom_center.getWidth(null),
                                                           page_edge_slider_bottom_center.getHeight(null)));

                    ((Graphics2D) g).setPaint(tiled_page_edge_background_top_center);
                    g.fillRect(0, 0, ourwidth, ourheight);
                    g.drawImage(page_edge_background_right_end, ourwidth - page_edge_background_right_end.getWidth(), 0, null);
                    // g.setColor(TOOLS_COLOR);
                    // g.fillRect(0, 0, ourwidth, ourheight);
                    if (display_style == PAGEEDGE_3D_PROGRESS_BAR_TOP) {
                        float percentage = ((float)min(page_count, current_page_index+(two_page ? 2 : 1)))/page_count;
                        ((Graphics2D) g).setPaint(tiled_page_edge_slider_top_center);
                        int xoffset = (int)(ourwidth * percentage) - page_edge_slider_top_right_end.getWidth(null);
                        g.fillRect(0, 0, xoffset, ourheight);
                        g.drawImage(page_edge_slider_top_right_end, xoffset, 0, null);
                    } else {
                        float percentage = ((float)min(page_count, current_page_index+(two_page ? 2 : 1)))/page_count;
                        ((Graphics2D) g).setPaint(tiled_page_edge_slider_bottom_center);
                        int xoffset = (int)(ourwidth * percentage) - page_edge_slider_bottom_right_end.getWidth(null);
                        g.fillRect(0, 0, xoffset, ourheight);
                        g.drawImage(page_edge_slider_bottom_right_end, xoffset, 0, null);
                    }
                    if (topl.showScribbles()) {
                        g.setColor(UPLIB_ORANGE_WASH);
                        for (int j = 0;  j < page_count;  j++) {
                            ArrayList s = (ArrayList) strokes.get(j);
                            if (s != null && s.size() > 0) {
                                int x = (int)(ourwidth * (j/(float)page_count));
                                int width = (int)(ourwidth / (float)page_count) - 1;
                                g.fillOval(x + width/2 - 2, 0, 4, 4);
                            }
                        }
                    }
                }

                if ((active_reading != null) && (show_active_reading || !active_reading.paused())) {

                    float page_div = getWidth() / (float) page_count;
                    float[] rval = active_reading.percentageAlongPage();
                    g.setColor(UPLIB_ORANGE);
                    int xpos = Math.round((current_page_index + rval[0]) * page_div);
                    int width = max(1, Math.round(rval[1] * page_div));
                    g.fillRect(xpos, 0, width, getHeight());

                }

            } catch (IndexOutOfBoundsException e) {
                System.err.println("Exception e caught in PageEdge paintComponent:  " + e);
            }
        }
    }


    public abstract class ScribbleSurface extends JPanel
        implements MouseInputListener {

        protected Scribble      current_stroke;
        protected ArrayList     this_page_scribbles;
        protected Rectangle     active_region;
        protected RenderingHints current_rendering_hints;
        protected Image         backing_store = null;

        private Point           last_scribble_point;
        private long            last_redraw_event_time = 0L;
        private int             skipped_redraws = 0;
        private int             skipped_points = 0;
        private Area            current_area = null;
        private Area            new_segment = null;
        private SoftReference   backing_store_ref = null;
        private boolean         wasOpaque;

        public ScribbleSurface () {
            super();
            current_stroke = null;
            last_scribble_point = null;
            this_page_scribbles = null;
            active_region = new Rectangle(0, 0, 0, 0);
            current_rendering_hints = high_quality_rendering_mode;
            backing_store = null;
            current_area = null;
            new_segment = new Area();
            backing_store_ref = null;
            wasOpaque = isOpaque();
        }

        protected Point eventPoint (MouseEvent e) {
            if (e.getComponent() != this) {
                return SwingUtilities.convertPoint(e.getComponent(), e.getPoint(), this);
            } else {
                return e.getPoint();
            }
        }

        protected void paintComponent (Graphics g) {
            if ((current_stroke != null) && (backing_store != null)) {
                Rectangle r = g.getClipBounds();
                ((Graphics2D)g).setRenderingHints(current_rendering_hints);
                /*
                boolean bv = g.drawImage(backing_store,
                                         r.x, r.y, r.width, r.height,
                                         r.x, r.y, r.width, r.height,
                                         null);
                */
                g.drawImage(backing_store, 0, 0, null);
                // System.err.println("drew scribbles fast at " + r);
            } else {
                // System.err.println("drawing " + this_page_scribbles.size() + " scribbles slowly");
                ((Graphics2D)g).setRenderingHints(current_rendering_hints);
                if (this_page_scribbles != null) {
                    for (int i = 0;  i < this_page_scribbles.size();  i++) {
                        Scribble d = (Scribble) this_page_scribbles.get(i);
                        if (d.within(Annotation.Timestamp.CREATED, annotation_span_start, annotation_span_end))
                            d.draw((Graphics2D) g, active_region.x, active_region.y);
                    }
                }
            }
        }

        protected abstract int ourPage();

        protected abstract void saveScribble (AnnotationStreamHandler handler, Scribble to_save);

        private void addScribblePoint (Point p, long when, boolean force_redraw) {
            if ((!p.equals(last_scribble_point)) || force_redraw) {
                current_stroke.addPoint(p);
                last_scribble_point = p;
                if (((when - last_redraw_event_time) > 50) || force_redraw) {
                    // only redraw every 50 ms
                    int marker_size = Math.round(current_stroke.static_thickness);
                    repaint(0L, (int) (current_stroke.bbox.x - marker_size),
                            (int) (current_stroke.bbox.y - marker_size),
                            (int) (current_stroke.bbox.width + marker_size),
                            (int) (current_stroke.bbox.height + marker_size));
                    last_redraw_event_time = when;
                } else
                    skipped_redraws++;
            } else {
                skipped_points++;
            }
        }

        private float calcStrokeWidth (PenEvent e) {
            float factor = (float) ((PenEvent)e).getPressure() * 1.33333f;
            float thickness = factor * factor * widget_inkpots.getSelected().getSize();
            return thickness;
        }

        private void addScribblePoint (MouseEvent e, boolean force_redraw) {

            if ((!eventPoint(e).equals(last_scribble_point)) || force_redraw) {

                // System.err.println("current_stroke is " + current_stroke.hashCode() + ", current_stroke.strokes is " + ((current_stroke.strokes == null) ? "null" : Integer.toString(current_stroke.strokes.hashCode())));
                Scribble.ScribblePoint lastPoint = (current_stroke.strokes.size() > 0) ?
                    (Scribble.ScribblePoint) (current_stroke.strokes.get(current_stroke.strokes.size() - 1)) : null;
                Scribble.ScribblePoint currentPoint;
                if (e instanceof PenEvent) {
                    Point p = new Point();
                    p.setLocation(((PenEvent)e).getXFloat(), ((PenEvent)e).getYFloat());
                    float thickness = calcStrokeWidth((PenEvent) e);
                    // System.err.println("pressure is " + ((PenEvent)e).getPressure() + ", thickness is " + thickness);
                    currentPoint = current_stroke.addPoint(p, thickness);
                } else {
                    currentPoint = current_stroke.addPoint(eventPoint(e).getLocation());
                }
                last_scribble_point = eventPoint(e).getLocation();
                long when = e.getWhen();

                // update backing_store
                if ((backing_store != null) && (lastPoint != null)) {
                    if (Scribble.calculateStrokeArea(new_segment,
                                                     lastPoint.x, lastPoint.y, lastPoint.thickness,
                                                     currentPoint.x, currentPoint.y, currentPoint.thickness)) {
                        new_segment.subtract(current_area);
                        Graphics2D g = (Graphics2D) backing_store.getGraphics();
                        g.setColor(current_stroke.color);
                        g.fill(new_segment);
                        repaint(new_segment.getBounds());
                        current_area.add(new_segment);
                    }
                }

                /*
                if (((when - last_redraw_event_time) > 50) || force_redraw) {
                    // only redraw every 50 ms
                    int marker_size = Math.round(current_stroke.static_thickness);
                    repaint(0L, (int) (current_stroke.bbox.x - marker_size),
                            (int) (current_stroke.bbox.y - marker_size),
                            (int) (current_stroke.bbox.width + marker_size),
                            (int) (current_stroke.bbox.height + marker_size));
                    last_redraw_event_time = when;
                } else
                    skipped_redraws++;
                */
            } else {
                skipped_points++;
            }
        }

        private void setupBackingStore() {

            if ((backing_store_ref == null) || ((backing_store = (Image) backing_store_ref.get()) == null) ||
                (backing_store.getWidth(null) != getWidth()) || (backing_store.getHeight(null) != getHeight())) {
                // backing_store = createImage(getWidth(), getHeight());
                backing_store = getGraphicsConfiguration().createCompatibleImage(getWidth(), getHeight());
                backing_store_ref = new SoftReference(backing_store);
            }

            // this works fine if you are drawing on an opaque surface, but not if you
            // are drawing on a translucent surface.  Then you have to somehow get the area
            // under "this" drawn on the backing store, as well.

            Graphics2D g = (Graphics2D) backing_store.getGraphics();
            this.paint(g);

            g.dispose();
        }


        public void mousePressed(MouseEvent e) {
            // System.err.println("mousePressed:  " + e + ", isConsumed is " + e.isConsumed());
            if (e.isConsumed())
                return;

            int ourpage = ourPage();
            if ((this_page_scribbles != null) && widget_inkpots.active() && (e.getButton() == MouseEvent.BUTTON1)
                && (current_stroke == null)) {

                float width = widget_inkpots.getSelected().getSize();

                if (e instanceof PenEvent) {
                    PenEvent pe = (PenEvent) e;
                    // System.err.println("PenEvent:  type " + pe.getType() + ", location " + pe.getXFloat() + " " + pe.getYFloat() + ", pressure " + pe.getPressure());
                    width = calcStrokeWidth(pe);
                }

                current_rendering_hints = high_quality_rendering_mode;
                setupBackingStore();
                if (!(wasOpaque = isOpaque()))
                    setOpaque(true);
                // current_rendering_hints = low_quality_rendering_mode;
                current_area = new Area();
                Annotation.Type scribble_type = Annotation.Type.SCRIBBLE;
                if (e instanceof PenEvent) {
                    if (((PenEvent)e).getType() == PenSupport.TYPE_PEN_TIP)
                        scribble_type = Annotation.Type.VSCRIBBLE;
                    else
                        scribble_type = Annotation.Type.ERASURE;
                }
                current_stroke = new Scribble(document_id, ourpage,
                                              widget_inkpots.getSelected().getColor(),
                                              widget_inkpots.getSelected().getSize(),
                                              new Point(active_region.x, active_region.y),
                                              scribble_type);
                // System.err.println("New current_stroke " + current_stroke.hashCode());
                last_scribble_point = null;
                skipped_redraws = 0;
                skipped_points = 0;
                last_redraw_event_time = e.getWhen();
                // addScribblePoint(eventPoint(e).getLocation(), e.getWhen(), false);
                addScribblePoint(e, false);

                this_page_scribbles.add(current_stroke);
            }
            e.consume();
        }

        public void mouseDragged(MouseEvent e) {
            // System.err.println("mouseDragged:  " + e + ", isConsumed is " + e.isConsumed());
            if (e.isConsumed())
                return;
            if (current_stroke != null)
                // addScribblePoint(eventPoint(e).getLocation(), e.getWhen(), false);
                addScribblePoint(e, false);
            e.consume();
        }

        public void mouseReleased(MouseEvent e) {
            // System.err.println("mouseReleased:  " + e + ", isConsumed is " + e.isConsumed());
            if (e.isConsumed())
                return;
            int ourpage = ourPage();
            Point thispoint = eventPoint(e);
            if ((e.getButton() == MouseEvent.BUTTON1) && (current_stroke != null)) {
                // force redraw after last stroke
                // addScribblePoint(thispoint.getLocation(), e.getWhen(), true);
                addScribblePoint(e, true);
                final Scribble saved = current_stroke;
                current_stroke = null;
                // System.err.println("Finished scribble " + saved + ", hashCode " + saved.hashCode());
                saved.finish(current_area);
                saveScribble(scribble_handler, saved);
                // System.err.println("skipped " + skipped_redraws + " redraws, " + skipped_points + " points");

                /*
                  try {
                    ImageIO.write((BufferedImage) backing_store, "PNG", new javax.imageio.stream.FileImageOutputStream(new File("test.png")));
                } catch (Exception x) {
                    x.printStackTrace(System.err);
                }
                */

                backing_store = null;
                setOpaque(wasOpaque);
                repaint(current_area.getBounds());
                current_area = null;
            }
            current_rendering_hints = high_quality_rendering_mode;
            e.consume();
        }
        
        public void mouseEntered(MouseEvent e) {
            // System.err.println("pageview size is " + getWidth() + "x" + getHeight());
        }

        public void mouseExited(MouseEvent e) {
            // System.err.println("Mouse event " + e);
        }

        public void mouseClicked(MouseEvent e) {
            // System.err.println("Mouse event " + e);
        }

        public void mouseMoved(MouseEvent e) {
        }
    }

    public Pageview createPageview(DocViewer topLevel, int page_width, int page_height, int offset, int animation_time) {
        // Extracted out as a method so it can be overridden by subclasses of DocViewer
        Pageview pView = new Pageview(this, page_width, page_height, offset, animation_time);
        return pView;
    }
    
    public PageControl createPageControl(DocViewer topLevel, boolean pots_visible, int initial_inkpot) {
        // Extracted out as a method so it can be overridden by subclasses of DocViewer
        PageControl pControl = new PageControl(topLevel, pots_visible, initial_inkpot, false);
        return pControl;
    }
    
    public SearchState createSearchState() {
        // Extracted out as a method so it can be overridden by subclasses of DocViewer
        SearchState state = new SearchState();
        return state;
    }
    
    public SelectionState createSelectionState() {
        SelectionState sState = new SelectionState();
        return sState;
    }
    
    public String getSelectionText() {
    	return selection==null ? null : selection.getText();
    }

    public Point getSelectionSpan() {
        // returns the current selection as two ints, or null if no selected text
        if ((selection != null) && selection.isActive() && (selection.getBoxes() != null)) {
            return new Point(selection.getStartPosAbsolute(), selection.getEndPosAbsolute());
        } else {
            return null;
        }
    }

    public Rectangle getSelectionRect () {
        if ((selection != null) && selection.isActive()) {
            return selection.getImageRect();
        } else {
            return null;
        }        
    }

    public int getSelectionPage () {
        if ((selection != null) && selection.isActive()) {
            return selection.getStartPage();
        } else {
            return -1;
        }        
    }

    //The component that actually presents the GUI.
    public class Pageview extends ScribbleSurface
        implements MouseInputListener, MouseWheelListener,
                   InkpotsListener, FocusListener,
                   DropTargetListener, DragGestureListener, DragSourceListener {

        private final static int DROPSTATE_NO_DROP = 1;
        private final static int DROPSTATE_GOOD_DROP = 2;
        private final static int DROPSTATE_BAD_DROP = 3;

        public DocViewer topl;
        public int page_offset;
        protected int last_page_this_was_on = -1;
        protected ArrayList this_page_hotspots = null;
        protected BufferedImage last_page_image = null;   // used for animating
        protected BufferedImage this_page_image = null;
        protected Image this_page_image_slow = null;
        protected Notesheets this_page_notes = null;
        protected PageText this_page_text = null;
        protected HotSpot this_page_current_hotspot = null;
        protected long animation_start_time = 0;
        protected long animation_time_limit = 0;
        protected boolean animation_forward;
        protected GraphicsConfiguration toplGC = null;
        protected Point clickPoint = null;
        protected int clickButton = 0;
        protected Font large_search_font = null;
        protected Font small_search_font = null;
        protected Rectangle search_rect = null;
        protected Rectangle selection_rect = null;
        protected long splash_page_time = 0;
        protected Random random_generator = null;
        protected PieMenu pie_menus = null;
        protected JMenuItem find_menu_more_google = null;
        protected JMenuItem find_menu_more_uplib = null;
        protected JMenuItem find_menu_uplib = null;
        protected JMenuItem find_menu_search = null;
        protected JMenuItem show_menu_rsvp = null;
        protected JMenuItem show_menu_pos = null;
        protected JMenuItem show_menu_hotspots = null;
        protected JMenuItem show_menu_2page = null;
        protected JMenuItem go_to_menu_repo = null;
        protected JMenuItem go_to_menu_purple = null;
        protected JMenuItem go_to_menu_red = null;
        protected JMenuItem go_to_menu_green = null;
        protected JMenuItem go_to_menu_start = null;
        protected JMenuItem go_to_menu_end = null;
        protected JMenuItem top_menu_zoom = null;
        protected JMenuItem top_menu_copy = null;
        protected Cursor current_cursor = null;
        private   int       drop_status;
        protected DragSource dragSource;
        protected boolean working_on_selection;
        protected boolean app_has_focus;

        public Pageview(DocViewer toplevel, int page_width, int page_height, int offset, int animation_time) {
            super();
            try {
                this_page_hotspots = null;
                super.setBackground(BACKGROUND_COLOR);
                setBackground(WHITE);
                setOpaque(false);
                active_region = new Rectangle(0, 0, page_width, page_height);
                Dimension d = new Dimension(page_width, page_height);
                setLayout(null);
                setPreferredSize(d);
                setMaximumSize(d);
                setMinimumSize(d);
                setFocusable(false);
                // System.err.println("Max size is " + getMaximumSize());
                topl = toplevel;
                page_offset = offset;
                last_page_this_was_on = -1;
                this_page_current_hotspot = null;
                animation_time_limit = animation_time;
                this_page_text = null;
                splash_page_time = 0;
                current_rendering_hints = high_quality_rendering_mode;
                current_cursor = our_cursor;
                working_on_selection = false;
                app_has_focus = false;

                // addMouseListener(this);
                // addMouseMotionListener(this);
                PenSupport.getInstance().addMouseInputListener(this, this);
                addMouseWheelListener(this);

                setupPieMenus();

                dragSource = DragSource.getDefaultDragSource();
                this.setTransferHandler(new DVTransferHandler());
                this.dragSource.createDefaultDragGestureRecognizer(this,
                                                                   DnDConstants.ACTION_COPY,
                                                                   this);
                this.drop_status = DROPSTATE_NO_DROP;
                this.setDropTarget(new DropTarget(this, DnDConstants.ACTION_COPY_OR_MOVE, this, true));

                // ToolTipManager.sharedInstance().registerComponent(this);
                setToolTipText("foo");

            } catch (Throwable t) {
                t.printStackTrace(System.err);
            }
        }

        protected void setupPieMenus() {

            JMenuItem item;

            // setup static parameters
            PieMenu.setAllAutoOpen(true);
            PieMenu.setAllTapHoldOpen();
            // PieMenu.setAllInitialDelay(500);    // ms
            // PieMenu.setAllSubmenuDelay(300);    // ms
            PieMenu.setDefaultBigRadius(min(115, active_region.width/4));
            PieMenu.setDefaultFillColor(BACKGROUND_COLOR);
            PieMenu.setDefaultLineColor(LEGEND_COLOR);
            PieMenu.setDefaultFontColor(BLACK);
            PieMenu.setDefaultSelectedColor(TOOLS_COLOR);

            // now create the menus
            PieMenu top = new PieMenu();

            {
                PieMenu go_to = new PieMenu("Go to");
                go_to_menu_repo = go_to.add("Repo", new ImageIcon(small_uplib_logo));
                go_to_menu_repo.addActionListener(topl);
                go_to_menu_start = go_to.add("Start");
                go_to_menu_start.addActionListener(topl);
                go_to_menu_purple = go_to.add("Purple");
                go_to_menu_purple.setIcon(bookmarks[0].makeIcon(32, 32, true));
                go_to_menu_purple.setDisabledIcon(bookmarks[0].makeIcon(32, 32, false));
                go_to_menu_purple.addActionListener(topl);
                go_to_menu_green = go_to.add("Green", bookmarks[1].makeIcon(32, 32, true));
                go_to_menu_green.setDisabledIcon(bookmarks[1].makeIcon(32, 32, false));
                go_to_menu_green.addActionListener(topl);
                go_to_menu_red = go_to.add("Red", bookmarks[2].makeIcon(32, 32, true));
                go_to_menu_red.setDisabledIcon(bookmarks[2].makeIcon(32, 32, false));
                go_to_menu_red.addActionListener(topl);
                go_to_menu_end = go_to.add("End");
                go_to_menu_end.addActionListener(topl);
                top.add(go_to);
            }


            top.add("");

            {
                PieMenu find = new PieMenu("Find");

                find_menu_more_uplib = find.add("More\n(UpLib)");
                find_menu_more_uplib.addActionListener(topl);

                find.add("");

                find_menu_more_google = find.add("More\n(Google)");
                find_menu_more_google.addActionListener(topl);

                find.add("");

                find_menu_search = find.add("Search");
                find_menu_search.addActionListener(topl);

                find_menu_uplib = find.add("UpLib");
                find_menu_uplib.addActionListener(topl);

                find.add("");
                top.add(find);
            }

            top_menu_copy = top.add("Copy");
            top_menu_copy.addActionListener(topl);

            {
                PieMenu show = new PieMenu("Show");

                show.add("Normal").addActionListener(topl);

                show_menu_rsvp = show.add("RSVP");
                show_menu_rsvp.addActionListener(topl);

                show_menu_pos = show.add("P.O.S");
                show_menu_pos.addActionListener(topl);

                show_menu_2page = show.add("2 Page");
                show_menu_2page.addActionListener(topl);

                show_menu_hotspots = show.add("Hotspots");
                show_menu_hotspots.addActionListener(topl);

                show.add("Thumbnails").addActionListener(topl);

                top.add(show);
            }

            top_menu_zoom = top.add("Zoom");
            top_menu_zoom.addActionListener(topl);

            top.addPieMenuTo(this);
            this.pie_menus = top;
        }

        public class Note extends ScribbleSurface
            implements MouseWheelListener, FocusListener, DocumentListener, InkpotsListener, Annotation {

            final static int    UL_CORNER = 1;
            final static int    LL_CORNER = 2;
            final static int    UR_CORNER = 3;
            final static int    LR_CORNER = 4;

            final static float  CORNER_DRAG_DISTANCE = 16.0F;
            final static int    DRAG_CORNER_RECT_SIZE = 32;

            private int         ourpage;
            private int         ournumber;
            private Point       drag_point;
            private int         stretch_corner;
            private Point       stretch_offset;
            private boolean     raised = false;
            private JTextPane   text = null;
            private boolean     in_text = false;
            public boolean      layout_dirty;
            public boolean      data_dirty;

            private Annotation.Timestamp created;
            private Annotation.Timestamp last_modified;

            private class ContentUpdater implements DocViewerCallback {
                private Note to_set;
                public ContentUpdater (Note to_set) {
                    this.to_set = to_set;
                }
                public void call (Object o) {
                    // System.err.println("@@@ value arrived for note " + to_set + ":  " + o);
                    if (o instanceof Vector) {
                        to_set.setContents((Vector)o);
                        to_set.repaint();
                    }
                }
                public void flush () {};
            }

            public Note (NoteFrame frame) {
                super();
                initialize(frame.page, frame.number, frame.x, frame.y, frame.width, frame.height, frame.background, false);
                frame.note_pane = new SoftReference(this);
            }

            public Note (int pageno, int note_no, int x, int y, int width, int height, Color background) {
                super();
                initialize(pageno, note_no, x, y, width, height, background, true);
            }

            private void initialize (int pageno, int note_no, int x, int y, int width, int height,
                                     Color background, boolean really_new) {

                // it's attached to a particular page
                ourpage = pageno;
                ournumber = note_no;
                data_dirty = false;
                layout_dirty = true;

                // set a property that's available when encoding layout stack
                putClientProperty("note-number", new Integer(ournumber));

                // we want to be able to scribble on it
                this_page_scribbles = new ArrayList();

                setLocation(new Point(x, y));
                setSize(width, height);
                active_region.x = 0;
                active_region.y = 0;
                active_region.width = width;
                active_region.height = height;
                setPreferredSize(new Dimension(width, height));
                setBackground((background == null) ? NOTE_BACKGROUND : background);
                created = null;
                last_modified = null;

                setLayout(new BoxLayout(this, BoxLayout.X_AXIS));
                setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
                DefaultStyledDocument d = new DefaultStyledDocument();
                text = new JTextPane(d);
                text.setBackground(CLEAR);
                text.setMargin(new Insets(1, 1, 1, 1));
                text.setOpaque(false);
                text.setSize(width - 20, height - 20);
                Style s = d.getStyle("default");
                StyleConstants.setItalic(s, true);
                s = d.addStyle("URL", s);
                StyleConstants.setForeground(s, BLUE_INK_COLOR);
                StyleConstants.setUnderline(s, true);
                // text.setLineWrap(true);
                // text.setWrapStyleWord(true);
                // text.addMouseListener(this);
                // text.addMouseMotionListener(this);
                PenSupport.getInstance().addMouseInputListener(this, text);
                text.addMouseWheelListener(this);
                text.addFocusListener(topl);
                text.addFocusListener(this);
                text.getCaret().setBlinkRate(0);        // no blinking cursors
                text.setCaretColor(DARK_COLOR);
                text.setSelectionColor(TOOLS_COLOR);
                d.addDocumentListener(this);
                add(text);

                addMouseWheelListener(this);
                PenSupport.getInstance().addMouseInputListener(this, this);

                stretch_corner = 0;
                stretch_offset = null;
                setOpaque(false);

                if (!really_new && (note_loader != null)) {
                    Object o = note_loader.get(document_id, ourpage, ournumber, new ContentUpdater(this));
                }
            }

            public int ourPage() {
                return ourpage;
            }

            public int number() {
                return ournumber;
            }

            public void setTextCursor (Cursor c) {
                if (c == null)
                    text.setCursor(Cursor.getPredefinedCursor(Cursor.TEXT_CURSOR));
                else
                    text.setCursor(c);
            }

            public void inkpotChanged (boolean active, Inkpots.Pot current) {
                if (active) {
                    Cursor c = current.getDrawingCursor();
                    setCursor(c);
                    setTextCursor(c);
                } else {
                    setCursor(our_cursor);
                    setTextCursor(null);
                }
            }

            private int getStretchCorner (Point p) {
                if (p.distance(new Point(0,0)) < CORNER_DRAG_DISTANCE)
                    return UL_CORNER;
                else if (p.distance(new Point(0,getHeight())) < CORNER_DRAG_DISTANCE)
                    return LL_CORNER;
                else if (p.distance(new Point(getWidth(),0)) < CORNER_DRAG_DISTANCE)
                    return UR_CORNER;
                else if (p.distance(new Point(getWidth(), getHeight())) < CORNER_DRAG_DISTANCE)
                    return LR_CORNER;
                else
                    return 0;
            }

            private Point getStretchOffset (Point p, int corner) {
                if (corner == UL_CORNER)
                    return new Point(0 - p.x, 0 - p.y);
                else if (corner == LL_CORNER)
                    return new Point(0 - p.x, getHeight() - p.y);
                else if (corner == UR_CORNER)
                    return new Point(getWidth() - p.x, 0 - p.y);
                else if (corner == LR_CORNER)
                    return new Point(getWidth() - p.x, getHeight() - p.y);
                else
                    return null;
            }

            public void focus() {
                // System.err.println("" + text.hashCode() + ":  Asking for focus:  text " + (text.isFocusOwner() ? "is" : "is not") + " focus owner");
                if (!text.isFocusOwner())
                    text.requestFocusInWindow();
            }

            protected void saveScribble (AnnotationStreamHandler handler, Scribble to_save) {
                data_dirty = true;
            }

            public void forceFocus() {
                System.err.println("" + text.hashCode() + ":  forcing focus");
                text.requestFocusInWindow();
            }

            private Rectangle getStretchRectangle (Point p) {
                Point current_location = getLocation();
                Dimension current_size = getSize();
                Rectangle r = null;
                if (stretch_corner == UL_CORNER)
                    r = new Rectangle(min(current_location.x + current_size.width - DRAG_CORNER_RECT_SIZE, current_location.x + p.x),
                                      min(current_location.y + current_size.height - DRAG_CORNER_RECT_SIZE, current_location.y + p.y),
                                      max(current_size.width - p.x, DRAG_CORNER_RECT_SIZE),
                                      max(current_size.height - p.y, DRAG_CORNER_RECT_SIZE));
                else if (stretch_corner == LL_CORNER)
                    r = new Rectangle(min(current_location.x + current_size.width - DRAG_CORNER_RECT_SIZE, current_location.x + p.x), current_location.y,
                                      max(current_size.width - p.x, DRAG_CORNER_RECT_SIZE), max(p.y, DRAG_CORNER_RECT_SIZE));
                else if (stretch_corner == UR_CORNER)
                    r = new Rectangle(current_location.x,
                                      min(current_location.y + current_size.height - DRAG_CORNER_RECT_SIZE, current_location.y + p.y),
                                      max(p.x, DRAG_CORNER_RECT_SIZE), max(current_size.height - p.y, DRAG_CORNER_RECT_SIZE));
                else if (stretch_corner == LR_CORNER)
                    r = new Rectangle(current_location.x, current_location.y,
                                      max(p.x, DRAG_CORNER_RECT_SIZE), max(p.y, DRAG_CORNER_RECT_SIZE));
                else
                    r = new Rectangle(current_location.x, current_location.y,
                                      current_size.width, current_size.height);
                return r;
            }

            public void mousePressed(MouseEvent e) {
                // System.err.println("mousePressed:  " + e);

                /*
                  States:

                  in corner or control-key down -> moving or resizing, no text activity
                  click past end of text -> moving, or beginning stroke, no text activity
                  otherwise:  in text
                */

                if (e.isConsumed())
                    return;

                Point p = eventPoint(e);

                in_text = false;
                raised = false;
                drag_point = null;
                if ((stretch_corner = getStretchCorner(p)) != 0) {
                    // resizing the note
                    stretch_offset = getStretchOffset(p, stretch_corner);
                    // System.err.println("offset is " + stretch_offset + ", location is " + getLocation() + ", size is " + getSize());
                    repaint();
                    e.consume();
                } else if (e.isControlDown() ||
                           (this.getComponentAt(p) != text) ||
                           (text.viewToModel(p) >= text.getDocument().getLength())) {
                    // past end of text
                    if (e.isControlDown() || (!widget_inkpots.active())) {
                        // dragging note
                        drag_point = p;
                    } else {
                        super.mousePressed(e);
                    }
                    e.consume();
                } else {
                    focus();
                    in_text = true;
                }
            }

            private void changePage (int newpage, int newx, JComponent oldparent) {
                if ((newpage < 0) || (newpage >= page_count)) {
                } else {
                    ArrayList ourpage_sheets = (ArrayList) note_sheets.get(ourpage);
                    ArrayList newpage_sheets = (ArrayList) note_sheets.get(newpage);
                    NoteFrame theframe = null;
                    for (int i = 0;  i < ourpage_sheets.size();  i++) {
                        NoteFrame tmp = (NoteFrame) ourpage_sheets.get(i);
                        if (tmp.number == ournumber)
                            theframe = tmp;
                    }
                    if (theframe != null) {
                        layout_dirty = true;
                        data_dirty = true;
                        ourpage_sheets.remove(theframe);
                        int newnumber = 1;
                        for (int i = 0;  i < newpage_sheets.size();  i++) {
                            NoteFrame tmp = (NoteFrame) newpage_sheets.get(i);
                            if (tmp.number >= newnumber)
                                newnumber = tmp.number + 1;
                            tmp.stacking_order += 1;
                        }
                        theframe.stacking_order = 0;
                        theframe.number = newnumber;
                        ournumber = newnumber;
                        theframe.page = newpage;
                        ourpage = newpage;
                        theframe.x = newx;
                        newpage_sheets.add(theframe);
                        if (oldparent != null) {
                            calculateNoteStackingOrder(oldparent.getComponents(), ourpage_sheets);
                        }
                    }
                }
            }

            private Point moveDelta (int deltax, int deltay) {

                Point location = getLocation();

                if ((deltax != 0) || (deltay != 0)) {

                    if (ourpage == 0) {
                        location.x = max(10 - getWidth(), location.x + deltax);
                    } else if (ourpage == (page_count - 1)) {
                        location.x = min(getParent().getWidth() - 10, location.x + deltax);
                    } else
                        location.x = location.x + deltax;
                    location.y = location.y + deltay;
                    setLocation(location);
                    layout_dirty = true;
                }
                return location;
            }

            private Point handleOffpageLocations (Point location) {

                JComponent parent = (JComponent) getParent();
                int parent_width = (parent != null) ? parent.getWidth() : 0;
                int parent_height = (parent != null) ? parent.getHeight() : 0;

                if (location.x > parent_width) {
                    // off-screen to right
                    location.x = location.x - parent_width;
                    setLocation(location);
                    parent.remove(this);
                    int lastpage = ourpage;
                    changePage(ourpage + 1, location.x, parent);
                    saveNotes(lastpage, true);
                    saveNotes(lastpage + 1, true);
                    layout_dirty = true;
                } else if ((location.x + getWidth()) < 0) {
                    // off-screen to left
                    location.x = parent_width + location.x;
                    setLocation(location);
                    parent.remove(this);
                    int lastpage = ourpage;
                    changePage(ourpage - 1, location.x, parent);
                    saveNotes(lastpage, true);
                    saveNotes(lastpage - 1, true);
                    layout_dirty = true;
                } else if (location.y > parent.getHeight()) {
                    // off-screen at bottom, so delete
                    location.y = -(getHeight() + 10);
                    setLocation(location);
                    layout_dirty = true;
                }
                return location;
            }

            public void mouseDragged(MouseEvent e) {
                // System.err.println("mouseDragged:  " + e);

                if (e.isConsumed())
                    return;
                if (in_text) {
                    // let text widget handle this
                    return;
                }

                Point p = eventPoint(e);

                if (stretch_corner != 0) {
                    p.x += stretch_offset.x;
                    p.y += stretch_offset.y;
                    Rectangle old = getBounds(null);
                    Rectangle r = getStretchRectangle(p);
                    // System.err.println("Resizing from " + old + " to " + r);
                    setLocation(new Point(r.x, r.y));
                    setSize (r.width, r.height);
                    // setBounds(r.x, r.y, r.width, r.height);
                    Rectangle dirty = r.union(old);
                    // getParent().invalidate();
                    getParent().repaint(dirty.x, dirty.y, dirty.width + 1, dirty.height + 1);
                    revalidate();
                    layout_dirty = true;
                } else if (drag_point != null) {
                    JComponent parent = (JComponent) getParent();
                    if ((drag_point.distance(eventPoint(e)) > 10) &&
                        (parent.getComponent(0) != ((Component) this)) &&
                        needsRaise()) {
                        parent.remove(this);
                        parent.add(this, 0);
                        System.err.println("** Raising note " + text.hashCode() + " (in drag)");
                        // parent.repaint();
                        raised = true;
                    }
                    moveDelta(e.getX() - drag_point.x, e.getY() - drag_point.y);
                    revalidate();
                    layout_dirty = true;
                } else
                    super.mouseDragged(e);
                e.consume();
            }

            public void mouseReleased(MouseEvent e) {
                // System.err.println("mouseReleased:  " + e);

                String link;

                if (e.isConsumed())
                    return;
                if (in_text) {
                    // let text widget deal with this
                    in_text = false;
                    return;
                }

                Point p = eventPoint(e);

                if (stretch_corner != 0) {
                    p.x += stretch_offset.x;
                    p.y += stretch_offset.y;
                    Rectangle old = getBounds(null);
                    Rectangle r = getStretchRectangle(p);
                    // System.err.println("Resizing from " + old + " to " + r);
                    setLocation(new Point(r.x, r.y));
                    setPreferredSize(new Dimension(r.width, r.height));
                    setSize (r.width, r.height);
                    // setBounds(r.x, r.y, r.width, r.height);
                    active_region.width = r.width;
                    active_region.height = r.height;
                    Rectangle dirty = r.union(old);
                    getParent().repaint(dirty.x, dirty.y, dirty.width + 1, dirty.height + 1);
                    stretch_corner = 0;
                    layout_dirty = true;
                } else if (drag_point != null) {
                    JComponent parent = (JComponent) getParent();
                    Point location = moveDelta(e.getX() - drag_point.x, e.getY() - drag_point.y);
                    handleOffpageLocations(location);
                    if (drag_point.distance(eventPoint(e)) < 10) {
                        // essentially a click
                        if (parent.getComponentCount() > 1) {
                            if (parent.getComponent(0) == ((Component) this)) {
                                if (!raised && needsSubmerge()) {
                                    System.err.println("** Submerging note " + text.hashCode());
                                    if (parent.getComponent(1) instanceof Note)
                                        ((Note)(parent.getComponent(1))).focus();
                                    parent.remove(this);
                                    parent.add(this);
                                }
                            } else if (needsRaise()) {
                                parent.remove(this);
                                parent.add(this, 0);
                                System.err.println("** Raising note " + text.hashCode());
                            }
                        }
                        // parent.repaint();
                    }
                    revalidate();
                    if ((parent.getComponentCount() > 0) &&
                        (parent.getComponent(0) == ((Component) this))) {
                        forceFocus();
                    }
                    layout_dirty = true;
                } else {
                    super.mouseReleased(e);
                }
                e.consume();
            }

            private String linkText (Element elm) {
                if (elm.isLeaf()) {
                    Object style = elm.getAttributes().getAttribute(StyleConstants.NameAttribute);
                    if ((style != null) && (style instanceof String) && ((String) style).equals("URL")) {
                        int start_offset = elm.getStartOffset();
                        try {
                            return elm.getDocument().getText(start_offset, elm.getEndOffset() - start_offset);
                        } catch (BadLocationException x) {
                            System.err.println("** Unexpected BadLocationException");
                            x.printStackTrace(System.err);
                        }
                    }
                }
                return null;
            }

            private String onLink (int pos) {
                Document d = text.getDocument();
                if (d instanceof StyledDocument) {
                    Element elm = ((StyledDocument)d).getCharacterElement(pos);
                    while (!elm.isLeaf())
                        elm = elm.getElement(pos);
                    return linkText(elm);
                }
                return null;
            }

            public void mouseClicked(MouseEvent e) {
                int pos = text.viewToModel(eventPoint(e));
                String link = null;

                if (e.getButton() == MouseEvent.BUTTON3) {
                    if (note_saver != null) {
                        System.err.println("data_dirty is " + data_dirty + ", layout_dirty is " + layout_dirty);
                        try {
                            note_saver.addAnnotation(this, document_id, ourpage, ournumber);
                            note_saver.flush();
                            data_dirty = false;
                        } catch (Exception x) {
                            x.printStackTrace(System.err);
                        }
                    }
                }   

                if ((pos < text.getDocument().getLength()) && ((link = onLink(pos)) != null)) {
                    System.err.println("URL " + link + " clicked on");
                    if (page_opener != null) {
                        try {
                            page_opener.call(new URL(link));
                        } catch (java.net.MalformedURLException x) {
                            System.err.println("Bad URL " + link);
                        }
                    }
                }
                    
                if ((getParent().getComponent(0) == (Component) this) && (!text.isFocusOwner())) {
                    System.err.println("requesting focus for note page" + text.hashCode());
                    text.requestFocusInWindow();
                }
            }

            public void mouseMoved(MouseEvent e) {
                int new_stretch_corner = getStretchCorner(eventPoint(e));
                if (new_stretch_corner != 0) {
                    stretch_offset = null;
                    if (new_stretch_corner == UL_CORNER) {
                        repaint(0, 0, (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    } else if (new_stretch_corner == LL_CORNER) {
                        repaint(0, getHeight() - (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    } else if (new_stretch_corner == UR_CORNER) {
                        repaint(getWidth() - (DRAG_CORNER_RECT_SIZE + 1), 0, (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    } else if (new_stretch_corner == LR_CORNER) {
                        repaint(getWidth() - (DRAG_CORNER_RECT_SIZE + 1), getHeight() - (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    }
                } else {
                    if (stretch_corner == UL_CORNER) {
                        repaint(0, 0, (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    } else if (stretch_corner == LL_CORNER) {
                        repaint(0, getHeight() - (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    } else if (stretch_corner == UR_CORNER) {
                        repaint(getWidth() - (DRAG_CORNER_RECT_SIZE + 1), 0, (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    } else if (stretch_corner == LR_CORNER) {
                        repaint(getWidth() - (DRAG_CORNER_RECT_SIZE + 1), getHeight() - (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    }
                }
                stretch_corner = new_stretch_corner;
            }

            public void mouseExited (MouseEvent e) {
                if (stretch_corner != 0 && (stretch_offset == null)) {
                    if (stretch_corner == UL_CORNER) {
                        repaint(0, 0, (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    } else if (stretch_corner == LL_CORNER) {
                        repaint(0, getHeight() - (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    } else if (stretch_corner == UR_CORNER) {
                        repaint(getWidth() - (DRAG_CORNER_RECT_SIZE + 1), 0, (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    } else if (stretch_corner == LR_CORNER) {
                        repaint(getWidth() - (DRAG_CORNER_RECT_SIZE + 1), getHeight() - (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1), (DRAG_CORNER_RECT_SIZE + 1));
                    }
                    stretch_corner = 0;
                }
            }                

            public void mouseWheelMoved (MouseWheelEvent e) {
                Color currentbg = getBackground();
                int alpha = max(0, min(255, (int) (currentbg.getAlpha() + (e.getWheelRotation() * 5))));
                setBackground(new Color(currentbg.getRed(), currentbg.getGreen(), currentbg.getBlue(), alpha));
                layout_dirty = true;
            }

            protected void paintComponent(Graphics g) {

                // Note

                if ((current_stroke != null) && (backing_store != null)) {
                    super.paintComponent(g);
                    return;
                }

                String numbertext = Integer.toString(ournumber);
                g.setFont(NOTE_NUMBER_FONT);
                Rectangle2D bounds = g.getFontMetrics(NOTE_NUMBER_FONT).getStringBounds(numbertext, g);

                ((Graphics2D)g).setRenderingHints(current_rendering_hints);

                g.setColor(getBackground());
                g.fillRect(0, 0, getWidth(), getHeight());
                g.setColor(TOOLS_COLOR);
                g.setFont(NOTE_NUMBER_FONT);
                int xl = Math.round(getWidth() - 10 - (int) bounds.getWidth());
                int yl = Math.round(getHeight() - 10);
                g.drawString(numbertext, xl, yl);
                // System.err.println("drew " + bounds.getWidth() + "x" + bounds.getHeight() + " \"" + numbertext + "\" at " + xl + ", " + yl + " in " + getWidth() + "," + getHeight());
                g.setColor(LEGEND_COLOR);
                g.drawRect(0, 0, getWidth() - 1, getHeight() - 1);
                super.paintComponent(g);
                if (stretch_corner != 0) {
                    int x = 0, y = 0;
                    if (stretch_corner == UL_CORNER) {
                        x = 0;
                        y = 0;
                    } else if (stretch_corner == LL_CORNER) {
                        x = 0;
                        y = getHeight();
                    } else if (stretch_corner == UR_CORNER) {
                        x = getWidth();
                        y = 0;
                    } else if (stretch_corner == LR_CORNER) {
                        x = getWidth();
                        y = getHeight();
                    }
                    g.drawImage(note_corner_image, x - DRAG_CORNER_RECT_SIZE, y - DRAG_CORNER_RECT_SIZE, null);
                }

            }

            private boolean needsRaise() {
                Rectangle ourBounds = getBounds();
                Component[] wins = ((Container) getParent()).getComponents();
                for (int i = 0;  (i < wins.length) && (wins[i] != this);  i++) {
                    if (wins[i].getBounds().intersects(ourBounds))
                        return true;
                }
                return false;
            }

            private boolean needsSubmerge() {
                Rectangle ourBounds = getBounds();
                Component[] wins = ((Container) getParent()).getComponents();
                for (int i = (wins.length - 1);  (i >= 0) && (wins[i] != this);  i--) {
                    if (wins[i].getBounds().intersects(ourBounds))
                        return true;
                }
                return false;
            }

            // FocusListener methods

            public void focusGained (FocusEvent e) {
                if (e.getComponent() == (Component) text) {
                    if (widget_inkpots.active()) {
                        text.getCaret().setVisible(false);
                        Cursor c = widget_inkpots.getSelected().getDrawingCursor();
                        setCursor(c);
                        setTextCursor(c);
                    } else {
                        setCursor(our_cursor);
                        setTextCursor(null);
                        text.getCaret().setVisible(true);
                    }
                }
                System.err.println("" + text.hashCode() + ":  gained focus");
                // save if necessary
                if ((layout_dirty || data_dirty) && (note_saver != null)) {
                    try {
                        if (data_dirty)
                            note_saver.addAnnotation(this, document_id, ourpage, number());
                        data_dirty = false;
                    } catch (IOException x) {
                        x.printStackTrace(System.err);
                    }
                }
            }
            
            public void focusLost (FocusEvent e) {
                text.getCaret().setVisible(false);
                Component c = e.getOppositeComponent();
                if (c != null)
                    System.err.println("lost focus to " + c.getClass().getName() + " " + c.hashCode());
                // save if necessary
                if ((data_dirty || layout_dirty) && (note_saver != null)) {
                    try {
                        if (data_dirty)
                            note_saver.addAnnotation(this, document_id, ourpage, number());
                        data_dirty = false;
                    } catch (IOException x) {
                        x.printStackTrace(System.err);
                    }
                }
            }

            // DocumentListener methods

            public void changedUpdate (DocumentEvent e) {
                data_dirty = true;
            }

            public void insertUpdate (DocumentEvent e) {
                data_dirty = true;
            }

            public void removeUpdate (DocumentEvent e) {
                data_dirty = true;
            }

            // code to get and set contents

            public Vector getContents () {
                
                Vector contents = getElements(text.getDocument().getDefaultRootElement(), 0);
                for (int i = 0;  i < this_page_scribbles.size();  i++) {
                    contents.add(this_page_scribbles.get(i));
                }
                return contents;
            }

            private Vector getElements (Element e, int offset) {

                Vector contents = new Vector();

                if (e.isLeaf()) {
                    // is it a link?
                    String t;
                    if ((t = linkText(e)) != null) {
                        try {
                            URL u = new URL(t);
                            contents.add(u);
                        } catch (java.net.MalformedURLException x) {
                            System.err.println("Bad URL in text:  \"" + t + "\" -- adding as text:");
                            contents.add(t);
                        }
                    } else if ("icon".equals(e.getName()) &&
                               e.getAttributes().isDefined(StyleConstants.CharacterConstants.IconAttribute)) {
                        Object o = e.getAttributes().getAttribute(StyleConstants.CharacterConstants.IconAttribute);
                        System.err.println("IconAttribute value is " + o);
                        if (o instanceof ImageIcon) {
                            BufferedImage bi = EmacsKeymap.convertImageIconToImage((ImageIcon)o);
                            contents.add(new ImageHolder(bi));
                        }
                    } else {
                        // plain text
                        int start = e.getStartOffset();
                        int end = e.getEndOffset();
                        try {
                            t = e.getDocument().getText(start, end - start);
                            contents.add(t);
                        } catch (BadLocationException exc) {
                            exc.printStackTrace(System.err);
                        }
                    }
                } else {
                    for (int limit = e.getElementCount(), i = 0;  i < limit;  i++) {
                        Element el = e.getElement(i);
                        contents.addAll(getElements(el, offset + 1));
                    }
                }
                return contents;
            }

            private void setContents (Vector contents) {

                // clear existing contents
                StyledDocument d = text.getStyledDocument();
                Style url_style = d.getStyle("URL");
                try {
                    d.remove(0, d.getLength());
                } catch (BadLocationException x) {
                    x.printStackTrace(System.err);
                }
                this_page_scribbles = new ArrayList();

                Iterator elements = contents.iterator();
                while (elements.hasNext()) {
                    Object o = elements.next();
                    if (o instanceof String) {  // text
                        try {
                            d.insertString(d.getLength(), (String) o, null);
                        } catch (BadLocationException x) {
                            x.printStackTrace(System.err);
                        }
                    } else if (o instanceof URL) {
                        try {
                            d.insertString(d.getLength(), ((URL)o).toExternalForm(), url_style);
                        } catch (BadLocationException x) {
                            x.printStackTrace(System.err);
                        }
                    } else if (o instanceof ImageHolder) {
                        ImageIcon icon = new ImageIcon(((ImageHolder) o).image());
                        text.setCaretPosition(d.getLength());
                        text.moveCaretPosition(d.getLength());
                        text.insertIcon(icon);
                    } else if (o instanceof Scribble) {
                        this_page_scribbles.add(o);
                    } else if (o instanceof Annotation.Timestamp) {
                        int k = ((Annotation.Timestamp)o).getKind();
                        if (k == Annotation.Timestamp.CREATED)
                            this.created = (Annotation.Timestamp) o;
                        else if ((k == Annotation.Timestamp.MODIFIED) &&
                                 ((this.last_modified == null) ||
                                  (this.last_modified.before((Annotation.Timestamp)o))))
                            this.last_modified = (Annotation.Timestamp) o;
                    }
                }

                data_dirty = false;
            }

            public boolean within (int kind, Date after, Date before) {
                Date d;
                if (kind == Annotation.Timestamp.CREATED)
                    d = this.created;
                else if (kind == Annotation.Timestamp.MODIFIED)
                    d = (this.last_modified == null) ? this.created : this.last_modified;
                else
                    return false;

                if (d == null)
                    return (after == null);
                else if ((before != null) && (!d.before(before)))
                    return false;
                else if ((after != null) && (!d.after(after)))
                    return false;
                else
                    return true;
            }

            // Annotation methods

            public int pageIndex() {
                return ourPage();
            }

            public String docId() {
                return document_id;
            }

            public Timestamp timestamp() {
                return ((last_modified == null) ? created : last_modified);
            }

            public Type getType () {
                return Annotation.Type.NOTE;
            }

            public java.awt.Rectangle getBounds() {
                return super.getBounds(null);
            }

            // on finalize, write out contents

            protected void finalize () throws Throwable {
                System.err.println("finalizing Note " + document_id + "/" + ourpage + "/" + number());
                if (data_dirty && note_saver != null) {
                    try {
                        note_saver.addAnnotation(this, document_id, ourpage, number());
                        data_dirty = false;
                    } catch (Exception x) {
                        x.printStackTrace(System.err);
                    }
                }
                super.finalize();
            }
        }

        private int nextNotePageNumber(int pageno) {

            ArrayList notes = (ArrayList) note_sheets.get(pageno);

            int number = 1;
            for (int i = 0;  i < notes.size();  i++) {
                NoteFrame nf = (NoteFrame) notes.get(i);
                if (nf.number >= number)
                    number = nf.number + 1;
            }
            return number;
        }

        private Note getNote (NoteFrame f) {
            Note n = (f.note_pane != null) ? ((Note) (f.note_pane.get())) : null;
            if (n == null) {
                System.err.println("creating new note for " + f);
                n = new Note(f);
                n.layout_dirty = false;
                n.addMouseListener(this);
                n.addMouseMotionListener(this);
                n.inkpotChanged(widget_inkpots.active(), widget_inkpots.getSelected());
            }
            return n;
        }

        private Note newNoteSheet (int x, int y, int width, int height) {

            Notesheets sheets = (Notesheets) note_sheets.get(ourPage());
            if (sheets == null) {
                sheets = new Notesheets(0, ourPage());
                note_sheets.set(ourPage(), sheets);
                this_page_notes = sheets;
            }
            Note n = new Note (ourPage(), nextNotePageNumber(ourPage()), x, y, width, height, null);
            add(n, 0);
            n.addMouseListener(n);
            n.addMouseMotionListener(n);
            NoteFrame nf = new NoteFrame (ourPage(), n.number(), x, y, width, height, 0, n.getBackground());
            nf.note_pane = new SoftReference(n);
            sheets.add(0, nf);
            for (int i = 1;  i < sheets.size();  i += 1) {
                // push everything else down one
                NoteFrame n2 = (NoteFrame) sheets.get(i);
                n2.stacking_order += 1;
            }
            n.layout_dirty = true;
            n.inkpotChanged(widget_inkpots.active(), widget_inkpots.getSelected());
            n.focus();

            System.err.println("created new note sheet " + n + "/" + n.number());
            return n;
        }

        public void newNoteSheet () {

            if (random_generator == null)
                random_generator = new Random();

            newNoteSheet(random_generator.nextInt(page_width/2),
                         random_generator.nextInt(page_height/2),
                         page_width/3, page_height/6);
        }

        private void saveNotes(int pageno, boolean force_layout) {

            if ((note_saver != null) && (pageno >= 0) && (pageno < page_count)) {

                Notesheets notes = (Notesheets) note_sheets.get(pageno);
                boolean layout_dirty = force_layout;

                if ((notes != null) && (notes.size() > 0)) {

                    System.err.println("Saving " + notes.size() + " notes for page " + pageno + "...");

                    for (int i = 0;  i < notes.size();  i++) {
                        NoteFrame nf = (NoteFrame) notes.get(i);
                        Note n = (nf.note_pane != null) ? (Note) (nf.note_pane.get()) : null;
                        if (n != null) {
                            if (n.layout_dirty) {
                                layout_dirty = true;
                                nf.x = n.getX();
                                nf.y = n.getY();
                                nf.width = n.getWidth();
                                nf.height = n.getHeight();
                                nf.background = n.getBackground();
                                n.layout_dirty = false;
                            }
                            if (n.data_dirty) {
                                System.err.println("    saving note " + n.number());
                                try {
                                    note_saver.addAnnotation(n, document_id, n.ourPage(), n.number());
                                    n.data_dirty = false;
                                } catch (IOException x) {
                                    x.printStackTrace(System.err);
                                }
                            }
                        }
                    }
                }

                if (layout_dirty) {
                    try {
                        System.err.println("    saving layout");
                        Component[] c = getComponents();
                        calculateNoteStackingOrder(c, notes);
                        note_saver.addAnnotation(notes, document_id, pageno, 0);
                    } catch (IOException x) {
                        x.printStackTrace(System.err);
                    }
                    System.err.println("...finished saving.");
                }
            }
        }

        private void calculateNoteStackingOrder (Component[] c, ArrayList sheets) {
            for (int i = 0;  i < sheets.size();  i++) {
                NoteFrame nf = (NoteFrame) sheets.get(i);
                for (int j = 0;  j < c.length;  j++) {
                    if (c[j] instanceof Note) {
                        Note n = (Note) c[j];
                        if ((n.ourPage() == nf.page) && (n.number() == nf.number)) {
                            nf.stacking_order = j;
                        }
                    }
                }
            }
        }

        private void changeNotes (int oldpageno, int newpageno) {
            
            saveNotes(oldpageno, false);

            Component[] components = getComponents();
            for (int i = 0;  i < components.length;  i++) {
                if (components[i] instanceof Note) {
                    Note n = (Note) components[i];
                    if ((n.ourPage() != newpageno) ||
                        (!n.within(Annotation.Timestamp.MODIFIED, annotation_span_start, annotation_span_end))) {
                        n.setVisible(false);
                        remove(n);
                    }
                }
            }
            if (newpageno >= 0) {
                this_page_notes = (Notesheets) note_sheets.get(newpageno);
                if (this_page_notes != null) {
                    for (int i = 0;  i < this_page_notes.size();  i++) {
                        NoteFrame nf = (NoteFrame) this_page_notes.get(i);
                        Note n = getNote(nf);
                        if (!isAncestorOf(n) &&
                            n.within(Annotation.Timestamp.MODIFIED, annotation_span_start, annotation_span_end)) {
                            n.setVisible(false);
                            add(n);
                        }
                    }
                    int component_count = getComponentCount();
                    for (int i = (this_page_notes.size() - 1);  i >= 0;  i--) {
                        NoteFrame nf = (NoteFrame) this_page_notes.get(i);
                        Note n = getNote(nf);
                        if (isAncestorOf(n)) {
                            // System.err.println("Moving note " + nf + " to position " + nf.stacking_order + " of " + component_count);
                            n.setVisible(false);
                            remove(n);
                            add(n, min(nf.stacking_order, component_count - 1));
                            n.setVisible(true);
                            n.inkpotChanged(widget_inkpots.active(), widget_inkpots.getSelected());
                        }
                    }
                }
            }
            revalidate();
        }

        protected void saveScribble (AnnotationStreamHandler handler, Scribble to_save) {
            if (handler != null) {
                // System.err.println("Saving scribble " + to_save + " (points " + ((to_save.points == null) ? "null" : Integer.toString(to_save.points.length)) + ") to " + handler);
                try {
                    handler.addAnnotation(to_save, document_id, current_page_index, 0);
                } catch (IOException x) {
                    x.printStackTrace(System.err);
                }
            }
        }

        // DropTargetListener methods

        private String calcLinkID(String originURL, String doc_id, int pageno, int x, int y) {
            try {
                MessageDigest md = MessageDigest.getInstance("MD5");
                md.update(originURL.getBytes());
                md.update(doc_id.getBytes());
                md.update(Integer.toString(pageno).getBytes());
                md.update(Integer.toString(x).getBytes());
                md.update(Integer.toString(y).getBytes());
                return new String(Base64.encode(md.digest()), "US-ASCII");
            } catch (java.security.NoSuchAlgorithmException x1) {
                // will never happen -- MD5 is required
            } catch (java.io.UnsupportedEncodingException x2) {
                // will never happen -- US-ASCII is required
            }
            return null;
        }

        protected String showLinkDescriptionDialog(String d, Point p) {
            LinkDescrDialog l = (link_description_dialog == null)
                ? (link_description_dialog = new LinkDescrDialog(this)) : link_description_dialog;
            Point loc = getLocationOnScreen();
            System.err.println("loc on screen is " + loc);
            l.setTitle("Description for new link...");
            l.setSize(400, 200);
            l.setDescription(d);
            l.validate();
            Point bloc = l.getOKButtonLocation();
            System.err.println("bloc is " + bloc);
            l.setLocation(new Point(p.x + loc.x - bloc.x - 20, p.y + loc.y - bloc.y - 10));
            l.setVisible(true);
            System.err.println("l.cancelled is " + l.cancelled + ", l.text is " + l.getDescription());
            if (l.cancelled)
                return null;
            else
                return l.getDescription();
        }

        public boolean doDrop (Object dropped, Point p) {
            System.err.println(dropped.toString() + " dropped at " + p);

            if (dropped instanceof DraggedHotspot) {

                DraggedHotspot dh = (DraggedHotspot) dropped;
                HotSpot h = dh.getHotspot();
                Image icon = dh.getIcon();
                if ((icon == null) || (!(icon instanceof BufferedImage))) icon = link_icon_translucent;
                int x = p.x - icon.getWidth(null)/2;
                int y = p.y - icon.getHeight(null)/2;

                if (h == drag_hotspot) {
                    // moving it, not copying it

                    h.setLocation(x, y);
                    drag_hotspot = null;

                } else {
                    // copying it to this page or document

                    String link_id = calcLinkID(h.getURL(), document_id, ourPage(), x, y);
                    try {
                        h = HotSpot.create (page_opener, link_id, document_id, false, ourPage(), x, y, icon.getWidth(null),
                                            icon.getHeight(null), dh.getHotspot());
                    } catch (java.net.MalformedURLException e) {
                        System.err.println("Can't copy dragged hotspot " + h);
                        e.printStackTrace(System.err);
                        return false;
                    }

                    if (h != null) {
                        ((ArrayList) hotspots.get(ourPage())).add(h);
                        if (this_page_hotspots == null) {
                            this_page_hotspots = (ArrayList) (hotspots.get(ourPage()));
                        }
                        topl.setShowHotspots(true);
                        if (hotspot_saver != null)
                            try {
                                hotspot_saver.addAnnotation (h, document_id, ourPage(), 0);
                            } catch (IOException e) {
                                e.printStackTrace(System.err);
                            }
                        System.err.println("added new hotspot " + h);
                    }
                    repaint();
                    System.err.println("dropped selection");
                }

                if (hotspot_saver != null)
                    try {
                        hotspot_saver.addAnnotation (h, document_id, ourPage(), 0);
                    } catch (IOException e) {
                        e.printStackTrace(System.err);
                    }

            } else if (dropped instanceof DraggedSelection) {
                DraggedSelection ds = (DraggedSelection) dropped;
                Image icon = ds.getIcon();
                if ((icon == null) || (!(icon instanceof BufferedImage)))
                    icon = link_icon_translucent;
                else if (ds.rect != null) {
                    // dragged rect
                    int w = icon.getWidth(null) / 3;
                    int h = icon.getHeight(null) / 3;
                    BufferedImage scaled_icon = new BufferedImage(w, h, BufferedImage.TYPE_INT_RGB);
                    Graphics g = scaled_icon.getGraphics();
                    Image di3 = icon.getScaledInstance(w, h, Image.SCALE_SMOOTH);
                    g.drawImage(di3, 0, 0, w, h, null);
                    g.dispose();
                    icon = scaled_icon;
                }
                int ul_x, ul_y, width, height;
                if (selection.isVisible() && selection.contains(p)) {
                    if (selection.getBoxes() == null) {
                        // rect selection
                        Rectangle r = selection.getImageRect();
                        ul_x = r.x;
                        ul_y = r.y;
                        width = r.width;
                        height = r.height;
                    } else {
                        // make the selection be the source anchor for the link
                        width = -1;
                        height = -1;
                        ul_x = selection.getStartPosAbsolute();
                        ul_y = selection.getEndPosAbsolute();
                    }
                } else {
                    width = icon.getWidth(null);
                    height = icon.getHeight(null);
                    ul_x = p.x - width/2;
                    ul_y = p.y - height/2;
                }
                URL u = ds.getURL();
                System.err.println("URL for dropped selection is " + u.toExternalForm());
                String link_id = calcLinkID(u.toExternalForm(), document_id, ourPage(), ul_x, ul_y);
                String description = ds.getDescription(true);
                if (show_dialog_on_drop) {
                    description = showLinkDescriptionDialog(description, p);
                    if (description == null)
                        return false;
                }
                HotSpot h = HotSpot.create (page_opener, link_id, document_id, false, ourPage(), ul_x, ul_y, width, height,
                                            u, description,
                                            (icon != link_icon_translucent) ? (BufferedImage) icon : null, ORIGIN_POINT);
                if (h != null) {
                    ((ArrayList) hotspots.get(ourPage())).add(h);
                    if (this_page_hotspots == null) {
                        this_page_hotspots = (ArrayList) (hotspots.get(ourPage()));
                    }
                    topl.setShowHotspots(true);
                    if (hotspot_saver != null)
                        try {
                            hotspot_saver.addAnnotation (h, document_id, ourPage(), 0);
                        } catch (IOException e) {
                            e.printStackTrace(System.err);
                        }
                    System.err.println("added new hotspot " + h);
                }
                repaint();
                System.err.println("dropped selection");

            } else if (dropped instanceof URL) {
                URL u = (URL) dropped;
                int ul_x, ul_y, width, height;
                if (selection.isVisible() && selection.contains(p)) {
                    if (selection.getBoxes() == null) {
                        // rect selection
                        Rectangle r = selection.getImageRect();
                        ul_x = r.x;
                        ul_y = r.y;
                        width = r.width;
                        height = r.height;
                    } else {
                        // make the selection be the source anchor for the link
                        width = -1;
                        height = -1;
                        ul_x = selection.getStartPosAbsolute();
                        ul_y = selection.getEndPosAbsolute();
                    }
                } else {
                    width = link_icon_translucent.getWidth();
                    height = link_icon_translucent.getHeight();
                    ul_x = p.x - width/2;
                    ul_y = p.y - height/2;
                }
                String description = u.toString();
                if (show_dialog_on_drop) {
                    description = showLinkDescriptionDialog(description, p);
                    if (description == null)
                        return false;
                }
                HotSpot h = HotSpot.create (page_opener, document_id, false, ourPage(),
                                            ul_x, ul_y, width, height, u, description);
                if (h != null) {
                    ((ArrayList) hotspots.get(ourPage())).add(h);
                    if (this_page_hotspots == null) {
                        this_page_hotspots = (ArrayList) (hotspots.get(ourPage()));
                    }
                    if (hotspot_saver != null)
                        try {
                            hotspot_saver.addAnnotation (h, document_id, ourPage(), 0);
                        } catch (IOException e) {
                            e.printStackTrace(System.err);
                        }
                    topl.setShowHotspots(true);
                }
                repaint();

            } else if (dropped instanceof String) {
                Note n = newNoteSheet(p.x - 10, p.y - 10, 200, 200);
                Vector v = new Vector(1);
                v.add(dropped);
                n.setContents(v);
                if (!widget_inkpots.isVisible()) {
                    topl.setShowScribbles(true);
                }
            } else {
                return false;
            }
            return true;
        }

        public boolean canImport (DataFlavor[] flavors) {
            if (current_drag_source)
                return false;
            for (int i = 0;  i < flavors.length;  i++) {
                if (DraggedSelection.isURLFlavor(flavors[i]) ||
                    DraggedSelection.isStringFlavor(flavors[i]) ||
                    DraggedSelection.isSelectionFlavor(flavors[i]))
                    return true;
            }
            return false;
        }

        public void dragEnter (DropTargetDragEvent e) {
            /*
              System.err.println("dragEnter " + e + ", dragsource is " + current_drag_source);
              System.err.println("e.getSource() is " + e.getSource());
              System.err.println("component is " + e.getDropTargetContext().getComponent());
            */
            if (drag_hotspot != null) {
                if (this.drop_status != DROPSTATE_GOOD_DROP) {
                    topl.setShowScribbles(false);
                    this.repaint();
                }
                this.drop_status = DROPSTATE_GOOD_DROP;
            } else if (current_drag_source) {
                this.drop_status = DROPSTATE_BAD_DROP;
            } else if (desiredFlavor(e.getCurrentDataFlavors()) != null) {
                if (this.drop_status != DROPSTATE_GOOD_DROP) {
                    topl.setShowScribbles(false);
                    this.repaint();
                }
                this.drop_status = DROPSTATE_GOOD_DROP;
            } else {
                if (this.drop_status != DROPSTATE_BAD_DROP)
                    this.repaint();
                this.drop_status = DROPSTATE_BAD_DROP;
            }
            if (this.drop_status != DROPSTATE_GOOD_DROP) {
                // System.err.println("   dragEnter rejects drag!");
                // e.rejectDrag();
            } else {
                current_drop_point = e.getLocation();
                // e.acceptDrag(DnDConstants.ACTION_COPY);
            }
            // System.err.println("dragEnter sets drop_status to " + drop_status);
        }

        public void dragExit (DropTargetEvent e) {
            if (this.drop_status != DROPSTATE_NO_DROP)
                this.repaint();
            current_drop_point = null;
            this.drop_status = DROPSTATE_NO_DROP;
        }

        public void dragOver (DropTargetDragEvent e) {
            if (this.drop_status != DROPSTATE_GOOD_DROP) {
                // e.rejectDrag();
            } else {
                current_drop_point = e.getLocation();
                // e.acceptDrag(DnDConstants.ACTION_LINK);
            }
        }

        public void dropActionChanged (DropTargetDragEvent e) {
        }

        public void drop (DropTargetDropEvent e) {
            if (this.drop_status != DROPSTATE_GOOD_DROP) {
                e.rejectDrop();
                this.drop_status = DROPSTATE_NO_DROP;
                return;
            }
            Transferable t = e.getTransferable();
            DataFlavor f = desiredFlavor(t.getTransferDataFlavors());
            System.err.println("importing " + t + " as " + f);
            if (f != null) {
                // System.err.println("Can import " + t + " as " + f);
                if (drag_hotspot != null)
                    e.acceptDrop(DnDConstants.ACTION_MOVE);
                else
                    e.acceptDrop(DnDConstants.ACTION_COPY);
                try {
                    Object o = t.getTransferData(f);
                    e.dropComplete(doDrop(o, e.getLocation()));
                } catch (UnsupportedFlavorException x) {
                    x.printStackTrace(System.err);
                } catch (IOException x) {
                    x.printStackTrace(System.err);
                }
            } else {
                System.err.println("Can't import " + t);
                e.rejectDrop();
            }
            if (this.drop_status != DROPSTATE_NO_DROP)
                repaint();
            this.drop_status = DROPSTATE_NO_DROP;
        }

        public Point getDropPoint () {
            return current_drop_point;
        }

        public DataFlavor desiredFlavor (DataFlavor[] flavors) {
            for (int i = 0;  i < flavors.length;  i++) {
                // System.err.println("flavor[" + i + "] is " + flavors[i]);
                if (DraggedHotspot.isHotspotFlavor(flavors[i]))
                    return flavors[i];
                else if (DraggedSelection.isSelectionFlavor(flavors[i]))
                    return flavors[i];
                else if (DraggedSelection.isURLFlavor(flavors[i]))
                    return flavors[i];
                else if (DraggedSelection.isStringFlavor(flavors[i]))
                    return flavors[i];
            }
            return null;
        }

        public void inkpotChanged (boolean active, Inkpots.Pot current) {
            if (isVisible()) {
                setCursor(active ? current.getDrawingCursor() : our_cursor);
                Component[] components = getComponents();
                for (int i = 0;  i < components.length;  i++) {
                    if (components[i] instanceof Note) {
                        Note n = (Note) components[i];
                        if (n.isShowing()) {
                            n.inkpotChanged(active, current);
                        }
                    }
                }
            }
        }

        public void setCursor(Cursor toset) {
            super.setCursor(toset);
            current_cursor = toset;
        }

        public int ourPage() {
            int ourpage = current_page_index + page_offset;
            if (ourpage < 0 || ourpage >= page_count)
                return -1;
            else
                return ourpage;
        }

        protected PageText getPageText () {
            int ourpage = ourPage();
            if (ourpage < 0)
                return null;
            if (((ourpage != last_page_this_was_on) || (this_page_text == null)) && (pagetext_loader != null)) {
                this_page_text = (PageText) pagetext_loader.get(document_id, ourpage, 0, null);
            }
            return this_page_text;                
        }

        public void setSize(Dimension d) {
            super.setSize(d);
            if (d.width > active_region.width) {
                active_region.x = (d.width - active_region.width) / 2;
            }
            if (d.height > (active_region.height + 10)) {
                active_region.y = 5 + (d.height - (active_region.height + 10)) / 2;
            }
        }

        private Image get_page_image(int p, BufferedImage fastImage) {
            BufferedImage i = (BufferedImage) page_image_loader.check(document_id, p, 0);
            if (i == null) {
                i = (BufferedImage) page_image_loader.get(document_id, p, 0, new PageImageSetter(p));
                if (i == null)
                    return null;
            }
            Graphics g = fastImage.getGraphics();
            int w1 = fastImage.getWidth(null);
            int h1 = fastImage.getHeight(null);
            int w2 = i.getWidth(null);
            int h2 = i.getHeight(null);
            int dx1 = max((w1-w2)/2, 0);
            int dy1 = max((h1-h2)/2, 0);
            int dx2 = min(w1, dx1 + w2);
            int dy2 = min(h1, dy1 + h2);
            int sx1 = max((w2-w1)/2, 0);
            int sy1 = max((h2-h1)/2, 0);
            int sx2 = min(w2, sx1 + w1);
            int sy2 = min(h2, sy1 + h1);
            g.setColor(WHITE);
            g.fillRect(0, 0, w1, h1);
            g.drawImage(i, dx1, dy1, dx2, dy2, sx1, sy1, sx2, sy2, null);
            return i;
        }

        public void animate_change (int old_pagenum, int new_pagenum) {
            if ((this_page_image_slow != null) &&
                (old_pagenum != new_pagenum) &&
                (animation_time_limit > 0)) {
                animation_forward = (new_pagenum > old_pagenum);
                animation_start_time = System.currentTimeMillis();
            }
        }

        protected void paintComponent(Graphics g) {

            // for Pageview

            if ((current_stroke != null) && (backing_store != null)) {
                super.paintComponent(g);
                return;
            }

            g.clearRect(0, 0, getWidth(), getHeight());
            boolean painting_splash_page = false;
            int ourpage = ourPage();

            if (ourpage < 0) {
                if (last_page_image != null) {
                    Graphics gi = last_page_image.getGraphics();
                    gi.setColor(BACKGROUND_COLOR);
                    gi.fillRect(0, 0, last_page_image.getWidth(null), last_page_image.getHeight(null));
                }
                last_page_this_was_on = ourpage;
                return;
            }

            if (this_page_image == null) {
                this_page_image = topl.getGraphicsConfiguration().createCompatibleImage(getWidth(), getHeight(), Transparency.OPAQUE);
            }
            if (last_page_image == null) {
                last_page_image = topl.getGraphicsConfiguration().createCompatibleImage(getWidth(), getHeight(), Transparency.OPAQUE);
            }
            if (first_page_expose && (activity_logger != null) && activities_on) {
                activity_logger.call(new Activity(document_id, ourpage, Activity.AC_OPENED_DOC));
                first_page_expose = false;
            }
            if (ourpage != last_page_this_was_on) {
                // swap last_page_image and this_page_image
                BufferedImage temp = last_page_image;
                if (last_page_this_was_on >= 0) {
                    if (this_page_image_slow == null)
                        get_page_image(ourpage, this_page_image);
                }
                last_page_image = this_page_image;
                this_page_scribbles = (ArrayList) strokes.get(ourpage);
                this_page_hotspots = (ArrayList) hotspots.get(ourpage);
                this_page_current_hotspot = null;
                try {
                    changeNotes (last_page_this_was_on, ourpage);
                } catch (Exception x) {
                    x.printStackTrace(System.err);
                }
                this_page_image_slow = get_page_image(ourpage, temp);
                this_page_image = temp;
                last_page_this_was_on = ourpage;
                this_page_text = null;
            }

            if ((this_page_text == null) && (pagetext_loader != null)) {
                this_page_text = (PageText) pagetext_loader.get(document_id, ourpage, 0, null);
                if ((this_page_text != null) && (this_page_hotspots != null) && (this_page_hotspots.size() > 0)) {
                    // process hotspots against text to resolve from-span links
                    for (int i = 0;  i < this_page_hotspots.size();  i++) {
                        HotSpot h = (HotSpot) (this_page_hotspots.get(i));
                        if ((h.width < 0) || (h.height < 0)) {
                            // from-span link
                            if (h.resolver instanceof HotSpot.RectResolver) {
                                h.resolver = new HotSpot.SpanResolver(h, this_page_text);
                                // System.err.println("new span HotSpot:  " + h.x + " to " + h.y + ", rect is " + h.getBounds());
                            }
                        }
                    }
                }
            }

            try {

                long animation_time = System.currentTimeMillis() - animation_start_time;
                long our_animation_start, our_animation_end, our_animation_time_limit;
                if (two_page) {
                    if (ourpage == current_page_index) {        // left side
                        if (animation_forward) {                // right-to-left
                            our_animation_start = animation_time_limit / 2;
                            our_animation_end = animation_time_limit;
                        } else {
                            our_animation_start = 0;
                            our_animation_end = animation_time_limit / 2;
                        }
                    } else {                                    // right page
                        if (animation_forward) {                // right-to-left
                            our_animation_start = 0;
                            our_animation_end = animation_time_limit / 2;
                        } else {
                            our_animation_start = animation_time_limit / 2;
                            our_animation_end = animation_time_limit;
                        }
                    }
                    our_animation_time_limit = animation_time_limit / 2;
                } else {
                    our_animation_start = 0;
                    our_animation_end = animation_time_limit;
                    our_animation_time_limit = animation_time_limit;
                }

                // handle the case where the current page hadn't been loaded the last time we painted
                if (this_page_image_slow == null)
                    this_page_image_slow = get_page_image(ourpage, this_page_image);
                // check to see if we're in the animation page-turn
                if ((last_page_this_was_on >= 0) &&
                    (this_page_image_slow != null) &&
                    (animation_time < animation_time_limit)) {

                    ((Graphics2D)g).setRenderingHints(low_quality_rendering_mode);

                    if ((animation_time > our_animation_start) &&
                        (animation_time < our_animation_end)) {

                        animation_time = our_animation_end - animation_time;
                        int w = max(this_page_image.getWidth(null), last_page_image.getWidth(null));
                        int h = max(this_page_image.getHeight(null), last_page_image.getHeight(null));
                        int oldw = (int) (((float) (animation_time * (w - 4)))/((float) our_animation_time_limit));
                        int neww = w - 4 - oldw;
                        int x = active_region.x +
                            max(0, (active_region.width - w)/2);
                        int y = active_region.y +
                            max(0, (active_region.height - h)/2);
                        if (animation_forward) {
                            g.drawImage(last_page_image, x, y, oldw, last_page_image.getHeight(null),
                                        getBackground(), null);                                
                            g.drawImage(this_page_image, x + oldw + 4, y, neww, this_page_image.getHeight(null),
                                        getBackground(), null);                                
                        } else {
                            g.drawImage(this_page_image, x, y, neww, this_page_image.getHeight(null),
                                        getBackground(), null);
                            g.drawImage(last_page_image, x + neww + 4, y, oldw, last_page_image.getHeight(null),
                                        getBackground(), null);                                
                        }
                        if (search_state != null) {
                            g.setColor(HALF_WHITE);
                            g.fillRect(x, y, w, h);
                        } else if ((active_reading != null) && (show_active_reading || (!active_reading.paused())) && !rsvp_mode) {
                            active_reading.tempHold((int)(animation_time_limit - animation_time));
                            g.setColor(WHITE80);
                            g.fillRect(x, y, w, h);
                        }
                        g.setColor(TOOLS_COLOR);
                        // paint a 4-pixel divider in the center
                        g.fillRect(x + (animation_forward ? oldw : neww), y, 4, h);
                        repaint();

                    } else {
                        // must be two-page animation, and your page isn't moving yet
                        Image the_page_image = (animation_time > our_animation_end) ? this_page_image : last_page_image;
                        int wd = the_page_image.getWidth(null);
                        int ht = the_page_image.getHeight(null);
                        int x = active_region.x +
                            max(0, (active_region.width - wd)/2);
                        int y = active_region.y +
                            max(0, (active_region.height - ht)/2);
                        g.drawImage(the_page_image, x, y, null);

                        if (search_state != null) {
                            g.setColor(HALF_WHITE);
                            g.fillRect(x, y, wd, ht);
                        } else if ((active_reading != null) && (show_active_reading || (!active_reading.paused())) && !rsvp_mode) {
                            active_reading.tempHold((int)(animation_time_limit - animation_time));
                            g.setColor(WHITE80);
                            g.fillRect(x, y, wd, ht);
                        }
                        repaint();
                    }
                } else if (this_page_image_slow != null) {
                    // regular page paint

                    Composite old_composite = ((Graphics2D)g).getComposite();

                    if (this_page_notes != null) {
                        boolean visibility = topl.showNotes();
                        for (int i = 0;  i < this_page_notes.size();  i++) {
                            NoteFrame nf = ((NoteFrame)(this_page_notes.get(i)));
                            Note n = getNote(nf);
                            n.setVisible(visibility);
                        }
                    }

                    try {

                        if (((splash_page_period > 0) || (splash_page_time > 0)) && (splash_image != null)) {
                            // are we painting the splash page?
                            if (splash_page_time == 0)
                                splash_page_time = System.currentTimeMillis();
                            int time_passed = (int) (System.currentTimeMillis() - splash_page_time);
                            painting_splash_page = (time_passed < splash_page_period);
                            if (painting_splash_page) {
                                int splash_page_x = (getWidth() - splash_image.getWidth(null))/2;
                                int splash_page_y = (getHeight() - splash_image.getHeight(null))/2;
                                g.drawImage(splash_image, splash_page_x, splash_page_y, null);
                                float alpha = max(0.5f, (1.0f - ((float) (splash_page_period - time_passed)) / ((float) splash_page_period)));
                                AlphaComposite new_composite = AlphaComposite.getInstance(AlphaComposite.SRC_OVER, alpha);
                                ((Graphics2D)g).setComposite(new_composite);
                            }

                        } else if (rsvp_mode && (active_reading != null) && (show_active_reading || (!active_reading.paused()))) {

                            java.util.List phrase_boxes = active_reading.getBoxes();

                            if (phrase_boxes != null) {

                                // System.err.println("  phraseboxes.size() is " + phrase_boxes.size());

                                int w = max(this_page_image.getWidth(null), last_page_image.getWidth(null));
                                int h = max(this_page_image.getHeight(null), last_page_image.getHeight(null));
                                int x = active_region.x +
                                    max(0, (active_region.width - w)/2);
                                int y = active_region.y +
                                    max(0, (active_region.height - h)/2);

                                g.setColor(WHITE);
                                g.fillRect(0, 0, getWidth(), getHeight());

                                Iterator it = phrase_boxes.iterator();
                                int width = 0, height = 0;
                                while (it.hasNext()) {
                                    Rectangle b = (Rectangle) it.next();
                                    width = (width == 0) ? (width + b.width) : (width + 3 + b.width);
                                    height = max(height, b.height);
                                }
                                it = phrase_boxes.iterator();
                                int xpos = (getWidth() - width) / 2;
                                int ypos = (getHeight() - height) / 2;
                                while (it.hasNext()) {
                                    Rectangle b = (Rectangle) it.next();
                                    g.drawImage(this_page_image,
                                                xpos, ypos, xpos + b.width + 1, ypos + b.height + 1,
                                                b.x, b.y, b.x + b.width + 1, b.y + b.height + 1,
                                                null);
                                    xpos += (3 + b.width);
                                }
                            }

                        } else if ((active_reading != null) && (show_active_reading || (!active_reading.paused()))) {

                            // Here's where we draw the active reading region

                            java.util.List phrase_boxes = active_reading.getBoxes();

                            if (phrase_boxes != null) {

                                // System.err.println("  phraseboxes.size() is " + phrase_boxes.size());

                                int w = max(this_page_image.getWidth(null), last_page_image.getWidth(null));
                                int h = max(this_page_image.getHeight(null), last_page_image.getHeight(null));
                                int x = active_region.x +
                                    max(0, (active_region.width - w)/2);
                                int y = active_region.y +
                                    max(0, (active_region.height - h)/2);

                                g.drawImage(this_page_image, x, y, null);
                                g.setColor(WHITE80);
                                g.fillRect(0, 0, getWidth(), getHeight());

                                Iterator it = phrase_boxes.iterator();
                                while (it.hasNext()) {
                                    Rectangle b = (Rectangle) it.next();
                                    g.drawImage(this_page_image,
                                                x + b.x, y + b.y, x + b.x + b.width, y + b.y + b.height,
                                                b.x, b.y, b.x + b.width, b.y + b.height,
                                                null);
                                }
                            }

                        } else {
                            // the default case of regular page paint.
                            if (this_page_notes != null) {
                                boolean visibility = topl.showNotes();
                                for (int i = 0;  i < this_page_notes.size();  i++) {
                                    NoteFrame nf = ((NoteFrame)(this_page_notes.get(i)));
                                    Note n = getNote(nf);
                                    n.setVisible(visibility);
                                }
                            }

                            int wd = this_page_image.getWidth(null);
                            int ht = this_page_image.getHeight(null);
                            int x = active_region.x +
                                max(0, (active_region.width - wd)/2);
                            int y = active_region.y +
                                max(0, (active_region.height - ht)/2);
                            g.drawImage(this_page_image, x, y, null);
                            if (topl.showScribbles())
                                super.paintComponent(g);
                            paintSelectionAndSearchState(g, ourpage, wd, ht, x, y);
                            

                            ((Graphics2D)g).setStroke(new BasicStroke(1.0f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                            if ((this_page_hotspots != null) && (this_page_hotspots.size() > 0)) {
                                if (topl.showHotspots()) {
                                    // System.err.println("showing hotspots " + this_page_hotspots);
                                    if (this_page_hotspots != null) {
                                        for (int i = 0;  i < this_page_hotspots.size();  i++) {
                                            HotSpot h = (HotSpot) this_page_hotspots.get(i);
                                            Rectangle r = h.getBounds();
                                            Color color = h.getColor();
                                            if (color == null)
                                                color = HOT_SPOT_COLOR;
                                            /*
                                              g.setColor(color);
                                              g.fillRect(h.x - 2, h.y - 2, h.width + 4, h.height + 4);
                                              g.setColor(UPLIB_ORANGE);
                                              g.drawRect(h.x - 2, h.y - 2, h.width + 4, h.height + 4);
                                            */
                                            if (!(h.isIntrinsic() ||
                                                  (h.resolver instanceof HotSpot.SpanResolver))) {
                                                Image im;
                                                Point ip;
                                                HotSpot.Icon ic = h.getIcon();
                                                if (ic == null) {
                                                    im = link_icon_translucent;
                                                    ip = ORIGIN_POINT;
                                                } else {
                                                    im = ic.getImage();
                                                    ip = ic.getLocation();
                                                }
                                                g.setColor(TRANSPARENT);
                                                int hx = r.x + ip.x;
                                                int hy = r.y + ip.y + r.height/2 - im.getHeight(null)/2;
                                                g.drawImage(im, hx, hy, null);
                                            }
                                            Stroke oldStroke = ((Graphics2D)g).getStroke();
                                            g.setColor(color);
                                            ((Graphics2D)g).setStroke(HOTSPOT_BORDER);
                                            g.drawRoundRect(r.x - 4, r.y - 4, r.width + 8, r.height + 8, 10, 10);
                                            ((Graphics2D)g).setStroke(oldStroke);
                                        }
                                    }
                                } else if ((this_page_current_hotspot != null) &&
                                           (this_page_current_hotspot != drag_hotspot)) {

                                    Rectangle r = this_page_current_hotspot.getBounds();

                                    if (!(this_page_current_hotspot.isIntrinsic()
                                          || (this_page_current_hotspot.resolver instanceof HotSpot.SpanResolver))) {

                                        // it's an added link without an anchor, so may have an icon
                                        Image im;
                                        Point ip;
                                        HotSpot.Icon ic = this_page_current_hotspot.getIcon();
                                        if (ic == null) {
                                            im = link_icon_translucent;
                                            ip = ORIGIN_POINT;
                                        } else {
                                            im = ic.getImage();
                                            ip = ic.getLocation();
                                        }
                                        g.setColor(TRANSPARENT);
                                        int hx = r.x + ip.x;
                                        int hy = r.y + ip.y + r.height/2 - im.getHeight(null)/2;
                                        g.drawImage(im, hx, hy, null);
                                    }
                                    Color color = this_page_current_hotspot.getColor();
                                    if (color == null)
                                        color = HOT_SPOT_COLOR;
                                    Stroke oldStroke = ((Graphics2D)g).getStroke();
                                    g.setColor(color);
                                    ((Graphics2D)g).setStroke(HOTSPOT_BORDER);
                                    g.drawRoundRect(r.x - 4, r.y - 4, r.width + 8, r.height + 8, 10, 10);
                                    ((Graphics2D)g).setStroke(oldStroke);
                                }
                            }

                            if ((this_page_text != null) && show_phrases) {
                                Iterator i = this_page_text.getWordBoxes(null);
                                Color color = null;
                                while (i.hasNext()) {
                                    PageText.WordBox box = (PageText.WordBox) i.next();
                                    if (box.beginsPhrase()) {
                                        if (box.beginsSentence())
                                            color = PHRASE_COLOR_3;
                                        else if ((color == PHRASE_COLOR_1) || (color == PHRASE_COLOR_3))
                                            color = PHRASE_COLOR_2;
                                        else
                                            color = PHRASE_COLOR_1;
                                    }
                                    if (color != null) {
                                        g.setColor(color);
                                        g.fillRect(box.x, box.y, box.width + 1, box.height + 1);
                                    }
                                }
                            }

                            // if we're in the process of sweeping out a new note rect...
                            if (selection_rect != null) {
                                // Change this to selecting a region

                                // g.setColor(NOTE_BACKGROUND);
                                // g.fillRect(selection_rect.x, selection_rect.y, selection_rect.width, selection_rect.height);
                                g.setColor(DARK_COLOR);
                                g.drawRect(selection_rect.x, selection_rect.y, selection_rect.width, selection_rect.height);
                                if ((selection_rect.width > 2) && (selection_rect.height > 2)) {
                                    g.setColor(BACKGROUND_COLOR);
                                    g.drawRect(selection_rect.x + 1, selection_rect.y + 1, selection_rect.width - 2, selection_rect.height - 2);
                                    
                                }
                            }

                        }
                    } finally {
                        if (painting_splash_page) {
                            ((Graphics2D)g).setComposite(old_composite);
                            repaint(0L, 0, 0, getWidth(), getHeight());
                        }
                    }
                    
                    if (ourpage < (page_count - 1)) {
                        page_image_loader.get(document_id, ourpage + 1, 0, null);
                        thumbnail_image_loader.get(document_id, ourpage + 1, 1, null);
                        if (pagetext_loader != null)
                            pagetext_loader.get(document_id, ourpage + 1, 0, null);
                        if (two_page && (ourpage < (page_count - 2))) {
                            page_image_loader.get(document_id, ourpage + 2, 0, null);
                            thumbnail_image_loader.get(document_id, ourpage + 2, 1, null);
                            if (pagetext_loader != null)
                                pagetext_loader.get(document_id, ourpage + 2, 0, null);
                        }
                    }
                    if (ourpage > 0) {
                        page_image_loader.get(document_id, ourpage - 1, 0, null);
                        thumbnail_image_loader.get(document_id, ourpage - 1, 1, null);
                        if (pagetext_loader != null)
                            pagetext_loader.get(document_id, ourpage - 1, 0, null);
                        if (two_page && (ourpage > 1)) {
                            page_image_loader.get(document_id, ourpage - 2, 0, null);
                            thumbnail_image_loader.get(document_id, ourpage - 2, 1, null);
                            if (pagetext_loader != null)
                                pagetext_loader.get(document_id, ourpage - 2, 0, null);
                        }
                    }

                } else {
                    // page isn't available yet
                    String s = "Page loading...";
                    int w = g.getFontMetrics().stringWidth(s);
                    int h = g.getFontMetrics().getMaxAscent();
                    g.setColor(BLACK);
                    g.drawString(s, (getWidth() - w)/2, (getHeight() - h)/2 + h);
                }

                if (two_page) {
                    // paint a thin stripe down the center
                    g.setColor(BACKGROUND_COLOR);
                    if (page_offset == 0)
                        g.drawLine(active_region.x + active_region.width - 1, active_region.y,
                                   active_region.x + active_region.width - 1, active_region.y + active_region.height);
                    else
                        g.drawLine(active_region.x, active_region.y,
                                   active_region.x, active_region.y + active_region.height);
                }

                // only draw the bookmarks if you have multiple pages
                if (page_count > 1 && (search_state == null) && (!rsvp_mode) &&
                    ((active_reading == null) || (!show_active_reading || active_reading.paused()))) {
                    for (int i = 0;  i < bookmarks.length;  i++) {
                        bookmarks[i].paint(this, (Graphics2D) g);
                    }
                }

                // if adjusting page controls
                if (annotation_span_controls.isVisible()) {
                    g.setColor(HALF_BLACK);
                    g.fillRect(0, 0, getWidth(), getHeight());
                }

                // if fielding a dnd drop
                else if (current_drag_source && (drop_status != DROPSTATE_GOOD_DROP)) {
                    g.setColor(HALF_WHITE);
                    g.fillRect(0, 0, getWidth(), getHeight());
                } else if (drop_status == DROPSTATE_GOOD_DROP) {
                    g.setColor(UPLIB_ORANGE_WASH);
                    int w = getWidth();
                    int h = getHeight();
                    g.fillRect(0, 0, w - 10, 10);
                    g.fillRect(w - 10, 0, 10, h);
                    g.fillRect(0, h - 10, w - 10, 10);
                    g.fillRect(0, 10, 10, h - 20);
                }

            } catch (IndexOutOfBoundsException e) {
                System.err.println("Exception e caught in Pageview paintComponent:  " + e);
            }
        }

        protected void paintSelectionAndSearchState(Graphics g, int ourpage, int wd, int ht, int x, int y) {
            // As these two kinds of selection interact, some sub-classes may wish to override this
            // method to resolve the interactions differently.
            paintSelection(g, ourpage, wd, ht, x, y);
            paintSearchState(g, ourpage, wd, ht, x, y);
        }

        protected void paintSelection(Graphics g, int ourpage, int wd, int ht, int x, int y) {
            // HIGHLIGHT_COLOR
            paintSelectionWithColor(g, ourpage, wd, ht, x, y, HIGHLIGHT_COLOR);
        }
		
        protected void paintSelectionWithColor(Graphics g, int ourpage, int wd, int ht, int x, int y,
                                               Color selColor) {
            java.util.List selected_boxes;
            Rectangle r;
            if (selection.isVisible() && selection.isActive()) {
                if ((selected_boxes = selection.getBoxes(ourpage)) != null) {
                    Iterator it = selected_boxes.iterator();
                    g.setColor(selColor);
                    Rectangle linebox = null;
                    while (it.hasNext()) {
                        PageText.WordBox b = (PageText.WordBox) it.next();
                        if (linebox == null)
                            linebox = b.getBounds();
                        else
                            linebox.add(b);
                        if (b.endOfLine() || (!it.hasNext())) {
                            g.fillRect(x + max(linebox.x - 0, 0),
                                       y + max(linebox.y - 0, 0),
                                       min(wd - (x + max(linebox.x - 0, 0)), linebox.width + 1),
                                       min(ht - (y + max(linebox.y - 0, 0)), linebox.height + 1));
                            linebox = null;
                        }
                    }
                } else if ((r = selection.getImageRect()) != null) {
                    ((Graphics2D)g).setStroke(new BasicStroke());
                    g.setColor(DARK_COLOR);
                    g.drawRect(r.x, r.y, r.width, r.height);
                    if ((r.width > 2) && (r.height > 2)) {
                        g.setColor(BACKGROUND_COLOR);
                        g.drawRect(r.x + 1, r.y + 1, r.width - 2, r.height - 2);
                        
                    }
                }
            }
        }

        protected void paintSearchState(Graphics g, int ourpage, int wd, int ht, int x, int y) {
            // I am factoring out this part of Pageview.paintComponent so that sub-classes
            // can override it.  -- E. Bier
            if (search_state != null) {
                if (large_search_font == null) {
                    large_search_font = new Font(g.getFont().getFamily(), Font.PLAIN, 18);
                    small_search_font = new Font(g.getFont().getFamily(), Font.PLAIN, 8);
                    g.setFont(large_search_font);
                    int search_font_height = g.getFontMetrics().getMaxAscent();
                    int search_box_width = 300;
                    search_rect = new Rectangle(max(getWidth() - search_box_width, 0), 0,
        					min(getWidth(), search_box_width), search_font_height + 20);
                }
                boolean search_goodness = ((search_state.search_string.length() == 0) ||
                                           search_state.hasMatch());
                boolean match_under = false;
                java.util.List boxes = null;
                g.setColor(HALF_WHITE);
                g.fillRect(0, 0, getWidth(), getHeight());
                if ((search_state.hasMatch()) &&
                    (search_state.getPage() == ourpage) &&
                    (this_page_text != null)) {
                    int pos = search_state.getPos();
                    boxes = this_page_text.getWordBoxes(pos, pos + search_state.getLength());
                    // System.err.println("search_state for \"" + search_state.search_string + "\" is " + pos + "/" + search_state.getLength() + "; " + boxes.size() + " boxes");
                    // draw other words on this page matching the search string
                    java.util.List prefix_matches = this_page_text.getMatchingStrings(search_state.search_string);
                    Iterator it = prefix_matches.iterator();
                    while (it.hasNext()) {
                        Iterator inner = ((java.util.List) it.next()).iterator();
                        while (inner.hasNext()) {
                            Rectangle b = (Rectangle) inner.next();
                            g.drawImage(this_page_image, x + max(b.x - 0, 0), y + max(b.y - 0, 0),
                                        x + max(b.x - 0, 0) + b.width, y + max(b.y - 0, 0) + b.height,
                                        b.x, b.y, b.x + b.width, b.y + b.height, null);
                        }
                    }
                    it = boxes.iterator();
                    while (it.hasNext()) {
                        Rectangle b = (Rectangle) it.next();
                        match_under = match_under || b.intersects(search_rect);
                        g.drawImage(this_page_image, x + max(b.x - 0, 0), y + max(b.y - 0, 0),
                                    x + max(b.x - 0, 0) + b.width, y + max(b.y - 0, 0) + b.height,
                                    b.x, b.y, b.x + b.width, b.y + b.height, null);
                        g.setColor(HIGHLIGHT_COLOR);
                        g.fillRect(x + max(b.x - 0, 0),
                                   y + max(b.y - 0, 0),
                                   min(wd - (x + max(b.x - 0, 0)), b.width + 0),
                                   min(ht - (y + max(b.y - 0, 0)), b.height + 0));
                    }
                }
        		
                Stroke oldstroke = ((Graphics2D)g).getStroke();
                g.setColor(search_goodness ? (match_under ? HALF_TOOLS_COLOR : TOOLS_COLOR) : UPLIB_ORANGE);
                g.fillRoundRect(search_rect.x + 1, search_rect.y + 1, search_rect.width - 3, search_rect.height - 3, 10, 10);
                ((Graphics2D)g).setStroke(new BasicStroke(3.0f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                ((Graphics2D)g).setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
                g.setColor(search_goodness ? (match_under ? HALF_LEGEND_COLOR : LEGEND_COLOR) : BLACK);
                g.drawRoundRect(search_rect.x + 1, search_rect.y + 1, search_rect.width - 3, search_rect.height - 3, 10, 10);
                ((Graphics2D)g).setStroke(oldstroke);
                if (search_state.search_string.length() > 0) {
                    if (search_state.wrapped()) {
                        g.setColor(HALF_BLACK);
                        g.setFont(small_search_font);
                        int sw = g.getFontMetrics().stringWidth("wrapped");
                        g.drawString("wrapped", getWidth() - (sw + 10), 10);
                    }
                    int stacksize = search_state.hits();
                    if (stacksize > 1) {
                        g.setColor(HALF_BLACK);
                        g.setFont(small_search_font);
                        int sw = g.getFontMetrics().stringWidth(Integer.toString(stacksize));
                        g.drawString(Integer.toString(stacksize), getWidth() - (sw + 10), search_rect.height - 5);
                    }
                    g.setColor(search_goodness ? (match_under ? HALF_BLACK : BLACK) : WHITE);
                    g.setFont(large_search_font);
                    g.drawString(search_state.search_string, getWidth() - (search_rect.width - 10), search_rect.height - 10);
                } else {
                    // No search string entered
                    g.setColor(BACKGROUND_COLOR);
                    g.setFont(large_search_font);
                    String message = "(Search)";
                    int sw = g.getFontMetrics().stringWidth(message);
                    g.drawString(message, (getWidth() - search_rect.width + ((search_rect.width - sw)/2)), search_rect.height - 10);
                }
            }
        }

        private String figureTooltipText(Point p) {
            if (topl.showHotspots() && (this_page_hotspots != null)) {
                HotSpot h = findHotspot(p);
                if (h != null) {
                    String d = h.getDescr();
                    if ((d != null) && (!d.toLowerCase().startsWith("<html>")))
                        return "<html>" + d.replaceAll("\n", "<br>") + "</html>";
                    else
                        return h.getURL();
                }
            } else if ((this_page_current_hotspot != null) && this_page_current_hotspot.contains(p)) {
                String d = this_page_current_hotspot.getDescr();
                if ((d != null) && (!d.toLowerCase().startsWith("<html>")))
                    return "<html>" + d.replaceAll("\n", "<br>") + "</html>";
                else
                    return this_page_current_hotspot.getURL();
            } else if (show_parts_of_speech && (this_page_text != null)) {
                PageText.WordBox box = this_page_text.getWordBox(p);
                if (box != null) {
                    return (box.partOfSpeechDescription());
                }
            }
            return null;
        }

        public String getToolTipText (MouseEvent e) {
            Point p = e.getPoint();
            // System.err.println("tooltip requested at " + p);
            String s = figureTooltipText(p);
            // System.err.println("              returning \"" + s + "\"");
            return s;
        }
        
        public void scribbleSurfaceMousePressed(MouseEvent e) {
        	super.mousePressed(e);
        }

        public void mousePressed(MouseEvent e) {
            int ourpage = ourPage();
            // System.err.println("Pageview mousePressed event");

            if (e.isConsumed())
                return;
            if (!topl.isFocusOwner())
                topl.requestFocusInWindow();

            if (ourpage < 0)
                return;

            if (e.isPopupTrigger()) {

                // make sure pie menus are in proper state

                top_menu_zoom.setEnabled(selection.isActive() && selection.isVisible());

                PageText pt = getPageText();
                boolean has_selected_text = (selection != null) && selection.isVisible();
                find_menu_more_uplib.setEnabled(has_selected_text);
                find_menu_more_google.setEnabled(has_selected_text);
                top_menu_copy.setEnabled(has_selected_text && (clipboard != null));
                find_menu_search.setEnabled(pt != null);
                // find_menu_more_google.setEnabled(has_selected_text);

                // figure out whether this document has part-of-speech tags
                boolean has_pos = false;
                boolean has_phrases = false;
                if (pt != null) {
                    PageText.WordBox box;
                    int counter = 0;
                    java.util.Iterator boxes = pt.getWordBoxes().iterator();
                    while ((counter < 100) && boxes.hasNext()) {
                        box = (PageText.WordBox) (boxes.next());
                        if (box.partOfSpeechCode() != 0)
                            has_pos = true;
                        if (box.beginsPhrase() && !box.beginsSentence())
                            has_phrases = true;
                        counter++;
                    }
                }
                show_menu_2page.setEnabled(true);
                show_menu_2page.setText(two_page ? "1 Page" : "2 Page");
                // show_menu_rsvp.setEnabled(has_phrases);
                show_menu_rsvp.setEnabled(has_phrases);
                show_menu_pos.setEnabled(has_pos);

                ArrayList ourhotspots = (ArrayList) hotspots.get(ourpage);
                boolean has_hotspots = (ourhotspots != null) && (ourhotspots.size() > 0);
                show_menu_hotspots.setEnabled(has_hotspots);

                go_to_menu_repo.setEnabled(logo_url != null);
                go_to_menu_purple.setEnabled(bookmarks[1].isSet());
                go_to_menu_green.setEnabled(bookmarks[1].isSet());
                go_to_menu_red.setEnabled(bookmarks[2].isSet());
                go_to_menu_start.setEnabled((page_count > 1) && (current_page_index != 0));
                go_to_menu_end.setEnabled((page_count > 1) && (current_page_index != (page_count - 1)));
            }

            int x = e.getX();
            int margin = (getWidth() - page_width) / 2;
            clickPoint = null;
            clickButton = 0;

            /* States:
               1.  No hotspots & Inkpot is selected & left mouse button -> start scribble
               2.  No hotspots & no Inkpot & left mouse button & shift key -> start note page
               3.  Hotspots or no inkpot or not left mouse button:
                   a)  Clear selection, if any
                   b)  Remember click point
                   c)  if pagetext, start a new selection
            */

            figureCurrentHotspot(e.getPoint());

            mousePressedMain(e);
        }

        public void mousePressedMain(MouseEvent e) {
            // This part of mousePressed can usefully be over-ridden by sub-classes.
            if (widget_inkpots.active() &&
                (e.getButton() == MouseEvent.BUTTON1) &&
                active_region.contains(e.getPoint()) &&
                (this_page_current_hotspot == null)) {
                super.mousePressed(e);
            } else {
                clickPoint = e.getPoint();
                clickButton = e.getButton();

                if (this_page_current_hotspot != null) {

                    System.err.println("possible hotspot drag...");

                } else if (selection.isVisible() && selection.contains(clickPoint)) {

                    System.err.println("possible selection drag...");

                } else if ((clickButton == MouseEvent.BUTTON1) && active_region.contains(clickPoint)) {
                    // System.err.println("pt for page " + (ourpage + first_page_number) + " is " + pt);
                    if (selection.isVisible()) {
                        Rectangle r = selection.getImageRect();
                        r.width += 1;
                        r.height += 1;
                        repaint(r);
                        selection.clear();
                    }
                    if (e.isShiftDown()) {
                        shift_key_pressed = true;
                        selection_rect = new Rectangle(clickPoint.x, clickPoint.y, 0, 0);
                    } else {
                        PageText pt = getPageText();
                        if (pt != null) {
                            selection.setFirst (pt.getNearestWordBox(clickPoint));
                            working_on_selection = true;
                            topl.repaintPageview();
                        }
                    }
                }
            }
        }

        public void mouseDragged(MouseEvent e) {
            // System.err.println("Mouse event " + e);

            if (e.isConsumed())
                return;

            int ourpage = ourPage();
            splash_page_period = 0;
            if (ourpage < 0)
                return;

            if (current_stroke != null) {
                super.mouseDragged(e);

            } else if (this_page_current_hotspot != null) {
                // drag hotspot

            } else if (selection.isVisible() && (!working_on_selection) && selection.contains(clickPoint)) {
                // drag selection

            } else if ((clickPoint != null) && (clickButton == MouseEvent.BUTTON1)) {
                if (clickPoint.distance(e.getPoint()) > 10.0 && active_region.contains(e.getPoint())) {
                    if (selection.isActive() && working_on_selection) {
                        PageText pt = getPageText();
                        selection.setLast(pt.getNearestWordBox(e.getPoint()));
                        repaint(0L, 0, 0, getWidth(), getHeight());
                    } else if (selection_rect != null) {
                        if (e.isShiftDown()) {
                            Point p = e.getPoint();
                            int width = p.x - clickPoint.x;
                            int height = p.y - clickPoint.y;
                            Rectangle r = new Rectangle((width < 0) ? p.x : clickPoint.x,
                                                        (height < 0) ? p.y : clickPoint.y,
                                                        Math.abs(width), Math.abs(height));
                            Rectangle dirty = selection_rect.union(r);
                            selection_rect = r;
                            repaint(dirty.x, dirty.y, dirty.width + 1, dirty.height + 1);
                        } else {
                            Rectangle dirty = selection_rect;
                            selection_rect = null;
                            repaint(dirty.x, dirty.y, dirty.width + 1, dirty.height + 1);
                        }
                    }
                }
            }
        }

        public void mouseReleased(MouseEvent e) {

            // System.err.println("mouseReleased:  " + e + ", isConsumed is " + e.isConsumed() + ", current_stroke is " + current_stroke);

            current_rendering_hints = high_quality_rendering_mode;

            if (e.isConsumed())
                return;

            int ourpage = ourPage();
            if (ourpage < 0)
                return;

            Point thispoint = e.getPoint();
            if ((e.getButton() == MouseEvent.BUTTON1) && current_stroke != null) {
                super.mouseReleased(e);
                // System.err.println("Finished stroke");
                if ((activity_logger != null) && activities_on) {
                    activity_logger.call(new Activity(document_id, current_page_index, Activity.AC_SCRIBBLED));
                }
            } else if (clickPoint != null) {

                if (drag_hotspot != null) {
                    // do something
                    System.err.println("releasing dragged hotspot?");
                    drag_hotspot = null;

                } else if (clickPoint.distance(thispoint) < 10.0) {
                    if (selection.isVisible() && (!working_on_selection)) {
                        Rectangle r = selection.getImageRect();
                        r.width += 1;
                        r.height += 1;
                        selection.clear();
                        topl.repaintPageview();
                    }
                    else
                        pseudoMouseClicked(e);

                } else if (selection.isVisible() && (!working_on_selection) && selection.contains(clickPoint)) {

                    // do something
                    System.err.println("releasing dragged selection?");

                } else if ((clickButton == MouseEvent.BUTTON1) && working_on_selection && selection.isActive()) {
                    PageText pt = getPageText();
                    selection.setLast(pt.getNearestWordBox(thispoint));
                    working_on_selection = false;
                    // repaint(0L, 0, 0, getWidth(), getHeight());
                    topl.repaintPageview();
                } else if (selection_rect != null) {
                    if (e.isShiftDown())
                        regionSelected(selection_rect);
                    repaint(0L, selection_rect.x, selection_rect.y, selection_rect.width + 1, selection_rect.height + 1);
                }
                clickPoint = null;
            }
            selection_rect = null;
            shift_key_pressed = e.isShiftDown();
        }
        
        public void mouseEntered(MouseEvent e) {
            // System.err.println("pageview size is " + getWidth() + "x" + getHeight());
        }

        public void mouseExited(MouseEvent e) {
            if (e.isConsumed())
                return;

            if (this_page_current_hotspot != null) {
                Rectangle r = this_page_current_hotspot.getBounds();
                this_page_current_hotspot = null;
                repaint(0L, r.x - HOTSPOT_BORDER_WIDTH, r.y - HOTSPOT_BORDER_WIDTH,
                        r.width + (2 * HOTSPOT_BORDER_WIDTH), r.height + (2 * HOTSPOT_BORDER_WIDTH));
            }
        }

        public void mouseClicked(MouseEvent e) {
            // System.err.println("Mouse event " + e);
        }

        private HotSpot findHotspot (Point p) {
            HotSpot h;
            if (this_page_hotspots == null)
                return null;
            for (int i = 0;  i < this_page_hotspots.size();  i++) {
                h = (HotSpot) this_page_hotspots.get(i);
                if (h.contains(p))
                    return h;
            }
            return null;
        }

        protected HotSpot figureCurrentHotspot(Point p) {
            if (this_page_hotspots != null) {
                HotSpot h = null;
                HotSpot last_hotspot = this_page_current_hotspot;
                if (! ((last_hotspot != null) &&
                       last_hotspot.contains(p))) {
                    this_page_current_hotspot = findHotspot(p);
                }
                if (this_page_current_hotspot != last_hotspot) {
                    // hotspot has changed
                    Rectangle r;
                    if (last_hotspot != null) {
                        r = last_hotspot.getBounds();
                        repaint(0L, r.x - HOTSPOT_BORDER_WIDTH, r.y - HOTSPOT_BORDER_WIDTH,
                                r.width + (2 * HOTSPOT_BORDER_WIDTH), r.height + (2 * HOTSPOT_BORDER_WIDTH));
                    }
                    if (this_page_current_hotspot != null) {
                        r = this_page_current_hotspot.getBounds();
                        repaint(0L, r.x - HOTSPOT_BORDER_WIDTH, r.y - HOTSPOT_BORDER_WIDTH,
                                r.width + (2 * HOTSPOT_BORDER_WIDTH), r.height + (2 * HOTSPOT_BORDER_WIDTH));
                    }
                }
            }
            return this_page_current_hotspot;
        }

        public void pseudoMouseClicked(MouseEvent e) {
            // System.err.println("Mouse event " + e);
            int margin = (getWidth() - page_width) / 2;
            Point p = e.getPoint();

            if (!topl.isFocusOwner()) {
                topl.requestFocusInWindow();
                return;
            }

            // clicking in search display window ends search
            else if ((search_state != null) && (search_rect!=null && search_rect.contains(p))) {
                if (search_state.hasMatch())
                    selection.setSpan ((PageText) pagetext_loader.get(document_id, search_state.getPage(), 0, null),
                                       search_state.getPos(), search_state.getLength());
                search_state = null;
                repaintPageview();
                return;
            }

            // clicking on a point while animation is active re-winds to that point
            if ((active_reading != null) && (show_active_reading || !active_reading.paused())) {
                active_reading.jumpTo(this_page_text.getNearestWordBox(p));
                return;
            }

            HotSpot h;
            if ((topl.showHotspots() && (this_page_hotspots.size() > 0) && ((h = findHotspot(p)) != null)) ||
                ((h = this_page_current_hotspot) != null)) {
                if ((activity_logger != null) && activities_on) {
                    byte[] url = null;
                    try {
                        url = h.getURL().getBytes("UTF-8");
                    } catch (Exception exc) {
                        System.err.println("Can't convert hotspot URL " + h.getURL() + " to UTF-8!:  " + exc);
                    }
                    ByteArrayOutputStream extension = new ByteArrayOutputStream(2 + url.length);
                    extension.write((url.length & 0xFF00) >> 8);
                    extension.write(url.length & 0xFF);
                    extension.write(url, 0, url.length);
                    activity_logger.call(new Activity(document_id, ourPage(), Activity.AC_HOTSPOT_CLICKED,
                                                      extension.toByteArray()));
                }
                String urlstring = h.getURL();
                int partIndex = urlstring.indexOf(INTERNAL_LINK_PREFIX);
                if (partIndex >= 0) {
                    // internal link to new location in this document; turn to that page
                    int pageindex = Integer.parseInt(urlstring.substring(partIndex + INTERNAL_LINK_PREFIX.length()));
                    topl.setPage(pageindex);
                } else {
                    // external link; open target in new window
                    h.call(h);
                }
                return;

            } else if (selection.isVisible()) {

                Rectangle r = selection.getImageRect();
                r.width += 1;
                r.height += 1;
                repaint(r);
                selection.clear();

            } else if (e.getButton() == MouseEvent.BUTTON3 || (!widget_inkpots.active())) {
            	int button = e.getButton();
            	if (DocViewer.this.clickForPageTurn) {
                    if (two_page) {
            			
                        if (page_offset == LEFT_PAGE_OFFSET) {
                            if (button == MouseEvent.BUTTON1)
                                topl.prevPage();
                            else if (button == MouseEvent.BUTTON3)
                                topl.nextPage();
                        } else if (page_offset == RIGHT_PAGE_OFFSET) {
                            if (button == MouseEvent.BUTTON1)
                                topl.nextPage();
                            else if (button == MouseEvent.BUTTON3)
                                topl.prevPage();
                        }
            			
                    } else {
                        int half_width = getWidth()/2;
                        int mouse_x = e.getX();
            			
                        if (mouse_x >= half_width) {
                            if (button == MouseEvent.BUTTON1)
                                topl.nextPage();
                            else if (button == MouseEvent.BUTTON3)
                                topl.prevPage();
                        } else if (mouse_x < half_width) {
                            if (button == MouseEvent.BUTTON1)
                                topl.prevPage();
                            else if (button == MouseEvent.BUTTON3)
                                topl.nextPage();
                        }
                    }
            	}
            }
        }

        public void mouseMoved(MouseEvent e) {

            if (e.isConsumed())
                return;

            if (!topl.focusOnOurApp())
                topl.requestFocusInWindow();
            // System.err.println("Mouse event " + e);

            figureCurrentHotspot(e.getPoint());
        }

        public void mouseWheelMoved (MouseWheelEvent e) {
            // System.err.println("Pageview mouse wheel event " + e);
            if (!topl.isFocusOwner())
                topl.requestFocusInWindow();
            int pages = e.getWheelRotation();
            if ((active_reading != null) && (!active_reading.paused())) {
                active_reading.speedUp(pages * 10);
            } else {
                topl.setPage(max(0, min(current_page_index + pages, (page_count - (two_page ? 2 : 1)))));
            }
        }

        protected void regionSelected (Rectangle r) {
            setSelection(current_page_index, r);
        }

        protected BufferedImage getDragImage (Rectangle correction) {
            java.util.List boxes = selection.getBoxes();
            BufferedImage im = new BufferedImage(correction.width, correction.height, BufferedImage.TYPE_INT_ARGB);
            Graphics2D g = (Graphics2D) im.getGraphics();
            if (boxes == null) {
                // rectangle drag
                g.drawImage(this_page_image,
                            0, 0, correction.width, correction.height,
                            correction.x, correction.y,
                            correction.x + correction.width, correction.y + correction.height,
                            null);
            } else {
                g.setColor(TRANSPARENT);
                g.fillRect(0, 0, im.getWidth(null), im.getHeight(null));
                g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC, 0.8f));
                if (boxes != null) {
                    for (Iterator i = boxes.iterator();  i.hasNext();) {
                        PageText.WordBox b = (PageText.WordBox) i.next();
                        int dx = b.x - correction.x;
                        int dy = b.y - correction.y;
                        g.drawImage(this_page_image,
                                    dx, dy, dx + b.width + 1, dy + b.height + 1,
                                    b.x, b.y, b.x + b.width + 1, b.y + b.height + 1,
                                    null);
                    }
                }
            }
            g.dispose();
            return im;
        }

        public void dragGestureRecognized (DragGestureEvent e) {
            // might drag either hotspot or selection

            if (clickPoint != null) {
                System.err.println("dragGestureRecognized:  " + e);

                if ((this_page_current_hotspot != null)
                    && (!this_page_current_hotspot.isIntrinsic())
                    && (!(this_page_current_hotspot.resolver instanceof HotSpot.SpanResolver))) {

                    drag_hotspot = this_page_current_hotspot;
                    Point p = e.getDragOrigin();
                    Rectangle r = drag_hotspot.getBounds();
                    Point drag_point = new Point(r.x - p.x, r.y - p.y);
                    HotSpot.Icon icon = drag_hotspot.getIcon();
                    BufferedImage di = null;
                    if (DragSource.isDragImageSupported()) {
                        if (icon == null)
                            di = link_icon;
                        else
                            di = icon.getImage();
                    }
                    DraggedHotspot s = new DraggedHotspot(drag_hotspot);
                    current_drag_source = true;
                    System.err.println("drag image is " + di);
                    ((DVTransferHandler)(this.getTransferHandler())).setTransferData(s, di);
                    if (DragSource.isDragImageSupported()) {
                        this.dragSource.startDrag(e,  DragSource.DefaultMoveDrop, di, drag_point, s, this);
                    } else {
                        this.dragSource.addDragSourceListener(this);
                        this.getTransferHandler().exportAsDrag(this, e.getTriggerEvent(), TransferHandler.COPY_OR_MOVE);
                    }
                    repaint();

                } else if (selection.isVisible() && (!working_on_selection) && selection.contains(clickPoint)) {

                    Point p = e.getDragOrigin();
                    Rectangle r = selection.getImageRect();
                    Point drag_point = new Point(r.x - p.x, r.y - p.y);
                    BufferedImage di = (DragSource.isDragImageSupported()) ? getDragImage(r) : null;
                    Image ii = getLinkImage(ourPage());
                    String t;
                    DraggedSelection s;
                    if ((t = selection.getText()) != null) {
                        s = new DraggedSelection(theRepositoryURL, document_id, ourPage(),
                                                 getPageNumberString(ourPage()),
                                                 selection.getStartPosAbsolute(),
                                                 selection.getEndPosAbsolute(),
                                                 t, document_properties, false, ii);
                    } else {
                        s = new DraggedSelection(theRepositoryURL, document_id, ourPage(),
                                                 getPageNumberString(ourPage()),
                                                 selection.getImageRect(), document_properties, false, di);
                    }
                    current_drag_source = true;
                    System.err.println("drag image is " + di);
                    ((DVTransferHandler)(this.getTransferHandler())).setTransferData(s, di);
                    if (DragSource.isDragImageSupported()) {
                        this.dragSource.startDrag(e,  DragSource.DefaultLinkNoDrop, di, drag_point, s, this);
                    } else {
                        this.dragSource.addDragSourceListener(this);
                        this.getTransferHandler().exportAsDrag(this, e.getTriggerEvent(), TransferHandler.COPY);
                    }
                    repaint();
                }
            }
        }

        // DragSourceListener methods

        public void dragDropEnd (DragSourceDropEvent e) {
            if (current_drag_source) {
                ((DVTransferHandler)(this.getTransferHandler())).setTransferData(null, null);
                current_drag_source = false;
                repaint();
            }
        }

        public void dragEnter (DragSourceDragEvent e) {
            // System.err.println("dragEnter " + e);
        }

        public void dragOver (DragSourceDragEvent e) {
            // System.err.println("dragOver " + e);
        }

        public void dropActionChanged (DragSourceDragEvent e) {
            // System.err.println("dropActionChanged " + e);
        }

        public void dragExit (DragSourceEvent e) {
            // System.err.println("dragExit " + e);
        }

        // FocusListener methods

        public void focusGained (FocusEvent e) {
            app_has_focus = true;
        }

        public void focusLost (FocusEvent e) {
            app_has_focus = false;
            if (this_page_current_hotspot != null) {
                Rectangle r = this_page_current_hotspot.getBounds();
                this_page_current_hotspot = null;
                repaint(0L, r.x - HOTSPOT_BORDER_WIDTH, r.y - HOTSPOT_BORDER_WIDTH,
                        r.width + (2 * HOTSPOT_BORDER_WIDTH), r.height + (2 * HOTSPOT_BORDER_WIDTH));
            }
        }

        protected void finalize () throws Throwable {
            System.err.println("finalizing Pageview " + this);
            saveNotes(ourPage(), false);
            super.finalize();
        }

    } // end of class Pageview


    static private interface InkpotsListener extends java.util.EventListener {
        public void inkpotChanged (boolean active, Inkpots.Pot current);
    }

    static public class Inkpots {

        final static Dimension BEST_CURSOR_SIZE = Toolkit.getDefaultToolkit().getBestCursorSize(32, 32);

        final static Color TRANSPARENT = new Color(0, 0, 0, 0);
        final static Color HALF_GRAY = new Color(0.5f, 0.5f, 0.5f, 0.5f);

        private boolean visible_flag = false;
        private Pot selected_inkpot = null;
        private Vector inkpots = null;
        private Vector listeners = null;

        public class Pot {

            private int index;
            private Color color;
            private float size;
            private Rectangle location;
            private String tooltip_text;
            private DocViewer topl;
            private Cursor drawing_cursor;

            public Pot (int index_p, Color color_p, float size_p, Rectangle location_p, String tooltiptext) {
                index = index_p;
                size = size_p;
                color = color_p;
                location = location_p;
                tooltip_text = tooltiptext;
                drawing_cursor = null;
            }

            public boolean contains (Point p) {
                return ((location != null) && location.contains(p));
            }


            public void select () {
                Inkpots.this.select(this);
            }

            public String getToolTipText (Point p) {
                if (visible_flag && contains(p))
                    return tooltip_text;
                return null;
            }

            public void setToolTipText (String text) {
                tooltip_text = text;
            }

            public Rectangle getRect() {
                return location;
            }

            public Color getColor () {
                return color;
            }

            public float getSize () {
                return size;
            }

            public void resize (int increment) {
                size = min(30.0f, max(1.0f, size + increment));
                drawing_cursor = null;
            }

            public void setLocation (int x, int y, int width, int height) {
                location.x = x;
                location.y = y;
                location.width = width;
                location.height = height;
            }

        /*
        public void draw (Graphics2D g2) {
            if ((visible_flag || (color == WHITE)) && (location != null)) {
                Ellipse2D e = new Ellipse2D.Double(location.x, location.y, location.width, location.height);

                if (size > 0) {
                    g2.setColor(WHITE);
                    g2.fill(e);
                }
                g2.setColor(color);
                g2.fill(e);
                g2.setColor(LEGEND_COLOR);
                g2.draw(e);
                if (color != WHITE) {
                    if (selected_inkpot == this) {
                        g2.draw(e);
                        g2.setColor(UPLIB_ORANGE);
                        g2.draw(new Ellipse2D.Double(location.x-2, location.y-2, location.width+4, location.height+4));
                    }
                    if (size > 0) {
                        g2.setColor(GRAY);
                        g2.draw(new Ellipse2D.Double(location.x + 4,
                                                     (int)(location.y + (location.height - size) / 2),
                                                     location.width - 8, (int) size));
                    }
                } else if (visible_flag && (selected_inkpot != this) && (selected_inkpot != null)) {
                    g2.setColor(selected_inkpot.color);
                    if (os_name.startsWith("Windows"))
                        // hack to work around Windows Java rendering bug
                        g2.fill(new Ellipse2D.Double(location.x+3.5, location.y+3.5, location.width-6, location.height-6));
                    else
                        g2.fill(new Ellipse2D.Double(location.x+3, location.y+3, location.width-6, location.height-6));
                }
            }
        }
        */

            public void draw (Graphics2D g2, boolean selection_active) {

                if (location != null) {

                    if (color == WHITE) {

                        g2.drawImage(visible_flag ? button_down_background : button_up_background, location.x, location.y, null);
                        if ((selected_inkpot != null) && (selected_inkpot != this)) {
                            Color c = selected_inkpot.color;
                            if (c.getAlpha() != 255) {
                                g2.setColor(WHITE);
                                g2.fillRoundRect(location.x + 7, location.y + 7, 16, 16, 3, 3);
                            }
                            g2.setColor(c);
                            g2.fillRoundRect(location.x + 7, location.y + 7, 16, 16, 3, 3);
                        }
                        g2.drawImage(small_inkpot_with_quill, location.x, location.y, null);
                        if ((selected_inkpot != null) && (selected_inkpot != this)) {
                            Color c = selected_inkpot.color;
                            if (c.getAlpha() != 255) {
                                g2.setColor(WHITE);
                                g2.fillRoundRect(location.x + 12, location.y + 17, 5, 4, 3, 3);
                            }
                            g2.setColor(c);
                            g2.fillRoundRect(location.x + 12, location.y + 17, 5, 4, 3, 3);
                        }

                    } else if (visible_flag) {

                        if (selection_active) {

                            g2.drawImage(button_up_background, location.x, location.y, null);
                            g2.drawImage(smalltext_image, location.x, location.y, null);
                            g2.setColor(color);
                            if (size >= 2.5f)
                                g2.fillRoundRect(location.x + 7, location.y + (location.height - (int) size)/2, 16, (int) size, 2, 2);
                            else
                                g2.fillRoundRect(location.x + 7, location.y + 23 - (int) size - 1, 16, (int) size, 2, 2);

                        } else if (selected_inkpot == this) {

                            g2.drawImage(button_down_background, location.x, location.y, null);
                            g2.drawImage(big_inkpot, location.x, location.y, null);
                            if (color.getAlpha() != 255) {
                                g2.setColor(WHITE);
                                g2.fillRoundRect(location.x + 9, location.y + 14, 10, 7, 3, 3);
                            }
                            g2.setColor(color);
                            g2.fillRoundRect(location.x + 9, location.y + 14, 10, 7, 3, 3);

                        } else {

                            g2.drawImage(button_up_background, location.x, location.y, null);
                            g2.drawImage(big_inkpot, location.x, location.y, null);
                            if (color.getAlpha() != 255) {
                                g2.setColor(WHITE);
                                g2.fillRoundRect(location.x + 9, location.y + 14, 10, 7, 3, 3);
                            }
                            g2.setColor(color);
                            g2.fillRoundRect(location.x + 9, location.y + 14, 10, 7, 3, 3);

                        }
                    }
                }
            }

            public Cursor getDrawingCursor () {
                if (drawing_cursor == null) {
                    BufferedImage img = new BufferedImage(BEST_CURSOR_SIZE.width, BEST_CURSOR_SIZE.height, BufferedImage.TYPE_INT_ARGB);
                    Point hotspot = new Point(img.getWidth()/2, img.getHeight()/2);
                    Graphics2D g = (Graphics2D) img.getGraphics();
                    g.setColor(TRANSPARENT);
                    g.fillRect(0, 0, img.getWidth(), img.getHeight());
                    if (os_name.startsWith("Windows"))
                        // Windows doesn't really support quality cursors
                        g.setRenderingHints(low_quality_rendering_mode);
                    else
                        g.setRenderingHints(high_quality_rendering_mode);
                    if (!PenSupport.isTabletAvailable()) {
                        // using a mouse, so add some graphics to small cursors
                        if (size < 5) {
                            g.setStroke(new BasicStroke(3.0f, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                            g.setColor(HALF_GRAY);
                            g.fill(new Line2D.Float(hotspot.x + size/2, hotspot.y - size/2, img.getWidth()-1, 1));
                        }
                    }
                    if (os_name.startsWith("Windows")) {
                        // work around translucency bug in Windows
                        g.setColor(WHITE);
                        g.fill(new Arc2D.Float(hotspot.x - size/2, hotspot.y - size/2, size, size, 0, 360, Arc2D.CHORD));
                    }
                    g.setColor(color);
                    g.fill(new Arc2D.Float(hotspot.x - size/2, hotspot.y - size/2, size, size, 0, 360, Arc2D.CHORD));
                    /*
                      try {
                      ImageIO.write(img, "PNG", new javax.imageio.stream.FileImageOutputStream(new File("test.png")));
                      } catch (Exception x) {
                      x.printStackTrace(System.err);
                      }
                    */
                    drawing_cursor = Toolkit.getDefaultToolkit().createCustomCursor(img, hotspot, this.toString());
                }
                return drawing_cursor;                    
            }

            public byte[] getInkBytes () {

                // to do this right, we should use something like
                // g.getDefaultTransform().concatenate(g.getEnvironment().getNormalizingTransform())
                // to figure the right scaling transform, but since we know that on screens the
                // coordinate system is in 72nds of an inch (approximately), we just use that.
                // Convert first to inches, then to decimillimeters.
                
                byte thickness = (byte) ((size / 72.0) * 254);
                return new byte[] { (byte) color.getRed(), (byte) color.getGreen(), (byte) color.getBlue(),
                                    (byte) color.getAlpha(), thickness };
            }
        }


        public Pot create (int index_p, Color color_p, float size_p, Rectangle location_p, String tooltiptext_p) {
            Pot v = new Pot(index_p, color_p, size_p, location_p, tooltiptext_p);
            add(v);
            return v;
        }

        public void add (Pot pot) {
            if (inkpots == null)
                inkpots = new Vector();
            inkpots.add(pot);
        }

        public void addListener (InkpotsListener l) {
            if (listeners == null)
                listeners = new Vector();
            listeners.add(l);
        }

        private void notifyListeners () {
            if (listeners != null) {
                boolean aktiv = this.active();
                Iterator i = listeners.iterator();
                while (i.hasNext()) {
                    InkpotsListener l = (InkpotsListener) (i.next());
                    l.inkpotChanged (aktiv, selected_inkpot);
                }
            }
        }

        void setVisible (boolean state) {
            visible_flag = state;
        }

        boolean isVisible() {
            return visible_flag;
        }

        public void select (Pot pot) {
            selected_inkpot = pot;
            notifyListeners();
        }

        Pot getSelected () {
            return selected_inkpot;
        }

        void clearSelected() {
            selected_inkpot = null;
            notifyListeners();
        }

        public boolean active() {
            return (visible_flag && (selected_inkpot != null) && (selected_inkpot.color != WHITE));
        }

        void selectByIndex (int index_p, boolean note) {
            Pot old_selected = selected_inkpot;
            Iterator i = inkpots.iterator();
            while (i.hasNext()) {
                Pot inkp = (Pot) i.next();
                if (inkp.index == index_p) {
                    if (note) 
                        inkp.select();
                    else
                        selected_inkpot = inkp;
                    notifyListeners();
                }
            }
        }

        Iterator getIterator () {
            return inkpots.iterator();
        }

        Pot inVisiblePot (Point p) {
            Iterator i = inkpots.iterator();
            while (i.hasNext()) {
                Pot inkp = (Pot) i.next();
                if ((inkp.color != WHITE) && (!visible_flag))
                    continue;
                if (inkp.contains(p))
                    return inkp;
            }
            return null;
        }
    }
    
    public boolean widgetInkpotsActive() {
    	return this.widget_inkpots.active();
    }

    public static class AnnotationTimeControl extends JPanel implements ChangeListener, ActionListener {

        JSlider before;
        JSlider after;
        JLabel before_label;
        JLabel after_label;
        JButton ok_button;
        JButton zoom_in_button;
        JButton zoom_out_button;
        long base_date;
        Calendar calendar;
        SimpleDateFormat df;
        DocViewer docv;

        static private final int MILLISECONDS_DIVIDER = 60000;
        static private final int YEAR_IN_MINUTES = (365 * 24 * 60);
        static private final int MONTH_IN_MINUTES = (30 * 24 * 60);
        static private final int WEEK_IN_MINUTES = (7 * 24 * 60);
        static private final int DAY_IN_MINUTES = (24 * 60);
        static private final long BEGINNING_OF_UPLIB = (new GregorianCalendar(2003, 0, 0)).getTimeInMillis() / MILLISECONDS_DIVIDER;

        public AnnotationTimeControl (DocViewer dv) {
            super();
            setBackground(TOOLS_COLOR);
            setOpaque(true);
            setVisible(false);
            setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));
            setMinimumSize(new Dimension(300, 0));

            Box b;

            JLabel toplabel = new JLabel(" Annotation Timespan ");
            toplabel.setFont(new Font(null, Font.ITALIC, getFont().getSize() + 2));
            toplabel.setForeground(DARK_COLOR);
            toplabel.setHorizontalAlignment(SwingConstants.CENTER);
            add(centered(toplabel));
            add(Box.createHorizontalStrut(300));
            add(Box.createVerticalStrut(5));

            before_label = new JLabel();
            before_label.setHorizontalAlignment(SwingConstants.CENTER);
            add(centered(before_label));
            before = new JSlider(SwingConstants.HORIZONTAL);
            before.addChangeListener(this);
            add(before);

            after = new JSlider(SwingConstants.HORIZONTAL);
            after.addChangeListener(this);
            add(after);
            after_label = new JLabel();
            after_label.setHorizontalAlignment(SwingConstants.CENTER);
            add(centered(after_label));

            b = Box.createHorizontalBox();
            b.add(Box.createHorizontalGlue());
            zoom_in_button = new JButton("Zoom In");
            zoom_in_button.addActionListener(this);
            zoom_in_button.setBackground(TOOLS_COLOR);
            zoom_in_button.setHorizontalAlignment(SwingConstants.CENTER);
            b.add(zoom_in_button);
            b.add(Box.createHorizontalGlue());
            zoom_out_button = new JButton("Zoom Out");
            zoom_out_button.addActionListener(this);
            zoom_out_button.setBackground(TOOLS_COLOR);
            zoom_out_button.setHorizontalAlignment(SwingConstants.CENTER);
            b.add(zoom_out_button);
            b.add(Box.createHorizontalGlue());
            ok_button = new JButton("OK");
            ok_button.addActionListener(this);
            ok_button.setBackground(TOOLS_COLOR);
            ok_button.setHorizontalAlignment(SwingConstants.CENTER);
            b.add(ok_button);
            b.add(Box.createHorizontalGlue());
            add(b);

            calendar = Calendar.getInstance();
            df = new SimpleDateFormat("EEE, d MMM yyyy, h:mm a");
            base_date = 0;
            docv = dv;
        }

        private JComponent centered (JComponent j) {
            Box b = Box.createHorizontalBox();
            b.add(Box.createHorizontalGlue());
            b.add(j);
            b.add(Box.createHorizontalGlue());
            return b;
        }

        private long tomorrow () {
            return System.currentTimeMillis() + (24 * 60 * MILLISECONDS_DIVIDER);
        }

        public void setVisible (boolean f) {
            if (f) {
                // make sure it's on top
                Container p = getParent();
                p.remove(this);
                p.add(this, 0);
                setRange((docv.annotation_span_start == null) ? BEGINNING_OF_UPLIB : docv.annotation_span_start.getTime(),
                         (docv.annotation_span_end == null) ? tomorrow() : docv.annotation_span_end.getTime());
                setSize(getPreferredSize());
                setLocation((p.getWidth() - getWidth()) / 2, (p.getHeight() - getHeight())/2);
                getRootPane().setDefaultButton(ok_button);
            }
            super.setVisible(f);
        }

        private void setUpSlider (JSlider slider, long range) {
            slider.setMinimum(0);
            slider.setMaximum((int) range);
            /*
            slider.setSnapToTicks(false);
            slider.setPaintTicks(false);
            if (range < 60) {
                slider.setPaintTicks(true);
                slider.setMajorTickSpacing(10);
                slider.setMinorTickSpacing(1);
                slider.setSnapToTicks(true);
            }
            */
        }

        public void setRange (long earliest, long latest) {
            long before_value = before.getValue() + base_date;
            long after_value = after.getValue() + base_date;
            long range = (latest - earliest) / MILLISECONDS_DIVIDER;
            if (range < 0)
              return;
            base_date = earliest / MILLISECONDS_DIVIDER;
            setUpSlider(after, range);
            after.setValue(Math.max(0, Math.min((int) range, (int) (after_value - base_date))));
            setUpSlider(before, range);
            if (before_value == after_value)
                before.setValue((int) range);
            else
              before.setValue(Math.max(0, Math.min((int) range, (int) (before_value - base_date))));
        }

        public void setRange (Date earliest, Date latest) {
            setRange(earliest.getTime(), latest.getTime());
        }

        public void setBefore (Date latest) {
            int t = (int) (latest.getTime() / MILLISECONDS_DIVIDER);
            if (before.getMaximum() < t)
              before.setMaximum(t);
            before.setValue(t);              
        }

        public void setAfter (Date earliest) {
            int t = (int) (earliest.getTime() / MILLISECONDS_DIVIDER);
            if (after.getMaximum() < t)
              after.setMaximum(t);
            after.setValue(t);              
        }

        public void stateChanged (ChangeEvent e) {
            if (e.getSource() == before) {
                calendar.setTimeInMillis((base_date + before.getValue()) * MILLISECONDS_DIVIDER);
                before_label.setText("before:  " + df.format(calendar.getTime()));
                if (after.getValue() > before.getValue())
                  after.setValue(Math.max(0, before.getValue() - 1));
            } else if (e.getSource() == after) {
                calendar.setTimeInMillis((base_date + after.getValue()) * MILLISECONDS_DIVIDER);
                after_label.setText("after:  " + df.format(calendar.getTime()));
                if (after.getValue() > before.getValue())
                  before.setValue(Math.min(before.getMaximum(), after.getValue() + 1));
            }
        }

        public void actionPerformed (ActionEvent e) {
            if (e.getSource() == ok_button) {
                docv.setAnnotationSpan(new Date((base_date + before.getValue()) * MILLISECONDS_DIVIDER),
                                       new Date((base_date + after.getValue()) * MILLISECONDS_DIVIDER));
                setVisible(false);
                docv.repaintPageview();
            } else if (e.getSource() == zoom_in_button) {
                setRange(new Date((base_date + after.getValue()) * MILLISECONDS_DIVIDER),
                         new Date((base_date + before.getValue()) * MILLISECONDS_DIVIDER));
            } else if (e.getSource() == zoom_out_button) {
                int midpoint = Math.max(((before.getValue() - after.getValue()) / 2) + after.getValue(), 1);
                long new_base = Math.max(BEGINNING_OF_UPLIB, base_date - (9 * midpoint));
                int new_max = Math.max(1, Math.min(10 * after.getMaximum(), (int) ((tomorrow() / MILLISECONDS_DIVIDER) - base_date)));
                setRange(new Date(new_base * MILLISECONDS_DIVIDER),
                         new Date((new_base + new_max) * MILLISECONDS_DIVIDER));
            }
        }
    }

    public class ZoomedViewer extends JPanel implements MouseListener, MouseMotionListener, MouseWheelListener
    {
        private BufferedImage page_image;
        private Rectangle selected_region;
        private Rectangle region_to_show;
        private DocViewer topl;
        private int current_page;
        private double current_scaling;
        private double scaling;         /* big-page-thumbnail-pixel position to hires-page-image-pixel position */
        private double translation_x;
        private double translation_y;  /* pixels to translate big-page-thumbnail to get hires-page-image location */
        private int hires_dpi;
        private Point mouse_drag_last_point;
        private int image_width;
        private int image_height;

        public ZoomedViewer (DocViewer topl, double scaling, Dimension translation, int hires_dpi) {
            this.topl = topl;
            this.region_to_show = null;
            this.selected_region = null;
            this.page_image = null;
            this.scaling = hires_dpi / (scaling * 72.0);
            this.translation_x = (translation.width * hires_dpi) / 72.0;
            this.translation_y = (translation.height * hires_dpi) / 72.0;
            this.hires_dpi = hires_dpi;
            this.mouse_drag_last_point = null;
            this.image_width = 0;
            this.image_height = 0;

            this.addMouseMotionListener(this);
            this.addMouseListener(this);
            this.addMouseWheelListener(this);
        }

        public Rectangle translate_rect_from_big_page_thumbnail (Rectangle r) {
            System.err.println("scaling is " + scaling + ", translation is " + translation_x + "," + translation_y + ", dpi is " + hires_dpi);
            if (page_image != null) {
                image_width = page_image.getWidth(null);
                image_height = page_image.getHeight(null);
            }

            Rectangle r2 = new Rectangle (Math.max(0, (int) ((r.x * scaling) - translation_x)),
                                          Math.max(0, (int) ((r.y * scaling) - translation_y)),
                                          (int) (r.width * scaling), (int) (r.height * scaling));
            System.err.println("" + r + " => " + r2);
            return r2;
        }

        public void fetch_page (int page_no) {
            page_image = null;
            current_page = page_no;
            if (hires_page_image_loader != null) {
                page_image = (BufferedImage) thumbnail_image_loader.get(document_id, current_page, 2, new PageImageSetter(page_no, this));
            }
        }

        private Rectangle identify_source_region (Rectangle r2) {
            int source_x = 0, source_y = 0, source_width = 0, source_height = 0;
            double aspect_ratio_image = (double) (r2.width) / (double) (r2.height);
            double aspect_ratio_window = (double) (getWidth()) / (double)(getHeight());
            if (aspect_ratio_image > aspect_ratio_window) {
                // dominated by width, so scale height
                source_x = r2.x;
                source_width = r2.width;
                source_height = (int) (((double) r2.width) / aspect_ratio_window);
                source_y = Math.max(0, r2.y - ((source_height - r2.height) / 2));
            } else {
                // dominated by height, so scale width
                source_y = r2.y;
                source_height = r2.height;
                source_width = (int) (((double) r2.height) * aspect_ratio_window);
                source_x = Math.max(0, r2.x - ((source_width - r2.width) / 2));
            }
            current_scaling = (double) source_height / (double) getHeight();
            return new Rectangle (source_x, source_y, source_width, source_height);
        }

        public void setRect (Rectangle r) {
            selected_region = translate_rect_from_big_page_thumbnail(r);
            region_to_show = identify_source_region(selected_region);
            adjust_region_to_show(0, 0);
        }

        public void clear() {
            page_image = null;
            selected_region = null;
            region_to_show = null;
            image_height = 0;
            image_width = 0;
        }

        public void paintComponent (Graphics g) {
            if (page_image == null)
                page_image = (BufferedImage) thumbnail_image_loader.get(document_id, current_page, 2, null);
            // System.err.println("repaint:  page image is " + page_image + ", region is " + region_to_show);
            if (page_image != null) {
                if ((image_width == 0) || (image_height == 0)) {
                    image_width = page_image.getWidth(null);
                    image_height = page_image.getHeight(null);
                }
                // comment out high-quality mode because it takes forever with large page images
                // ((Graphics2D)g).setRenderingHints(high_quality_rendering_mode);
                g.drawImage(page_image,
                            0, 0, getWidth(), getHeight(),
                            region_to_show.x, region_to_show.y,
                            region_to_show.x + region_to_show.width,
                            region_to_show.y + region_to_show.height,
                            null);
            } else {
                String notetext = "Loading high-resolution page image...";
                Rectangle2D bounds = g.getFontMetrics().getStringBounds(notetext, g);
                g.setColor(BACKGROUND_COLOR);
                g.fillRect(0, 0, getWidth(), getHeight());
                int xl = Math.round((getWidth() - (int) bounds.getWidth()) / 2);
                int yl = Math.round((getHeight() - (int) bounds.getHeight()) / 2);
                g.setColor(WHITE);
                g.fillRoundRect(xl - 10, yl - 10 - (int) bounds.getHeight(), (int) (bounds.getWidth() + 20), (int) (bounds.getHeight() + 20), 10, 10);
                g.setColor(BLACK);
                g.drawString(notetext, xl, yl);
            }
        }

        private void adjust_region_to_show (int deltax, int deltay) {
            if (deltax != 0)
                region_to_show.x = Math.max(0, region_to_show.x - (int) (deltax * current_scaling));
            if (deltay != 0)
                region_to_show.y = Math.max(0, region_to_show.y - (int) (deltay * current_scaling));
            if ((image_width > 0) && ((region_to_show.x + region_to_show.width) > image_width))
                region_to_show.x = Math.max(0, image_width - region_to_show.width);
            if ((image_height > 0) && ((region_to_show.y + region_to_show.height) > image_height))
                region_to_show.y = Math.max(0, image_height - region_to_show.height);
        }

        private void adjust_region_to_show (double new_scaling) {
            region_to_show.x = Math.max(0, (int) (region_to_show.x + ((region_to_show.width - (region_to_show.width * new_scaling)) / 2)));
            region_to_show.y = Math.max(0, (int) (region_to_show.y + ((region_to_show.height - (region_to_show.height * new_scaling)) / 2)));
            region_to_show.width = (int) (region_to_show.width * new_scaling);
            region_to_show.height = (int) (region_to_show.height * new_scaling);
            current_scaling = current_scaling * new_scaling;
            if ((image_width > 0) && ((region_to_show.x + region_to_show.width) > image_width))
                region_to_show.x = Math.max(0, image_width - region_to_show.width);
            if ((image_height > 0) && ((region_to_show.y + region_to_show.height) > image_height))
                region_to_show.y = Math.max(0, image_height - region_to_show.height);
        }

        public void mouseClicked(MouseEvent e) {
            if (e.getClickCount() > 1) {
                topl.hideZoomIn();
            }
        }

        public void mouseEntered(MouseEvent e) {
        }

        public void mouseExited(MouseEvent e) {
        }

        public void mousePressed(MouseEvent e) {
            mouse_drag_last_point = e.getPoint();
        }

        public void mouseReleased(MouseEvent e) {
            if (mouse_drag_last_point != null) {
                Point p = e.getPoint();
                adjust_region_to_show(p.x - mouse_drag_last_point.x, p.y - mouse_drag_last_point.y);
                mouse_drag_last_point = null;
            }
            repaint();
        }

        public void mouseDragged(MouseEvent e) {
            if (mouse_drag_last_point != null) {
                Point p = e.getPoint();
                adjust_region_to_show(p.x - mouse_drag_last_point.x, p.y - mouse_drag_last_point.y);
                mouse_drag_last_point = p;
            }
            repaint();
        }

        public void mouseMoved(MouseEvent e) {
        }

        public void mouseWheelMoved (MouseWheelEvent e) {
            int clicks = e.getWheelRotation();
            double new_scaling = 1.0D;
            if (clicks > 0)
                new_scaling = Math.pow(1.1D, (double) clicks);
            else if (clicks < 0)
                new_scaling = Math.pow(0.9D, (double) -clicks);
            else
                return;
            adjust_region_to_show(new_scaling);
            // System.err.println("clicks is " + clicks + ", scaling is " + new_scaling + ", current_scaling is " + current_scaling);
            repaint();
        }
    }

    public class PageControl extends JPanel
        implements MouseListener, MouseMotionListener, MouseWheelListener,
                   ImageObserver,
                   DragGestureListener, DragSourceListener {

        protected Rectangle       next_rect;
        protected Rectangle       back_rect;
        protected Rectangle       logo_rect;
        protected Rectangle       eyeball_rect;
        protected Rectangle       hotspots_rect;
        protected Rectangle       thumbnails_rect;
        protected Rectangle       search_rect;
        protected Rectangle       note_rect;
        protected Rectangle       snapback_rect;
        protected Rectangle       zoom_in_rect;
        protected Inkpots.Pot     white_ink_pot = null;
        protected DocViewer       topl;
        protected boolean         show_pots = false;
        protected int             image_bits = 0;
        protected int             font_height;
        protected Rectangle       clickedRect = null;
        protected int             clickedButton = 0;
        protected Point           dragging_bookmark = null;
        protected Bookmark        bookmark_being_dragged = null;
        protected Point           bookmark_dragging_initial_spot = null;
        protected boolean         mouse_in_clickedRect = false;
        protected DragSource      dragSource = null;
        protected boolean         horizontal;

        public PageControl(DocViewer toplevel, boolean pots_visible, int initial_inkpot, boolean horizontal) {
            super(new BorderLayout());
            topl = toplevel;
            // setBackground(WHITE);
            setBackground(TOOLS_COLOR);
            addMouseListener(this);
            addMouseWheelListener(this);
            addMouseMotionListener(this);
            setFocusable(false);

            /*
              set up some dummy sizes for the images rects.  Real sizes
              will be set up when images finish loading.
              */

            next_rect = new Rectangle(0, 35, 30, 30);
            back_rect = new Rectangle(0, 60, 30, 30);
            snapback_rect = new Rectangle(0, 90, 30, 30);
            eyeball_rect = new Rectangle(0, 120, 30, 30);
            logo_rect = new Rectangle(0, 150, 30, 30);
            search_rect = new Rectangle(0, 185, 30, 30);

            eyeball_rect.setSize(eyeball_image.getWidth(null), eyeball_image.getHeight(null));
            next_rect.setSize(next_arrow.getWidth(null), next_arrow.getHeight(null));
            back_rect.setSize(back_arrow.getWidth(null), back_arrow.getHeight(null));
            logo_rect.setSize(small_uplib_logo.getWidth(null), small_uplib_logo.getHeight(null));
            snapback_rect.setSize(snapback_left_image.getWidth(null), snapback_left_image.getHeight(null));

            white_ink_pot = widget_inkpots.create(0, WHITE, 0.0f, new Rectangle(0, 230, 30, 30), "");
            widget_inkpots.create(1, RED_INK_COLOR, 2.0f, new Rectangle(0, 260, 30, 30), "Pick up red pen");
            widget_inkpots.create(2, BLUE_INK_COLOR, 2.0f, new Rectangle(0, 285, 30, 30), "Pick up blue pen");

            widget_inkpots.create(4, GREEN_MARKER_COLOR, 16.0f, new Rectangle(0, 310, 30, 30), "Pick up green hi-lighter");
            widget_inkpots.create(5, BLUE_MARKER_COLOR, 16.0f, new Rectangle(0, 335, 30, 30), "Pick up blue hi-lighter");
            widget_inkpots.create(3, PINK_MARKER_COLOR, 16.0f, new Rectangle(0, 360, 30, 30), "Pick up pink hi-lighter");

            widget_inkpots.setVisible(pots_visible);
            widget_inkpots.selectByIndex(initial_inkpot, false);

            note_rect = new Rectangle(0, 400, 30, 30);
            font_height = 0;

            hotspots_rect = new Rectangle(0, 435, 30, 30);
            thumbnails_rect = new Rectangle(0, 470, 30, 30);
            zoom_in_rect = new Rectangle(0, 505, 30, 30);

            hotspots_rect.setSize(hotspots_image.getWidth(null), hotspots_image.getHeight(null));
            thumbnails_rect.setSize(thumbnails_image.getWidth(null), thumbnails_image.getHeight(null));
            zoom_in_rect.setSize(zoom_in_image.getWidth(null), zoom_in_image.getHeight(null));

            setPreferredSize(new Dimension(max(eyeball_rect.width,
                                               max(next_rect.width,
                                                   max(back_rect.width,
                                                       logo_rect.width))) + 10,
                                           (page_rotated ? page_width + 10 : page_height + 10)));


            arrangeButtons();

            // we set this to any string just to signal that we support tooltips
            setToolTipText("UpLib controls");

            dragSource = DragSource.getDefaultDragSource();
            dragSource.addDragSourceListener(this);
            this.setTransferHandler(new DVTransferHandler());
            this.dragSource.createDefaultDragGestureRecognizer(this,
                                                               DnDConstants.ACTION_COPY,
                                                               this);
        }

        private int setButtonLocation (int offset, Rectangle button, int spacing) {
            if (horizontal) {
                button.x = offset + spacing;
                button.y = 0;
            } else {
                button.x = 0;
                button.y = offset + spacing;
            }
            return (offset + spacing + button.width);
        }

        private void positionButtonOffscreen(Rectangle r) {
            r.x = -5 - r.width;
            r.y = -5 - r.height;
        }

        protected int arrangeButtons () {

            int offset = 25;  /* just after page # */

            if (page_count > 1) {
                offset = setButtonLocation(offset, next_rect, 0);
                offset = setButtonLocation(offset, back_rect, -5);
                offset = setButtonLocation(offset, snapback_rect, -5);
            } else {
                positionButtonOffscreen(next_rect);
                positionButtonOffscreen(back_rect);
                positionButtonOffscreen(snapback_rect);
            }
            offset = setButtonLocation(offset, eyeball_rect, 0);
            offset = setButtonLocation(offset, logo_rect, 0);
            if (pagetext_loader != null)
                offset = setButtonLocation(offset, search_rect, 0);
            
            offset += 5;

            Iterator i = widget_inkpots.getIterator();
            while (i.hasNext()) {
                Inkpots.Pot p = (Inkpots.Pot) (i.next());
                offset = setButtonLocation(offset, p.getRect(), -6);
            }
            offset = setButtonLocation(offset, note_rect, -2);
            offset = setButtonLocation(offset, zoom_in_rect, 0);

            if (page_count > 1)
                offset = setButtonLocation(offset, thumbnails_rect, 0);
            else
                positionButtonOffscreen(thumbnails_rect);
            offset = setButtonLocation(offset, hotspots_rect, 0);

            return offset;
        }

        public Dimension getMaximumSize() {
            Dimension t = null;
            try {
                if (topl != null)
                    t = topl.getPreferredSize();
            } catch (Exception x) {
            }
            Dimension d = getPreferredSize();
            Dimension s = super.getMaximumSize();
            int width = min((page_rotated ? (page_height + 10) : (page_width + 10)),
                            (d.width < 1) ? (((t != null) && (t.width > 0)) ? t.width : s.width) : d.width);
            int height = min((page_rotated ? (page_width + 10) : (page_height + 10)),
                             (d.height < 1) ? (((t != null) && (t.height > 0)) ? t.height : s.height) : d.height);
            // System.err.println("PageControl preferred size is " + d + ", super max size is " + s);
            return new Dimension(width, height);
        }

        private boolean hotspotsRelevant () {
            return ((hotspots.size() > 0) &&
                    ((((ArrayList) hotspots.get(current_page_index)).size() > 0) ||
                     (two_page &&
                      ((current_page_index + 1) < page_count) &&
                      (((ArrayList)hotspots.get(current_page_index + 1)).size() > 0))));
        }

        public String getToolTipText (MouseEvent e) {
            Point p = e.getPoint();
            int pagenumber = min(current_page_index + (two_page ? 1 : 0), (page_count - 1));
            if ((logo_url != null) && logo_rect.contains(p)) {
                return "Leave this document";
            } else if (back_rect.contains(p) && (pagenumber > 1)) {
                return "Back " + (two_page ? "two pages" : "one page");
            } else if (next_rect.contains(p) && (pagenumber < page_count)) {
                return "Forward " + (two_page ? "two pages" : "one page");
            } else if ((activity_logger != null) && eyeball_rect.contains(p)) {
                if (activities_on)
                    return "Disable activity monitor";
                else
                    return "Enable activity monitor";
            } else if (note_rect.contains(p) && (widget_inkpots.isVisible() ||
                                                 (selection.isVisible() &&
                                                  selection.isActive() &&
                                                  selection.getBoxes() == null))) {
                return "Add note page";
            } else if (search_rect.contains(p)) {
                if (search_state != null)
                    return "Stop text search";
                else
                    return "Search for text in document";
            } else if (hotspotsRelevant() && hotspots_rect.contains(p)) {
                if (topl.showHotspots())
                    return "Turn off hotspots";
                else
                    return "Show hotspots";
            } else if ((snapback_page >= 0) && snapback_rect.contains(p)) {
                if (snapback_page < current_page_index)
                    return "Snap back to page " + (snapback_page + first_page_number);
                else
                    return "Snap forward to page " + (snapback_page + first_page_number);
            } else if (thumbnails_rect.contains(p)) {
                if (thumbnails_showing)
                    return "Return to page view";
                else
                    return "Show page thumbnails";
            } else if ((hires_page_image_loader != null) && zoom_in_rect.contains(p)) {
                return "Zoom In";
            } else if (p.y < font_height) {
                return "Page " + min(page_count, current_page_index + (two_page ? 2 : 1)) + " of " + page_count + " pages";
            } else {
                Inkpots.Pot inkp = widget_inkpots.inVisiblePot(p);
                if (inkp == white_ink_pot) {
                    if (widget_inkpots.isVisible()) {
                        if (widget_inkpots.getSelected() == white_ink_pot)
                            return "Turn off scribble mode";
                        else
                            return "Put pen or hi-lighter down";
                    }
                    else
                        return "Turn on scribble mode";
                } else if (inkp != null) {
                    return inkp.getToolTipText(p);
                }
            }
            return null;
        }

        private void paintButton (Graphics g, BufferedImage label, int x, int y, boolean down) {
            g.drawImage(down ? button_down_background : button_up_background, x, y, null);
            g.drawImage(label, x, y, null);
        }

        protected void paintComponent(Graphics g) {

            // PageControl

            int x1, x2;
            int y1, y2;
            Graphics2D g2 = (Graphics2D) g;

            super.paintComponent(g);
            setCursor(our_cursor);

            g.drawImage(doccontrol_center, 0, 0, getWidth(), getHeight(), null);
            g.drawImage(doccontrol_top, 0, 0, null);
            g.drawImage(doccontrol_bottom, 0, getHeight() - 6, null);

            // only draw the bookmarks if you have multiple pages
            if (page_count > 1) {
                for (int i = 0;  i < bookmarks.length;  i++)
                    bookmarks[i].paint (this, (Graphics2D) g);
            }

            if (font_height == 0) {
                font_height = g.getFontMetrics().getMaxAscent();
            }
            String pagenumber_text = getPageNumberString(min(current_page_index + (two_page ? 1 : 0), (page_count - 1)));
            Rectangle2D bounds = g.getFontMetrics(g.getFont()).getStringBounds(pagenumber_text, g);
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g.setColor(DARK_COLOR);
            g.drawString(pagenumber_text,
                         min(3, (int) Math.round((getWidth() - bounds.getWidth())/2)), font_height + 1);
            if (current_page_index < (page_count - (two_page ? 2 : 1)))
                paintButton(g, next_arrow, next_rect.x, next_rect.y, (clickedRect == next_rect) && mouse_in_clickedRect);
              // g.drawImage(next_arrow, next_rect.x, next_rect.y, null);
            if (current_page_index > 0)
                paintButton(g, back_arrow, back_rect.x, back_rect.y, (clickedRect == back_rect) && mouse_in_clickedRect);
              // g.drawImage(back_arrow, back_rect.x, back_rect.y, null);
            if (logo_url != null)
                paintButton(g, small_uplib_logo, logo_rect.x, logo_rect.y, (clickedRect == logo_rect) && mouse_in_clickedRect);
              // g.drawImage(small_uplib_logo, logo_rect.x, logo_rect.y, null);
            if (activity_logger != null) {
                if (activities_on)
                    paintButton(g, eyeball_image, eyeball_rect.x, eyeball_rect.y, !((clickedRect == eyeball_rect) && mouse_in_clickedRect));
                else
                    paintButton(g, grayed_eyeball_image, eyeball_rect.x, eyeball_rect.y, (clickedRect == eyeball_rect) && mouse_in_clickedRect);
                /*
                Ellipse2D ed = new Ellipse2D.Double(eyeball_rect.x, eyeball_rect.y, eyeball_rect.width, eyeball_rect.height);
                g.setColor(WHITE);
                g2.fill(ed);
                if (activities_on) {
                    g.drawImage(eyeball_image, eyeball_rect.x, eyeball_rect.y, null);
                }
                else {
                    g.drawImage(grayed_eyeball_image, eyeball_rect.x, eyeball_rect.y, null);
                }
                g.setColor(LEGEND_COLOR);
                g2.draw(ed);
                */
            }

            // now draw the ink pots
            for (Iterator i = widget_inkpots.getIterator();  i.hasNext();) {
                Inkpots.Pot inkp = (Inkpots.Pot) i.next();
                inkp.draw((Graphics2D) g, selection.isVisible());
            }
            // and the note page adder
            if (widget_inkpots.isVisible() ||
                (selection.isVisible() && selection.isActive() && (selection.getBoxes() == null))) {
                paintButton(g, postit_image, note_rect.x, note_rect.y, ((clickedRect == note_rect) && mouse_in_clickedRect));
            }

            if (page_count > 1)
                paintButton (g, thumbnails_image, thumbnails_rect.x, thumbnails_rect.y, thumbnails_showing || ((clickedRect == thumbnails_rect) && mouse_in_clickedRect));

            if ((page_image_scaling != java.lang.Double.NaN) && (hires_page_image_loader != null)
                && selection.isActive() && selection.isVisible()) {
                paintButton (g, zoom_in_image, zoom_in_rect.x, zoom_in_rect.y,
                             zoom_in_showing || ((clickedRect == zoom_in_rect) && mouse_in_clickedRect));
            }

            if (pagetext_loader != null) {
                paintButton (g, search_icon_image, search_rect.x, search_rect.y, (clickedRect == search_rect) && mouse_in_clickedRect);
                if (search_state != null)
                  g.drawImage(search_again_label, search_rect.x, search_rect.y, null);
            }

            if (snapback_page >= 0) {
                paintButton(g, (snapback_page < current_page_index) ? snapback_left_image : snapback_right_image,
                            snapback_rect.x, snapback_rect.y, (clickedRect == snapback_rect) && mouse_in_clickedRect);
                /*
                Ellipse2D.Double dh = new Ellipse2D.Double(snapback_rect.x, snapback_rect.y,
                                                           snapback_rect.width, snapback_rect.height);
                BufferedImage img = (snapback_page < current_page_index) ? snapback_left_image : snapback_right_image;
                g2.setColor(WHITE);
                g2.fill(dh);
                g.drawImage(img, snapback_rect.x+1, snapback_rect.y+1, null);
                g2.setColor(DARK_COLOR);
                g2.draw(dh);
                */
            }

            if (hotspotsRelevant()) {
                paintButton(g, hotspots_image, hotspots_rect.x, hotspots_rect.y, topl.showHotspots() || ((clickedRect == hotspots_rect) && mouse_in_clickedRect));
                /*
                Ellipse2D.Double dh = new Ellipse2D.Double(hotspots_rect.x, hotspots_rect.y,
                                                          hotspots_rect.width, hotspots_rect.height);
                if (topl.showHotspots()) {
                    g2.setColor(UPLIB_ORANGE);
                    g2.fill(dh);
                    g.drawImage(hotspots_image, hotspots_rect.x, hotspots_rect.y, null);
                    g2.setColor(DARK_COLOR);
                    g2.draw(dh);
                } else {
                    g2.setColor(WHITE);
                    g2.fill(dh);
                    g.drawImage(hotspots_image, hotspots_rect.x, hotspots_rect.y, null);
                    g2.setColor(LEGEND_COLOR);
                    g2.draw(dh);
                }
                */
            }
            if (!topl.focusOnOurApp()) {
                g.setColor(HALF_WHITE);
                g.fillRect(0, 0, getWidth(), getHeight());
            };
        }

        public void mouseClicked(MouseEvent e) {
            if (!topl.focusOnOurApp())
                topl.requestFocusInWindow();
        }

        public void processMouseClick (MouseEvent e) {
            Point p = e.getPoint();
            int button = e.getButton();
            if (!topl.focusOnOurApp())
                topl.requestFocusInWindow();
            if ((logo_url != null) && logo_rect.contains(p)) {
                logo_url.call(null);
            } else if (back_rect.contains(p)) {
                if (button == MouseEvent.BUTTON3)
                    topl.nextPage();
                else if (button == MouseEvent.BUTTON1)
                    topl.prevPage();
            } else if (next_rect.contains(p)) {
                if (button == MouseEvent.BUTTON3)
                    topl.prevPage();
                else if (button == MouseEvent.BUTTON1)
                    topl.nextPage();
            } else if (hotspotsRelevant() && hotspots_rect.contains(p)) {
                if (topl.showHotspots()) {
                    topl.setShowHotspots(false);
                    topl.repaintPageview();
                } else {
                    topl.setShowHotspots(true);
                    topl.repaintPageview();
                }
            } else if ((snapback_page >= 0) && snapback_rect.contains(p)) {
                topl.setPage(snapback_page);
            } else if (thumbnails_rect.contains(p)) {
                if (thumbnails_showing)
                    topl.hideThumbnails();
                else
                    topl.showThumbnails();
            } else if ((hires_page_image_loader != null) && zoom_in_rect.contains(p)
                       && selection.isVisible() && selection.isActive()) {
                if (zoom_in_showing)
                    topl.hideZoomIn();
                else
                    topl.showZoomIn(selection.getImageRect());
            } else if (search_rect.contains(p)) {
                if (search_state == null)
                    search_state = createSearchState();
                else if (button == MouseEvent.BUTTON1)
                    search_state.extendSearch(CONTROL_S);
                else if (button == MouseEvent.BUTTON3) {
                    if (search_state.hasMatch())
                        setSelection ((PageText) pagetext_loader.get(document_id, search_state.getPage(), 0, null),
                                      search_state.getPos(), search_state.getPos() + search_state.getLength());
                    search_state = null;
                }
                repaintPageview();
            } else if ((activity_logger != null) && eyeball_rect.contains(p)) {
                activities_on = ! activities_on;
                repaint(0L, eyeball_rect.x, eyeball_rect.y, eyeball_rect.width, eyeball_rect.height);
            } else if (white_ink_pot.contains(p)) {

                // there are three states here.
                // 1.  Pots not visible --> make pots visible
                // 2.  Pots visible, no pot selected --> make pots invisible
                // 3.  Pots visible, some pot selected --> deselect that pot

                boolean was_visible = widget_inkpots.isVisible();
                Inkpots.Pot selected = widget_inkpots.getSelected();

                System.err.println("was_visible is " + was_visible + ", modifiers are " + e.getModifiersEx() + ", annotation_span_controls visibility is " + annotation_span_controls.isVisible());
                if (was_visible && ((e.getModifiersEx() & InputEvent.CTRL_DOWN_MASK) != 0)) {
                    if (!annotation_span_controls.isVisible())
                      topl.showAnnotationTimespanControls();
                    else
                      topl.hideAnnotationTimespanControls();
                    return;
                }

                if (!was_visible)
                    widget_inkpots.setVisible(true);
                else if (selected == white_ink_pot)
                    widget_inkpots.setVisible(false);
                else {
                    Rectangle r = selected.getRect();
                    repaint (0L, 0, r.y - 4, getWidth(), r.y + r.height + 4);
                    white_ink_pot.select();
                    r = white_ink_pot.getRect();
                    repaint (0L, 0, r.y - 4, getWidth(), r.y + r.height + 4);
                }

                topl.setShowScribbles(widget_inkpots.isVisible());
                topl.setPageviewCursor(null);
                if (widget_inkpots.isVisible() != was_visible) {
                    if (topl.hasAnnotations(current_page_index) ||
                        (two_page && topl.hasAnnotations(current_page_index + 1)))
                        topl.repaintPageview();
                    else
                        repaint(0L, 0, 0, getWidth(), getHeight());
                }

            } else if (note_rect.contains(p) &&
                       (widget_inkpots.isVisible() || (selection.isVisible() &&
                                                       selection.isActive() &&
                                                       (selection.getBoxes() == null)))) {

                Pageview pv = ((!two_page) || (current_page_index == topl.left_pageview.page_offset)) ? topl.left_pageview : topl.right_pageview;
                if (selection.isActive() && selection.isVisible() && (selection.getBoxes() == null)) {
                    // rectangle selected
                    Rectangle r = selection.getImageRect();
                    selection.clear();
                    pv.newNoteSheet(r.x, r.y, r.width, r.height);
                    widget_inkpots.setVisible(true);
                    topl.setShowScribbles(true);
                    this.repaint();
                } else {
                    pv.newNoteSheet();
                }
                pv.repaint();
                    
            } else if (widget_inkpots.isVisible()) {

                Inkpots.Pot i = widget_inkpots.inVisiblePot(p);
                if (i != null) {

                    // We're in a non-white inkpot.
                    //
                    // There are two cases here:
                    // 1.  selection active --> convert selection to scribble in this inkpot, clear selection
                    // 2.  selection clear --> select this inkpot

                    if (selection.isActive()) {

                        java.util.List boxes = selection.getBoxes();
                        if ((boxes != null) && (boxes.size() > 0)) {
                            int page = ((PageText.WordBox)(boxes.get(0))).getPageText().getPageIndex();
                            Iterator it = boxes.iterator();
                            Rectangle linebox = null;
                            Point[] points = new Point[2];
                            while (it.hasNext()) {
                                PageText.WordBox b = (PageText.WordBox) it.next();
                                if (linebox == null)
                                    linebox = b.getBounds();
                                else
                                    linebox.add(b);
                                if (b.endOfLine() || (!it.hasNext())) {
                                    float thickness = i.getSize();
                                    float size = (float) min(linebox.width, linebox.height);
                                    boolean vertical = linebox.height > linebox.width;
                                    Point start, end;
                                    if (thickness < 2.5f) {
                                        // underline
                                        start = new Point(linebox.x, linebox.y + linebox.height);
                                        end = new Point(linebox.x + linebox.width, linebox.y + linebox.height);
                                    } else if (linebox.height > linebox.width) {
                                        // vertical highlight
                                        start = new Point(linebox.x + linebox.width/2, linebox.y + linebox.width/4);
                                        end = new Point(linebox.x + linebox.width/2, linebox.y + (linebox.height - linebox.width/4));
                                    } else {
                                        // horizontal highlight
                                        start = new Point(linebox.x + linebox.height/4, linebox.y + linebox.height/2);
                                        end = new Point(linebox.x + (linebox.width - linebox.height/4), linebox.y + linebox.height/2);
                                    }
                                    points[0] = start;
                                    points[1] = end;
                                    Scribble s = new Scribble(document_id, page, i.getColor(),
                                                              (thickness < 2.5f) ? 1.0f : size, points,
                                                              new Annotation.Timestamp(Annotation.Timestamp.CREATED));
                                    ((ArrayList) strokes.get(page)).add(s);

                                    if (scribble_handler != null) {
                                        final Scribble saved = s;
                                        try {
                                            scribble_handler.addAnnotation(saved, document_id, current_page_index, 0);
                                        } catch (IOException x) {
                                            x.printStackTrace(System.err);
                                        }
                                    }

                                    linebox = null;
                                }
                            }
                            if ((activity_logger != null) && activities_on) {
                                activity_logger.call(new Activity(document_id, page, Activity.AC_SCRIBBLED));
                            }
                            if (selection.isVisible())
                                topl.repaintPageview();
                        }

                        selection.clear();

                    } else {

                        // no selection, so instead, make this the current inkpot
                        
                        Inkpots.Pot selected = widget_inkpots.getSelected();
                        if (i != selected) {
                            Rectangle r = selected.getRect();
                            repaint (0L, 0, r.y - 4, getWidth(), r.y + r.height + 4);
                            i.select();
                            r = i.getRect();
                            repaint (0L, 0, r.y - 4, getWidth(), r.y + r.height + 4);
                            r = white_ink_pot.getRect();
                            repaint (0L, 0, r.y - 4, getWidth(), r.y + r.height + 4);
                            if ((activity_logger != null) && activities_on) {
                                activity_logger.call(new Activity(document_id, current_page_index,
                                                                  Activity.AC_INK_SELECTED, i.getInkBytes()));
                            }
                        }
                        Cursor c = widget_inkpots.getSelected().getDrawingCursor();
                        topl.setPageviewCursor(c);
                    }
                }
            }
        }

        public void mousePressed(MouseEvent e) {

            if (clickedButton > 0)
                // already a mouse-button down
                return;

            Point p = e.getPoint();

            clickedRect = null;
            clickedButton = e.getButton();
            splash_page_period = 0;
            if ((logo_url != null) && logo_rect.contains(p)) {
                clickedRect = logo_rect;
            } else if (back_rect.contains(p)) {
                clickedRect = back_rect;
            } else if (next_rect.contains(p)) {
                clickedRect = next_rect;
            } else if (hotspots_rect.contains(p)) {
                clickedRect = hotspots_rect;
            } else if (snapback_rect.contains(p)) {
                clickedRect = snapback_rect;
            } else if (thumbnails_rect.contains(p)) {
                clickedRect = thumbnails_rect;
            } else if ((hires_page_image_loader != null) && zoom_in_rect.contains(p) && (page_image_scaling != java.lang.Double.NaN)) {
                clickedRect = zoom_in_rect;
            } else if (note_rect.contains(p) && (widget_inkpots.isVisible() ||
                                                 (selection.isVisible() &&
                                                  selection.isActive() &&
                                                  selection.getBoxes() == null))) {
                clickedRect = note_rect;
            } else if ((pagetext_loader != null) && search_rect.contains(p)) {
                clickedRect = search_rect;
            } else if ((activity_logger != null) && eyeball_rect.contains(p)) {
                clickedRect = eyeball_rect;
            } else {
                Inkpots.Pot i = widget_inkpots.inVisiblePot(p);
                if (i != null)
                    clickedRect = i.getRect();
            }
            for (int i = 0;  i < bookmarks.length;  i++) {
                if (bookmarks[i].contains(this, p.x, p.y)) {
                    dragging_bookmark = p;
                    bookmark_being_dragged = bookmarks[i];
                    bookmark_dragging_initial_spot = p;
                }
            }

            if (clickedRect != null) {
                mouse_in_clickedRect = true;
                repaint(clickedRect);
            }

            if (!topl.focusOnOurApp())
                topl.requestFocusInWindow();
        }

        public void mouseMoved (MouseEvent e) {
        }

        public void mouseDragged (MouseEvent e) {
            Point p = e.getPoint();
            // System.err.println("mouse dragged to " + p.x + "," + p.y);
            if (dragging_bookmark != null) {
                bookmark_being_dragged.changeHeight(p.y - dragging_bookmark.y);
                dragging_bookmark = p;
                // System.err.println("ignoreRepaint is " + topl.getIgnoreRepaint());
                topl.repaint();
            }
            boolean old_mouse_in_clickedRect = mouse_in_clickedRect;
            boolean mouse_in_clickedRect = (clickedRect != null) && (clickedRect.contains(p));
            if (mouse_in_clickedRect != old_mouse_in_clickedRect)
                repaint(clickedRect);
        }

        private void processBookmark (Bookmark the_bookmark, Point p, Point initial_spot, int button) {
            int page = the_bookmark.getPage();
            if ((button != MouseEvent.BUTTON3) && (page <= page_count)) {
                if (page == current_page_index) {
                    if ((dragging_bookmark == null) || (bookmark_dragging_initial_spot.distance(p) < 10.0))
                        the_bookmark.setPage(page_count + 1);
                } else {
                    the_bookmark.gotoPage();
                }
            } else {
                the_bookmark.setPage(current_page_index);
            }
            topl.repaintPageview();
        }

        public void mouseReleased(MouseEvent e) {

            if (e.getButton() != clickedButton)
                return;

            Point p = e.getPoint();
            if (clickedRect != null) {
                if (clickedRect.contains(p))
                  processMouseClick(e);
                Rectangle old_rect = clickedRect;
                clickedRect = null;
                mouse_in_clickedRect = false;
                repaint(old_rect);
            }
            if (dragging_bookmark != null)
                bookmark_being_dragged.changeHeight(p.y - dragging_bookmark.y);
            if ((bookmark_being_dragged != null) &&
                (bookmark_being_dragged.contains(this, p.x, p.y))) {
                processBookmark(bookmark_being_dragged, p, bookmark_dragging_initial_spot, e.getButton());
            }
            dragging_bookmark = null;
            bookmark_dragging_initial_spot = null;
            clickedButton = 0;
        }
        
        public void mouseEntered(MouseEvent e) {
            // System.err.println("Mouse event " + e);
            setToolTipText("page controls");
        }

        public void mouseExited(MouseEvent e) {
        }

        public void mouseWheelMoved (MouseWheelEvent e) {
            // System.err.println("Controls mouse wheel event " + e);
            int rotation = e.getWheelRotation();
            Point p = e.getPoint();
            Inkpots.Pot i = widget_inkpots.inVisiblePot(p);
            if (i != null) {
                i.resize(rotation);
                repaint(i.getRect());
                if (!topl.focusOnOurApp())
                    topl.requestFocusInWindow();
            } else {
                topl.setPage(max(0, min(current_page_index + rotation, (page_count - (two_page ? 2 : 1)))));
                System.err.println("PageControl mouseWheelMoved event");
                if (!topl.isFocusOwner())
                    topl.requestFocusInWindow();
            }
        }

        // DragGestureListener methods

        public void dragGestureRecognized (DragGestureEvent e) {
            Point p = e.getDragOrigin();
            if (p.y < font_height) {
                System.err.println("dragGestureRecognized:  " + e);
                Point drag_point = new Point(p.x, p.y);
                int startpos = -1;
                int endpos = -1;
                String text = null;
                if (pagetext_loader != null) {
                    PageText pt = (PageText) pagetext_loader.get(document_id, current_page_index, 0, null);
                    if (pt != null) {
                        text = pt.getText();
                    }
                }
                BufferedImage di = null;
                if (DragSource.isDragImageSupported() && (thumbnail_image_loader != null))
                    di = (BufferedImage) thumbnail_image_loader.get(document_id, current_page_index, 1, null);
                DraggedSelection s = new DraggedSelection(theRepositoryURL, document_id,
                                                          current_page_index, getPageNumberString(current_page_index),
                                                          -1, -1, text, document_properties, true, getLinkImage(current_page_index));
                current_drag_source = true;
                ((DVTransferHandler)(this.getTransferHandler())).setTransferData(s, di);
                this.dragSource.startDrag(e, DragSource.DefaultCopyNoDrop, di, drag_point, s, this);
                topl.repaintPageview();
            }
        }

        // DragSourceListener methods

        public void dragDropEnd (DragSourceDropEvent e) {
            if (current_drag_source) {
                ((DVTransferHandler)(this.getTransferHandler())).setTransferData(null, null);
                current_drag_source = false;
                topl.repaintPageview();
            }
        }

        public void dragEnter (DragSourceDragEvent e) {
            /*
            System.err.println("dragEnter(" + e + ") on " + topl);
            System.err.println("getSource is " + e.getSource());
            System.err.println("context.getComponent() is " + e.getDragSourceContext().getComponent());
            */
            int action = e.getDropAction();
            // System.err.println("dragEnter action is " + action);
            if (current_drag_source) {
                e.getDragSourceContext().setCursor(DragSource.DefaultCopyNoDrop);
            } else if (((action & DnDConstants.ACTION_LINK) == DnDConstants.ACTION_LINK) &&
                ((action & DnDConstants.ACTION_REFERENCE) == DnDConstants.ACTION_REFERENCE)) {
                e.getDragSourceContext().setCursor(DragSource.DefaultLinkDrop);
            } else if ((action & DnDConstants.ACTION_COPY) == DnDConstants.ACTION_COPY) {
                e.getDragSourceContext().setCursor(DragSource.DefaultCopyDrop);
            } else {
                e.getDragSourceContext().setCursor(DragSource.DefaultCopyNoDrop);
            }
        }

        public void dragOver (DragSourceDragEvent e) {
        }

        public void dropActionChanged (DragSourceDragEvent e) {
            int action = e.getDropAction();
            // System.err.println("dropActionChanged action is " + action);
            if (current_drag_source) {
                e.getDragSourceContext().setCursor(DragSource.DefaultCopyNoDrop);
            } else if (((action & DnDConstants.ACTION_LINK) == DnDConstants.ACTION_LINK) &&
                ((action & DnDConstants.ACTION_REFERENCE) == DnDConstants.ACTION_REFERENCE)) {
                e.getDragSourceContext().setCursor(DragSource.DefaultLinkDrop);
            } else if ((action & DnDConstants.ACTION_COPY) == DnDConstants.ACTION_COPY) {
                e.getDragSourceContext().setCursor(DragSource.DefaultCopyDrop);
            } else {
                e.getDragSourceContext().setCursor(DragSource.DefaultCopyNoDrop);
            }
        }

        public void dragExit (DragSourceEvent e) {
            e.getDragSourceContext().setCursor(DragSource.DefaultCopyNoDrop);
        }

    }

    public class DocThumbnails extends JPanel
        implements Scrollable, MouseListener {

        final int SPACING = 5;

        public DocViewer topl;
        int last_page = -1;
        int last_width;
        int columns = 1;
        
        public DocThumbnails (DocViewer toplevel) {
            super();
            topl = toplevel;
            setBackground(BACKGROUND_COLOR);
            long square_size = Math.round(Math.ceil(Math.sqrt((double)page_count)));
            // setPreferredSize(figureNeededSize((thumbnail_width + 2) * (int) square_size));
            setMinimumSize(new Dimension(thumbnail_width, thumbnail_height));
            last_width = getWidth();
            columns = max(last_width / (thumbnail_width + SPACING), 1);
            addMouseListener(this);
        }

        public Dimension getPreferredScrollableViewportSize() {
            return getPreferredSize();
        }

        public int getScrollableUnitIncrement (Rectangle f, int orientation, int direction) {
            return (SPACING + ((orientation == SwingConstants.VERTICAL) ? thumbnail_height : thumbnail_width));
        }
            
        public int getScrollableBlockIncrement (Rectangle f, int orientation, int direction) {
            if (orientation == SwingConstants.VERTICAL) {
                if (direction < 0)
                    return min(f.y, f.height);
                else {
                    int max_height = ((page_count / columns) + 1) * (thumbnail_height + SPACING) + 1;
                    return min((max_height - (f.y + f.height)), f.height);
                }
            } else {
                return 0;
            }
        }
            
        public boolean getScrollableTracksViewportWidth() {
            return true;
        }

        public boolean getScrollableTracksViewportHeight() {
            return false;
        }

        private Dimension figureNeededSize (int new_width) {
            int components_per_line = max(1, (new_width - (SPACING - 1)) / (thumbnail_width + SPACING));
            int lines_needed = (page_count + (components_per_line - 1))/ components_per_line;
            // System.err.println("DocThumbnails: refigured " + components_per_line + " x " + lines_needed + " => " + new_width + "," + ((lines_needed * (thumbnail_height + 4)) + 2));
            columns = components_per_line;
            return new Dimension(new_width, (lines_needed * (thumbnail_height + SPACING)) + SPACING);
        }

        public void setBounds (int x, int y, int width, int height) {
            super.setBounds(x, y, width, height);
            // System.err.println("DocThumbnails.setBounds(" + width + ", " + height + ") called");
            if ((width < 1) || (height < 1))
                return;
            if (width != last_width) {
                Dimension d = figureNeededSize(width);
                if (height != d.height) {
                    setPreferredSize(d);
                    invalidate();
                }
            }
            last_width = width;
        }

        private void paintThumbnail (Graphics g, int page_no, int x, int y, int width, int height) {

            BufferedImage img;
            boolean selected_page = ((current_page_index == page_no) ||
                                     (two_page && ((current_page_index + 1) == page_no)));

            img = (BufferedImage) thumbnail_image_loader.get(document_id, page_no, 1, null);
            if (img == null) {
                img = (BufferedImage) thumbnail_image_loader.get(document_id, page_no, 1, new PageImageSetter(page_no, this));
            }
            if (img != null) {
                g.drawImage(img.getScaledInstance(width-2,height-2,Image.SCALE_SMOOTH), x + 1, y + 1, null);
            } else {
                g.setColor(selected_page ? UPLIB_ORANGE : LEGEND_COLOR);
                String s = "loading...";
                int h = g.getFontMetrics().getMaxAscent();
                String pno = getPageNumberString(page_no);
                g.drawString(pno, x + 6, y + h + 6);
                int w = g.getFontMetrics().stringWidth(s);
                g.drawString(s, (width - w)/2, (height - h)/2 + h);
            }
            if (selected_page) {
                g.setColor(UPLIB_ORANGE_WASH);
                g.fillRect(x + 1, y + 1, width - 2, height - 2);
            }
            g.setColor(selected_page ? UPLIB_ORANGE : LEGEND_COLOR);
            g.drawRect(x, y, width - 1, height - 1);
            /* 
            if (topl.showScribbles() && (big_to_small_transform != null)) {
                System.err.println("page " + page_no + ":  showing notes on thumbnails");
                // big-thumbnail -> small-thumbnail point translation:
                //   x = (x/big-thumbnail-scaling + big_thumbnail_translation.x) * small_thumbnail_scaling
                //   y = (y/big-thumbnail-scaling + big_thumbnail_translation.y) * small_thumbnail_scaling
                ArrayList notes = (ArrayList) note_sheets.get(page_no);
                System.err.println("       " + notes.size() + " notes");
                int x, y, width, height;
                for (int j = 0;  j < notes.size();  j++) {
                    NoteFrame nf = (NoteFrame) notes.get(j);
                    Point2D location = big_to_small_transform.transform(new Point(nf.x, nf.y), null);
                    Point2D size = big_to_small_transform.transform(new Point(nf.width, nf.height), null);
                    System.err.println("       " + nf.width + "x" + nf.height + "+" + nf.x + "+" + nf.y + " --> " +
                                       (int) Math.round(size.getX()) + "x" + (int) Math.round(size.getY()) + "+" +
                                       (int) Math.round(location.getX()) + "+" + (int) Math.round(location.getY()));
                    g.setColor(nf.background);
                    g.fillRect((int) Math.round(location.getX()), (int) Math.round(location.getY()),
                               (int) Math.round(size.getX()), (int) Math.round(size.getY()));
                    g.setColor(LEGEND_COLOR);
                    g.drawRect((int) Math.round(location.getX()), (int) Math.round(location.getY()),
                               (int) Math.round(size.getX() - 1), (int) Math.round(size.getY() - 1));
                }
            }
            */
            for (int i = 0;  i < bookmarks.length;  i++) {
                if (bookmarks[i].getPage() == page_no) {
                    bookmarks[i].paint(this, (Graphics2D) g);
                }
            }
        }

        private void repaintThumbnail (int page_no) {
            Rectangle r = new Rectangle();
            figurePageRect (page_no, r);
            if (thumbnails_viewport.getViewRect().contains(r))
                repaint(r);
        }

        private void figurePageRect (int page_index, Rectangle r) {
            r.x = SPACING + ((page_index % columns) * (SPACING + thumbnail_width)) - 1;
            r.y = SPACING + ((page_index / columns) * (SPACING + thumbnail_height)) - 1;
            r.width = thumbnail_width + 2;
            r.height = thumbnail_height + 2;            
        }

        protected void paintComponent(Graphics g) {
            super.paintComponent(g);

            if (last_page < 0) {
                changePage(current_page_index);
                return;
            }

            Rectangle clipshape = g.getClip().getBounds().getBounds();
            // System.err.println("clipshape is " + clipshape + ", thumbnail_width is " + thumbnail_width + ", thumbnail_height is " + thumbnail_height);
            int page_index;
            Rectangle r = new Rectangle();

            int first_row = clipshape.y / (thumbnail_height + SPACING);
            int last_row = (clipshape.y + clipshape.height + (thumbnail_height + SPACING)) / (thumbnail_height + SPACING);

            // System.err.println("first_row is " + first_row + ", last_row is " + last_row);

            for (page_index = (first_row * columns);
                 (page_index < ((last_row + 1) * columns)) && (page_index < page_count);
                 page_index++) {

                figurePageRect (page_index, r);
                paintThumbnail (g, page_index, r.x, r.y, r.width, r.height);
                // System.err.println("paintThumbnail(g, " + page_index + ", " + x + ", " + y + ", " + thumbnail_width + ", " + thumbnail_height + ");");
            }
        }

        private int figurePage (Point p) {

            int row = (p.y - 1) / (thumbnail_height + SPACING);
            if ((row * columns) > page_count)
                return -1;      // off-thumbnail at bottom
            int height = p.y - (row * (thumbnail_height + SPACING));
            if ((height > 0) && (height < (SPACING - 1)))
                return -1;      // in the inter-thumbnail spacing

            int col = (p.x - 1) / (thumbnail_width + SPACING);
            if (col >= columns)
                return -1;      // off-thumbnail at right
            int width = p.x - (col * (thumbnail_width + SPACING));
            if ((width > 0) && (width < (SPACING - 1)))
                return -1;      // in the inter-thumbnail spacing

            int page = (row * columns) + col;
            return ((page > page_count) ? -1 : page);
        }

        public void changePage (int new_page) {
            if (new_page != last_page) {
                if (isVisible()) {
                    // need to repaint last_page?
                    if (two_page) {
                        int next_page = new_page + 1;
                        if (last_page != next_page) {
                            if (last_page >= 0)
                                repaintThumbnail(last_page);
                            repaintThumbnail(next_page);
                        }
                        if (new_page != (last_page + 1)) {
                            repaintThumbnail(new_page);
                            if (last_page >= 0)
                                repaintThumbnail(last_page + 1);
                        }
                    } else {
                        if (last_page >= 0)
                            repaintThumbnail(last_page);
                        repaintThumbnail(new_page);
                    }
                }
                last_page = new_page;
                Rectangle r = new Rectangle();
                figurePageRect(new_page, r);
                scrollRectToVisible(r);
            }
        }

        public void mouseClicked(MouseEvent e) {
            // System.err.println("DocThumbnail mouse event " + e + "; getClickCount() = " + e.getClickCount());
            int page_no = figurePage(e.getPoint());
            System.err.println("page is " + page_no);
            if ((page_no >= 0) && (page_no != current_page_index)) {
                topl.setPage(((page_no < (page_count - 1)) || !two_page) ? page_no : page_no - 1);
            } else if (e.getClickCount() > 1) {
                topl.hideThumbnails();
            }
        }

        public void mousePressed(MouseEvent e) {
            // System.err.println("Mouse event " + e);
        }

        public void mouseReleased(MouseEvent e) {
            // System.err.println("Mouse event " + e);
        }
        
        public void mouseEntered(MouseEvent e) {
        }

        public void mouseExited(MouseEvent e) {
            // System.err.println("Mouse event " + e);
        }
    }

    public class Bookmark {

        private DocViewer topl;
        private int page_no;
        private int where;
        private int width, height;
        private TexturePaint paint;
        private int my_idx;

        private int font_height = 0;

        public Bookmark (DocViewer toplevel, int index_no, BufferedImage image, int initial_page, int initial_height) {
            topl = toplevel;
            page_no = initial_page;
            where = initial_height;
            height = image.getHeight(null);
            width = image.getWidth(null);
            paint = new TexturePaint(image, new Rectangle(0, 0, width, height));
            my_idx = index_no;
        }

        public ImageIcon makeIcon (int width, int height, boolean selected) {
            BufferedImage iconimage = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
            Rectangle r = new Rectangle(0, 0, width, height);
            Graphics2D g = iconimage.createGraphics();
            g.setColor(WHITE);
            g.fillRect(0, 0, width, height);
            g.setPaint(paint);
            g.fill(r);
            if (! selected) {
                g.setColor(TRANSPARENT_TOOLS_COLOR);
                g.fillRect(0, 0, width, height);
            }
            return new ImageIcon(iconimage);
        }

        public void gotoPage () {
            int old_page = current_page_index;
            topl.setPage(page_no);
            snapback_page = old_page;
            if ((activity_logger != null) && activities_on) {
                activity_logger.call(new Activity(document_id, page_no, Activity.AC_BOOKMARK_USED,
                                                  new byte[] { (byte) my_idx }));
            }
        }

        public int index() {
            return my_idx;
        }

        public void setPage (int page) {
            page_no = page;
            if ((activity_logger != null) && activities_on) {
                int h = min(65535, (int) (((float) where)/((float)page_height) * 65536));
                activity_logger.call(new Activity(document_id, current_page_index,
                                                  (page > page_count) ? Activity.AC_BOOKMARK_UNSET : Activity.AC_BOOKMARK_SET,
                                                  new byte[] { (byte) my_idx, (byte) ((h & 0xFF00) >> 8), (byte) (h & 0xFF) }));

            }
        }

        public void setHeight (int h) {
            where = h;
        }

        public void changeHeight (int delta) {
            setHeight(max(0, min(where + delta, topl.getHeight() - height)));
        }

        public int getHeight () {
            return where;
        }

        public int getPage () {
            return page_no;
        }

        public boolean contains (JPanel p, int x, int y) {
            Point offset = new Point(0, 0);
            for (Container c = p;  c != topl;  c = c.getParent()) {
                Point loc = c.getLocation();
                offset.x += loc.x;
                offset.y += loc.y;
            }
            if (p instanceof Pageview) {
                if (!((current_page_index == page_no) ||
                      (two_page && ((current_page_index - 1) == page_no))))
                    return false;
                return ((y > (where - offset.y)) && (y <= ((where - offset.y) + height)));
            } else if (p instanceof PageControl) {
                return ((y > (where - offset.y)) && (y <= ((where - offset.y) + height)));
            }
            return false;
        }

        public boolean isSet () {
            return (page_no < page_count);
        }

        public void paint (JPanel p, Graphics2D g) {

            Point offset = new Point(0, 0);
            for (Container x = p;  x != topl;  x = x.getParent()) {
                Point loc = x.getLocation();
                offset.x += loc.x;
                offset.y += loc.y;
            }
            if (p instanceof Pageview) {
                if (!((current_page_index == page_no) ||
                      (two_page && ((current_page_index - 1) == page_no))))
                    return;
                g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_OFF);
                g.setPaint(paint);
                g.fill(new Rectangle(0, (where - offset.y), p.getWidth(), height));

            } else if (p instanceof PageControl) {
                g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_OFF);
                boolean is_set = (page_no < page_count);
                int pcw = p.getWidth();
                int w = min(pcw, height/2);
                int fillwidth = (pcw - w);
                g.drawImage(bookmark_drop_shadow, 0, (where - offset.y), null);
                g.setColor(WHITE);
                if (fillwidth > 0)
                    g.fillRect(0, (where - offset.y), fillwidth - 1, height);
                g.fillArc(fillwidth - (w + 1), (where - offset.y), 2 * w, height - 1, 90, -180);
                g.setPaint(paint);
                if (fillwidth > 0)
                    g.fillRect(0, (where - offset.y), fillwidth - 1, height);
                g.fillArc(fillwidth - (w + 1), (where - offset.y), 2 * w, height - 1, 90, -180);
                if (is_set) {
                    if (font_height == 0) {
                        font_height = g.getFontMetrics().getMaxAscent();
                    }
                    g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
                    g.setColor(WHITE);
                    g.drawString(getPageNumberString(page_no), 3, (where - offset.y) + (height + font_height)/2);
                } else {
                    g.setColor(TRANSPARENT_TOOLS_COLOR);
                    if (fillwidth > 0)
                        g.fillRect(0, (where - offset.y), fillwidth - 1, height);
                    g.fillArc(fillwidth - (w + 1), (where - offset.y), 2 * w, height - 1, 90, -180);
                }
            } else if (p instanceof DocThumbnails) {
                Rectangle r = new Rectangle();
                ((DocThumbnails)p).figurePageRect(page_no, r);
                int h = max(3, ((r.height - 2) * height) / page_height);
                int y = (((r.height - 2) * where) / page_height) + (r.y + 1);
                g.setColor(WHITE);
                g.fillRect(r.x + 1, y, r.width - 2, h);                
                g.setPaint(paint);
                g.fillRect(r.x + 1, y, r.width - 2, h);                
            }
        }
    }

    public void showAnnotationTimespanControls () {
        annotation_span_controls.setVisible(true);
        repaintPageview();
    }

    public void hideAnnotationTimespanControls () {
        annotation_span_controls.setVisible(false);
        repaintPageview();
    }

    public void showZoomIn (Rectangle r) {
        zoomed_viewer.fetch_page(current_page_index);
        zoomed_viewer.setRect(r);
        ((CardLayout)views_flipper.getLayout()).show(views_flipper, "zoom-in");
        zoom_in_showing = true;
        repaintPageview();
        if ((activity_logger != null) && activities_on) {
            activity_logger.call(new Activity(document_id, current_page_index, Activity.AC_ZOOMED_IN));
        }
    }

    public void hideZoomIn () {
        ((CardLayout)views_flipper.getLayout()).show(views_flipper, "pages");
        zoom_in_showing = false;
        zoomed_viewer.clear();
        repaintPageview();
        if ((activity_logger != null) && activities_on) {
            activity_logger.call(new Activity(document_id, current_page_index, Activity.AC_ZOOMED_OUT));
        }
    }

    public void showThumbnails () {
        ((CardLayout)views_flipper.getLayout()).show(views_flipper, "thumbnails");
        thumbnails_showing = true;
        repaintPageview();
        if ((activity_logger != null) && activities_on) {
            activity_logger.call(new Activity(document_id, current_page_index, Activity.AC_THUMBNAILS_OPENED));
        }
    }

    public void hideThumbnails() {
        ((CardLayout)views_flipper.getLayout()).show(views_flipper, "pages");
        thumbnails_showing = false;
        repaintPageview();
        if ((activity_logger != null) && activities_on) {
            activity_logger.call(new Activity(document_id, current_page_index, Activity.AC_THUMBNAILS_CLOSED));
        }
    }

    public void keyPressed (KeyEvent e) {
        int k = e.getKeyCode();
        // System.err.println("key " + e + " pressed");
        if (k == KeyEvent.VK_SHIFT) {
            // System.err.println("Shift key pressed");
            shift_key_pressed = true;
            repaintPageview();
        } else if (k == KeyEvent.VK_ALT && (!thumbnails_showing)) {
            // System.err.println("Alt key pressed, displaying thumbnails");
            System.err.println("" + e);
            showThumbnails();
        } else if (k == KeyEvent.VK_ALT) {
            System.err.println("" + e);
            // System.err.println("Alt key pressed");
        }
    }

    public void keyReleased (KeyEvent e) {
        int k = e.getKeyCode();
        // System.err.println("key " + e + " released");
        if (k == KeyEvent.VK_SHIFT) {
            shift_key_pressed = false;
            repaintPageview();
        } else if (k == KeyEvent.VK_ALT && thumbnails_showing) {
            // System.err.println("Alt key released, displaying pages");
            System.err.println("" + e);
            hideThumbnails();
        } else if (k == KeyEvent.VK_ALT) {
            System.err.println("" + e);
            // System.err.println("Alt key released");
        } else if (k == KeyEvent.VK_RIGHT) {
            // System.err.println("Left key released");
            if ((active_reading != null) && (!active_reading.paused()))
                active_reading.speedUp(100);
            else
                nextPage();
        } else if ((k == KeyEvent.VK_DOWN) || (k == KeyEvent.VK_PAGE_DOWN)) {
            nextPage();
        } else if (k == KeyEvent.VK_LEFT) {
            // System.err.println("Right key released");
            if ((active_reading != null) && (!active_reading.paused()))
                active_reading.slowDown(100);
            else
                prevPage();
        } else if ((k == KeyEvent.VK_UP) || (k == KeyEvent.VK_PAGE_UP)) {
            // System.err.println("Right key released");
            prevPage();
        } else if (k == KeyEvent.VK_HOME) {
            // System.err.println("HOME key released");
            firstPage();
        } else if (k == KeyEvent.VK_END) {
            // System.err.println("END key released");
            lastPage();
        }
    }

    protected class SelectionState {

        protected PageText.WordBox first;
        protected PageText.WordBox last;
        protected int page_index;
        protected java.util.List boxes;
        protected PageText pagetext;
        protected String text;
        protected Rectangle image_rect;

        public SelectionState () {
            clear();
        }

        public void clear () {
            first = null;
            last = null;
            page_index = -1;
            boxes = null;
            pagetext = null;
            text = null;
            image_rect = null;
        }

        public String toString () {
            String t = "<SelectionState ";
            if ((first != null) && (last != null)) {
                t += ("page " + page_index + ", " + first.contentsPosition() + "-" + (last.contentsPosition() + last.contentsLength() - 1) + " \"" + getText() + "\"");
            } else {
                t += "(empty)";
            }
            t += ">";
            return t;
        }

        public boolean isActive () {
            return (((first != null) || (image_rect != null)) &&
                    ((page_index == current_page_index) ||
                     (two_page && (page_index == (current_page_index + 1)))));
        }

        public boolean isVisible () {
            return (((boxes != null) || (image_rect != null)) &&
                    ((page_index == current_page_index) ||
                     (two_page && (page_index == (current_page_index + 1)))));
        }

        public void setRect(int page, Rectangle r) {
            clear();
            page_index = page;
            image_rect = r;
        }

        public Rectangle getImageRect() {
            if ((image_rect == null) && (boxes != null)) {
                Rectangle r = null;
                for (Iterator i = boxes.iterator();  i.hasNext();) {
                    PageText.WordBox b = (PageText.WordBox) i.next();
                    if (r == null)
                        r = b.getBounds();
                    else
                        r.add(b);
                }
                image_rect = r;
            }
            return image_rect;
        }

        public boolean contains (Point p) {
            if (boxes != null) {
                for (Iterator i = boxes.iterator();  i.hasNext();) {
                    PageText.WordBox b = (PageText.WordBox) i.next();
                    if (b.contains(p))
                        return true;
                }
            } else if (image_rect != null) {
                return image_rect.contains(p);
            }
            return false;
        }

        public java.util.List getBoxes (int page_no) {
            if (page_no != page_index)
                return null;
            return boxes;
        }

        public java.util.List getBoxes () {
            return boxes;
        }

        public void setFirst (PageText.WordBox box) {
            first = box;
            last = null;
            boxes = null;
            if (box != null) {
                pagetext = box.getPageText();
                page_index = box.getPageText().getPageIndex();
            } else {
                pagetext = null;
                page_index = 0;
            }
            text = null;
            image_rect = null;
        }

        public void setLast (PageText.WordBox box) {
            if (first != null && box != null) {
                last = box;
                int pos1 = first.contentsPosition();
                int pos2 = last.contentsPosition();
                if (pos1 <= pos2)
                    boxes = pagetext.getWordBoxes (pos1, pos2);
                else
                    boxes = pagetext.getWordBoxes (pos2, pos1);
                text = null;
                image_rect = null;
            }
        }
        
        public void setSpan (PageText pt, int contents_position, int contents_length) {
            if (pt == null)
                return;
            first = pt.getWordBox(contents_position);
            last = pt.getWordBox(contents_position + contents_length);
            page_index = pt.getPageIndex();
            pagetext = pt;
            boxes = pagetext.getWordBoxes (first.contentsPosition(), last.contentsPosition());
            text = null;        // lazily evaluate this
            image_rect = null;
        }

        public String getText () {
            if ((text == null) && (first != null) && (last != null)) {
                int pos1 = first.contentsPosition();
                int pos2 = last.contentsPosition();
                String t = null;
                if (pos1 <= pos2)
                    t = pagetext.getText (pos1, pos2 + last.contentsLength());
                else
                    t = pagetext.getText (pos2, pos1 + first.contentsLength());
                text = t;
                if (t == null) return null;
                for (int i = t.length() - 1;  i >= 0;  i--) {
                    if (Character.isWhitespace(t.charAt(i)))
                        text = t.substring(0, i);
                    else
                        break;
                }
            }
            return text;
        }

        public int getStartPos () {
            // return first pos relative to beginning of page
            if ((first != null) && (last != null)) {
                int pos1 = first.contentsPosition();
                int pos2 = last.contentsPosition();
                if (pos1 <= pos2)
                    return pos1;
                else
                    return pos2;
            }
            return -1;
        }

        public int getStartPosAbsolute () {
            // return first pos relative to beginning of document
            if ((first != null) && (last != null)) {
                int pos1 = first.contentsPosition();
                int pos2 = last.contentsPosition();
                if (pos1 <= pos2)
                    return pos1 + first.getPageText().getTextLocation();
                else
                    return pos2 + last.getPageText().getTextLocation();
            }
            return -1;
        }

        public int getEndPos () {
            // return last pos relative to beginning of page
            if ((first != null) && (last != null)) {
                int pos1 = first.contentsPosition();
                int pos2 = last.contentsPosition();
                if (pos1 > pos2)
                    return pos1;
                else
                    return pos2;
            }
            return -1;
        }

        public int getEndPosAbsolute () {
            // return last pos relative to beginning of document
            if ((first != null) && (last != null)) {
                int pos1 = first.contentsPosition();
                int pos2 = last.contentsPosition();
                if (pos1 > pos2)
                    return pos1 + first.getPageText().getTextLocation();
                else
                    return pos2 + last.getPageText().getTextLocation();
            }
            return -1;
        }

        public int getFirstPos () {
            // return first pos relative to beginning of page
            if ((first != null) && (last != null)) {
                return first.contentsPosition();
            }
            return -1;
        }

        public int getLastPos () {
            // return first pos relative to beginning of page
            if ((first != null) && (last != null)) {
                return last.contentsPosition();
            }
            return -1;
        }

        public int getStartPage () {
            if ((first != null) && (last != null)) {
                return first.getPageText().getPageIndex();
            }
            return -1;
        }

        protected String getURLText () {
            return "doc_id=" + document_id + "&page=" + getStartPage() +
                "&selection-start=" + getStartPosAbsolute() +
                "&selection-end=" + getEndPosAbsolute();
        }

        public void setURL() {
            if (seturl_handler != null) {
                seturl_handler.call(getURLText());
            }
        }

        protected String getAnnotatedSelectedText () {
            // should add some metadata to this text
            return getText();
        }

        protected void setClipboard () {
            if (clipboard != null) {
                String selected_text = getText();
                System.err.println("Setting clipboard to " + selected_text);
                java.awt.datatransfer.StringSelection s = new java.awt.datatransfer.StringSelection(selected_text);
                try {
                    clipboard.setContents(s);
                    System.err.println("Clipboard has been set to:  " + selected_text);
                } catch (IllegalStateException x) {
                    System.err.println("Couldn't set clipboard:  " + x);
                }
            }
        }
    }

    public void setSelection (PageText pt, int contents_position, int contents_end) {
        if (pt != null) {
            selection.setSpan(pt, contents_position, contents_end - contents_position);
            repaintPageview();
        }
    }

    public void setSelection (int page, int start, int end) {
        PageText pt = (PageText) pagetext_loader.get(document_id, page, 0, null);
        if (pt != null) {
            selection.setSpan(pt, start - pt.getTextLocation(), end - start);
            repaintPageview();
        }
    }

    public void setSelection (int page, Rectangle r) {
        selection.setRect(page, r);
        repaintPageview();
    }

    public void setURLHandler(DocViewerCallback c) {
        seturl_handler = c;
    }

    public void setADHState (int period_p) {
        active_reading = new ADHState(this, period_p);
        active_reading.start();
    }

    private class ADHState extends Thread {

        private int period;
        private int extraPeriod;
        private DocViewer topl;
        private PageText.WordBox next_phrase_first_box = null;
        private int this_page_index = -1;
        private Iterator current_page_iterator = null;
        private volatile boolean not_paused;
        private java.util.List current_boxes;
        private float phrase_difficulty = 1.0f;
        private int phrase_extra = 0;
        private boolean last_phrase_ended_line = false;
        private boolean destroying = false;
        private int waiting_for_page = -1;

        public ADHState (DocViewer dv_p, int period_p) {

            super("ADH for " + document_id);
            topl = dv_p;
            period = (period_p < 100) ? 100 : period_p;
            extraPeriod = 0;
            not_paused = false;
            current_boxes = null;
            current_page_iterator = null;
            last_phrase_ended_line = false;
            waiting_for_page = -1;
            try {
                setDaemon(true);
            } catch (Exception e) {
                System.err.println ("Exception setting active_reading thread to daemon state:  " + e);
            }
            System.err.println("Created ADH thread...");
        }

        public void run () {
            long t;
            while (true) {
                try {
                    setPhraseBoxes();
                    if (not_paused) {
                        // System.err.println("Advancing to phrase " + this_page_index + "/" + ((PageText.WordBox)(current_boxes.get(0))).contentsPosition() + ", phrase_difficulty is " + phrase_difficulty + ", phrase_extra is " + phrase_extra);
                        topl.repaintPageview();
                        // System.err.println("sleep is " + (int)((period * phrase_difficulty) + phrase_extra));
                        try {
                            sleep((long)max(200, ((period * phrase_difficulty) + phrase_extra)));
                            while ((t = getTempHold()) > 0) {
                                // System.err.println("extra sleep is " + t);
                                sleep(t);
                            }
                        } catch (InterruptedException e) {
                            if (destroying)
                                throw e;
                        }
                    } else {
                        synchronized(this) {
                            while (!not_paused) {
                                if (current_page_iterator == null)
                                    setPhraseBoxes();
                                // System.err.println("ADH thread waiting...");
                                wait();
                                // System.err.println("ADH thread awakened.");
                            }
                        }
                    }
                } catch (InterruptedException e) {
                    if (destroying)
                        break;
                }
            }
            System.err.println("exiting ADHState thread");
            return;
        }

        public void destroy () {
            destroying = true;
            this.interrupt();
        }

        public java.util.List getBoxes () {
            synchronized(this) {
                return current_boxes;
            }
        }

        private PageText waitForPagetext (int pageno) {
            PageText pt;
            if ((pt = (PageText) pagetext_loader.get(document_id, pageno, 0, null)) == null)
                pt = (PageText) pagetext_loader.get(document_id, pageno, 0, new PageTextSetter(pageno, false));
            synchronized (this) {
                this.waiting_for_page = pageno;
                while (((pt = (PageText) pagetext_loader.get(document_id, pageno, 0, null)) == null) &&
                       (waiting_for_page >= 0)) {
                    try {
                        // System.err.println("" + this + " waiting...");
                        wait();
                        // System.err.println("" + this + " resumed.");
                    } catch (InterruptedException x) {
                        // System.err.println("" + this + " interrupted.");
                    }
                }
            }
            return pt;
        }

        public void pagetextDelivered (int pageno) {
            synchronized(this) {
                if (waiting_for_page == pageno) {
                    waiting_for_page = -1;
                    notify();
                }
            }
        }

        private void setPhraseBoxes () {

            PageText pt = null;
            Vector boxes = new Vector();
            int pagetries = 0;

            while ((next_phrase_first_box == null) && (pagetries < page_count)) {
                if (this_page_index < 0)
                    this_page_index = current_page_index;
                else if (this_page_index >= (page_count - 1))
                    // wrap from end around to beginning
                    this_page_index = 0;
                else if (current_page_iterator != null)
                    this_page_index += 1;
                pagetries += 1;
                if (pagetext_loader != null) {
                    pt = waitForPagetext(this_page_index);
                    if (pt != null) {
                        current_page_iterator = pt.getWordBoxes(null);
                        if (current_page_iterator.hasNext())
                            next_phrase_first_box = (PageText.WordBox) (current_page_iterator.next());
                    } else {
                        return;
                    }
                }
            }
            if (next_phrase_first_box == null) {
                pause();
                return;
            }

            if (current_page_index != this_page_index)
                setPage(this_page_index);

            boxes.add(next_phrase_first_box);
            next_phrase_first_box = null;

            while (current_page_iterator.hasNext()) {
                next_phrase_first_box = (PageText.WordBox) (current_page_iterator.next());
                if (next_phrase_first_box.beginsPhrase())
                    break;
                else
                    boxes.add(next_phrase_first_box);
            }

            // at this point we can do some phrase analysis
            float cd = 1.0f;
            int   ce = 0;
            Iterator i = boxes.iterator();
            while (i.hasNext()) {
                PageText.WordBox b = (PageText.WordBox) i.next();

                boolean this_phrase_ends_sentence = (next_phrase_first_box != null) && next_phrase_first_box.beginsSentence();
                boolean this_phrase_ends_page = (next_phrase_first_box == null);
                
                // add some extra time for longer phrases
                for (int j = boxes.size(), incr = period/8;  j > 4 && incr > 0;  j--, incr = incr/2) {
                    ce += incr;
                }
                // subtract some time for shorter phrases
                for (int j = 4 - boxes.size(), incr = period/8;  j > 0 && incr > 0;  j--, incr = incr/2) {
                    ce -= incr;
                }
                if (this_phrase_ends_page) {
                    // last word on a page
                    ce += 200;
                    last_phrase_ended_line = false;
                } else if (this_phrase_ends_sentence) {
                    // last wordbox of a sentence
                    ce += (period / 8);
                    last_phrase_ended_line = false;
                } else if (last_phrase_ended_line && (boxes.elementAt(0) == (Object) b)) {
                    // first wordbox of a new phrase on a new line
                    ce += (period / 8);
                    last_phrase_ended_line = false;
                }
                if (b.endOfLine())
                    last_phrase_ended_line = true;
            }

            PageText.WordBox first = (PageText.WordBox)(boxes.elementAt(0));
            // System.err.println("phrase " + this_page_index + "/" + first.contentsPosition() + ", " + boxes.size() + " wordboxes, difficulty " + cd + ", extra " + ce + ", period is " + period + ", sleeptime is " + ((period * cd) + ce));

            synchronized(this) {
                if (current_page_iterator == null)
                    current_boxes = null;
                else
                    current_boxes = boxes;
                phrase_difficulty = cd;
                phrase_extra = ce;
            }
        }

        public void jumpTo (PageText.WordBox box) {
            next_phrase_first_box = box;
            this_page_index = box.getPageText().getPageIndex();
            current_page_iterator = box.getPageText().getWordBoxes(box);
            this.interrupt();
        }

        public void tempHold (int extra) {
            synchronized(this) {
                extraPeriod += extra;
            }
        }

        public synchronized float[] percentageAlongPage () {
            float[] rval = new float[2];
            if (current_boxes == null) {
                rval[0] = 0.0f;
                rval[1] = 1.0f;
            } else {
                PageText.WordBox firstBox = (PageText.WordBox) (current_boxes.get(0));
                PageText.WordBox lastBox = (PageText.WordBox) (current_boxes.get(current_boxes.size() - 1));
                int pagelength = firstBox.getPageText().getTextBytes().length;
                rval[0] = ((float) firstBox.contentsPosition()) / (float) pagelength;
                rval[1] = ((float) (lastBox.contentsPosition() - firstBox.contentsPosition())) / (float) pagelength;
            }
            return rval;
        }

        private int getTempHold () {
            int t = 0;
            synchronized(this) {
                t = extraPeriod;
                extraPeriod = 0;
            }
            return t;
        }

        public synchronized void pause () {
            not_paused = false;
        }

        private class UnPauser implements DocViewerCallback {
            public UnPauser () {
            }
            public void call (Object o) {
                if (o instanceof PageText) {
                    PageText pt = (PageText) o;
                    current_page_iterator = pt.getWordBoxes(null);
                    if (current_page_iterator.hasNext())
                        next_phrase_first_box = (PageText.WordBox) (current_page_iterator.next());
                    synchronized(this) {
                        this.notify();
                    }
                }
            }
            public void flush () {};
        }

        public synchronized void unPause () {
            not_paused = true;
            if (this_page_index != current_page_index) {
                this_page_index = current_page_index;
                pagetext_loader.get(document_id, this_page_index, 0, new UnPauser());
            } else
                this.notify();
        }

        public synchronized void speedUp (int increment) {
            period = max(50, period - increment);
        }

        public synchronized void slowDown (int increment) {
            period = period + increment;
        }

        public synchronized boolean paused () {
            return (!not_paused);
        }

    }

    protected class SearchState {

        protected int search_page;
        protected int search_pos;
        public String search_string;
        protected int search_bytes_len;
        protected Stack page_stack;
        protected Stack pos_stack;
        protected Stack len_stack;
        protected int last_match_len = 0;
        protected int match_count = 0;
        protected int wrap_count = 0;
        
        public SearchState () {
            search_page = current_page_index;
            search_pos = -1;
            search_string = "";
            search_bytes_len = 0;
            page_stack = new Stack();
            pos_stack = new Stack();
            len_stack = new Stack();
            match_count = 0;
            wrap_count = 0;

            if (selection.isVisible()) {
                search_page = selection.getStartPage();
                search_pos = selection.getStartPos();
                String t = selection.getText();
                selection.clear();
                for (int i = 0;  i < t.length();  i++) {
                    this.extendSearch(t.charAt(i));
                }
            }
        }

        public int getPage () {
            return search_page;
        }

        public int hits() {
            return (match_count + (hasMatch() ? 1 : 0));
        }

        public boolean wrapped() {
            return (wrap_count > 0);
        }

        public String toString () {
            String name = "<SearchState \"" + search_string + "\"; page:" + search_page + "; pos:" + search_pos;
            if (match_count > 0)
                name = name + "; matches:" + match_count;
            name = name + ">";
            return name;
        }

        public int getPos () {
            return search_pos;
        }

        public int getLength() {
            return search_bytes_len;
        }

        public boolean hasMatch() {
            return (search_string.length() > 0 && search_page >= 0 && search_pos >= 0);
        }

        public void waitForPage (int page_index) {
            PageText pt;
            if (page_index < 0 || page_index >= page_count) {
                Throwable t = new Throwable();
                t.printStackTrace(System.err);
                return;
            }
            setPage(page_index);
            synchronized (this) {
                while ((pt = (PageText) pagetext_loader.get(document_id, page_index, 0, null)) == null) {
                    try {
                        // System.err.println("" + this + " waiting...");
                        wait();
                        // System.err.println("" + this + " resumed.");
                    } catch (InterruptedException x) {
                        // System.err.println("" + this + " interrupted.");
                    }
                }
            }
        }

        protected void extendSearch (char c) {
            if ((c == DELETE) || (c == BACKSPACE)) {
                if (match_count > 0) {
                    int old_search_page = search_page;
                    int old_search_pos = search_pos;
                    search_page = ((Integer) page_stack.pop()).intValue();
                    search_pos = ((Integer) pos_stack.pop()).intValue();
                    search_bytes_len = ((Integer) len_stack.pop()).intValue();
                    // System.err.println("Popped " + search_page + "/" + search_pos + " off the stack, which now contains:");
                    // for (int i = 0;  i < page_stack.size();  i++) {
                    // System.err.println("     " + ((Integer) page_stack.get(i)).intValue() + "/" + ((Integer) pos_stack.get(i)).intValue() + "/" + ((Integer) len_stack.get(i)).intValue());
                    //}
                    if ((search_page != current_page_index) && (search_page >= 0) && (search_page < page_count))
                        waitForPage(search_page);
                    match_count -= 1;
                    if ((search_page > old_search_page) || ((search_page == old_search_page) && (search_pos >= old_search_pos)))
                        wrap_count -= 1;
                    return;
                } else if (search_string.length() > 0) {
                    search_string = search_string.substring(0, search_string.length() - 1);
                    search_page = ((Integer) page_stack.pop()).intValue();
                    search_pos = ((Integer) pos_stack.pop()).intValue();
                    search_bytes_len = ((Integer) len_stack.pop()).intValue();
                    // System.err.println("Popped " + search_page + "/" + search_pos + " off the stack, which now contains:");
                    // for (int i = 0;  i < page_stack.size();  i++) {
                    // System.err.println("     " + ((Integer) page_stack.get(i)).intValue() + "/" + ((Integer) pos_stack.get(i)).intValue() + "/" + ((Integer) len_stack.get(i)).intValue());
                    //}
                    last_match_len -= 1;
                    if ((search_page != current_page_index) && (search_page >= 0) && (search_page < page_count))
                        waitForPage(search_page);
                    return;
                }
            } else if (c == CONTROL_G) {
                // end search
                search_string = null;
                search_page = -1;
                search_pos = -1;
                repaintPageview();
                return;
            } else if (c == CONTROL_S) {
                if (hasMatch()) {
                    match_count += 1;
                    page_stack.push(new Integer(search_page));
                    pos_stack.push(new Integer(search_pos));
                    len_stack.push(new Integer(search_bytes_len));
                    search_pos += 1;
                } else {
                    wrap_count += 1;
                }
            } else {
                search_string = search_string.concat(Character.toString(c));
                page_stack.push(new Integer(search_page));
                pos_stack.push(new Integer(search_pos));
                len_stack.push(new Integer(search_bytes_len));
            }

            if (search_string.length() == 0)
                return;

            byte[] search_bytes = null;
            try {
                search_bytes = search_string.getBytes("UTF-8");
                search_bytes_len = search_bytes.length;
            } catch (UnsupportedEncodingException uee) {
                System.err.println("Impossible exception occurred!  " + uee);
                uee.printStackTrace(System.err);
                search_string = null;
                search_page = -1;
                search_pos = -1;
                return;
            }

            int i, j, page;
            for (page = (search_page < 0) ? 0 : search_page;  page < page_count;  page++, search_pos = 0) {
                PageText pt;
                while ((pt = (PageText) pagetext_loader.get(document_id, page, 0, null)) == null)
                    waitForPage(page);
                byte[] pagebytes = pt.getTextBytes();
                for (i = (search_pos < 0) ? 0 : search_pos;  i < (pagebytes.length - search_bytes.length);  i++) {
                    for (j = 0;  j < search_bytes.length;  j++) {
                        if (Character.isWhitespace((char) (0x0000 | search_bytes[j])) &&
                            Character.isWhitespace((char) (0x0000 | pagebytes[i + j])))
                            continue;
                        if (search_bytes[j] != pagebytes[i + j]) {
                            break;
                        }
                    }
                    if (j >= search_bytes.length) {
                        // we've found a match, so break
                        break;
                    }
                }
                if (i < (pagebytes.length - search_bytes.length)) {
                    // found a match
                    search_page = page;
                    last_match_len = search_string.length();
                    search_pos = i;
                    // System.err.println("found match, page " + search_page + ", pos " + search_pos);
                    break;
                }
            }
            if (page >= page_count) {
                // no match found
                search_page = -1;
                search_pos = -1;
            } else if ((search_page != current_page_index) && (search_page >= 0) && (search_page < page_count)) {
                // need to move to this page
                waitForPage(search_page);
            }
        }
    } // end of class SearchState

    Container findResizableAncestor () {
        if ((scaled_jcomponent_class != null) && (content_pane_class != null)) {
            Container cont = getParent();
            // System.err.println("parent component is " + cont.getClass().getName());
            try {
                if (content_pane_class.isInstance(cont)) {
                    // we skip over the ZeroPane instance in ScaledJComponent
                    Container cont2 = cont.getParent().getParent();
                    // System.err.println("super-parent is " + cont2.getClass().getName());
                    return cont2;
                }
            } catch (Exception x) {
                System.err.println("Error while attempting to resize document:");
                x.printStackTrace(System.err);
            }
        }
        return null;
    }

    protected BufferedImage getLinkImage (int pageno) {
        BufferedImage ii = null;
        if (cached_link_image == null) {
            if (thumbnail_image_loader != null) {
                BufferedImage di2 = (BufferedImage) thumbnail_image_loader.get(document_id, -1, 0, null);
                if (di2 != null) {
                    int w = di2.getWidth(null) / 3;
                    int h = di2.getHeight(null) / 3;
                    cached_link_image = new BufferedImage(w, h, BufferedImage.TYPE_INT_RGB);
                    Graphics g = cached_link_image.getGraphics();
                    Image di3 = di2.getScaledInstance(w, h, Image.SCALE_SMOOTH);
                    g.drawImage(di3, 0, 0, w, h, null);
                }
            }
        }
        if (cached_link_image != null) {
            String pageno_string = getPageNumberString(pageno);
            ii = new BufferedImage(cached_link_image.getWidth(null), cached_link_image.getHeight(null),
                                   BufferedImage.TYPE_INT_RGB);
            Graphics g = ii.getGraphics();
            g.drawImage(cached_link_image, 0, 0, null);
            Rectangle2D bounds = g.getFontMetrics(g.getFont()).getStringBounds(pageno_string, g);
            int x = (int) Math.round(ii.getWidth(null) - 3 - bounds.getWidth());
            int y = (int) Math.round(1 + bounds.getHeight());
            g.setColor(WHITE);
            g.drawString(pageno_string, x-1, y-1);
            g.drawString(pageno_string, x+1, y+1);
            g.drawString(pageno_string, x-1, y+1);
            g.drawString(pageno_string, x+1, y-1);
            g.setColor(BLACK);
            g.drawString(pageno_string, x, y);
        }
        return ii;
    }

    public void setSearchString(String phrase) {
        if (this.pagetext_loader==null) return; // extendSearch() only works if word bounding boxes are available
        search_state = createSearchState(); 
        for (int i = 0, m = phrase.length(); i < m; i++) {
            char c = phrase.charAt(i);
            search_state.extendSearch(c);
        }
        repaintPageview();
    }
    
    public void keyTyped (KeyEvent e) {
        // System.err.println("key " + e + " typed, controlDown is " + e.isControlDown());
        splash_page_period = 0;
        char c = e.getKeyChar();
        if ((pagetext_loader != null) && e.isControlDown() && (c == CONTROL_S) && (search_state == null)) {
            search_state = createSearchState();
            repaintPageview();
        } else if (c == CONTROL_W || c == CONTROL_C) {
            // CONTROL_C added by Bier, as it is the standard control sequence in Windows
            if (selection != null)
              selection.setClipboard();
        } else if (search_state != null) {
            if ((c == CONTROL_G) || (((c == DELETE) || (c == BACKSPACE)) && (search_state.search_string.length() < 1))){
                // System.err.println("quitting search");
                if (search_state.hasMatch())
                    setSelection ((PageText) pagetext_loader.get(document_id, search_state.getPage(), 0, null),
                                  search_state.getPos(), search_state.getPos() + search_state.getLength());
                search_state = null;
            }
            else if ((c == BACKSPACE) || (c == DELETE) || (c == CONTROL_S) || (!Character.isISOControl(c)))
                search_state.extendSearch(c);
            repaintPageview();
        } else if ((c == CONTROL_D) && (snapback_page != -1)) {
            setPage(snapback_page);
        } else if (c == CONTROL_I) {
            show_phrases = ! show_phrases;
            repaintPageview();
        } else if (c == CONTROL_J) {
            rsvp_mode = !rsvp_mode;
            repaintPageview();
        } else if ((c == CONTROL_V) || (c == CONTROL_N)) {
            nextPage();
        } else if ((c == CONTROL_P) || ((c == 'v') && e.isMetaDown())) {
            prevPage();
        } else if (c == CONTROL_F) {
            Container resizable_component;
            if (((resizable_component = findResizableAncestor()) != null) &&
                (top_level_ancestor != null) && (top_level_ancestor instanceof JWindow)) {
                    try {
                        if ((getWidth() > top_level_ancestor.getWidth()) || (getHeight() > top_level_ancestor.getHeight())) {
                            // must be scaled down, so scale back to full size
                            Method m = resizable_component.getClass().getMethod("resizeToUnitTransform", (Class[]) null);
                            m.invoke(resizable_component, (Object[]) null);
                            repaintPageview();
                        } else {
                            // scale down to small size
                            // if it's a Window, we need to allow for the titlebar
                            Dimension d2 = ((JWindow)top_level_ancestor).getContentPane().getPreferredSize();
                            int titlebar_height = (top_level_ancestor.getHeight() - d2.height);
                            top_level_ancestor.setSize(getWidth()/3, getHeight()/3 + titlebar_height);
                        }
                    } catch (Exception x) {
                        System.err.println("Error while attempting to resize document:");
                        x.printStackTrace(System.err);
                    }
            }
        } else if (c == CONTROL_U) {
            setTwoPage(!two_page);
        } else if (c == CONTROL_Q) {
            if ((locate_handler != null) && (selection != null) && selection.isActive()) {
                locate_handler.call(selection.getText());
            }
        } else if (c == CONTROL_R) {
            if ((google_handler != null) && (selection != null) && selection.isActive()) {
                google_handler.call(selection.getText());
            }
        } else if (c == CONTROL_T) {
            if ((selection != null) && (seturl_handler != null))
                selection.setURL();
        } else if (c == CONTROL_O) {
            show_active_reading = !show_active_reading;
            repaintPageview();
        } else if (c == CONTROL_M) {
        } else if (c == SPACE) {
            if (active_reading != null) {
                if (active_reading.paused())
                    active_reading.unPause();
                else {
                    active_reading.pause();
                }
                repaintPageview();
            }
        } else {
            System.err.println("keyTyped: " + e);
        }
    }

    public void setShowActiveReading (boolean value, boolean rsvp) {
        show_active_reading = value;
        rsvp_mode = rsvp;
        repaintPageview();
    }

    public boolean hasAnnotations (int page_index) {
        return (hasScribbles(page_index) || hasNotes(page_index));
    }

    public boolean hasNotes (int page_index) {
        if (page_index < 0 || page_index >= page_count)
            return false;
        return (!((ArrayList)note_sheets.get(page_index)).isEmpty());
    }

    public boolean hasScribbles (int page_index) {
        if (page_index < 0 || page_index >= page_count)
            return false;
        return (!((ArrayList)strokes.get(page_index)).isEmpty());
    }

    public void setShowScribbles (boolean trueToShow) {
        show_scribbles = trueToShow;
        if ((activity_logger != null) && activities_on) {
            activity_logger.call(new Activity(document_id, current_page_index,
                                              (trueToShow ? Activity.AC_ANNOTATIONS_ON : Activity.AC_ANNOTATIONS_OFF)));
        }
    }

    public boolean showScribbles () {
        return (show_scribbles ^ shift_key_pressed);
    }

    public boolean showNotes () {
        return (showScribbles() &&
                (search_state == null) && 
                ((active_reading == null) || (show_active_reading == false) || active_reading.paused()) &&
                (rsvp_mode == false));
    }

    public boolean showHotspots () {
        return (show_hotspots ^ shift_key_pressed);
    }

    public Map getDocumentProperties () {
        return Collections.unmodifiableMap(document_properties);
    }

    public void setRepositoryURL (URL v) {
        document_properties.put("repository-URL", v);
        theRepositoryURL = v;
    }

    public void setShowHotspots (boolean trueToShow) {
        show_hotspots = trueToShow;
        if ((activity_logger != null) && activities_on) {
            activity_logger.call(new Activity(document_id, current_page_index,
                                              (trueToShow ? Activity.AC_HOTSPOTS_ON : Activity.AC_HOTSPOTS_OFF)));
        }
    }

    public void setAnnotationSpan (Date after, Date before) {
        annotation_span_start = after;
        annotation_span_end = before;
    }

    public void repaintPageview () {

        if (!gui_created)
            return;

        if (!focusOnOurApp())
            requestFocusInWindow();

        left_pageview.repaint();
        if (two_page)
            right_pageview.repaint();
        if (top_edge_type != PAGEEDGE_NONE)
            top_page_edge.repaint();
        if (bottom_edge_type != PAGEEDGE_NONE)
            bottom_page_edge.repaint();
        if (show_controls)
            controls.repaint();
    }

    public void setPageviewCursor (Cursor c) {
        Cursor toset = (c == null) ? our_cursor : c;
        left_pageview.setCursor(toset);
        if (two_page)
            right_pageview.setCursor(toset);
    }

    public void repaintPageview (int old_pagenum, int new_pagenum) {
        if (old_pagenum != new_pagenum) {
            left_pageview.animate_change(old_pagenum, new_pagenum);
            if (two_page)
                right_pageview.animate_change(old_pagenum, new_pagenum);
        }
        repaintPageview();
    }

    public int getPage() {
	return current_page_index;
    }

    protected void setPage(int page_index, boolean repaint) {

        if (page_index >= 0 && page_index < page_count) {
            if (thumbnails != null)
                thumbnails.changePage(page_index);
            int old_page_index = current_page_index;
            current_page_index = page_index;
            if (page_image_loader != null) {
                page_image_loader.get(document_id, page_index, 0, (repaint ? new PageImageSetter(page_index) : null));
                if (two_page && (page_index < (page_count - 1)))
                    page_image_loader.get(document_id, page_index + 1, 0, (repaint ? new PageImageSetter(page_index + 1) : null));
                thumbnail_image_loader.get(document_id, page_index, 1, null);
                /*
                if (!two_page && (page_index < (page_count - 1))) {
                    page_image_loader.get(document_id, page_index + 1, 0, null);
                    thumbnail_image_loader.get(document_id, page_index + 1, 1, null);
                }
                if (page_index > 0) {
                    page_image_loader.get(document_id, page_index - 1, 0, null);
                    thumbnail_image_loader.get(document_id, page_index - 1, 1, null);
                }
                */
            }
            if (pagetext_loader != null) {
                pagetext_loader.get(document_id, page_index, 0, new PageTextSetter(page_index, repaint, search_state));
                /*
                if (page_index < (page_count - 1))
                    // get following page into cache
                    pagetext_loader.get(document_id, page_index + 1, 0, null);
                */
            }
            if (note_loader != null) {
                note_loader.get(document_id, page_index, 0, new NoteFramesSetter(page_index));
            }
            if ((activity_logger != null) && activities_on) {
                activity_logger.call(new Activity(document_id, current_page_index, Activity.AC_PAGE_TURNED));
            }
            if (Math.abs(current_page_index - old_page_index) > (two_page ? 2 : 1))
                snapback_page = old_page_index;
            else
                snapback_page = -1;
            if (repaint)
                repaintPageview(old_page_index, current_page_index);
        }
    }

    public void setPage (int page_index) {
        setPage(page_index, true);
    }

    public void nextPage () {
        if (current_page_index < (page_count - (two_page ? 2 : 1)))
            setPage(current_page_index + (two_page ? 2 : 1));
    }

    public void prevPage () {
        if (current_page_index > 0)
            setPage(max(0, current_page_index - (two_page ? 2 : 1)));
    }

    public void firstPage () {
        if (current_page_index > (two_page ? 1 : 0))
            setPage(two_page ? 1 : 0);
    }

    public void lastPage () {
        if (current_page_index < (page_count - (two_page ? 2 : 1)))
            setPage(page_count - (two_page ? 2 : 1));
    }

    public void actionPerformed(ActionEvent evt) {
        String action = evt.getActionCommand();
        System.out.println("Activating " + action);
        
        // search menu first

        if ((pagetext_loader != null) && action.equals("Search") && (search_state == null)) {
            search_state = createSearchState();
            repaintPageview();
        } else if ((search_state != null) && action.equals("Search")) {
            search_state.extendSearch(CONTROL_S);
            repaintPageview();
        } else if (action.equals("UpLib")) {
                logo_url.call(null);
        } else if (action.equals("More\n(UpLib)")) {
            if ((locate_handler != null) && (selection != null) && selection.isActive()) {
                locate_handler.call(selection.getText());
            }
        } else if (action.equals("More\n(Google)")) {
            if ((google_handler != null) && (selection != null) && selection.isActive()) {
                google_handler.call(selection.getText());
            }

        }

        // show menus

        else if (action.equals("Phrases")) {
            show_phrases = true;
            rsvp_mode = false;
            show_active_reading = false;
            if (active_reading != null)
                active_reading.pause();
            repaintPageview();
        } else if (action.equals("RSVP")) {
            rsvp_mode = true;
            show_phrases = false;
            show_active_reading = false;
            if (active_reading != null) {
                if (active_reading.paused())
                    active_reading.unPause();
            }
            repaintPageview();
        } else if (action.equals("P.O.S")) {
            show_parts_of_speech = !show_parts_of_speech;
        } else if (action.equals("1 Page")) {
            setTwoPage(false);
        } else if (action.equals("2 Page")) {
            setTwoPage(true);
        } else if (action.equals("Normal")) {
            rsvp_mode = false;
            show_phrases = false;
            show_active_reading = false;
            if (active_reading != null)
                active_reading.pause();
            repaintPageview();
        } else if (action.equals("Hotspots")) {
            setShowHotspots(true);
            repaintPageview();
        }

        // Go to menu

        else if (action.equals("Start")) {
            firstPage();
        } else if (action.equals("End")) {
            lastPage();
        } else if (action.equals("Repo")) {
            if (logo_url != null)
                logo_url.call(null);
        } else if (action.equals("Purple")) {
            bookmarks[0].gotoPage();
        } else if (action.equals("Green")) {
            bookmarks[1].gotoPage();
        } else if (action.equals("Red")) {
            bookmarks[2].gotoPage();
        }

        // rubberbanding for zoom

        else if (action.equals("Zoom")) {
            showZoomIn(selection.getImageRect());
        }

        // other menus

        else if (action.equals("Copy") && (selection != null)) {
            selection.setClipboard();
        }

        else if (action.equals("Thumbnails")) {
            showThumbnails();
        }

        else {
            System.err.println("Unhandled action " + evt);
        }
    }

    public void focusGained (FocusEvent e) {
        Component last_focus = focus_window;
        focus_window = e.getComponent();
        if (show_controls && (last_focus == null))
            controls.repaint(0L, 0, 0, controls.getWidth(), controls.getHeight());
        if (last_focus == null)
            System.err.println("gained focus");
    }

    public void focusLost (FocusEvent e) {
        // System.err.println("Lost focus to " + e.getOppositeComponent() + ", " + (e.isTemporary() ? "temp" : "perm"));
        focus_window = e.getOppositeComponent();
        if (show_controls && (focus_window == null))
            controls.repaint(0L, 0, 0, controls.getWidth(), controls.getHeight());
        if (focus_window == null)
            System.err.println("lost focus");
    }

    public boolean focusOnOurApp () {
        return (focus_window != null);
    }

    private void fetchPagetext(int pageno, boolean redraw) {
        if (pagetext_loader != null) {
            PageTextSetter pts = new PageTextSetter(pageno, redraw);
            PageText p = (PageText) pagetext_loader.get(document_id, pageno, 0, pts);
            if (p != null)
                pts.call(p);
        }
    }

    public void setLocateHandler (DocViewerCallback arg) {
        locate_handler = arg;
    }

    public void setGoogleHandler (DocViewerCallback arg) {
        google_handler = arg;
    }

    public void setLogoImage (BufferedImage img) {
        small_uplib_logo = img;
    }

    public int getHumanPageNumber (int page_index) {
        int result = -1;
        if (page_number_data != null) {
            for (int i = 0;  i < page_number_data.size();  i++) {
                Object[] entry = (Object[]) page_number_data.get(i);
                if ((page_index >= ((Integer)entry[0]).intValue()) &&
                    (page_index <= ((Integer)entry[1]).intValue())) {
                    result = ((FormatBlankNumbers)(entry[2])).offset + page_index;
                    break;
                }
            }
        }
        if (result == -1)
            result = page_index + first_page_number;
        if (result < 1)
            result = -1;
        return result;
    }

    public String getPageNumberString (int page_no) {
        String result = null;
        if (page_number_data != null) {
            for (int i = 0;  i < page_number_data.size();  i++) {
                Object[] entry = (Object[]) page_number_data.get(i);
                if ((page_no >= ((Integer)entry[0]).intValue()) &&
                    (page_no <= ((Integer)entry[1]).intValue())) {
                    result = ((FormatBlankNumbers)(entry[2])).format(page_no);
                    break;
                }
            }
        }
        if (result == null) {
            int v = page_no + first_page_number;
            if (v == 0)
                v += 1;
            if (v < 0)
                result = RomanNumerals.toRoman(v - first_page_number + 1);
            else
                result = String.valueOf(v);
        }
        return result;
    }

    private BufferedImage getImageFromResources(String thisImageName) throws java.lang.IllegalArgumentException {
    	Class thisClass = this.getClass();
  	  InputStream thisStream = thisClass.getResourceAsStream(thisImageName);
  	  if (thisStream==null) {
  	  	String msg = "DocViewer was unable to find a needed image resource named ["+thisImageName+"].\n";
                msg += "Verify that your .jar files contain this resource.\n";
                msg += "Also, be sure to clear old versions of your .jar files from your cache and restart browsers.";
  	  	throw new java.lang.IllegalArgumentException(msg);
  	  }
  	  BufferedImage thisImage = null;
  	  try {
              thisImage = ImageIO.read(thisStream);
  	  } catch (IOException e) {
              String msg = "getImageFromResources can't read image file ["+thisImageName+"].  Error is:  " + e + ". ";
              String resourceName = thisClass.getResource(thisImageName).toString();
              msg = msg + "This resource WAS found however, at: ["+resourceName+"]";
              System.err.println(msg);
              throw new java.lang.IllegalArgumentException(msg);
  	  }
  	  return thisImage;
    }

    public void setTwoPage (boolean v) {

        if (v != two_page) {

            if (v && (!two_page)) {
                right_pageview = createPageview(this, page_width, page_height, RIGHT_PAGE_OFFSET, default_pageturn_animation_time);
                right_pageview.setBackground(BACKGROUND_COLOR);
                pageview_holder.add(right_pageview);
            } else if (two_page && !v) {
                pageview_holder.remove(right_pageview);
                right_pageview = null;
            }

            two_page = v;

            pageview_holder.invalidate();
            views_flipper.setPreferredSize(pageview_holder.getParent().getPreferredSize());
            invalidate();

            if (top_level_ancestor != null) {
                int titlebar_height = 0;
                Dimension d = getPreferredSize();
                if (top_level_ancestor instanceof RootPaneContainer) {
                    Dimension d2 = ((RootPaneContainer)top_level_ancestor).getContentPane().getPreferredSize();
                    titlebar_height = (top_level_ancestor.getHeight() - d2.height);
                }
                // System.err.println("Setting size to " + d.width + "x" + (d.height + titlebar_height));
                top_level_ancestor.setSize(d.width, d.height + titlebar_height);
            }
        }
    }

    public void setTopLevelWindow (Container w) {
        top_level_ancestor = w;
    }

    private void createGUI() {

        BufferedImage bookmark_image = null;

        our_cursor = new Cursor(Cursor.HAND_CURSOR);
        setCursor(our_cursor);
        EmacsKeymap.setupEmacsKeymap();

        Class thisClass = this.getClass();
        //next_arrow = this.getImageFromResources("/right-arrow-icon-alpha.png");
        //back_arrow = this.getImageFromResources("/left-arrow-icon-alpha.png");
        //small_uplib_logo = this.getImageFromResources("/applet-logo.png");
        button_up_background = this.getImageFromResources("/blank-button-unpressed.png");
        button_down_background = this.getImageFromResources("/blank-button-pressed.png");
        next_arrow = this.getImageFromResources("/right-arrow-label.png");
        back_arrow = this.getImageFromResources("/left-arrow-label.png");
        small_uplib_logo = this.getImageFromResources("/uplib-logo-label.png");
        eyeball_image = this.getImageFromResources("/eyeball.png");
        link_icon = this.getImageFromResources("/link-icon.png");
        note_corner_image = this.getImageFromResources("/note-corner.png");
        grayed_eyeball_image = this.getImageFromResources("/eyeball-grayed.png");
        thumbnails_image = this.getImageFromResources("/thumbnails.png");
        zoom_in_image = this.getImageFromResources("/zoom-in.png");
        search_icon_image = this.getImageFromResources("/search-icon.png");
        search_again_label = this.getImageFromResources("/search-again-label.png");
        small_inkpot_with_quill = this.getImageFromResources("/inkpot-with-quill-label.png");
        big_inkpot = this.getImageFromResources("/inkpot-label.png");
        postit_image = this.getImageFromResources("/postit-label.png");
        smalltext_image = this.getImageFromResources("/structured-selection-label.png");
        hotspots_image = this.getImageFromResources("/hotspots-label.png");
        snapback_left_image = this.getImageFromResources("/snapback-left.png");
        snapback_right_image = this.getImageFromResources("/snapback-right.png");
        doccontrol_top = this.getImageFromResources("/toolbar-top.png");
        doccontrol_center = this.getImageFromResources("/toolbar-center.png");
        doccontrol_bottom = this.getImageFromResources("/toolbar-bottom.png");
        page_edge_background_right_end = this.getImageFromResources("/page-edge-background-right-end.png");
        page_edge_background_center = this.getImageFromResources("/page-edge-background-center.png");
        page_edge_slider_top_right_end = this.getImageFromResources("/slider-top-right-end.png");
        page_edge_slider_top_center = this.getImageFromResources("/slider-top-center.png");
        page_edge_slider_bottom_right_end = this.getImageFromResources("/slider-bottom-right-end.png");
        page_edge_slider_bottom_center = this.getImageFromResources("/slider-bottom-center.png");
        bookmark_image = this.getImageFromResources("/small-ribbon-image.png");
        bookmark_drop_shadow = this.getImageFromResources("/bookmark-drop-shadow.png");
        purple_bookmark = this.getImageFromResources("/purple-ribbon.png");
        red_bookmark = this.getImageFromResources("/red-ribbon.png");
        green_bookmark = this.getImageFromResources("/green-ribbon.png");

        // make dimmed version of link icon
        link_icon_translucent = new BufferedImage(link_icon.getWidth(null), link_icon.getHeight(null), BufferedImage.TYPE_INT_ARGB);
        Graphics2D g = (Graphics2D) link_icon_translucent.getGraphics();
        g.setColor(TRANSPARENT);
        g.fillRect(0, 0, link_icon_translucent.getWidth(null), link_icon_translucent.getHeight(null));
        g.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC, 0.5f));
        g.drawImage(link_icon, 0, 0, null);
        g.dispose();

        // splash_image = this.getImageFromResources("/reader-logo.png");

        // do bookmarks
        int bookmark_pages[] = new int[] {-2, -2, -2};
        float bookmark_heights[] = new float[] {0, 0, 0};
        String[] bookmark_data = initial_bookmark_data.split(";");
        for (int i = 0;  i < bookmark_data.length;  i++) {
            System.err.println("bookmark_data[" + i + "] is " + bookmark_data[i]);
            String parts[] = bookmark_data[i].split(",");
            if (parts.length < 2)
                continue;
            bookmark_pages[i] = Integer.parseInt(parts[0]);
            bookmark_heights[i] = Float.parseFloat(parts[1]);
        }
        bookmarks = new Bookmark[3];
        bookmarks[0] = new Bookmark (this, 0, purple_bookmark,
                                     (bookmark_pages[0] < 0) ? page_count + 1 : bookmark_pages[0],
                                     (int)((bookmark_pages[0] == -2) ? (page_height - purple_bookmark.getHeight(null)) : (bookmark_heights[0] * page_height)));
        bookmarks[1] = new Bookmark (this, 1, green_bookmark,
                                     (bookmark_pages[1] < 0) ? page_count + 1 : bookmark_pages[1],
                                     (int)((bookmark_pages[1] == -2) ? (page_height - (2 * purple_bookmark.getHeight(null))) : (bookmark_heights[1] * page_height)));

        bookmarks[2] = new Bookmark (this, 2, red_bookmark,
                                     (bookmark_pages[2] < 0) ? page_count + 1 : bookmark_pages[2],
                                     (int) ((bookmark_pages[2] == -2) ? (page_height - (3 * purple_bookmark.getHeight(null))) : (bookmark_heights[2] * page_height)));


        widget_inkpots = new Inkpots();

        setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));
        Box leftizingContainer = Box.createHorizontalBox();
        Box pageContainer = Box.createVerticalBox();

        if (top_edge_type != PAGEEDGE_NONE) {
            top_page_edge = new PageEdge(this, page_width, page_height, top_edge_type);
            pageContainer.add (top_page_edge);
        } else {
            top_page_edge = null;
        }

        System.err.println("new Pageview (" + page_width + ", " + page_height + ", " + LEFT_PAGE_OFFSET + ", " + default_pageturn_animation_time + ")");

        left_pageview = createPageview(this, page_width, page_height, LEFT_PAGE_OFFSET, default_pageturn_animation_time);

        widget_inkpots.addListener(left_pageview);
        left_pageview.setBackground(BACKGROUND_COLOR);
        pageview_holder = new Box(BoxLayout.X_AXIS);
        pageview_holder.add(left_pageview);
        if (two_page) {
            right_pageview = createPageview(this, page_width, page_height, RIGHT_PAGE_OFFSET, default_pageturn_animation_time);
            right_pageview.setBackground(BACKGROUND_COLOR);
            widget_inkpots.addListener(right_pageview);
            pageview_holder.add(right_pageview);
        }
        pageContainer.add(pageview_holder);

        if (bottom_edge_type != PAGEEDGE_NONE) {
            bottom_page_edge = new PageEdge(this, page_width, page_height, bottom_edge_type);
            pageContainer.add(bottom_page_edge);
        } else {
            bottom_page_edge = null;
        }
        
        page_indicator = new JLabel("", JLabel.CENTER);
        page_indicator.setVisible(false);
        add(page_indicator);
        page_indicator.setLocation(0, (top_page_edge == null) ? 0 : top_page_edge.getHeight());

        views_flipper = new JPanel();
        // views_flipper.setBackground(getBackground());
        views_flipper.setBackground(BLACK);
        views_flipper.setLayout(new CardLayout());
        views_flipper.add(pageContainer, "pages");
        Dimension d = pageContainer.getPreferredSize();
        views_flipper.setPreferredSize(d);
        // views_flipper.setMinimumSize(d);
        views_flipper.setMaximumSize(d);

        annotation_span_controls = new AnnotationTimeControl(this);
        if (two_page) {
            right_pageview.add(annotation_span_controls);
        } else {
            left_pageview.add(annotation_span_controls);
        }
        Dimension x = annotation_span_controls.getPreferredSize();
        Date tomorrow = new Date();
        tomorrow.setTime(tomorrow.getTime() + (24 * 60 * 60 * 1000));
        Calendar then = Calendar.getInstance();
        then.set(2003, 1, 1);
        annotation_span_controls.setRange(then.getTime(), tomorrow);

        // zoom-in viewer

        zoomed_viewer = null;

        // thumbnails

        thumbnails = new DocThumbnails(this);
        JScrollPane jsp = new JScrollPane(thumbnails,
                                          JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED,
                                          JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
        if (jsp.getBorder() != null) {
            System.err.println(jsp.getBorder());
            System.err.println(jsp.getBorder().getBorderInsets(jsp));
            jsp.setBorder(null);
        }
        jsp.getVerticalScrollBar().setFocusable(false);
        jsp.getHorizontalScrollBar().setFocusable(false);
        thumbnails_viewport = jsp.getViewport();
        thumbnails_viewport.setFocusable(false);
        thumbnails_viewport.setBackground(BACKGROUND_COLOR);
        thumbnails_viewport.setScrollMode(JViewport.BLIT_SCROLL_MODE);
        jsp.setVisible(true);
        jsp.setFocusable(false);
        jsp.setBackground(BACKGROUND_COLOR);
        views_flipper.add(jsp, "thumbnails");

        // System.err.println("added thumbnails scrollpane");

        leftizingContainer.add(views_flipper);

        if (show_controls) {
            // Box controlsBox = Box.createVerticalBox();
            controls = createPageControl(this, show_scribbles, initial_selected_inkpot);
            Dimension d2 = new Dimension(30, getHeight());
            controls.setPreferredSize(d2);
            controls.setSize(d2);

            // controlsBox.add(controls);
            // controlsBox.add(createVerticalGlue());
            // leftizingContainer.add(controlsBox);
            leftizingContainer.add(controls);
        } else {
            controls = null;
        }

        leftizingContainer.add(Box.createHorizontalGlue());
        add(leftizingContainer);
        add(Box.createVerticalGlue());

        addKeyListener(this);
        // setFocusTraversalKeysEnabled(false);
        addFocusListener(this);
        addFocusListener(left_pageview);
        if (right_pageview != null)
            addFocusListener(right_pageview);
        if (!isFocusOwner()) {
            requestFocusInWindow();
        }

        setPageviewCursor(null);

        gui_created = true;
    }

    public void setBackground (Color c) {
        if (views_flipper != null)
            views_flipper.setBackground(c);
        super.setBackground(c);
    }

    public void finalize () throws Throwable {
        System.err.println("closing " + this.hashCode() + " (" + this + ")");

        left_pageview.finalize();
        if (two_page)
            right_pageview.finalize();
        if (note_saver != null)
            note_saver.flush();

        if (active_reading != null) {
            synchronized(active_reading) {
                active_reading.destroy();
                active_reading = null;
            }
        }
        if (scribble_handler != null) {
            scribble_handler.flush();
            scribble_handler = null;
        }

        if (note_saver != null) {
            note_saver.flush();
            note_saver = null;
        }

        if (hotspot_saver != null) {
            hotspot_saver.flush();
            hotspot_saver = null;
        }

        if ((!doc_closed) && (activity_logger != null) && activities_on) {
            activity_logger.call(new Activity(document_id, current_page_index, Activity.AC_CLOSED_DOC));
            activity_logger.flush();
            doc_closed = true;
        }
        removeFocusListener(this);
        setFocusable(false);
        removeKeyListener(this);

        super.finalize();
    }

    public void flushScribbleHandler() {
        try {
            if (scribble_handler != null)
                scribble_handler.flush();
        } catch (IOException x) {
            x.printStackTrace(System.err);
        }
    }

    private int getPageForPosition (int pos) {
        int i;
        for (i = 0;  i < page_count;  i++) {
            if (page_texts_starts[i] > pos)
                break;
            if (page_texts_starts[i] < 0)
                return -1;
        }
        return (i - 1);
    }

    public void setThumbnailSizeFactors (Dimension bt_translation, double bt_scaling, double st_scaling) {

        /*
        System.err.println("bt_translation is " + bt_translation.x + "," + bt_translation.y + ", bt_scaling is " + bt_scaling + ", st_scaling is " + st_scaling);

        page_image_scaling = bt_scaling;

        AffineTransform aft = new AffineTransform();
        aft.scale(st_scaling, st_scaling);
        aft.translate(bt_translation.getX(), bt_translation.getY());
        aft.scale(1.0D / bt_scaling, 1.0D / bt_scaling);
        big_to_small_transform = aft;

        aft = new AffineTransform();
        aft.scale(bt_scaling, bt_scaling);
        aft.scale(- bt_translation.getX(), - bt_translation.getY());
        aft.scale(1.0D / st_scaling, 1.0D / st_scaling);
        small_to_big_transform = aft;
        */
    }

    public void setNoteSaver (AnnotationStreamHandler s) {
        note_saver = s;
    }

    public void setNoteLoader (SoftReferenceCache c) {
        note_loader = c;
    }

    public void setClipboard (Clipboard c) {
        clipboard = c;
    }

    private static class FormatBlankNumbers {
        public int offset = 0;
        FormatBlankNumbers (int fp) {
            offset = fp;
        }
        FormatBlankNumbers () {
        }
        String format (int page_index) {
            return "";
        }
    }

    private static class FormatRomanNumbers extends FormatBlankNumbers {
        FormatRomanNumbers(int fp) {
            super(fp);
        }
        String format (int page_index) {
            return RomanNumerals.toRoman(page_index + offset);
        }
    }

    private static class FormatDecimalNumbers extends FormatBlankNumbers {
        FormatDecimalNumbers(int fp) {
            super(fp);
        }
        String format (int page_index) {
            return Integer.toString(page_index + offset);
        }
    }

    private static ArrayList dissectPageNumberData (String pnd) {

        if ((pnd == null) || (pnd.length() == 0))
            return null;
        try {
            System.err.println("page number data is " + pnd);
            ArrayList result = new ArrayList();
            Matcher m = PAGERANGES.matcher(pnd);
            if (m.matches()) {
                int first_page = Integer.parseInt(m.group(1));
                int last_page = Integer.parseInt(m.group(3));
                result.add(new Object[] { new Integer(0), new Integer(last_page - first_page),
                                            new FormatDecimalNumbers(first_page) });
            } else {
                String[] parts = pnd.split(";");
                for (int i = 0;  i < parts.length;  i++) {
                    String[] subparts = parts[i].split(",");
                    if (subparts.length != 3)
                      throw new Exception("badly formatted page-number data:  \"" + pnd + "\":  " + subparts.length + " subparts in part " + i + " (" + parts[i] + ")");
                    int first_page = 1;
                    int range_first = 0;
                    int range_last = 0;
                    if (subparts[1].length() > 0)
                      first_page = Integer.parseInt(subparts[1]);
                    String[] pagerange = subparts[2].split("-");
                    if (pagerange.length == 1) {
                        range_first = Integer.parseInt(subparts[2]);
                        range_last = range_first;
                    } else {
                        range_first = Integer.parseInt(pagerange[0]);
                        range_last = Integer.parseInt(pagerange[1]);
                    }
                    if (subparts[0].toLowerCase().equals("d"))
                      result.add(new Object[] { new Integer(range_first), new Integer(range_last),
                                                  new FormatDecimalNumbers(first_page - range_first) });
                    else if (subparts[0].toLowerCase().equals("b"))
                      result.add(new Object[] { new Integer(range_first), new Integer(range_last),
                                                  new FormatBlankNumbers() });
                    else if (subparts[0].toLowerCase().equals("r"))
                      result.add(new Object[] { new Integer(range_first), new Integer(range_last),
                                                  new FormatRomanNumbers(first_page - range_first) });
                    else
                      throw new Exception("Bad page-number type \"" + subparts[0] + "\"");
                }
            }
            return result;
        } catch (Exception x) {
            x.printStackTrace(System.err);
            return null;
        }
    }

    public void showDialogOnDrop (boolean state) {
        show_dialog_on_drop = state;
    }

    public void setHotspotSaver(AnnotationStreamHandler saver) {
        hotspot_saver = saver;
    }

    public void setHiResPageImageLoader (SoftReferenceCache loader, double pt_scaling,
                                         Dimension pt_translation, int hires_dpi) {
        hires_page_image_loader = loader;
        zoomed_viewer = new ZoomedViewer(this, pt_scaling, pt_translation, hires_dpi);
        zoomed_viewer.setPreferredSize(views_flipper.getPreferredSize());
        views_flipper.add(zoomed_viewer, "zoom-in");
    }

    public DocViewer(SoftReferenceCache page_image_loader_p,
                     SoftReferenceCache thumbnail_image_loader_p,
                     String document_title_p,
                     String document_id_p,
                     DocViewerCallback logo_url_p,
                     int page_count_p,
                     int first_page_number_p,
                     String page_number_data_p,
                     int current_page_p,
                     Dimension page_size,
                     Dimension thumbnail_size,
                     boolean show_controls_p,
                     int top_edge_p,
                     int bottom_edge_p,
                     boolean two_pages_p,
                     Scribble[] scribbles_p,
                     AnnotationStreamHandler scribble_handler_p,
                     HotSpot[] hotspots_p,
                     DocViewerCallback activity_logger_p,
                     boolean activities_on_p,
                     boolean annotations_on_p,
                     int initial_annotation_inkpot_p,
                     String bookmark_data_p,
                     int pageturn_animation_time,
                     int splash_page_period_p,
                     SoftReferenceCache pagetext_loader_p,
                     DocViewerCallback page_opener_p,
                     AnnotationStreamHandler note_saver_p,
                     SoftReferenceCache note_loader_p) {

        page_image_loader = page_image_loader_p;
        thumbnail_image_loader = thumbnail_image_loader_p;
        hires_page_image_loader = null;
        document_title = document_title_p;
        document_properties = new TreeMap();
        if (document_title != null)
            document_properties.put("title", document_title);
        document_id = document_id_p;
        document_properties.put("id", document_id);
        logo_url = logo_url_p;
        page_count = page_count_p;
        first_page_number = first_page_number_p;
        if (page_number_data_p != null)
            page_number_data = dissectPageNumberData(page_number_data_p);
        else
            page_number_data = null;
        current_page_index = current_page_p;
        snapback_page = -1;
        page_width = page_size.width;
        page_height = page_size.height;
        show_controls = show_controls_p;
        top_edge_type = top_edge_p;
        bottom_edge_type = bottom_edge_p;
        scribble_handler = scribble_handler_p;
        two_page = two_pages_p;
        thumbnail_width = thumbnail_size.width;
        thumbnail_height = thumbnail_size.height;
        activity_logger = activity_logger_p;
        activities_on = activities_on_p;
        initial_selected_inkpot = initial_annotation_inkpot_p;
        annotation_span_end = null;
        annotation_span_start = null;
        if (bookmark_data_p == null)
            initial_bookmark_data = ";;;";
        else
            initial_bookmark_data = bookmark_data_p;
        default_pageturn_animation_time = pageturn_animation_time;
        pagetext_loader = pagetext_loader_p;
        System.err.println("pagetext_loader is " + pagetext_loader);
        if (splash_page_period_p >= 0)
            splash_page_period = splash_page_period_p;

        page_texts_starts = new int[page_count];
        strokes = new ArrayList(page_count);
        hotspots = new ArrayList(page_count);
        note_sheets = new ArrayList(page_count);
        note_loader = note_loader_p;
        note_saver = note_saver_p;
        for (int i = 0;  i < page_count;  i++) {
            page_texts_starts[i] = -1;
            strokes.add(new ArrayList());
            hotspots.add(new ArrayList());
            note_sheets.add(new Notesheets(0, i));
        }

        if (scribbles_p != null) {
            for (int i = 0;  i < scribbles_p.length;  i++) {
                ((ArrayList) strokes.get(scribbles_p[i].pageIndex())).add(scribbles_p[i]);
            }
        }

        if (hotspots_p != null) {
            for (int i = 0;  i < hotspots_p.length;  i++) {
                try {
                    HotSpot h = hotspots_p[i];
                    ((ArrayList) hotspots.get(h.pageIndex())).add(h);
                    // System.err.println("added hotspot " + hotspots_p[i]);
                } catch (Exception e) {
                    // don't let bad hotspots abort document opening
                    e.printStackTrace(System.err);
                }
            }
        }
        theRepositoryURL = null;
        selection = createSelectionState();

        show_scribbles = annotations_on_p;
        page_opener = page_opener_p;

        show_hotspots = false;

        show_parts_of_speech = false;

        top_level_ancestor = null;
        views_flipper = null;

        // cache resources for first page
        setPage (current_page_index, false);

        os_name = System.getProperty("os.name");

        // see if we can access the clipboard
        SecurityManager security = System.getSecurityManager();
        if (security != null) {
            try {
                security.checkSystemClipboardAccess();
                // if that succeeded, we can read it
                clipboard = new WrappedSystemClipboard();
            } catch (SecurityException x) {
                clipboard = null;
            } catch (HeadlessException x) {
                clipboard = null;
            }
        } else {
            try {
                clipboard = new WrappedSystemClipboard();
            } catch (HeadlessException x) {
                clipboard = null;
            }
        }

        // pre-load the document icon for this document
        thumbnail_image_loader.get(document_id, -1, 0, null);

        //Execute a job on the event-dispatching thread:
        //creating this applet's GUI.
        try {
	    if (!javax.swing.SwingUtilities.isEventDispatchThread()) {
		javax.swing.SwingUtilities.invokeAndWait(new Runnable() {
		    public void run() {
		        createGUI();
		    }
		});
	    }
	    else {
	        createGUI();
	    }
        } catch (Exception e) { 
            System.err.println("createGUI didn't successfully complete:  " + e);
            e.printStackTrace(System.err);
        }

        System.err.println("GUI created");
        setFocusable(true);
        setVisible(true);

        if (!isFocusOwner())
            requestFocusInWindow();

        try {
            scaled_jcomponent_class = Class.forName("com.parc.uplib.readup.widget.ResizableDocViewer");
            content_pane_class = Class.forName("com.parc.uplib.readup.widget.ScaledJComponent$ContentPane");
            // System.err.println("scaled_jcomponent_class is " + scaled_jcomponent_class.getName());
            // System.err.println("content_pane_class is " + content_pane_class.getName());
        } catch (java.lang.ClassNotFoundException x) {
            // expected, if those resizing classes aren't used -- ignore it
        } catch (RuntimeException x) {
            System.err.println("Ignoring exception " + x);
        } catch (Exception x) {
            System.err.println("Ignoring exception " + x);
        }
    }
}
