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

/*
 * UpLibDropTarget.java is a portable application that allows files
 * to be dropped on top of it, upon which it submits them to the UpLib
 * repository.
 */

package com.parc.uplib.portal;

import java.awt.CardLayout;
import java.awt.Color;
import java.awt.Container;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.Frame;
import java.awt.Graphics;
import java.awt.Graphics2D;
import java.awt.GraphicsConfiguration;
import java.awt.Point;
import java.awt.RenderingHints;
import java.awt.datatransfer.DataFlavor;
import java.awt.datatransfer.Transferable;
import java.awt.datatransfer.UnsupportedFlavorException;
import java.awt.dnd.DnDConstants;
import java.awt.dnd.DropTarget;
import java.awt.dnd.DropTargetDragEvent;
import java.awt.dnd.DropTargetDropEvent;
import java.awt.dnd.DropTargetEvent;
import java.awt.dnd.DropTargetListener;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.awt.event.MouseEvent;
import java.awt.geom.AffineTransform;
import java.awt.image.AffineTransformOp;
import java.awt.image.BufferedImage;
import java.io.BufferedReader;
import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.net.URL;
import java.util.Collections;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.Set;
import java.util.Vector;
import java.util.logging.Logger;
import java.util.regex.Pattern;

import javax.imageio.ImageIO;
import javax.swing.AbstractButton;
import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.ButtonGroup;
import javax.swing.ImageIcon;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JComponent;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JPasswordField;
import javax.swing.JRadioButton;
import javax.swing.JScrollPane;
import javax.swing.JSlider;
import javax.swing.JSpinner;
import javax.swing.JTextArea;
import javax.swing.JTextField;
import javax.swing.SpinnerNumberModel;
import javax.swing.SwingConstants;
import javax.swing.TransferHandler;
import javax.swing.border.Border;
import javax.swing.border.CompoundBorder;
import javax.swing.border.EmptyBorder;
import javax.swing.border.LineBorder;

import com.parc.uplib.util.Configurator;
import com.parc.uplib.util.ErrorDialog;
import com.parc.uplib.util.LogStackTrace;
import com.parc.uplib.util.WorkPopup;
import com.parc.uplib.util.WorkThread;

public class Portal extends JPanel implements WorkThread.DialogCounter, DropTargetListener {

    private final static int N_DIVISIONS = 60;

    private final static int DROPSTATE_NO_DROP = 1;
    private final static int DROPSTATE_GOOD_DROP = 2;
    private final static int DROPSTATE_BAD_DROP = 3;
    
    private static class UploadFilenameFilter implements java.io.FilenameFilter {
        public UploadFilenameFilter () {
        }
        public boolean accept (File dir, String name) {
            return (! (name.startsWith(".") || name.startsWith("#")));
        }
    }

    private final static UploadFilenameFilter UPLOAD_FILENAME_FILTER = new UploadFilenameFilter();

    final static Color BACKGROUND_COLOR = new Color(.878f, .941f, .973f);
    final static Color TOOLS_COLOR = new Color(.754f, .848f, .910f);
    final static Color UPLIB_ORANGE = new Color(.937f, .157f, .055f);
    final static Color WHITE = new Color(1.0f, 1.0f, 1.0f);
    final static Color BLACK = new Color(0.0f, 0.0f, 0.0f);
    final static Color BORDER_GRAY = new Color(0.7f, 0.7f, 0.7f);

    protected static Pattern quotes = Pattern.compile("'");
    protected static String addDocumentProgramString = null;
    protected static String getDocumentProgramString = null;
    private static String uplibVersion = null;
    private static String drycleanURL = null;

    private static BufferedImage logoImage = null;
    private static ImageIcon uplib_favicon = null;
    private static BufferedImage swirlImage = null;
    private static BufferedImage docImage = null;
    private static ImageIcon docIcon = null;
    private static BufferedImage badDropImage = null;
    private static BufferedImage goodDropImage = null;
    private static BufferedImage[] rotatedSwirlImages = new BufferedImage[N_DIVISIONS];
    private static BufferedImage[] rotatedDocImages = new BufferedImage[N_DIVISIONS];
    private static RenderingHints logo_rendering_hints = null;
    private static PortalTransferHandler pth = null;

    private static Runtime theRuntime = Runtime.getRuntime();

    private static boolean is_mac = false;
    private static boolean is_windows = false;

    private static float doc_size_increment = 1.0f;

    // --------------------- private instance variables -------------------

    // logger to send messages to
    private Logger logger;

    // the rotated swirl image that's current
    private int which_swirl_image = 0;
    private int which_doc_image = 0;
    // the size of the spinning document icon, if displayed
    private float doc_size = 0.0f;

    // "sticky" search and upload settings
    private String filepath = null;
    private String query = null;
    private File   currentDir = null;
    private int rememberedMinScore = 25;
    private String theRepoURL = null;
    private String theRepoPassword = null;
    private String retrieval_format = null;
    private String retrieval_action = null;
    private boolean show_popup = true;
    
    // lists of currently active uploads and searches
    private java.util.List uploads;
    private java.util.List searches;

    // current state of drop acceptance
    private int drop_status = DROPSTATE_NO_DROP;

    // is there a query dialog currently being displayed?
    private int dialog_showing = 0;

    // should swirling be used in display of portal?
    private boolean do_swirl = true;

    // list of listeners to notify when some action is performed
    private LinkedList listeners;

    static {
        try {
            is_mac = System.getProperty("os.name").toLowerCase().startsWith("mac");
            is_windows = System.getProperty("os.name").toLowerCase().startsWith("win");

            findResources();

        } catch (Exception x) {
            LogStackTrace.severe(Logger.getLogger("global"), "Can't load resources needed for Portal widget", x);
        }
    }

    private static class AnimationThread extends Thread {

        private Set portals;
        private boolean exiting;

        public AnimationThread () {
            super("com.parc.uplib.portal.Portal.AnimationThread");
            setDaemon(true);
            portals = new HashSet();
            exiting = false;
        }

        synchronized public void exit () {
            exiting = true;
        }

        public void run () {

            // set a timer to periodically check the number of active uploads
            // and update the display

            int loop_counter = 0;
            Iterator portals_iterator;
            Portal portal;

            while (! exiting) {

                try {
                    Thread.sleep(100);  // sleep 100 ms
                } catch (InterruptedException x) {
                    // no big deal
                };

                loop_counter += 1;

                portals_iterator = portals.iterator();

                while (portals_iterator.hasNext()) {

                    portal = (Portal) (portals_iterator.next());
                    java.util.List current_uploads = portal.currentUploads();
                    java.util.List current_searches = portal.currentSearches();

                    // go through the current_uploads list and
                    // current_searches list and check to see if there are any
                    // dead soldiers
                    for (int i = 0;  i < current_uploads.size(); ) {
                        UploadThread t = (UploadThread) current_uploads.get(i);
                        int s = t.getWorkerState();
                        if (s == WorkThread.PROCSTATE_COMPLETE) {
                            current_uploads.remove(t);
                            int stat = t.exitval;
                            String filename = t.filename;
                            if (filename != null)
                                portal.notifyActionListeners(new DocumentUploaded(portal, filename, stat));
                            portal.repaint();
                        } else if (s == WorkThread.PROCSTATE_INITIALIZATION) {
                            i += 1;
                        } else {
                            i += 1;
                        }
                    }

                    for (int i = 0;  i < current_searches.size(); ) {
                        SearchThread t = (SearchThread) current_searches.get(i);
                        int s = t.getWorkerState();
                        if (s == WorkThread.PROCSTATE_COMPLETE) {
                            current_searches.remove(t);
                            String query = portal.getQuery();
                            int stat = t.exitval;
                            if (query != null)
                                portal.notifyActionListeners(new SearchPerformed(portal, query));
                            portal.repaint();
                        } else {
                            i += 1;
                        }
                    }

                    portal.incrementSwirlImage();
                }
            }

        }

        private static AnimationThread the_animation_thread = null;

