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

import javax.swing.JApplet;
import java.io.*;
import java.awt.dnd.*;
import java.util.*;
import java.util.regex.*;
import java.util.logging.*;
import java.awt.event.*;
import java.awt.image.*;
import java.awt.geom.*;
import java.awt.font.*;
import java.awt.*;
import java.awt.dnd.*;
import java.awt.CardLayout;
import java.awt.datatransfer.*;
import java.awt.BorderLayout;
import javax.swing.*;
import javax.swing.event.*;
import javax.swing.text.*;
import javax.swing.text.html.*;
import javax.swing.border.*;
import javax.imageio.*;
import java.net.URL;
import java.net.URLEncoder;
import java.net.URLDecoder;
import java.lang.reflect.*;
import java.lang.ref.SoftReference;
import java.security.GeneralSecurityException;
import java.text.SimpleDateFormat;

import com.parc.uplib.util.BrowserLauncher;
import com.parc.uplib.util.CertificateHandler;
import com.parc.uplib.util.ClientKeyManager;
import com.parc.uplib.util.Configurator;
import com.parc.uplib.util.MetadataFile;
import com.parc.uplib.util.LogStackTrace;
import com.parc.uplib.util.EmacsKeymap;
import com.parc.uplib.util.WorkThread;
import com.parc.uplib.util.WorkPopup;
import com.parc.uplib.util.ErrorDialog;
import com.parc.uplib.util.BaseApp;

class Janitor extends BaseApp implements ActionListener {

    private final static Color BACKGROUND_COLOR = new Color(.878f, .941f, .973f);
    private final static Color YELLOW = new Color(1.0f, 1.0f, 0.0f);
    private final static Color UPLIB_ORANGE = new Color(.937f, .157f, .055f);
    private final static Color TOOLS_COLOR = new Color(.754f, .848f, .910f);
    private final static Color LEGEND_COLOR = new Color(.602f, .676f, .726f);
    private final static Color WHITE = new Color(1.0f, 1.0f, 1.0f);
    private final static Color BLACK = new Color(0, 0, 0);
    private final static Color DARK_COLOR = new Color(.439f, .475f, .490f);
    
    private final static String WINDOWS_PASSWORD = "WINDOWS_PASSWORD";
    private final static String DARWIN_PASSWORD = "DARWIN_ADMIN_PASSWORD";

    private class MakeRepositoryDialog extends WorkPopup implements ActionListener {

        JTextField     directory_widget;
        JPasswordField password_widget;
        JPasswordField pwconfirm_widget;
        JTextField     port_widget;
        JTextField     title_widget;
        JButton        submit_button;
        JButton        cancel_button;
        JPasswordField windows_password;

