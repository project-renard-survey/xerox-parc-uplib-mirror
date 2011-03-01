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

public abstract class BaseApp implements AncestorListener, FeedbackApp, HyperlinkListener {

    static boolean is_mac = System.getProperty("os.name").toLowerCase().startsWith("mac");
    static boolean is_windows = System.getProperty("os.name").toLowerCase().startsWith("win");

    private Configurator conf;
    private File userPropertiesFile;
    private File appsupportdir;
    private String appname;
    private Logger logger;

    protected boolean exiting = false;

    public Configurator getConfigurator() {
        return conf;
    }

    public Logger getLogger() {
        return logger;
    }

    // return an HTML string describing the application
    abstract protected String getHTMLAppInfo ();

    protected Icon getAppIcon () {
        return null;
    }

    public void hyperlinkUpdate (HyperlinkEvent e) {
        if (e.getEventType() == HyperlinkEvent.EventType.ACTIVATED) {
            try {
                BrowserLauncher.openURL(e.getURL().toExternalForm());
            } catch (Exception x) {
                LogStackTrace.warning(Logger.getLogger("global"), "Can't open URL " + e.getURL().toString(), x);
            }
        }
    }

    protected void popupInfoWindow(boolean block) {
        String uplibVersion = getConfigurator().get("UPLIB_VERSION");
        try {
            String info = getHTMLAppInfo();
            JEditorPane p = new JEditorPane("text/html", info);
            p.addHyperlinkListener(this);
            p.setEditable(false);
            p.setOpaque(false);
            if (block) {
                Object[] options = new String[] { "OK", "Exit"};
                int option = JOptionPane.showOptionDialog(null, p, appname,
                                                          0,
                                                          JOptionPane.PLAIN_MESSAGE,
                                                          getAppIcon(),
                                                          options,
                                                          options[0]);
                if (option == 1) {
                    logger.warning("User selected shutdown option.");
                    exiting = true;
                }
            } else {
                JOptionPane.showMessageDialog(null, p, appname,
                                              JOptionPane.INFORMATION_MESSAGE, getAppIcon());
            }
        } catch (Exception x) {
            logger.info("popupInfoWindow signals " + x);
        }
    }

    public static GraphicsConfiguration findScreen (int x, int y) {
        GraphicsEnvironment ge = GraphicsEnvironment.getLocalGraphicsEnvironment();
        GraphicsDevice[] gd = ge.getScreenDevices();
        for (int i = 0;  i < gd.length;  i++) {
            GraphicsConfiguration gc = gd[i].getDefaultConfiguration();
            Rectangle r = gc.getBounds();
            if (r.contains(x, y))
                return gc;
        }
        return null;
    }

    public static boolean onScreen (int x, int y) {
        // logger.info("onScreen(" + x + ", " + y + ") => " + findScreen(x, y));
        return (findScreen(x, y) != null);
    }

    public void ancestorAdded (AncestorEvent e) {
    }

    public void ancestorRemoved (AncestorEvent e) {
    }

    protected void appComponentMoved (JComponent c, int x, int y, boolean onscreen) {
    }

    public void ancestorMoved (AncestorEvent e) {
        Object c = e.getSource();
        if ((c != null) && (c instanceof JComponent)) {
            Point p = ((JComponent)c).getTopLevelAncestor().getLocation();
            appComponentMoved((JComponent) c, p.x, p.y, onScreen(p.x, p.y));
        }
    }

    public void trackAppComponentLocation(JComponent c) {
        c.addAncestorListener(this);
    }

    public static int readIntProperty (Properties p, String propertyName) {
        String tmp = p.getProperty(propertyName);
        if (tmp != null) {
            return Integer.parseInt(tmp);
        }
        return 0;
    }

    public Properties loadApplicationProperties() {
        Properties p = new Properties();
        try {
            if (userPropertiesFile.exists()) {
                p.load(new FileInputStream(userPropertiesFile));
            }
        } catch (Exception e) {
            logger.warning("Unexpected error " + e + " reading user properties file " + userPropertiesFile);
        }
        return p;
    }

