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

package com.parc.uplib.portal;

import java.io.*;
import java.util.*;
import java.util.regex.*;
import java.awt.event.*;
import java.awt.image.*;
import java.awt.geom.*;
import java.awt.dnd.*;
import java.awt.*;
import java.awt.datatransfer.*;
import javax.swing.*;
import javax.swing.event.*;
import javax.swing.text.*;
import javax.swing.border.*;
import javax.imageio.*;
import java.net.URL;
import java.util.logging.*;

import com.parc.uplib.util.FeedbackApp;
import com.parc.uplib.util.EmacsKeymap;
import com.parc.uplib.util.Configurator;
import com.parc.uplib.util.LogStackTrace;
import com.parc.uplib.util.BrowserLauncher;
import com.parc.uplib.util.BaseApp;

// wish we could inherit from both BaseApp and MouseInputAdapter here...

class DesktopPortal extends BaseApp
    implements ActionListener, MouseInputListener {

    final private static int FLAG_VALUE = -10000000;

    static private int desiredWidth = 64;
    static private int desiredHeight = 64;
    static private int desiredX = FLAG_VALUE;
    static private int desiredY = FLAG_VALUE;
    static private File flagFile;
    static private String uplibVersion;
    static private ImageIcon logo_icon;

    static private Portal portal;
    static private Container top;

    final private static Logger appLogger = Logger.getLogger("com.parc.uplib.portal.DesktopPortal");

    private static class Shower implements Runnable {

        // see http://java.sun.com/developer/JDCTechTips/2003/tt1208.html#1

        final Window top;
        final boolean emacs;
        public Shower (Window top, boolean emacs) {
            this.top = top;
            this.emacs = emacs;
        }

        public void run () {

            // we set-up the keymap here to do it in the event-dispatching loop

            if (emacs)
                EmacsKeymap.setupEmacsKeymap();

            top.pack();
            top.setVisible(true);
        }
    }

    private static class CheckOnScreen implements Runnable {

        final DesktopPortal app;

        public CheckOnScreen (DesktopPortal app) {
            this.app = app;
        }

        public void run () {

            if (! app.onScreen(app.top.getX(), app.top.getY())) {
                Rectangle bounds = app.top.getGraphicsConfiguration().getBounds();
                int newx = bounds.x + bounds.width - app.top.getWidth();
                int newy = bounds.y + bounds.height - app.top.getHeight();
                app.top.setLocation(newx, newy);
                app.getLogger().info("Setting location to " + newx + "," + newy);
            }
        }
    }

    private static class GUICreator implements Runnable {

        DesktopPortal app;
        String desiredRepo;
        boolean show_popup;
        boolean titlebar;

        public GUICreator (DesktopPortal app, String desiredRepo, boolean show_popup, boolean titlebar) {
            this.app = app;
            this.desiredRepo = desiredRepo;
            this.show_popup = show_popup;
            this.titlebar = titlebar;
        }

        public void run () {

            // Create our object
            portal = new Portal(app.desiredWidth, app.desiredHeight, desiredRepo, true, app.getLogger());
            portal.setFont(new Font(null, Font.BOLD, portal.getFont().getSize()));
            portal.setShowPopup(show_popup);
            portal.addActionListener(app);
            portal.addMouseListener(app);
            app.trackAppComponentLocation(portal);
            
            // Figure out which screen to use in a multi-screen environment
            GraphicsConfiguration desired_screen = ((app.desiredX != FLAG_VALUE)
                                                    ? BaseApp.findScreen(app.desiredX, app.desiredY) : null);

            // Create and set up the window.
            if (titlebar) {
                JFrame topj = new JFrame("UpLib Portal", desired_screen);
                topj.setBackground(Color.white);
                topj.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
                topj.setResizable(false);
                // if window is too wide for the portal, center it in the window
                Box pbox = Box.createHorizontalBox();
                pbox.add(Box.createHorizontalGlue());
                pbox.add(portal);
                pbox.add(Box.createHorizontalGlue());
                topj.setContentPane(pbox);
                top = (Container) topj;
            } else {
                JWindow topw = new JWindow(desired_screen);
                if (app.isMac())
                    // we have support for transparent top-level windows
                    topw.setBackground(new Color(0, 0, 0, 0));
                else
                    topw.setBackground(Color.white);
                topw.setContentPane(portal);
                top = (Container) topw;
            }

            if (app.desiredX != FLAG_VALUE)
                top.setLocation(app.desiredX, app.desiredY);
        }
    }

    protected String getHTMLAppInfo () {
        return "This is a portal for <b>UpLib " + uplibVersion + "</b>.<br><br>" +
            "Drag documents onto the portal to add them to a repository.<br>" +
            "<i>Left-click</i> on the portal to search for a document.<br>" +
            "<i>Shift-Left-click</i> on it to upload a specific file or directory.<br>" +
            "<i>Right-click</i> on it for this message.<br><br>" +
            "More info at <a href=\"http://parcweb.parc.xerox.com/project/uplib/\">" +
            "http://parcweb.parc.xerox.com/project/uplib/</a>.<br><br>";
    }

    protected Icon getAppIcon () {
        try {
            return (new ImageIcon(ImageIO.read(Portal.class.getResource("/favicon256.png"))
                                  .getScaledInstance(48, 48, Image.SCALE_SMOOTH)));
        } catch (IOException x) {
            LogStackTrace.warning(getLogger(), "Can't read logo image", x);
        }
        return null;
    }

    public void Usage(String badarg) {
        if (badarg != null)
            getLogger().warning("Invalid argument \"" + badarg + "\".");
        getLogger().severe("Usage:  java Portal [--titlebar] [--animated] [--noswirl] [--size=WIDTHxHEIGHT] [--location=X,Y]");
        System.exit(1);
    }

    protected void appComponentMoved (JComponent c, int x, int y, boolean onscreen) {
        if (onscreen) {
            Properties p = loadApplicationProperties();
            p.setProperty("upper-left-x", Integer.toString(x));
            p.setProperty("upper-left-y", Integer.toString(y));
            Insets i = top.getInsets();
            p.setProperty("width", Integer.toString(top.getWidth() - i.left - i.right));
            p.setProperty("height", Integer.toString(top.getHeight() - i.top - i.bottom));
            saveApplicationProperties(p);
        }
    }

    // called to signal application that it has been "re-opened"
    public void reOpenApplication (String path) {
        portal.searchThread();
    }

    // called to signal application that it has been asked to open a document
    public void openDocument(String docpath) {
        getLogger().info("File " + docpath);
        portal.uploadThread(new File(docpath));
    }

    // called to ask the application to exit
    public void exitApplication() {
        getLogger().info("exitApplication called");
        if (flagFile.exists())
            flagFile.delete();
        exiting = true;
    }

    static class ShutdownFinalizer extends Thread {

        private File lockfile;

        public ShutdownFinalizer (File lockfile) {
            this.lockfile = lockfile;
        }

        public void run () {
            if (lockfile.exists()) {
                lockfile.delete();
            }
        }
    }

    public void mousePressed(MouseEvent e) {
        // getLogger().info("portal " + (new Date()) + ": mousePressed event");
    }

    public void mouseReleased(MouseEvent e) {
        // getLogger().info("portal " + (new Date()) + ": mouseReleased event");
    }

    public void mouseEntered(MouseEvent e) {
        // getLogger().info("portal " + (new Date()) + ": mouseEntered event");
    }

    public void mouseExited(MouseEvent e) {
        // getLogger().info("portal " + (new Date()) + ": mouseExited event");
    }

    public void mouseClicked(MouseEvent e) {
        // getLogger().info("portal " + (new Date()) + ": mouseClicked event");
        int button = e.getButton();
        if (button == MouseEvent.BUTTON1)
            if (e.isShiftDown()) {
                portal.uploadThread();
            } else {
                portal.searchThread();
            }
        else
            popupInfoWindow(true);
    }

    public void mouseMoved(MouseEvent e) {
        // getLogger().info("portal " + (new Date()) + ": mouseMoved event");
    }

    public void mouseDragged(MouseEvent e) {
        // getLogger().info("portal " + (new Date()) + ": mouseDragged event");
    }

    public void actionPerformed (ActionEvent e) {
        if (e instanceof Portal.StickyPropertySet) {
            String pname = ((Portal.StickyPropertySet) e).getName();
            String pvalue = ((Portal.StickyPropertySet) e).getValue();
            getLogger().info("StickyPropertySet(name=" + pname + ", value=" + pvalue + ")");
            Properties p = loadApplicationProperties();
            if (pvalue == null)
                p.remove(pname);
            else
                p.setProperty(pname, pvalue);
            saveApplicationProperties(p);
        } else if (e instanceof Portal.DocumentUploaded) {
            String docpath = ((Portal.DocumentUploaded)e).getDocument();
            int status = ((Portal.DocumentUploaded)e).getStatus();
            if (status == 0)
                getLogger().info("Document " + docpath + " successfully uploaded.");
            else
                getLogger().warning("Document " + docpath + " upload failed with status " + status);
        } else if (e instanceof Portal.SearchPerformed) {
            String query = ((Portal.SearchPerformed)e).getQuery();
        }
    }

    public DesktopPortal () {
        super("UpLibPortal");
    }

    public static void main(String[] args) {

        int dancestate = 0;
        boolean debug_output = false;
        String user_home = System.getProperty("user.home");
        Pattern SIZE_PATTERN = Pattern.compile("--size=([0-9]+)x([0-9]+)");
        Pattern LOCATION_PATTERN = Pattern.compile("--location=([0-9]+),([0-9]+)");
        String desiredRepo = null;
        DesktopPortal app = new DesktopPortal();
        int loop_counter;
        boolean emacs;
        boolean titlebar;
        boolean show_popup = true;

        Configurator c = app.getConfigurator();
        uplibVersion = c.get("UPLIB_VERSION");
        String default_repo = c.get("default-repository");

        String logfile = c.get("portal-log-file");
        if (logfile != null) {
            try {
                app.getLogger().addHandler(new FileHandler(logfile, true));
            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
        }

        Properties p = app.loadApplicationProperties();
        if (p != null) {
            desiredHeight = BaseApp.readIntProperty(p, "height");
            if (desiredHeight < 5) desiredHeight = 64;
            desiredWidth = BaseApp.readIntProperty(p, "width");
            if (desiredWidth < 5) desiredWidth = 64;
            desiredX = BaseApp.readIntProperty(p, "upper-left-x");
            // if (desiredX < -desiredWidth) desiredX = 0;
            desiredY = BaseApp.readIntProperty(p, "upper-left-y");
            // if (desiredY < -desiredHeight) desiredY = 0;
            desiredRepo = p.getProperty("repository");
            // whether or not to show the metadata pop-up
            String v = app.getConfigurator().get("portal-show-submission-popup");
            if ((v != null) && v.toLowerCase().equals("false"))
                show_popup = false;
        }

        if ((desiredRepo == null) && (default_repo != null))
            desiredRepo = default_repo;
        if (desiredRepo == null) {
            File[] known_local_repositories = Configurator.knownLocalRepositories();
            // just pick the first one
            if (known_local_repositories.length > 0) {
                File port_file = new File(new File(known_local_repositories[0], "overhead"), "stunnel.port");
                try {
                    BufferedReader r = new BufferedReader(new FileReader(port_file));
                    String portnumber = r.readLine();
                    desiredRepo = "https://127.0.0.1:" + portnumber + "/";
                } catch (Exception x) {
                    LogStackTrace.info(app.getLogger(), "Couldn't read port number for local repository " + known_local_repositories[0], x);
                }
            }
        }

        try {
            flagFile = new File(app.getAppSupportDir(), "portal-running-flagfile");
            Runtime.getRuntime().addShutdownHook(new ShutdownFinalizer(flagFile));
            FileOutputStream fp = new FileOutputStream(flagFile);
            fp.write(10);
            fp.close();
        } catch (Exception x) {
            LogStackTrace.severe(app.getLogger(), "Couldn't set up shutdown hook!", x);
            System.exit(1);
        }

        titlebar = !app.isMac();
        emacs = !app.isWindows();
        for (int i = 0;  i < args.length;  i++) {
            if (args[i].equals("--titlebar"))
                titlebar = true;
            else if (args[i].equals("--notitlebar"))
                titlebar = false;
            else if (args[i].equals("--debug"))
                debug_output = true;
            else if (args[i].equals("--emacskeys"))
                emacs = true;
            else if (args[i].equals("--noemacskeys"))
                emacs = false;
            else if (args[i].equals("--noshowpopup"))
                show_popup = false;
            else if (args[i].equals("--showpopup"))
                show_popup = true;
            else if (args[i].startsWith("--size=")) {
                Matcher m = SIZE_PATTERN.matcher(args[i]);
                if (!m.matches())
                    app.Usage(args[i]);
                else {
                    desiredWidth = Integer.parseInt(m.group(1));
                    desiredHeight = Integer.parseInt(m.group(2));
                }
            }
            else if (args[i].startsWith("--location=")) {
                Matcher m = LOCATION_PATTERN.matcher(args[i]);
                if (!m.matches())
                    app.Usage(args[i]);
                else {
                    desiredX = Integer.parseInt(m.group(1));
                    desiredY = Integer.parseInt(m.group(2));
                }
            }
            else if (args[i].startsWith("-")) {
                app.Usage(args[i]);
            }
        }

        if (!debug_output) {
            app.getLogger().setLevel(Level.WARNING);
        }

        // turn off resizing corner on Mac OS X
        System.setProperty("apple.awt.showGrowBox", "false");

        boolean show_icon = System.getProperty("com.parc.uplib.Portal.showIcon", "true").toLowerCase().equals("true");

        //Execute a job on the event-dispatching thread:
        //creating this applet's GUI.
        GUICreator gui_creator = new GUICreator(app, desiredRepo, show_popup, titlebar);
        try {
	    if (!javax.swing.SwingUtilities.isEventDispatchThread()) {
		javax.swing.SwingUtilities.invokeAndWait(gui_creator);
	    }
	    else {
                gui_creator.run();
	    }
        } catch (Exception e) { 
            System.err.println("createGUI didn't successfully complete:  " + e);
            e.printStackTrace(System.err);
            System.exit(1);
        }

        if (show_icon)
            EventQueue.invokeLater (new Shower((Window)top, emacs));

        app.declareAvailable();

        // set a timer to periodically check the number of active uploads
        // and update the display

        loop_counter = 0;
        CheckOnScreen screen_check = new CheckOnScreen(app);

        while (!app.exiting) {
            try {
                Thread.sleep(100);  // sleep 100 ms
            } catch (InterruptedException x) {
                app.getLogger().info("Interrupted!");
            };

            loop_counter += 1;

            // See if we're offscreen due to window resize.  If so, move
            // back on-screen

            if ((loop_counter % 5) == 0) {
                EventQueue.invokeLater(screen_check);
            }
        }
        System.exit(0);
    }
}