        MakeRepositoryDialog (JFrame frame) {
            super (frame, false);
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

            setTitle("New UpLib Repository Parameters");
            setBackground(BACKGROUND_COLOR);

            Box b = Box.createVerticalBox();
            b.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

            Container contents = getContentPane();
	    contents.setBackground(TOOLS_COLOR);

            Font bold = new Font(null, Font.BOLD, contents.getFont().getSize());
            Font italic = new Font(null, Font.ITALIC, contents.getFont().getSize());
            Font typewriter = new Font("Monospaced", Font.PLAIN, contents.getFont().getSize());

            f = new JLabel("<html>This should be the new location for the UpLib repository you are creating.  It should be a directory which does not already exist, on this machine.  You can use the 'browse' button to bring up a file explorer if you need it to look for a location.</html>");
            f.setForeground(DARK_COLOR);
            f.setHorizontalAlignment(SwingConstants.LEFT);
            s = Box.createHorizontalBox();
            s.add(Box.createGlue());
            s.add(f);
            s.add(Box.createGlue());
            b.add(s);

            s = Box.createHorizontalBox();
            f = new JLabel("Location:");
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            directory_widget = new JTextField();
            s.add(Box.createHorizontalStrut(5));
            s.add(directory_widget);
            s.add(Box.createGlue());
            JButton browse = new JButton("Browse");
            browse.setActionCommand("browse");
            browse.addActionListener(this);
            s.add(browse);
            s.add(Box.createGlue());
            b.add(s);

            b.add(Box.createVerticalStrut(10));
            f = new JLabel("<html>Each repository can have its own password.  You can specify it now, or leave it blank for now and set it later.  You have to type it in twice to make sure you didn't mistype it.</html>");
            f.setForeground(DARK_COLOR);
            f.setHorizontalAlignment(SwingConstants.LEFT);
            s = Box.createHorizontalBox();
            s.add(Box.createGlue());
            s.add(f);
            s.add(Box.createGlue());
            b.add(s);

            s = Box.createHorizontalBox();
            f = new JLabel("Password (optional):");
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            password_widget = new JPasswordField();
            s.add(Box.createHorizontalStrut(5));
            s.add(Box.createGlue());
            s.add(password_widget);
            b.add(s);

            s = Box.createHorizontalBox();
            f = new JLabel("Password (confirm):");
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            pwconfirm_widget = new JPasswordField();
            s.add(Box.createHorizontalStrut(5));
            s.add(Box.createGlue());
            s.add(pwconfirm_widget);
            b.add(s);

            b.add(Box.createVerticalStrut(10));
            f = new JLabel("<html>Each repository has its own 'guardian angel', a server that listens for requests on a particular port.  If you want it to listen on a specific port, you can put that port number here.  Simplest thing to do is just let the automatic port figurer pick one, which is the default.</html>");
            f.setForeground(DARK_COLOR);
            s = Box.createHorizontalBox();
            s.add(Box.createGlue());
            s.add(f);
            s.add(Box.createGlue());
            b.add(s);

            s = Box.createHorizontalBox();
            f = new JLabel("Port to listen on:");
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            port_widget = new JTextField("(auto)");
            s.add(Box.createHorizontalStrut(5));
            s.add(Box.createGlue());
            s.add(port_widget);
            b.add(s);

            b.add(Box.createVerticalStrut(10));
            f = new JLabel("<html>Each repository can have a name or title, which helps you to figure out which one you're looking at if you have a number of them.  You can specify that name here, or set it later if you prefer.</html>");
            f.setForeground(DARK_COLOR);
            s = Box.createHorizontalBox();
            s.add(Box.createGlue());
            s.add(f);
            s.add(Box.createGlue());
            b.add(s);

            s = Box.createHorizontalBox();
            f = new JLabel("Title (optional):");
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
            labels.add(f);
            s.add(f);
            title_widget = new JTextField("");
            s.add(Box.createHorizontalStrut(5));
            s.add(Box.createGlue());
            s.add(title_widget);
            b.add(s);
            
            if(BaseApp.isWindows())
            {
                b.add(Box.createVerticalStrut(10));
                f = new JLabel("<html>The 'guardian angel' for the repository runs as a Windows service on this machine.  We need your Windows password in order to establish the service on this machine.</html>");
                f.setForeground(DARK_COLOR);
                s = Box.createHorizontalBox();
                s.add(Box.createGlue());
                s.add(f);
                s.add(Box.createGlue());
                b.add(s);

		s = Box.createHorizontalBox();
                f = new JLabel("Your Windows password:");
                f.setForeground(UPLIB_ORANGE);
                f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
                labels.add(f);
                s.add(f);
                windows_password = new JPasswordField("");
                s.add(Box.createHorizontalStrut(5));
                s.add(Box.createGlue());
                s.add(windows_password);
                b.add(s);               
            }

            if(BaseApp.isMac())
            {
                b.add(Box.createVerticalStrut(10));
                f = new JLabel("<html>The 'guardian angel' for the repository runs as a launchd service on this machine.  We need your admin password in order to establish the service on this machine.</html>");
                f.setForeground(DARK_COLOR);
                s = Box.createHorizontalBox();
                s.add(Box.createGlue());
                s.add(f);
                s.add(Box.createGlue());
                b.add(s);

		s = Box.createHorizontalBox();
                f = new JLabel("Your admin password:");
                f.setForeground(UPLIB_ORANGE);
                f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
                labels.add(f);
                s.add(f);
                windows_password = new JPasswordField("");
                s.add(Box.createHorizontalStrut(5));
                s.add(Box.createGlue());
                s.add(windows_password);
                b.add(s);               
            }

            b.add(Box.createVerticalStrut(10));
            f = new JLabel("<html>Once you press the 'Create' button, it will take about 30 seconds to actually set up the repository and start the 'guardian angel' for it.  When it's ready, you'll see a panel for it appear in the Janitor.</html>");
            f.setForeground(DARK_COLOR);
            s = Box.createHorizontalBox();
            s.add(Box.createGlue());
            s.add(f);
            s.add(Box.createGlue());
            b.add(s);

            s = Box.createHorizontalBox();
            s.add(Box.createHorizontalStrut(10));
            cancel_button = new JButton("Cancel");
            cancel_button.setActionCommand("cancel");
            cancel_button.addActionListener(this);
            s.add(cancel_button);

            f = new JLabel ("<html><b>UpLib " + uplib_version + "</b> &middot; <small>PARC / ISL</small></html>",
                            uplib_favicon, SwingConstants.CENTER);
            f.setFont(new Font("Serif", Font.PLAIN, 14));
            f.setIconTextGap(10);
            f.setForeground(DARK_COLOR);
            f.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));

            s.add(Box.createGlue());
            s.add(f);
            s.add(Box.createGlue());

            submit_button = new JButton("Create");
            submit_button.setActionCommand("submit");
            submit_button.addActionListener(this);
            s.add(submit_button);
            s.add(Box.createHorizontalStrut(10));
            b.add(s);

            contents.add(b);