        public static void addPortal (Portal p) {
            synchronized(AnimationThread.class) {
                if (the_animation_thread != null)
                    the_animation_thread.portals.add(p);
            }
        }

        public static void removePortal (Portal p) {
            synchronized(AnimationThread.class) {
                if (the_animation_thread != null)
                    the_animation_thread.portals.remove(p);
            }
        }

        public static synchronized void ensurePortalAnimationThread () {
            synchronized (AnimationThread.class) {
                if (the_animation_thread == null) {
                    the_animation_thread = new AnimationThread();
                    the_animation_thread.setDaemon(true);
                    the_animation_thread.start();
                }
            }
        }
    }

    public static class StickyPropertySet extends java.awt.event.ActionEvent {
        final static String ACTION_NAME = "StickyPropertySet";
        String name;
        String value;
        public StickyPropertySet (Portal p, String pname, String pvalue) {
            super(p, ActionEvent.ACTION_PERFORMED, ACTION_NAME);
            this.name = pname;
            this.value = pvalue;
        }
        public String getName () {
            return name;
        }
        public String getValue() {
            return value;
        }
    }

    public static class DocumentUploaded extends java.awt.event.ActionEvent {
        final static String ACTION_NAME = "DocumentUploaded";
        String document;
        int status;
        public DocumentUploaded (Portal p, String docpath, int status) {
            super(p, ActionEvent.ACTION_PERFORMED, ACTION_NAME);
            this.document = docpath;
            this.status = status;
        }
        public String getDocument () {
            return document;
        }
        public int getStatus() {
            return status;
        }
    }

    public static class SearchPerformed extends java.awt.event.ActionEvent {
        final static String ACTION_NAME = "SearchPerformed";
        String query;
        public SearchPerformed (Portal p, String query) {
            super(p, ActionEvent.ACTION_PERFORMED, ACTION_NAME);
            this.query = query;
        }
        public String getQuery () {
            return query;
        }
    }

    private class GetDocumentPopup extends WorkPopup
        implements ActionListener {

        String myRepoURL;
        String myRepoPassword;
        String format;
        String action;

        JTextField      repository_widget;
        JCheckBox       stickyrepo_widget;
        JPasswordField  password_widget;
        JTextField      query_widget;
        JTextField      action_widget;
        JSlider         minscore_widget;
        JSpinner        format_widget;
        JCheckBox       pickall_widget;
        private ButtonGroup format_buttons;

        JButton         submit_button;
        JButton         cancel_button;

        private String  myquery;

        GetDocumentPopup (Frame frame, String q, String repoURL, String repoPassword, String format, String action) {
            super (frame, false);
            myquery = q;
            myRepoURL = repoURL;
            myRepoPassword = repoPassword;
            this.action = action;
            this.format = format;
            // getLogger().info("URL is " + repoURL + ", password is " + repoPassword);
            finish();
        }

        public void initValues() {
        }

        public String getFormat() {
            return format_buttons.getSelection().getActionCommand();
        }

        public void setFormat(String f) {
            Enumeration e = format_buttons.getElements();
            while (e.hasMoreElements()) {
                AbstractButton b = (AbstractButton) (e.nextElement());
                format_buttons.setSelected(b.getModel(), b.getActionCommand().equals(f));
            }
        }

        public void initComponents() {
            Box s;
            JLabel f;

            setTitle("Find UpLib Document");

            Box b = Box.createVerticalBox();
            b.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

            Container contents = getContentPane();

            Font bold = new Font(null, Font.BOLD, contents.getFont().getSize());
            Font italic = new Font(null, Font.ITALIC, contents.getFont().getSize());

            s = Box.createHorizontalBox();
            f = new JLabel("Query");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            s.add(f);
            query_widget = new JTextField((myquery == null) ? "" : myquery);
            query_widget.addActionListener(this);
            query_widget.setActionCommand("queried");
            initialfocus = query_widget;
            s.add(Box.createHorizontalStrut(5));
            s.add(query_widget);
            s.add(Box.createHorizontalStrut(5));
            Border outer = new LineBorder(UPLIB_ORANGE, 3);
            Border inner = new EmptyBorder(5, 5, 5, 5);
            s.setBorder(new CompoundBorder(outer, inner));
            b.add(s);

            b.add(Box.createVerticalStrut(20));

            s = Box.createHorizontalBox();
            f = new JLabel("Repository");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            s.add(f);
            repository_widget = new JTextField((myRepoURL == null) ? "" : myRepoURL);
            s.add(Box.createHorizontalStrut(5));
            s.add(repository_widget);
            s.add(Box.createGlue());
            b.add(s);

            s = Box.createHorizontalBox();
            f = new JLabel("Password");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            s.add(f);
            password_widget = new JPasswordField((myRepoPassword == null) ? "" : myRepoPassword);
            s.add(Box.createHorizontalStrut(5));
            s.add(password_widget);
            s.add(Box.createHorizontalStrut(5));
            s.add(Box.createGlue());
            stickyrepo_widget = new JCheckBox("Remember", (myRepoURL != null) || (myRepoPassword != null));
            s.add(stickyrepo_widget);
            s.add(Box.createGlue());
            b.add(s);

            b.add(Box.createVerticalStrut(20));

            s = Box.createHorizontalBox();
            f = new JLabel("Format");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            s.add(f);

            String[] formats = new String[] {"html", "pdf", "images", "text", "icon", "metadata", "uplib"};

            //            s.add(Box.createHorizontalStrut(5));
            // format_widget = new JSpinner(new SpinnerListModel(formats));
            // ((JSpinner.ListEditor)format_widget.getEditor()).getTextField().setEditable(false);
            // s.add(format_widget);

            format_buttons = new ButtonGroup();
            JRadioButton first = null, selected = null;
            for (int i = 0;  i < formats.length;  i++) {
                Box s2 = Box.createHorizontalBox();
                JRadioButton r = new JRadioButton(formats[i]);
                if (i == 0)
                    first = r;
                r.setActionCommand(formats[i]);
                format_buttons.add(r);
                if ((format != null) && format.equals(formats[i])) {
                    selected = r;
                    r.setSelected(true);
                }
                s2.add(r);
                s2.setBorder(new LineBorder(BORDER_GRAY, 1));
                if (i > 0) {
                    s.add(Box.createHorizontalStrut(2));
                }
                s.add(s2);
            }
            if (selected == null)
                first.setSelected(true);
            
            b.add(s);
            b.add(Box.createVerticalStrut(5));

            s = Box.createHorizontalBox();
            f = new JLabel("Action");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            s.add(f);
            action_widget = new JTextField((action != null) ? action : "(default for format)");
            s.add(Box.createHorizontalStrut(5));
            s.add(action_widget);
            b.add(s);

            b.add(Box.createVerticalStrut(10));

            s = Box.createHorizontalBox();
            f = new JLabel("Min score");
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            s.add(f);
            // minscore_widget = new JSpinner(new SpinnerNumberModel(.75d, 0d, 1d, 0.05d));
            minscore_widget = new JSlider(0, 100, rememberedMinScore);
            s.add(minscore_widget);
            s.add(Box.createHorizontalStrut(10));
            pickall_widget = new JCheckBox("Show All", false);
            s.add(pickall_widget);
            b.add(s);

            s = Box.createHorizontalBox();
            s.add(Box.createHorizontalStrut(10));
            cancel_button = new JButton("Cancel");
            cancel_button.setActionCommand("cancel");
            cancel_button.addActionListener(this);
            s.add(cancel_button);

            f = new JLabel ("<html><b>UpLib " + uplibVersion + "</b> &middot; <small>PARC / ISL</small></html>",
                            uplib_favicon, SwingConstants.CENTER);
            f.setFont(new Font("Serif", Font.PLAIN, 14));
            f.setIconTextGap(10);
            f.setForeground(WHITE);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));

            s.add(Box.createGlue());
            s.add(f);
            s.add(Box.createGlue());