    public void saveApplicationProperties (Properties p) {
        try {
            p.store(new FileOutputStream(userPropertiesFile), null);
        } catch (FileNotFoundException e) {
            logger.warning("Can't store properties in file " + userPropertiesFile + ":  " + e);
        } catch (IOException e) {
            logger.warning("Unexpected exception " + e + " storing user properties in " + userPropertiesFile);
        }
    }

    // called to signal the application that it has been "opened"
    public void openApplication (String path) {
    };

    // called to signal application that it has been "re-opened"
    public void reOpenApplication (String path) {
    };

    // called to signal application that it has been asked to open a document
    public void openDocument(String path) {
    };

    // called to ask the application to exit
    public void exitApplication() {
    };

    // called to ask the application to open a preferences editor to edit configuration options
    public void editPreferences() {
    };

    // called to ask the application to print a document
    public void printDocument (java.lang.String filename) {
    };

    // called to ask the application to display a splash screen.
    // return false if not interested.
    public boolean showSplashScreen () {
        popupInfoWindow(false);
        return true;
    }

    public File getAppSupportDir() {
        return appsupportdir;
    }

    public File getUserPropertiesFile () {
        return userPropertiesFile;
    }

    public static boolean isMac() {
        return is_mac;
    }

    public static boolean isWindows() {
        return is_windows;
    }

    public void declareAvailable() {

        // after the code at http://developer.apple.com/samplecode/OSXAdapter/listing1.html

        if (System.getProperty("os.name").toLowerCase().equals("mac os x")) {
            try {

                Class osxAdapter = Class.forName("com.parc.uplib.util.MacOSXAppSupport");

                Class[] defArgs = {Class.forName("com.parc.uplib.util.FeedbackApp")};
                java.lang.reflect.Method registerMethod = osxAdapter.getDeclaredMethod("setupEventHandling", defArgs);
                if (registerMethod != null) {
                    Object[] args = { this };
                    registerMethod.invoke(osxAdapter, args);
                }

            } catch (NoClassDefFoundError e) {
                logger.info("This version of Mac OS X does not support the Apple EAWT. (" + e + ")");
            } catch (ClassNotFoundException e) {
                logger.info("This version of Mac OS X does not support the Apple EAWT. (" + e + ")");
            } catch (Exception e) {
                logger.warning("Exception while loading the OSXAdapter:");
                e.printStackTrace();
            }
        }
    }

    public static File figureAppSupportDir(String appname) {
        File user_home_file = new File(System.getProperty("user.home"));
        if (is_mac) {
            return new File(user_home_file, "Library/Application Support/com.parc.uplib/" + appname);
        } else {
            return new File(user_home_file, "." + appname.replaceAll(" ", "_"));
        }
    }

    public BaseApp (String appname) {

        logger = Logger.getLogger("com.parc.uplib." + appname);
        try {
            conf = new Configurator();
        } catch (IOException e) {
            LogStackTrace.severe(logger, "Can't create a new Configurator:", e);
            System.exit(1);
        }
        File user_home_file = new File(System.getProperty("user.home"));
        if (is_mac) {
            userPropertiesFile = new File(user_home_file, "Library/Preferences/com.parc.uplib/" + appname + "/Properties");
            File parent = userPropertiesFile.getParentFile();
            if ((parent != null) && (!parent.exists()))
                parent.mkdirs();
        } else {
            userPropertiesFile = new File(user_home_file, "." + appname + "-rc");
        }
        appsupportdir = figureAppSupportDir(appname);
        if (!appsupportdir.exists())
            appsupportdir.mkdirs();

        if (System.getProperty("os.name").toLowerCase().equals("mac os x")) {

            // for macs
            System.setProperty("com.apple.mrj.application.apple.menu.about.name", appname);

            // turn off traversal of applications on OS X
            System.setProperty("JFileChooser.appBundleIsTraversable", "never");
            // Make sure we use the screen-top menu on OS X
            System.setProperty("apple.laf.useScreenMenuBar", "true");
        }
    }
}