            setPreferredSize(new Dimension(600, 700));

        }

        private Integer validateInteger (String v) {
            try {
                return Integer.valueOf(v);
            } catch (NumberFormatException x) {
                return null;
            }
        }

        private boolean validateParameters () {
            File f = new File(expandUser(directory_widget.getText()));
            File parent = f.getParentFile();
            if (f.exists()) {
                JOptionPane.showMessageDialog (this,
                                               "<html>The specified location <tt>" + directory_widget.getText() + "</tt>,<br>" +
                                               "already exists.  You must specify a location that doesn't yet exist.");
                return false;
            } else if ((parent != null) && (!parent.exists())) {
                JOptionPane.showMessageDialog (this,
                                               "<html>There's no directory <tt>" + parent.getPath() + "</tt>.<br>");
                while ((f != null) && (!(f = f.getParentFile()).exists()))
                    ;
                directory_widget.setText((f == null) ? "" : f.getPath());
                return false;
            } else if ((parent != null) && (!parent.isDirectory())) {
                JOptionPane.showMessageDialog (this,
                                               "<html><tt>" + parent.getPath() + "</tt> isn't a directory.<br>" +
                                               "You can't put an UpLib repository in it.");
                while ((f != null) && (!(f = f.getParentFile()).isDirectory()))
                    ;
                directory_widget.setText(f.getPath());
                return false;
            } else if (!(new String(password_widget.getPassword())).equals(new String(pwconfirm_widget.getPassword()))) {
                JOptionPane.showMessageDialog (this,
                                               "<html>The two password fields don't match.");
                password_widget.setText("");
                pwconfirm_widget.setText("");
                return false;
            } else if ((!port_widget.getText().equals("(auto)")) &&
                       (validateInteger(port_widget.getText()) == null)) {
                System.err.println("port is <" + port_widget.getText() + ">, " + Integer.getInteger(port_widget.getText()));
                JOptionPane.showMessageDialog (this,
                                               "<html>Bad port specified.  The port must be an integer.<br>" +
                                               "Leave it at \"(auto)\" to have the system pick a reasonable value for you.");
                port_widget.setText("(auto)");
                return false;
            } else if (BaseApp.isWindows() && ((windows_password.getText() == null) ||
					       (windows_password.getText().trim().length() == 0))) {
                JOptionPane.showMessageDialog (this,
                                               "<html>Your Windows password was not given.<p>" +
                                               "Since your repository will run as you, we need this to restart<br>the repository service when the machine reboots.");
                windows_password.setText("");
                return false;
            } else if (BaseApp.isMac() && ((windows_password.getText() == null) ||
                                           (windows_password.getText().trim().length() == 0))) {
                JOptionPane.showMessageDialog (this,
                                               "<html>Your admin password was not given.<p>" +
                                               "Since your repository will run as a launchd daemon, we need this to restart<br>the repository service when the machine reboots.");
                windows_password.setText("");
                return false;
	    }

            return true;
        }

        private String expandUser (String s) {
            if (s.startsWith("~"))
                return System.getProperty("user.home") + s.substring(1);
            else
                return s;
        }

        public String getDirectory () {
            return expandUser(directory_widget.getText());
        }

        public void actionPerformed(ActionEvent e) {
            if (submit_button.getActionCommand().equals(e.getActionCommand()) && validateParameters()) {
                submitted = true;
                dispose();
            } else if (e.getActionCommand().equals("browse")) {
                JFileChooser j = new JFileChooser(new File(System.getProperty("user.home")));
                j.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
                int r = j.showOpenDialog(this);
                if (r == JFileChooser.APPROVE_OPTION) {
                    File f = j.getSelectedFile();
                    try {
                        if (f.isDirectory())
                            directory_widget.setText(f.getCanonicalPath());
                        else if (f.isFile())
                            directory_widget.setText(f.getParentFile().getCanonicalPath());
                        else {
                            File parent = f.getParentFile();
                            if (!parent.exists()) {
                                if (parent.mkdirs()) {
                                    directory_widget.setText(f.getCanonicalPath());
                                } else {
                                    JOptionPane.showMessageDialog
                                        (this, "Can't create that directory. Try something else.");
                                }
                            } else 
                                directory_widget.setText(f.getCanonicalPath());
                        }
                    } catch (IOException x) {
                        LogStackTrace.warning(getLogger(), "Bad filename " + f, x);
                    }
                }                
            } else if (cancel_button.getActionCommand().equals(e.getActionCommand())) {
                cancelled = true;
                dispose();
            }
        }
    }

    private class MakeRepositoryThread extends WorkThread {
        
        GraphicsConfiguration gc;
        String directory = null;

        public MakeRepositoryThread (GraphicsConfiguration gc, Logger l) {
            super(l, null);
            this.gc = gc;
        }

        public void createDialog () throws WorkThread.DialogError {
            dialog = new MakeRepositoryDialog(the_window);
            dialog.setTitle("Creating new UpLib repository");
            Dimension d = dialog.getSize();
            if (d.width < 400)
                dialog.setSize(new Dimension(400, d.height));
            Point p = WorkPopup.bestLocation(dialog, gc.getBounds(), the_window.getBounds());
            if (p != null)
                dialog.setLocation(p);
            dialog.setDefaultCloseOperation(JDialog.DISPOSE_ON_CLOSE);
        }

        public void finalCleanup() {
            if (!cancelled) {
                if ((directory != null) &&
                    (getWorkerState() == WorkThread.PROCSTATE_FINISHED)) {
                    if (exitval == 0) {
                        // successful completion
                        File rdir;
                        try {
                            repositories_box.remove(no_repos_advisory);
                            repositories_box.add(new RepositoryDisplay(new RepositoryMonitor(new File(directory),
                                                                                             false, TOOLS_COLOR),
                                                                       getLogger(), true));
                            repositories_box.add(Box.createRigidArea(new Dimension(250, 2)));
                            the_window.validate();
                            the_window.setSize(the_window.getPreferredSize());
                        } catch (Exception x) {
                            LogStackTrace.warning(getLogger(), "Can't add new repository " + directory, x);
                        }
                    } else {
                        ErrorDialog.say("Can't add new repository at " + directory + ":<br>"
                                        + "uplib-make-repository signals error with exitval " + exitval + ".",
                                        error_output.toString(), "Make repository at " + directory);
                    }
                }
            }
            create_button.setEnabled(true);
        }

        public Vector getCommandLine() {

            MakeRepositoryDialog theDialog = (MakeRepositoryDialog) dialog;
            if (BaseApp.isWindows()) {
                String windowsPassword = new String(theDialog.windows_password.getPassword());
                addEnvironmentProperty(WINDOWS_PASSWORD, windowsPassword);
            }
            if (BaseApp.isMac()) {
                String windowsPassword = new String(theDialog.windows_password.getPassword());
                addEnvironmentProperty(DARWIN_PASSWORD, windowsPassword);
            }
            
            directory = theDialog.getDirectory();
            String password = new String(theDialog.password_widget.getPassword());
            String port = theDialog.port_widget.getText();
            String title = theDialog.title_widget.getText();

            Vector c = new Vector();
            c.add(make_repository_program);
            c.add("--directory=" + quoteit(directory));
            c.add("--password=" + password);
            c.add("--autoport");
            c.add("--nouser");
            c.add("--expert");
            if (!(port.equals("") || port.equals("(auto)")))
                c.add("--port=" + port);
            if (title.trim().length() > 0)
                c.add("--name=" + quoteit(title.trim()));

            getLogger().info("command is " + c.toString());

            return c;
        }
    }

    public static class RepositoryDisplay extends JPanel implements ActionListener, MouseListener {

        final static int onmask = MouseEvent.SHIFT_DOWN_MASK;
        final static int offmask = MouseEvent.CTRL_DOWN_MASK | MouseEvent.META_DOWN_MASK | MouseEvent.ALT_DOWN_MASK;

        public static class DisplayOpened extends ActionEvent {
            public final static String LABEL = "DisplayOpened";
            public RepositoryMonitor monitor;
            public DisplayOpened (RepositoryDisplay d, RepositoryMonitor m) {
                super(d, ActionEvent.ACTION_PERFORMED, LABEL);
                this.monitor = m;
            }
        }

        public static class DisplayClosed extends ActionEvent {
            public final static String LABEL = "DisplayClosed";
            public RepositoryMonitor monitor;
            public DisplayClosed (RepositoryDisplay d, RepositoryMonitor m) {
                super(d, ActionEvent.ACTION_PERFORMED, LABEL);
                this.monitor = m;
            }
        }

        private RepositoryMonitor mon;
        private JLabel label;
        private JLabel info;
        private JCheckBox but;
        private Logger logger;
        private HashSet listeners;

        public RepositoryDisplay (RepositoryMonitor m, Logger l, boolean open) {
            super();
            listeners = new HashSet();
            logger = l;
            setLayout(new BorderLayout());
            setBorder(BorderFactory.createLineBorder(BACKGROUND_COLOR, 2));
            setBackground(TOOLS_COLOR);
            mon = m;
            Box b = Box.createHorizontalBox();
            but = new JCheckBox();
            but.setFocusPainted(false);
            but.setOpaque(false);
            but.setIcon(right_arrow);
            but.setSelectedIcon(down_arrow);
            but.setActionCommand("but");
            but.addActionListener(this);
            b.add(but);
            b.add(Box.createHorizontalStrut(5));
            b.add(label = new JLabel(m.getRepositoryLocation().getPath()));
            label.addMouseListener(this);
            b.add(Box.createHorizontalStrut(6));
            b.add(Box.createHorizontalGlue());
            b.add(info = new JLabel(""));
            info.setText("(port " + m.getStunnelPort() + ", " + m.getDocumentCount() + " docs)");
            info.setForeground(WHITE);
            info.addMouseListener(this);
            b.add(Box.createHorizontalStrut(2));
            mon.addActionListener(this);
            add(b, BorderLayout.NORTH);
            if (open) {
                but.setSelected(true);
                add(mon, BorderLayout.SOUTH);
            }
            invalidate();
        }

        public void addActionListener(ActionListener l) {
            listeners.add(l);
        }

        public void removeActionListener (ActionListener l) {
            listeners.remove(l);
        }

        public void notifyListeners (ActionEvent e) {
            for (Iterator i = listeners.iterator();  i.hasNext(); )
                ((ActionListener)(i.next())).actionPerformed(e);
        }

        public void actionPerformed(ActionEvent e) {
            if (e.getActionCommand().equals(but.getActionCommand())) {
                if (but.isSelected()) {
                    info.setText("     (port " + mon.getStunnelPort() + ", " + mon.getDocumentCount() + " docs)");
                    add(mon, BorderLayout.SOUTH);
                    notifyListeners(new DisplayOpened(this, mon));
                } else {
                    info.setText("     (port " + mon.getStunnelPort() + ", " + mon.getDocumentCount() + " docs)");
                    remove(mon);
                    notifyListeners(new DisplayClosed(this, mon));
                }
                invalidate();
                Container c = getTopLevelAncestor();
                ((Window)c).pack();
                c.setSize(c.getPreferredSize());
            } else if ((e instanceof RepositoryMonitor.StateChanged) &&
                     (e.getSource() == mon)) {
                int current_state = mon.getState();
                logger.info("state of " + mon.getRepositoryLocation() + " is now " + current_state);
                info.setForeground(WHITE);
                if (current_state == RepositoryMonitor.STATE_RUNNING) {
                    label.setForeground(BLACK);
                } else if (current_state == RepositoryMonitor.STATE_STOPPED) {
                    label.setForeground(DARK_COLOR);
                } else if (current_state == RepositoryMonitor.STATE_TRANSITIONING) {
                    label.setForeground(DARK_COLOR);
                } else if (current_state == RepositoryMonitor.STATE_MISSING) {
                    if (!mon.getRepositoryLocation().exists()) {
                        info.setForeground(UPLIB_ORANGE);
                        info.setText("Directory missing!");
                        info.repaint();
                    }                        
                    label.setForeground(UPLIB_ORANGE);
                } else if (current_state == RepositoryMonitor.STATE_TROUBLED) {
                    label.setForeground(UPLIB_ORANGE);
                }
                label.repaint();
            }
        }

        public void mouseClicked (MouseEvent e) {
            if ((e.getSource() == label || e.getSource() == info)) {
                // logger.info("modifier mask is " + e.getModifiersEx());
                // logger.info("result is " + ((e.getModifiersEx() & (onmask | offmask)) == onmask));
                if (e.getClickCount() > 1) {
                    if (mon.getState() == RepositoryMonitor.STATE_RUNNING) {
                        try {
                            String main_URL_string = mon.getRepositoryURL().toExternalForm();
                            BrowserLauncher.openURL(main_URL_string);
                        } catch (Exception x) {
                            LogStackTrace.warning(logger, "While attempting to open repository", x);
                        }
                    }
                } else if ((e.getModifiersEx() & (onmask | offmask)) == onmask) {
                    try {
                        logger.info("opening log files");
                        mon.openLogFiles();
                    } catch (Exception x) {
                        LogStackTrace.warning(logger, "While attempting to open log files", x);
                    }
                }
            }
        }

        // we ignore these other events
        public void mouseEntered (MouseEvent e) {
        }
        public void mouseExited (MouseEvent e) {
        }
        public void mousePressed (MouseEvent e) {
        }
        public void mouseReleased (MouseEvent e) {
        }        
    }

    private static String uplib_version = "1.5";
    private static String doc_index_url = null;
    private static ImageIcon right_arrow = null;
    private static ImageIcon down_arrow = null;
    private static ImageIcon uplib_favicon = null;
    private static String make_repository_program = null;
    private static String uplib_portal_program = null;

    private static JButton create_button = null;
    private static JButton portal_button = null;
    private static JButton help_button = null;

    private static File portalFlagfile = null;
    private static boolean portalExists = false;

    private static Janitor the_janitor = null;
    private static JFrame the_window = null;
    private static Box repositories_box = null;
    private static Box no_repos_advisory = null;

    static File[] repositories;

    static Janitor app;
    static boolean use_emacs_key_bindings;
    static Vector open_repositories;

    private HashSet opened_repositories;
    private int upper_left_x = 0, upper_left_y = 0;

    public Janitor () {
        super("UpLibJanitor");
        opened_repositories = new HashSet();
        Properties p = loadApplicationProperties();
        if (p != null) {
            upper_left_x = BaseApp.readIntProperty(p, "upper-left-x");
            upper_left_y = BaseApp.readIntProperty(p, "upper-left-y");
            String tmp = p.getProperty("open-repositories");
            if (tmp != null) {
                String[] encodings = tmp.split(",");
                for (int i = 0;  i < encodings.length;  i++) {
                    try {
                        String fpath = URLDecoder.decode(encodings[i], "UTF-8");
                        opened_repositories.add(new File(fpath));
                    } catch (UnsupportedEncodingException x) {
                        // never happens -- UTF-8 is standard
                    }
                }
            }
        }
    }

    protected String getHTMLAppInfo () {
        return "This is the Janitor for <b>UpLib " + uplib_version + "</b>.<br><br>" +
            "More info at <a href=\"http://uplib.parc.com/\">" +
            "http://uplib.parc.com/</a>.<br><br>";
    }

    protected Icon getAppIcon () {
        try {
            return (new ImageIcon(ImageIO.read(Janitor.class.getResource("/janitor-icon.png"))
                                  .getScaledInstance(48, 48, Image.SCALE_SMOOTH)));
        } catch (IOException x) {
            LogStackTrace.warning(getLogger(), "Can't read logo image", x);
        }
        return null;
    }

    public void saveApplicationProperties (Properties p) {
        p.setProperty("upper-left-x", Integer.toString(upper_left_x));
        p.setProperty("upper-left-y", Integer.toString(upper_left_y));
        String open_repos = null;
        for (Iterator i = opened_repositories.iterator();  i.hasNext(); ) {
            File f = (File) (i.next());
            try {
                String t = URLEncoder.encode(f.getPath(), "UTF-8");
                if (open_repos == null)
                    open_repos = t;
                else
                    open_repos = open_repos + "," + t;
            } catch (Exception x) {
                LogStackTrace.warning(getLogger(), "Can't get file path for open file " + f, x);
            }
        }
        if (open_repos != null)
            p.setProperty("open-repositories", open_repos);
        super.saveApplicationProperties(p);
    }

    protected void appComponentMoved (JComponent c, int x, int y, boolean onscreen) {
        if (onscreen) {
            upper_left_x = x;
            upper_left_y = y;
        }
        saveApplicationProperties(loadApplicationProperties());
    }

    public Point getDesiredLocation() {
        return new Point(upper_left_x, upper_left_y);
    }

    public void log (String msg) {
        getLogger().info(msg);
    }

    private void makeNewRepository () {
        MakeRepositoryThread t = new MakeRepositoryThread (the_window.getGraphicsConfiguration(), getLogger());
        t.start();
    }

    private void openDisplay (File repo_location) {
        opened_repositories.add(repo_location);
        saveApplicationProperties(loadApplicationProperties());
    }

    private void closeDisplay (File repo_location) {
        opened_repositories.remove(repo_location);
        saveApplicationProperties(loadApplicationProperties());
    }

    public boolean isOpen(File repo_location) {
        return opened_repositories.contains(repo_location);
    }

    public void actionPerformed (ActionEvent e) {
        if (e.getSource() == create_button) {
            create_button.setEnabled(false);
            makeNewRepository();
        } else if (e.getSource() == help_button) {
            try {
                BrowserLauncher.openURL(doc_index_url);
            } catch (Exception x) {
                LogStackTrace.warning(Logger.getLogger("global"), "Can't open documentation at " + doc_index_url, x);
            }
        } else if (e.getSource() == portal_button) {
            try {
                String osname = Configurator.osName();
                if (osname.equals("Darwin")) {
                    Runtime.getRuntime().exec(new String[] {"/bin/sh", "-c", "/usr/bin/open -a UpLibPortal"});
                } else if (osname.equals("Linux")) {
                    Runtime.getRuntime().exec(new String[] {"/bin/sh", "-c", "(" + uplib_portal_program + " &)"});
                } else if (osname.equals("win32")) {
                    Runtime.getRuntime().exec(new String[] {uplib_portal_program});
                } else {
                    Logger.getLogger("global").warning("Can't start portal -- don't know anything about OS \"" + osname + "\".");
                }
            } catch (Exception x) {
                LogStackTrace.warning(Logger.getLogger("global"), "Can't open documentation at " + doc_index_url, x);
            }
        } else if (e instanceof RepositoryDisplay.DisplayOpened) {
            openDisplay(((RepositoryDisplay.DisplayOpened)e).monitor.getRepositoryLocation());
        } else if (e instanceof RepositoryDisplay.DisplayClosed) {
            closeDisplay(((RepositoryDisplay.DisplayClosed)e).monitor.getRepositoryLocation());
        }
    }

    private static class GUICreator implements Runnable {

        Janitor app;
        File[] repositories;
        boolean use_emacs_bindings;

        public GUICreator (Janitor app, File[] repositories, boolean emacs) {
            this.app = app;
            this.repositories = repositories;
            this.use_emacs_bindings = emacs;
        }

        public void run () {

            JFrame top;
            Box b, mainpanel;

            try {
                app.uplib_favicon = new ImageIcon(ImageIO.read(Janitor.class.getResource("/applet-logo.png")));
                app.right_arrow = new ImageIcon(ImageIO.read(Janitor.class.getResource("/sparrow-right-triangle.png")));
                app.down_arrow = new ImageIcon(ImageIO.read(Janitor.class.getResource("/sparrow-down-triangle.png")));
            } catch (IOException x) {
                LogStackTrace.warning(Logger.getLogger("global"), "Can't read graphics files for Janitor", x);
            }


            if (use_emacs_bindings)
                EmacsKeymap.setupEmacsKeymap();

            // Create and set up the window.
            the_window = new JFrame("UpLib " + app.uplib_version + " on \"" + Configurator.fqdnName() + "\"");
            the_window.getContentPane().setBackground(TOOLS_COLOR);
            the_window.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            the_window.setResizable(false);
            the_window.setLocation(app.getDesiredLocation());

            // stack contents vertically
            mainpanel = Box.createVerticalBox();
            app.trackAppComponentLocation(mainpanel);
            mainpanel.add(Box.createVerticalGlue());
            mainpanel.setOpaque(false);
            mainpanel.setBackground(TOOLS_COLOR);
            the_window.getContentPane().add(mainpanel);

            /*
            // put the UpLib branding at the top
            b = Box.createHorizontalBox();
            b.add(Box.createHorizontalGlue());
            JLabel f = new JLabel ("<html><b>UpLib " + uplib_version + "</b> &middot; <small>PARC / ISL</small></html>",
            uplib_favicon, SwingConstants.CENTER);
            f.setFont(new Font("Serif", Font.PLAIN, 14));
            f.setIconTextGap(10);
            f.setForeground(WHITE);
            f.setBorder(BorderFactory.createEmptyBorder(2,2,2,2));
            b.add(f);
            b.add(Box.createHorizontalGlue());
            mainpanel.add(b);
            */

            // now a box for all the repositories
            repositories_box = Box.createVerticalBox();
            repositories_box.setBackground(TOOLS_COLOR);
            repositories_box.setBorder(BorderFactory.createTitledBorder(BorderFactory.createLineBorder(BLACK, 1),
                                                                        "Local Repositories",
                                                                        TitledBorder.LEADING,
                                                                        TitledBorder.TOP,
                                                                        null,        // default font
                                                                        BLACK));

            no_repos_advisory = Box.createHorizontalBox();
            if (repositories.length == 0) {
                no_repos_advisory.add(Box.createHorizontalGlue());
                JLabel j = new JLabel ("<html><center>No repositories on this machine.  Click the<br><b>New Repository</b><br>button" +
                                       " to create your first repository.</center>");
                j.setOpaque(true);
                j.setBackground(WHITE);
                j.setBorder(BorderFactory.createEmptyBorder(5,5,5,5));
                no_repos_advisory.add(j);
                no_repos_advisory.add(Box.createHorizontalGlue());
                repositories_box.add(no_repos_advisory);
                repositories_box.add(Box.createRigidArea(new Dimension(250, 1)));
            }

            // create a panel for each repository
            for (int i = 0;  i < repositories.length;  i++) {
                try {
                    RepositoryMonitor m = new RepositoryMonitor(repositories[i], false, TOOLS_COLOR);
                    RepositoryDisplay d = new RepositoryDisplay(m, app.getLogger(), app.isOpen(repositories[i]));
                    d.addActionListener(app);
                    repositories_box.add(d);
                    repositories_box.add(Box.createRigidArea(new Dimension(250, 2)));
                } catch (IOException e) {
                    app.log("Can't create monitor for repository at " + repositories[i]);
                    LogStackTrace.warning(app.getLogger(), "Can't create monitor for repository at " + repositories[i], e);
                }
            }
            mainpanel.add(repositories_box);

            // create a button that will create new repositories
            b = Box.createHorizontalBox();
            b.setBackground(TOOLS_COLOR);
            portal_button = new JButton("Portal");
            portal_button.setEnabled(!app.portalExists);
            portal_button.addActionListener(app);
            portal_button.setBackground(TOOLS_COLOR);
            b.add(portal_button);
            b.add(Box.createHorizontalStrut(5));
            b.add(Box.createHorizontalGlue());
            help_button = new JButton("Help");
            help_button.addActionListener(app);
            help_button.setBackground(TOOLS_COLOR);
            b.add(help_button);
            b.add(Box.createHorizontalStrut(5));
            b.add(Box.createHorizontalGlue());
            create_button = new JButton("New Repository");
            create_button.addActionListener(app);
            create_button.setBackground(TOOLS_COLOR);
            b.add(create_button);
            mainpanel.add(b);

            the_window.pack();

            // and display the lot of them
            the_window.setVisible(true);
        }
    }

    protected static boolean checkForPortal () {
        if (portalFlagfile == null) {
            portalFlagfile = new File(BaseApp.figureAppSupportDir("UpLibPortal"), "portal-running-flagfile");
        }
        portalExists = portalFlagfile.exists();
        // System.out.println("portalExists is " + portalExists + ", portalFlagfile is " + portalFlagfile);
        return portalExists;
    }

    private static int readPort(File repo) {
        try {
            BufferedReader r = new BufferedReader(new FileReader(new File(new File(repo, "overhead"), "angel.port")));
            int port = Integer.parseInt(r.readLine().trim());
            r.close();
            return port;
        } catch (java.io.IOException x) {
            x.printStackTrace(System.err);
            return 0;
        }
    }

    public static void main(String[] args) {

        app = new Janitor();

        String[] sections = new String[8];
        sections[3] = Configurator.machineID();
        sections[4] = Configurator.fqdnName();
        sections[5] = Configurator.osName();
        sections[6] = "client";
        sections[7] = "default";

        ClientKeyManager cm = new ClientKeyManager();
        repositories = Configurator.knownLocalRepositories();
        for (int i = 0;  i < repositories.length;  i++) {
            try {
                String port = Integer.toString(readPort(repositories[i]));
                sections[0] = Configurator.machineID() + ":" + repositories[i].getCanonicalPath();
                sections[1] = Configurator.machineID() + ":" + port;
                sections[2] = Configurator.fqdnName() + ":" + port;
                Configurator conf = new Configurator(sections);
                cm.addJavaClientCert(conf, "127.0.0.1:" + port);
            } catch (IOException x) {
                System.err.println("While trying to check for client-side certificate for " + repositories[i] + ":");
                x.printStackTrace(System.err);
            } catch (GeneralSecurityException x) {
                System.err.println("While trying to check for client-side certificate for " + repositories[i] + ":");
                x.printStackTrace(System.err);
            }
        }

        String logfile = app.getConfigurator().get("janitor-log-file");
        if (logfile != null) {
            try {
                app.getLogger().addHandler(new FileHandler(logfile, true));
            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
        }

        uplib_version = app.getConfigurator().get("UPLIB_VERSION", "1.5");
        if (uplib_version == null) {
            System.err.println("Can't determin UpLib version.");
            System.exit(1);
        }
        File doc_root = new File(app.getConfigurator().get("uplib-share"), "doc");
        File doc_index = new File(doc_root, "index.html");
        if (! doc_index.exists()) {
            System.err.println("Can't find documentation index.");
            System.exit(1);
        }
        doc_index_url = "file:" + doc_index.getPath();
        make_repository_program = app.getConfigurator().get("uplib-make-repository-program");
        uplib_portal_program = new File(app.getConfigurator().get("uplib-bin"),
                                        ("win32".equals(Configurator.osName())) ? "uplib-portal.bat" : "uplib-portal")
            .getPath();

        if (make_repository_program == null) {
            System.err.println("No value for uplib-make-repository-program.");
            System.exit(1);
        }

        use_emacs_key_bindings = !BaseApp.isWindows();
        boolean debug_output = false;

        for (int i = 0;  i < args.length;  i++) {
            if (args[i].equals("--empty"))
                repositories = new File[0];
            else if (args[i].equals("--debug"))
                debug_output = true;
            else if (args[i].equals("--emacskeys"))
                use_emacs_key_bindings = true;
            else if (args[i].equals("--noemacskeys"))
                use_emacs_key_bindings = false;
            else if (args[i].startsWith("-")) {
                System.err.println("Unrecognized option \"" + args[i] + "\"");
                System.err.println("Usage:  UpLibJanitor [--debug] [--emacskeys] [--noemacskeys] [--empty]");
                System.exit(1);
            }
        }

        if (!debug_output) {
            app.getLogger().setLevel(Level.WARNING);
        } else {
            app.getLogger().setLevel(Level.ALL);
            app.getLogger().info("Janitor:  debug logging enabled.");
        }

        if (BaseApp.isWindows()) {
            // check to see if the user has the right logon rights
            String python = app.getConfigurator().get("python");
            String uplib_bin = app.getConfigurator().get("uplib-bin");
            WorkThread.SubProc sp = WorkThread.doInThread(new String[] {
                    python, new File(uplib_bin, "uplib-check-windows-service-right.py").getAbsolutePath()},
                true);
            String[] parts = sp.getStandardOutput().trim().split(" ");
            if (parts.length != 3) {
                ErrorDialog.say("Don't understand output from uplib-check-windows-service-right.py",
                                sp.getStandardOutput());
                System.exit(1);
            }
            if (!parts[2].equals("True")) {
                String ref = "http://support.microsoft.com/kb/259733";
                ErrorDialog.say("Can't start the Janitor.<br>" +
                                "User " + parts[0] + "\\" + parts[1] + " doesn't have the right " +
                                "to 'Log on as a Service', which is necessary to use UpLib.<br>" +
                                "To fix this, see <a href=\"" + ref + "\">" + ref + "</a>.");
                System.exit(1);
            }
        }

        boolean showPortalButton = checkForPortal();

        //Execute a job on the event-dispatching thread:
        //creating this applet's GUI.
        try {
            GUICreator gui_creator = new GUICreator(app, repositories, use_emacs_key_bindings);
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

        CertificateHandler.ignoreCerts(cm);

        RepositoryMonitor.startMonitoring();
        app.declareAvailable();

        while (!app.exiting) {
            try {
                Thread.sleep(200);  // sleep 200 ms
            } catch (InterruptedException x) {
                app.getLogger().info("Interrupted!");
            };
            checkForPortal();
            if (portalExists != showPortalButton) {
                portal_button.setEnabled(! portalExists);
                the_window.repaint();
            }
            showPortalButton = portalExists;
        }
        System.exit(0);
    }
}