            submit_button = new JButton("Submit");
            submit_button.setActionCommand("submit");
            submit_button.addActionListener(this);
            s.add(submit_button);
            s.add(Box.createHorizontalStrut(10));
            b.add(s);

            contents.add(b);
        }

        public void actionPerformed(ActionEvent e) {
            if ("submit".equals(e.getActionCommand())) {
                submitted = true;
                setVisible(false);
            }
            else if ("cancel".equals(e.getActionCommand())) {
                cancelled = true;
                setVisible(false);
            }
            else if ("queried".equals(e.getActionCommand())) {
                submitted = true;
                setVisible(false);
            }
            else
                getLogger().info("Unexpected Action " + e);
        }
    }

    private class SearchThread extends WorkThread {
        
        private String[] UpLibGetDocumentExitVals = new String[] {
            "Error of some kind",
            "Invalid or missing password supplied",
            "No results matching query",
            "No results above score threshold",
            "Bad command-line option specified",
            "Couldn't communicate with the specified repository",
        };

        private static final int GETDOC_GENERAL_ERROR = 1;
        private static final int GETDOC_UNAUTHORIZED = 2;
        private static final int GETDOC_NO_RESULTS = 3;
        private static final int GETDOC_NO_RESULTS_ABOVE_THRESHOLD = 4;
        private static final int GETDOC_BAD_OPTION = 5;
        private static final int GETDOC_COMM_ERROR = 6;

        private Portal portal;

        public SearchThread (Portal top) {
            super(top.getLogger(), top);
            portal = top;
        }

        public void createDialog() throws WorkThread.DialogError {
            GraphicsConfiguration gc = portal.getGraphicsConfiguration();
            dialog = new GetDocumentPopup(new JFrame("Get Document", gc), query, theRepoURL, theRepoPassword,
                                          retrieval_format, retrieval_action);
            Dimension d = dialog.getSize();
            if (d.width < 300)
                dialog.setSize(new Dimension(300, d.height));
            Point p = WorkPopup.bestLocation(dialog, gc.getBounds(), portal.getTopLevelAncestor().getBounds());
            if (p != null)
                dialog.setLocation(p);
        }

        public Vector getCommandLine() {

            GetDocumentPopup theDialog = (GetDocumentPopup) dialog;

            thePassword = new String(theDialog.password_widget.getPassword());

            query = theDialog.query_widget.getText();
            String theRepository = theDialog.repository_widget.getText();
            retrieval_format = theDialog.getFormat();
            retrieval_action = theDialog.action_widget.getText();
            rememberedMinScore = theDialog.minscore_widget.getValue();
            float minscore = rememberedMinScore/100.0f;

            if (theDialog.stickyrepo_widget.isSelected()) {
                setRepoURLAndPassword(theRepository, thePassword);
            } else {
                setRepoURLAndPassword(null, null);
            }

            Vector c = new Vector();
            c.add(getDocumentProgramString);
            if (theDialog.pickall_widget.isSelected())
                c.add("--pickall");
            else
                c.add("--pickone");
            if (theRepository.length() > 0) {
                c.add("--repository=" + theRepository);
            };
            if (thePassword.equals("(none)") || thePassword.length() == 0) {
                // do something somewhere
                c.add("--nopassword");
            } else {
                addEnvironmentProperty("UPLIB_PASSWORD", thePassword);
            }
            if (!(retrieval_format == null || retrieval_format.length() == 0 || retrieval_format.equals("(default)")))
                c.add("--format=" + retrieval_format);
            if (!(retrieval_action == null || retrieval_action.length() == 0 || retrieval_action.equals("(default for format)")))
                c.add("--action=" + retrieval_action);
            c.add("--minscore=" + minscore);

            c.add(quoteit(query));

            return c;
        }

        private String figureStatus (int exitval) {
            if (exitval < 1)
                return null;
            else if (exitval == GETDOC_UNAUTHORIZED) {
                if (thePassword.equals("(none)") || thePassword.length() == 0)
                    return "No password supplied.";
                else
                    return "Invalid password supplied.";
            } else if (exitval == GETDOC_COMM_ERROR) {
                return "Couldn't communicate with the UpLib repository.";
            } else if (exitval > UpLibGetDocumentExitVals.length)
                return UpLibGetDocumentExitVals[0];
            else
                return UpLibGetDocumentExitVals[exitval-1];
        }

        public void finalCleanup() {
            if (!cancelled) {
                if (exitval != 0) {
                    String msg = figureStatus(exitval);
                    ErrorDialog.say(msg, (exitval == 1) ? error_output.toString() : null, "Search:  " + query);
                    // JOptionPane.showMessageDialog(null, msg, "Search:  " + query, JOptionPane.ERROR_MESSAGE);
                } else {
                    query = null;
                }
            }
        }

    }

    private class SubmissionParameterPopup extends WorkPopup
        implements ActionListener {

        String theFilename;
        String myRepoURL;
        String myRepoPassword;

        JTextField     repository_widget;
        JCheckBox      stickyrepo_widget;
        JPasswordField password_widget;
        JTextField     categories_widget;
        JTextField     authors_widget;
        JTextField     title_widget;
        JTextField     keywords_widget;
        JTextField     date_widget;
        JTextField     source_widget;
        JSpinner       dpi_widget;
        ButtonGroup    dpi_buttons;

        JCheckBox      monochrome_widget;
        JCheckBox      notext_widget;
        JCheckBox      keepblankpages_widget;
        JCheckBox      dryclean_widget;

        JButton        submit_button;
        JButton        cancel_button;

        SubmissionParameterPopup (Frame frame, String filename, String repoURL, String repoPassword) {
            super (frame, false);
            theFilename = filename;
            myRepoURL = repoURL;
            myRepoPassword = repoPassword;
            finish();
        }

        public int getDPI () {
            String dpi = dpi_buttons.getSelection().getActionCommand();
            if (dpi == "auto")
                return 0;
            else if (dpi == "75")
                return 75;
            else if (dpi == "other")
                return ((SpinnerNumberModel)(dpi_widget.getModel())).getNumber().intValue();
            return 0;
        }

        private JTextField addField (String fieldname, Box b, Font font, Vector labels) {

            JLabel f;
            JTextField w;
            Box s;

            s = Box.createHorizontalBox();
            f = new JLabel(fieldname);
            if (font != null)
                f.setFont(font);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            w = new JTextField();
            s.add(Box.createHorizontalStrut(5));
            s.add(Box.createGlue());
            s.add(w);
            s.add(Box.createGlue());
            b.add(s);

            return w;
        }

        public void initValues() {
        }

        public void initComponents() {
            Box s, s2, s3;
            JLabel f;
            Vector labels = new Vector();

            setTitle("UpLib Upload Parameters");

            Box b = Box.createVerticalBox();
            b.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

            Container contents = getContentPane();

            Font bold = new Font(null, Font.BOLD, contents.getFont().getSize());
            Font italic = new Font(null, Font.ITALIC, contents.getFont().getSize());

            s = Box.createHorizontalBox();
            s.add(Box.createHorizontalStrut(10));
            s.add(Box.createGlue());
            f = new JLabel();
            f.setFont(bold);
            if (theFilename.length() > 100)
                f.setText(theFilename.substring(0,50) + "..." + theFilename.substring(theFilename.length()-50, theFilename.length()));
            else
                f.setText(theFilename);
            s.add(f);
            s.add(Box.createGlue());
            s.add(Box.createHorizontalStrut(10));
            b.add(s);              

            b.add(Box.createVerticalStrut(10));

            s = Box.createHorizontalBox();
            f = new JLabel("Repository");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            repository_widget = new JTextField((myRepoURL == null) ? "" : myRepoURL);
            s.add(Box.createHorizontalStrut(5));
            s.add(repository_widget);
            s.add(Box.createGlue());
            b.add(s);

            s = Box.createHorizontalBox();
            f = new JLabel("Password");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            password_widget = new JPasswordField((myRepoPassword == null) ? "" : myRepoPassword);
            s.add(Box.createHorizontalStrut(5));
            s.add(Box.createGlue());
            s.add(password_widget);
            s.add(Box.createHorizontalStrut(5));
            stickyrepo_widget = new JCheckBox("Remember", (myRepoURL != null) || (myRepoPassword != null));
            s.add(stickyrepo_widget);
            s.add(Box.createGlue());
            b.add(s);

            b.add(Box.createVerticalStrut(10));

            title_widget = addField("Title", b, italic, labels);
            initialfocus = title_widget;
            authors_widget = addField("Authors", b, italic, labels);
            date_widget = addField("Date", b, italic, labels);
            categories_widget = addField("Categories", b, italic, labels);
            keywords_widget = addField("Keywords", b, italic, labels);
            source_widget = addField("Source", b, italic, labels);

            b.add(Box.createVerticalStrut(10));

            s = Box.createHorizontalBox();
            f = new JLabel("DPI:");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            s.add(f);
            dpi_buttons = new ButtonGroup();
            JRadioButton r = new JRadioButton("auto");
            r.setActionCommand("auto");
            dpi_buttons.add(r);
            r.setSelected(true);
            s2 = Box.createHorizontalBox();
            s3 = Box.createVerticalBox();
            s3.add(Box.createGlue());
            s3.add(r);
            s3.add(Box.createGlue());
            s2.add(s3);
            s2.setBorder(new LineBorder(BORDER_GRAY, 1));
            s.add(s2);
            s.add(Box.createHorizontalStrut(3));
            r = new JRadioButton("75");
            r.setActionCommand("75");
            dpi_buttons.add(r);
            s2 = Box.createHorizontalBox();
            s3 = Box.createVerticalBox();
            s3.add(Box.createGlue());
            s3.add(r);
            s3.add(Box.createGlue());
            s2.add(s3);
            s2.setBorder(new LineBorder(BORDER_GRAY, 1));
            s.add(s2);
            s.add(Box.createHorizontalStrut(3));
            s2 = Box.createHorizontalBox();
            r = new JRadioButton("other");
            r.setActionCommand("other");
            dpi_buttons.add(r);
            s2.add(r);
            dpi_widget = new JSpinner(new SpinnerNumberModel(400, 50, 600, 5));
            s2.add(dpi_widget);
            s2.setBorder(new LineBorder(BORDER_GRAY, 1));
            s.add(s2);
            s.add(Box.createGlue());
            b.add(s);

            s = Box.createHorizontalBox();
            monochrome_widget = new JCheckBox("No color", false);
            s.add(monochrome_widget);
            s.add(Box.createGlue());
            notext_widget = new JCheckBox("No text", false);
            s.add(notext_widget);
            s.add(Box.createGlue());
            keepblankpages_widget = new JCheckBox("Keep blank pages", false);
            s.add(keepblankpages_widget);
            if (drycleanURL != null) {
                s.add(Box.createGlue());
                dryclean_widget = new JCheckBox("Dryclean", false);
                s.add(dryclean_widget);
            } else {
                dryclean_widget = null;
            }
            b.add(s);

            b.add(Box.createVerticalStrut(10));

            s = Box.createHorizontalBox();
            s.add(Box.createHorizontalStrut(10));
            cancel_button = new JButton("Cancel");
            cancel_button.setActionCommand("cancel");
            cancel_button.addActionListener(this);
            s.add(cancel_button);

            f = new JLabel ("<html><b>UpLib " + uplibVersion + "</b> &middot; <small>PARC / ISL</small></html>",
                            uplib_favicon, SwingConstants.CENTER);
            f.setFont(new Font("Serif", Font.PLAIN, 14));
            f.setIconTextGap(10);
            f.setForeground(WHITE);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));

            s.add(Box.createGlue());
            s.add(f);
            s.add(Box.createGlue());

            submit_button = new JButton("Submit");
            submit_button.setActionCommand("submit");
            submit_button.addActionListener(this);
            s.add(submit_button);
            s.add(Box.createHorizontalStrut(10));
            b.add(s);

            contents.add(b);

        }

        public void actionPerformed(ActionEvent e) {
            if ("submit".equals(e.getActionCommand())) {
                if (repository_widget.getText().length() > 0) {
                    submitted = true;
                    setVisible(false);
                } else {
                    JOptionPane.showMessageDialog(this, "No repository specified.", "Can't submit", JOptionPane.ERROR_MESSAGE);
                }
            }
            else if ("cancel".equals(e.getActionCommand())) {
                cancelled = true;
                filepath = null;
                setVisible(false);
            }
        }
    }

    private class SnippetSubmissionPopup extends WorkPopup
        implements ActionListener {

        String theSnippet;
        String myRepoURL;
        String myRepoPassword;

        JTextField     repository_widget;
        JCheckBox      stickyrepo_widget;
        JPasswordField password_widget;
        JTextField     categories_widget;
        JTextField     authors_widget;
        JTextField     title_widget;
        JTextField     keywords_widget;
        JTextField     date_widget;
        JTextField     source_widget;
        // SnippetEditorPane    snippet_widget;
        JTextArea      snippet_widget;

        JButton        submit_button;
        JButton        cancel_button;

        SnippetSubmissionPopup (Frame frame, String snippet, String repoURL, String repoPassword) {
            super (frame, false);
            theSnippet = snippet;
            myRepoURL = repoURL;
            myRepoPassword = repoPassword;
            finish();
        }

        private JTextField addField (String fieldname, Box b, Font font, Vector labels) {

            JLabel f;
            JTextField w;
            Box s;

            s = Box.createHorizontalBox();
            f = new JLabel(fieldname);
            if (font != null)
                f.setFont(font);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            w = new JTextField();
            s.add(Box.createHorizontalStrut(5));
            s.add(Box.createGlue());
            s.add(w);
            s.add(Box.createGlue());
            b.add(s);

            return w;
        }

        public void initValues() {
        }

        public void initComponents() {
            Box s, s2, s3;
            JLabel f;
            Vector labels = new Vector();

            setTitle("UpLib Upload Parameters");

            Box b = Box.createVerticalBox();
            b.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

            Container contents = getContentPane();

            Font bold = new Font(null, Font.BOLD, contents.getFont().getSize());
            Font italic = new Font(null, Font.ITALIC, contents.getFont().getSize());
            Font typewriter = new Font("Monospaced", Font.PLAIN, contents.getFont().getSize());

            s = Box.createHorizontalBox();
            f = new JLabel("Repository");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            repository_widget = new JTextField((myRepoURL == null) ? "(default)" : myRepoURL);
            s.add(Box.createHorizontalStrut(5));
            s.add(repository_widget);
            s.add(Box.createGlue());
            b.add(s);

            s = Box.createHorizontalBox();
            f = new JLabel("Password");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            password_widget = new JPasswordField((myRepoPassword == null) ? "" : myRepoPassword);
            s.add(Box.createHorizontalStrut(5));
            s.add(Box.createGlue());
            s.add(password_widget);
            s.add(Box.createHorizontalStrut(5));
            stickyrepo_widget = new JCheckBox("Remember", (myRepoURL != null) || (myRepoPassword != null));
            s.add(stickyrepo_widget);
            s.add(Box.createGlue());
            b.add(s);

            b.add(Box.createVerticalStrut(10));

            s = Box.createHorizontalBox();
            f = new JLabel("Snippet:");
            f.setFont(italic);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            s.add(f);
            s.add(Box.createGlue());
            b.add(s);
            snippet_widget = new JTextArea(theSnippet);
            snippet_widget.setRows(8);
            snippet_widget.setLineWrap(true);
            snippet_widget.setWrapStyleWord(true);
            snippet_widget.setFont(typewriter);
            snippet_widget.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            JScrollPane jsp = new JScrollPane(snippet_widget,
                                              JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED,
                                              JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
            b.add(jsp);
            b.add(Box.createVerticalStrut(10));

            title_widget = addField("Title", b, italic, labels);
            source_widget = addField("Source", b, italic, labels);
            initialfocus = source_widget;
            authors_widget = addField("Authors", b, italic, labels);
            date_widget = addField("Date", b, italic, labels);
            categories_widget = addField("Categories", b, italic, labels);
            categories_widget.setText("snippet");
            keywords_widget = addField("Keywords", b, italic, labels);

            b.add(Box.createVerticalStrut(10));

            s = Box.createHorizontalBox();
            s.add(Box.createHorizontalStrut(10));
            cancel_button = new JButton("Cancel");
            cancel_button.setActionCommand("cancel");
            cancel_button.addActionListener(this);
            s.add(cancel_button);

            f = new JLabel ("<html><b>UpLib " + uplibVersion + "</b> &middot; <small>PARC / ISL</small></html>",
                            uplib_favicon, SwingConstants.CENTER);
            f.setFont(new Font("Serif", Font.PLAIN, 14));
            f.setIconTextGap(10);
            f.setForeground(WHITE);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));

            s.add(Box.createGlue());
            s.add(f);
            s.add(Box.createGlue());

            submit_button = new JButton("Submit");
            submit_button.setActionCommand("submit");
            submit_button.addActionListener(this);
            s.add(submit_button);
            s.add(Box.createHorizontalStrut(10));
            b.add(s);

            contents.add(b);
        }

        public Dimension getPreferredSize () {
            Dimension d = snippet_widget.getPreferredSize();
            // getLogger().info("first d is " + d);
            d = super.getPreferredSize();
            // getLogger().info("second d is " + d);
            return d;
        }

        public void actionPerformed(ActionEvent e) {
            if ("submit".equals(e.getActionCommand())) {
                submitted = true;
                setVisible(false);
            }
            else if ("cancel".equals(e.getActionCommand())) {
                cancelled = true;
                filepath = null;
                setVisible(false);
            }
        }
    }

    private class UploadThread extends WorkThread {
        
        Portal portal;
        String filename;
        String repository;
        private boolean show_dialog;
        private SubmissionParameterPopup inner_dialog;

        public UploadThread (String theFilename, Portal top, boolean show_popup) {
            super(top.getLogger(), top);
            portal = top;
            filename = theFilename;
            show_dialog = show_popup;
            inner_dialog = null;
        }
        
        public void createDialog () throws WorkThread.DialogError {
            File pfile;            
            
            if (filename == null) {
                if (filepath != null) {
                    filename = filepath;
                } else {
                    Frame owner;
                    Container c = portal.getTopLevelAncestor();
                    if (!(c instanceof Frame)) {
                        owner = new Frame(portal.getGraphicsConfiguration());
                    } else {
                        owner = (Frame) c;
                    }
                    java.awt.FileDialog chooser = new java.awt.FileDialog(owner);
                    chooser.setMode(java.awt.FileDialog.LOAD);
                    chooser.setTitle("Select file to upload to UpLib");
                    chooser.setModal(true);
                    chooser.setResizable(true);
                    while (filename == null) {
                        if (currentDir != null) {
                            try {
                                chooser.setDirectory(currentDir.getCanonicalPath());
                            } catch (IOException x) {
                                LogStackTrace.warning(getLogger(), x);
                            }
                        }
                        chooser.setVisible(true);
                        String selFile = chooser.getFile();
                        if (selFile == null) {
                            dialog = null;
                            throw new WorkThread.DialogError("No file selected.");
                        } else if ((pfile = new File(chooser.getDirectory(), selFile)).canRead()) {
                            filename = pfile.getPath();
                            getLogger().info("Opening this file:  " + filename);
                        } else {
                            String possibleDir = chooser.getDirectory();
                            if ((possibleDir != null) && (new File(possibleDir)).exists()) {
                                currentDir = new File(possibleDir);
                            }
                            if (pfile.exists()) {
                                ErrorDialog.say("Can't read file " + pfile.getPath() + ".", null, "Unreadable File");
                            } else {
                                ErrorDialog.say("File " + pfile.getPath() + " doesn't exist.", null, "Unreadable File");
                            }
                        }
                    }
                }
            }
            filepath = filename;
            GraphicsConfiguration gc = portal.getGraphicsConfiguration();
            inner_dialog = new SubmissionParameterPopup(new JFrame("UpLib Upload Parameters", gc), filename,
                                                  portal.theRepoURL, portal.theRepoPassword);
            if (show_dialog) {
                dialog = inner_dialog;
                Dimension d = dialog.getSize();
                if (d.width < 400)
                    dialog.setSize(new Dimension(400, d.height));
                Point p = WorkPopup.bestLocation(dialog, gc.getBounds(), portal.getTopLevelAncestor().getBounds());
                if (p != null)
                    dialog.setLocation(p);
            } else {
                dialog = null;
                inner_dialog.actionPerformed(new ActionEvent(inner_dialog, ActionEvent.ACTION_PERFORMED, "submit"));
            }
        }

        public Vector getCommandLine() {

            SubmissionParameterPopup theDialog = (SubmissionParameterPopup) ((dialog != null) ? dialog : inner_dialog);

            thePassword = new String(theDialog.password_widget.getPassword());

            repository = theDialog.repository_widget.getText();
            String authors = theDialog.authors_widget.getText();
            String keywords = theDialog.keywords_widget.getText();
            String categories = theDialog.categories_widget.getText();
            String title = theDialog.title_widget.getText();
            String date = theDialog.date_widget.getText();
            String source = theDialog.source_widget.getText();
            int tiffdpi = theDialog.getDPI();

            boolean noColor = theDialog.monochrome_widget.isSelected();
            boolean noText = theDialog.notext_widget.isSelected();
            boolean keepBlankPages = theDialog.keepblankpages_widget.isSelected();
            boolean dryclean = (theDialog.dryclean_widget == null) ? false : theDialog.dryclean_widget.isSelected();

            if (theDialog.stickyrepo_widget.isSelected()) {
                setRepoURLAndPassword(repository, thePassword);
            } else {
                setRepoURLAndPassword(null, null);
            }

            Vector c = new Vector();
            c.add(addDocumentProgramString);
            if (!repository.equals("(default)")) {
                c.add("--repository=" + repository);
            };
            if (thePassword.equals("(none)") || thePassword.length() == 0) {
                c.add("--nopassword");
            } else {
                addEnvironmentProperty("UPLIB_PASSWORD", thePassword);
            }
            if (title.length() > 0) {
                c.add("--title=" + quoteit(title, "title"));
            }
            if (authors.length() > 0) {
                c.add("--authors=" + quoteit(authors, "authors"));
            }
            if (categories.length() > 0) {
                c.add("--categories=" + quoteit(categories, "categories"));
            }
            if (keywords.length() > 0) {
                c.add("--keywords=" + quoteit(keywords, "keywords"));
            }
            if (source.length() > 0) {
                c.add("--source=" + quoteit(source, "source"));
            }
            if (date.length() > 0) {
                c.add("--date=" + date);
            }
            if (tiffdpi > 0) {
                c.add("--tiff-dpi=" + tiffdpi);
            }
            if (dryclean) {
                c.add("--dryclean");
            };
            if (noColor) {
                c.add("--nocolor");
            };
            if (noText) {
                c.add("--notext");
            };
            if (keepBlankPages) {
                c.add("--keepblankpages");
            };
            c.add(quoteit(filename));

            return c;
        }

        final static int ADDDOC_CONN_ERROR = 2;
        final static int ADDDOC_UNAUTHORIZED = 3;
        final static int ADDDOC_NO_PARSER = 4;
        final static int ADDDOC_PROCESS_ERROR = 5;

        private String figureStatus (int exitval) {
            getLogger().info("exitval is " + exitval);
            if (exitval < 1)
                return null;
            else if (exitval == ADDDOC_UNAUTHORIZED) {
                if (thePassword.equals("(none)") || thePassword.length() == 0)
                    return "No password supplied.";
                else
                    return "Invalid password supplied.";
            } else if (exitval == ADDDOC_CONN_ERROR) {
                return "Can't connect to repository at " + repository + ".";
            } else if (exitval == ADDDOC_NO_PARSER) {
                return "No parser for the document's format.";
            } else if (exitval == ADDDOC_PROCESS_ERROR) {
                return null;
            } else {
                return null;
            }
        }

        public void finalCleanup() {
            if (exitval != 0) {
                if (!cancelled) {
                    String msg = figureStatus(exitval);
                    if (msg == null)
                        msg = "Error adding " + filename;
                    else
                        msg = "Error adding " + filename + "<br>" + msg;
                    ErrorDialog.say(msg, (msg == null) ? error_output.toString() : null, "Add " + filename);
                }
            } else {
                filepath = null;
            }
        }
    }

    private class DeletableFileUploadThread extends UploadThread {

        public DeletableFileUploadThread (String fname, Portal top, boolean sp) {
            super(fname, top, sp);
        }

        public void finalCleanup() {
            if (!(new File(filename).delete())) {
                String msg = "Couldn't delete: " + filename;
                ErrorDialog.say(msg, msg, "Delete: " + filename);
            }
            super.finalCleanup();
        }
    }

    private class SnippetUploadThread extends UploadThread {
        
        String snippet;
        String repository;
        File snippet_file;

        public SnippetUploadThread (String theSnippet, Portal top) {
            super(null, top, show_popup);
            snippet = theSnippet;
            snippet_file = null;
        }

        public void createDialog () throws WorkThread.DialogError {
            if (snippet == null)
                snippet = "";
            GraphicsConfiguration gc = portal.getGraphicsConfiguration();
            dialog = new SnippetSubmissionPopup(new JFrame("UpLib Upload Parameters", gc), snippet,
                                                portal.theRepoURL, portal.theRepoPassword);
            Dimension d = dialog.getSize();
            if (d.width < 400)
                dialog.setSize(new Dimension(400, d.height));
            Point p = WorkPopup.bestLocation(dialog, gc.getBounds(), portal.getTopLevelAncestor().getBounds());
            if (p != null)
                dialog.setLocation(p);
        }

        public void finalCleanup() {
            super.finalCleanup();
            if ((snippet_file != null) && (snippet_file.exists()))
                snippet_file.delete();
        }

        public Vector getCommandLine() {

            SnippetSubmissionPopup theDialog = (SnippetSubmissionPopup) dialog;

            String final_snippet = theDialog.snippet_widget.getText();
            if (final_snippet == null)
                return null;

            thePassword = new String(theDialog.password_widget.getPassword());

            repository = theDialog.repository_widget.getText();
            String authors = theDialog.authors_widget.getText();
            String keywords = theDialog.keywords_widget.getText();
            String categories = theDialog.categories_widget.getText();
            String title = theDialog.title_widget.getText();
            String date = theDialog.date_widget.getText();
            String source = theDialog.source_widget.getText();
            String pathname = null;

            if (theDialog.stickyrepo_widget.isSelected()) {
                setRepoURLAndPassword(repository, thePassword);
            } else {
                setRepoURLAndPassword(null, null);
            }

            try {
                snippet_file = File.createTempFile("UpLibSnippet", ".3x5");
                FileOutputStream os = new FileOutputStream(snippet_file);
                os.write(final_snippet.getBytes("ISO-8859-1"));
                os.close();
                snippet_file.deleteOnExit();
                pathname = snippet_file.getCanonicalPath();
            } catch (IOException x) {
                LogStackTrace.warning(getLogger(), "Can't create temporary file for snippet:", x);
                return null;
            }

            Vector c = new Vector();
            c.add(addDocumentProgramString);
            if (!repository.equals("(default)")) {
                c.add("--repository=" + repository);
            };
            if (thePassword.equals("(none)") || thePassword.length() == 0) {
                c.add("--nopassword");
            };
            if (title.length() > 0) {
                c.add("--title=" + quoteit(title, "title"));
            }
            if (source.length() > 0) {
                c.add("--source=" + quoteit(source, "source"));
            }
            if (authors.length() > 0) {
                c.add("--authors=" + quoteit(authors, "authors"));
            }
            if (categories.length() > 0) {
                c.add("--categories=" + quoteit(categories, "categories"));
            }
            if (keywords.length() > 0) {
                c.add("--keywords=" + quoteit(keywords, "keywords"));
            }
            if (date.length() > 0) {
                c.add("--date=" + date);
            }
            c.add(quoteit(pathname));

            return c;
        }
    }

    static class PortalTransferHandler extends TransferHandler {

        // we're only worrying about drops on the Portal, so we don't need to support
        // things designed for drags, like "getVisualRepresentation"

        private Logger logger;

        PortalTransferHandler(Logger l) {
            super();
            logger = l;
        }

        private static java.net.URL testForURL (String p) {
            if (p.trim().split(" ").length > 1) {
                // System.err.println("spaces not allowed in URL");
                return null;
            } else {
                try {
                    java.net.URL u = new java.net.URL(p.trim());
                    String proto = u.getProtocol().toLowerCase();
                    // System.err.println(proto);
                    if (!(proto.equals("http") || proto.equals("https") || proto.equals("file") || proto.equals("ftp")))
                        return null;
                    return u;
                } catch (java.net.MalformedURLException x) {
                    // x.printStackTrace();
                    return null;
                }
            }
        }

        public boolean canImport(JComponent c, DataFlavor[] flavors) {
            //for (int i = 0;  i < flavors.length;  i++)
            //    logger.info("" + i + ":  " + flavors[i]);
            if (hasFileFlavor(flavors)) { return true; }
            if (hasURLFlavor(flavors) != null) { return true; }
            if (hasTextFlavor(flavors) != null) { return true; }
            return false;
        }

        public boolean importData(JComponent c, Transferable t) {

            // logger.info("importData(" + c + ", " + t + ")");

            if (!(c instanceof Portal))
                return false;
            if (!canImport(c, t.getTransferDataFlavors())) {
                return false;
            }

            Portal pt = (Portal) c;

            try {
                DataFlavor f;

                if (hasFileFlavor(t.getTransferDataFlavors())) {
                    String str = null;
                    java.util.List files =
                        (java.util.List)t.getTransferData(DataFlavor.javaFileListFlavor);
                    for (int i = 0; i < files.size(); i++) {
                        File file = (File)files.get(i);
                        pt.doDrop(file);
                    }
                    return true;

                } else if ((f = hasURLFlavor(t.getTransferDataFlavors())) != null) {
                    java.net.URL url = (java.net.URL) t.getTransferData(f);
                    // check for file: URLs
                    if (url.getProtocol().toLowerCase().equals("file")) {
                        String filepath = url.getPath();
                        pt.doDrop(new File(url.getPath()));
                    } else {
                        pt.doDrop(url);
                    }
                    return true;

                } else if ((f = hasTextFlavor(t.getTransferDataFlavors())) != null) {
                    BufferedReader r = new BufferedReader(f.getReaderForText(t));
                    String snippet = "";
                    String line = null;
                    while ((line = r.readLine()) != null) {
                        snippet = snippet + ((snippet.length() == 0) ? "" : "\n") + line;
                    }
                    r.close();
                    java.net.URL u = testForURL(snippet);
                    if (u == null)
                        pt.doDrop(snippet);
                    else
                        pt.doDrop(u);
                    return true;
                }
            } catch (UnsupportedFlavorException ufe) {
                pt.getLogger().info("importData: unsupported data flavor");
            } catch (IOException ieo) {
                pt.getLogger().info("importData: I/O exception");
            }
            return false;
        }

        private boolean hasFileFlavor(DataFlavor[] flavors) {
            for (int i = 0; i < flavors.length; i++) {
                // logger.info("Flavor " + i + " is " + flavor);
                if (DataFlavor.javaFileListFlavor.equals(flavors[i])) {
                    return true;
                }
            }
            return false;
        }

        private DataFlavor hasURLFlavor(DataFlavor[] flavors) {
            for (int i = 0; i < flavors.length; i++) {
                // logger.info("Flavor " + i + " is " + flavor);
                if (flavors[i].getMimeType().startsWith("application/x-java-url;"))
                    return flavors[i];
            }
            return null;
        }

        private DataFlavor hasTextFlavor(DataFlavor[] flavors) {
            for (int i = 0; i < flavors.length; i++) {
                // logger.info("Flavor " + i + " is " + flavor);
                if (flavors[i].getMimeType().startsWith("text/plain"))
                    return flavors[i];
            }
            return null;
        }
    }

    // DropTargetListener methods

    public void dragEnter (DropTargetDragEvent e) {
        int old_drop_status = drop_status;
        if (getTransferHandler().canImport(this, e.getCurrentDataFlavors())) {
            drop_status = DROPSTATE_GOOD_DROP;
        } else {
            drop_status = DROPSTATE_BAD_DROP;
        }
        if (old_drop_status != drop_status)
            repaint();
    }

    public void dragExit (DropTargetEvent e) {
        int old_drop_status = drop_status;
        drop_status = DROPSTATE_NO_DROP;
        if (old_drop_status != drop_status)
            repaint();
    }

    public void dragOver (DropTargetDragEvent e) {
        int old_drop_status = drop_status;
        if (getTransferHandler().canImport(this, e.getCurrentDataFlavors())) {
            drop_status = DROPSTATE_GOOD_DROP;
        } else {
            drop_status = DROPSTATE_BAD_DROP;
        }
        if (old_drop_status != drop_status)
            repaint();
    }

    public void dropActionChanged (DropTargetDragEvent e) {
    }

    public void drop (DropTargetDropEvent e) {
        // logger.info("drop(" + e + ")");
        int old_drop_status = drop_status;
        if (getTransferHandler().canImport(this, e.getCurrentDataFlavors())) {
            e.acceptDrop(e.getSourceActions());
            e.dropComplete(getTransferHandler().importData(this, e.getTransferable()));
        } else {
            e.rejectDrop();
        }
        drop_status = DROPSTATE_NO_DROP;
        if (old_drop_status != drop_status)
            repaint();
    }

    public void doDrop (Object f) {

        UploadThread t = null;

        
        if (f instanceof File) {

            String fullPath = ((File)f).getAbsolutePath();

            // this solves a windows drag and drop problem
            // after the drop is handled, the drag and drop system will delete the file
            // ... to get around this, we copy the file and upload that one

            getLogger().info("File " + ((File)f).getAbsolutePath());
            if(is_windows &&
               // check to see if it's a Windows Temp file given us by drag-n-drop
               (fullPath.indexOf("\\Temp\\") != -1)) {

                try {
                    int lastDotPos = fullPath.lastIndexOf(".");
                    File t2 = File.createTempFile("uplib", (lastDotPos < 0) ? "" : fullPath.substring(lastDotPos));
                    BufferedInputStream in = new BufferedInputStream(new FileInputStream((File)f));
                    BufferedOutputStream out = new BufferedOutputStream(new FileOutputStream(t2));
                    byte[] buf = new byte[1 << 16];
                    int count;
                    while ((count = in.read(buf, 0, buf.length)) >= 0)
                        out.write(buf, 0, count);
                    out.close();
                    in.close();
                    t = new DeletableFileUploadThread(t2.getAbsolutePath(), this, show_popup);
                } catch(Exception e) {
                    LogStackTrace.severe(getLogger(), "Couldn't upload drag-and-drop temp file", e);
                    return;
                }
            } else
                t = new UploadThread(fullPath, this, show_popup);

            if (t != null) {
                uploads.add(t);
                t.start();
            }

        } else if (f instanceof URL) {

            getLogger().info("URL " + ((URL)f).toExternalForm());
            uploadThread(((URL)f).toExternalForm());

        } else if (f instanceof String) {

            // getLogger().info("Snippet: " + (String) f);
            t = new SnippetUploadThread((String) f, this);
            uploads.add(t);
            t.start();

        } else {
            getLogger().info("Can't upload objects of type " + f.getClass().getName());
            return;
        }
    }

    // DialogCounter methods

    public synchronized void incrementDialogCount () {
        dialog_showing += 1;
    }

    public synchronized void decrementDialogCount () {
        dialog_showing -= 1;
    }

    public void setRepoURLAndPassword (String repoURL, String repoPassword) {
        // getLogger().info("Setting URL and password to " + repoURL + ", " + repoPassword);
        theRepoURL = repoURL;
        theRepoPassword = repoPassword;
        notifyActionListeners(new StickyPropertySet(this, "repository", repoURL));
    }

    public void incrementSwirlImage () {

        int activecount = uploads.size() + searches.size();

        if ((activecount > 0) || (dialog_showing > 0)) {
            if (do_swirl) {
                if (dialog_showing > 0) {
                    doc_size = 0;
                    which_doc_image = 0;
                } else {
                    doc_size = doc_size + doc_size_increment;
                    which_doc_image = (which_doc_image + 1) % N_DIVISIONS;
                }
                which_swirl_image = (which_swirl_image + 1) % N_DIVISIONS;
                repaint();
            }
        }
    }

    public void paintComponent(Graphics g) {

	if (isOpaque()) {
	    g.setColor(Color.white);
	    g.fillRect(0,0,getWidth(),getHeight());
        };

        int uploads_count = uploads.size();

        if (uploads_count > 0 || searches.size() > 0 || (dialog_showing > 0)) {
            int text_baseline;
            int ds = Math.round(doc_size);
            BufferedImage rotatedSwirlImage = rotatedSwirlImages[which_swirl_image];
            BufferedImage rotatedDocImage = rotatedDocImages[which_doc_image];

            java.awt.geom.Rectangle2D stringbounds = g.getFontMetrics().getStringBounds("" + uploads_count, g);
            int text_start = (new Long(Math.round(getWidth()/2 - (stringbounds.getWidth()/2)))).intValue();

            if (do_swirl) {
                g.drawImage(rotatedSwirlImage, 0, 0, getWidth(), getHeight(), 0, 0, swirlImage.getWidth(), swirlImage.getHeight(), this);
                text_baseline = Math.min(getHeight() - 2, (new Long(Math.round((getHeight() + stringbounds.getHeight() + 1)/2))).intValue());
            } else {
                ((Graphics2D)g).setRenderingHints(logo_rendering_hints);
                g.drawImage(logoImage, 0, 0, getWidth(), getHeight(), 0, 0, logoImage.getWidth(), logoImage.getHeight(), this);
                text_baseline = Math.min(getHeight() - 2, (new Long(Math.round((getHeight() * 3)/5 + stringbounds.getHeight() + 1))).intValue());
            }

            if (uploads.size() > 0) {
                g.setColor(WHITE);
                g.drawString("" + uploads_count, text_start - 1, text_baseline - 1);
                g.drawString("" + uploads_count, text_start - 1, text_baseline + 1);
                g.drawString("" + uploads_count, text_start + 1, text_baseline - 1);
                g.drawString("" + uploads_count, text_start + 1, text_baseline + 1);
                g.setColor(BLACK);
                g.drawString("" + uploads_count, text_start, text_baseline);
            }

            if (do_swirl && (uploads.size() > 0)) {
                // getLogger().info("w = " + rotatedDocImage.getWidth() + "; h = " + rotatedDocImage.getHeight());
                int iw = docImage.getWidth();
                int ih = docImage.getHeight();
                int x = (getWidth() - (iw - ds))/2;
                int y = (getHeight() - (ih - ds))/2;
                int w = getWidth() - (2 * x);
                int h = getHeight() - (2 * y);
                if (w > 0 && h > 0) {
                    g.drawImage(rotatedDocImage, x, y, x + w, y + h, 0, 0, iw, ih, this);
                }
            }
        } else {
            ((Graphics2D)g).setRenderingHints(logo_rendering_hints);
            g.drawImage(logoImage, 0, 0, getWidth(), getHeight(), 0, 0, logoImage.getWidth(), logoImage.getHeight(), this);
        }

        if (drop_status != DROPSTATE_NO_DROP) {
            g.setColor(new Color(0.0f, 0.0f, 1.0f));
            int w = getWidth();
            int h = getHeight();
            if (drop_status == DROPSTATE_GOOD_DROP)
                g.drawImage(goodDropImage, 0 + (w - goodDropImage.getWidth(null))/2,
                            0 + (h - goodDropImage.getHeight(null))/2, null);
            else if (drop_status == DROPSTATE_GOOD_DROP)
                g.drawImage(badDropImage, 0 + (w - badDropImage.getWidth(null))/2,
                            0 + (h - badDropImage.getHeight(null))/2, null);
        }
    }

    public void actionPerformed(ActionEvent e) {
        getLogger().info("ActionEvent " + e);
        getLogger().info("Action " + e.getActionCommand());
    }

    private void popupGetFile(MouseEvent e) {
        UploadThread t = new UploadThread(null, this, false);
        uploads.add(t);
        t.start();
    }

    public java.util.List currentSearches() {
        return searches;
    }

    public java.util.List currentUploads() {
        return uploads;
    }

    public void searchThread() {
        SearchThread t = new SearchThread(this);
        searches.add(t);
        t.start();
    }
    
    public void uploadThread()
    {
        UploadThread t = new UploadThread(null, this, true);
        uploads.add(t);
        t.start();        
    }

    public void uploadThread(String docpath) {
        uploadThread(docpath, false);
    }
    
    public void uploadThread(String docpath, boolean doDelete) {
        UploadThread t = (doDelete ? new DeletableFileUploadThread(docpath, this, show_popup) : new UploadThread(docpath, this, show_popup));
        uploads.add(t);
        t.start();
    }

    public void uploadThread(File doc) {
        try {
            uploadThread(doc.getCanonicalPath());
        } catch (IOException x) {
            LogStackTrace.warning(getLogger(), x);
        }
    }

    static public void SetupSwirl (int width, int height)
        throws IOException {

        double scaling = 1.0d;

        if ((height != swirlImage.getHeight()) ||
            (width != swirlImage.getWidth())) {
            scaling = Math.min(((double)width) / swirlImage.getWidth(),
                               ((double)height) / swirlImage.getHeight());
            swirlImage = (new AffineTransformOp(AffineTransform.getScaleInstance(scaling, scaling),
                                                AffineTransformOp.TYPE_BILINEAR)).filter(swirlImage, null);
            docImage = (new AffineTransformOp(AffineTransform.getScaleInstance(scaling, scaling),
                                              AffineTransformOp.TYPE_BILINEAR)).filter(docImage, null);
            doc_size_increment = (float) scaling;
        }
            
        // create our rotated versions
        rotatedSwirlImages[0] = swirlImage;
        rotatedDocImages[0] = docImage;
        double i_x = swirlImage.getWidth()/2.0;
        double i_y = swirlImage.getHeight()/2.0;
        double d_x = docImage.getWidth()/2.0;
        double d_y = docImage.getHeight()/2.0;
        for (int i = 1;  i < N_DIVISIONS;  i++) {
            double theta = (i * (2.0 * Math.PI)) / N_DIVISIONS;

            // getLogger().info("x,y is " + center_x + ", " + center_y + ", theta is " + theta);

            rotatedSwirlImages[i] = (new AffineTransformOp(AffineTransform.getRotateInstance(-theta, i_x, i_y),
                                                           AffineTransformOp.TYPE_BILINEAR)).filter(swirlImage, null);
            rotatedDocImages[i] = (new AffineTransformOp(AffineTransform.getRotateInstance(theta, d_x, d_y),
                                                         AffineTransformOp.TYPE_BILINEAR)).filter(docImage, null);
        }
    }

    static private void findResources () {
        try {           
            Configurator conf = new Configurator();
            Logger l = Logger.getLogger("global");
            
            addDocumentProgramString = conf.get("uplib-add-program");
            getDocumentProgramString = conf.get("uplib-get-program");               
            
            if(addDocumentProgramString == null)
            {
                l.severe("uplib-add-program not defined!");
                System.exit(1);
            }
            if(getDocumentProgramString == null)
            {
                l.severe("uplib-get-program not defined!");
                System.exit(1);
            }                

            uplibVersion = conf.get("UPLIB_VERSION");   

            logoImage = ImageIO.read(Portal.class.getResource("/favicon256.png"));
            swirlImage = ImageIO.read(Portal.class.getResource("/swirl.png"));
            docImage = ImageIO.read(Portal.class.getResource("/swirldoc.png"));

            goodDropImage = ImageIO.read(Portal.class.getResource("/drop-ok.png"));
            badDropImage = ImageIO.read(Portal.class.getResource("/drop-bad.png"));
            
            drycleanURL = conf.get("dryclean-service-url");
            if ((drycleanURL != null) && (drycleanURL.length() == 0))
                drycleanURL = null;

            SetupSwirl(64, 64);

        } catch (IOException x) {
            LogStackTrace.severe(Logger.getLogger("global"), "Can't load resources needed for Portal widget", x);
            System.exit(1);
        }
    }

    public void setLogger (Logger l) {
        logger = l;
    }

    public Logger getLogger() {
        if (logger == null)
            logger = Logger.getLogger("global");
        return logger;
    }

    public void setShowPopup (boolean v) {
        show_popup = v;
    }

    public String getQuery() {
        return query;
    }

    public void addActionListener (ActionListener l) {
        listeners.add(l);
    }

    public void removeActionListener (ActionListener l) {
        listeners.remove(l);
    }

    private void notifyActionListeners (ActionEvent e) {
        for (int i = 0;  i < listeners.size();  i++)
            ((ActionListener)(listeners.get(i))).actionPerformed(e);
    }

    private static class GUILoader implements Runnable {
        public void run () {
            try {
                Portal.uplib_favicon = new ImageIcon(ImageIO.read(Portal.class.getResource("/applet-logo.png")));
                Portal.docIcon = new ImageIcon(Portal.docImage);
                // set up rendering hits for the logo
                Portal.logo_rendering_hints = new RenderingHints(null);
                Portal.logo_rendering_hints.put (RenderingHints.KEY_ANTIALIASING,
                                          RenderingHints.VALUE_ANTIALIAS_ON);
                Portal.logo_rendering_hints.put (RenderingHints.KEY_ALPHA_INTERPOLATION,
                                          RenderingHints.VALUE_ALPHA_INTERPOLATION_QUALITY);
                Portal.logo_rendering_hints.put (RenderingHints.KEY_RENDERING,
                                          RenderingHints.VALUE_RENDER_QUALITY);
                Portal.logo_rendering_hints.put (RenderingHints.KEY_INTERPOLATION,
                                          RenderingHints.VALUE_INTERPOLATION_BICUBIC);
            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
        }
    }

    public Portal (int width, int height, String repo, boolean swirl, Logger l) {

        super(new CardLayout());

        synchronized (Portal.class) {
            if (docIcon == null) {
                try {
                    GUILoader gui_loader = new GUILoader();
                    if (!javax.swing.SwingUtilities.isEventDispatchThread()) {
                        javax.swing.SwingUtilities.invokeAndWait(gui_loader);
                    } else {
                        gui_loader.run();
                    }
                } catch (Exception e) { 
                    System.err.println("createGUI didn't successfully complete:  " + e);
                    e.printStackTrace(System.err);
                    System.exit(1);
                }
            }
        }

        logger = l;

        uploads = Collections.synchronizedList(new LinkedList());
        searches = Collections.synchronizedList(new LinkedList());
        do_swirl = swirl;
        theRepoURL = repo;
        theRepoPassword = null;
        listeners = new LinkedList();
        show_popup = true;

        Dimension size = new Dimension(width, height);

        PortalTransferHandler pth = new PortalTransferHandler(l);
        this.setTransferHandler(pth);
        this.setDropTarget(new DropTarget(this, DnDConstants.ACTION_COPY | DnDConstants.ACTION_LINK, this));

        setPreferredSize(size);
        setSize(size);
        setOpaque(! is_mac);
        AnimationThread.ensurePortalAnimationThread();
        AnimationThread.addPortal(this);
    }
}
