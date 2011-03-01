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
import java.net.HttpURLConnection;
import javax.net.ssl.HttpsURLConnection;
import java.lang.reflect.*;
import java.lang.ref.SoftReference;
import java.text.SimpleDateFormat;

import com.parc.uplib.util.BrowserLauncher;
import com.parc.uplib.util.Configurator;
import com.parc.uplib.util.MetadataFile;
import com.parc.uplib.util.LogStackTrace;
import com.parc.uplib.util.DocIDFilenameFilter;
import com.parc.uplib.util.WorkThread;
import com.parc.uplib.util.WorkPopup;
import com.parc.uplib.util.ErrorDialog;

public class RepositoryMonitor extends JPanel implements ActionListener {

    public final static int STATE_RUNNING = 0;
    public final static int STATE_TROUBLED = 1;
    public final static int STATE_STOPPED = 2;
    public final static int STATE_TRANSITIONING = 4;
    public final static int STATE_MISSING = 8;

    private final static Color BACKGROUND_COLOR = new Color(.878f, .941f, .973f);
    private final static Color YELLOW = new Color(1.0f, 1.0f, 0.0f);
    private final static Color UPLIB_ORANGE = new Color(.937f, .157f, .055f);
    private final static Color TOOLS_COLOR = new Color(.754f, .848f, .910f);
    private final static Color LEGEND_COLOR = new Color(.602f, .676f, .726f);
    private final static Color WHITE = new Color(1.0f, 1.0f, 1.0f);
    private final static Color BLACK = new Color(0, 0, 0);
    private final static Color DARK_COLOR = new Color(.439f, .475f, .490f);

    private final static Border OK_BORDER = new LineBorder(TOOLS_COLOR, 5);
    private final static String hostFQDN = Configurator.fqdnName();
    private final static PendingFolderFilenameFilter PFILTER = new PendingFolderFilenameFilter();
    private final static LogFileFilter LOGFILE_COUNT_FILTER = new LogFileFilter();
    private final static DocIDFilenameFilter DOCID_FILTER = new DocIDFilenameFilter();

    private final static long ONE_MONTH = (31L * 24L * 60L * 60L * 1000L);  // milliseconds in a month

    private final static long BYTES_PER_MB = (1024 * 1024);

    private final static int OSTYPE_WINDOWS = 1;
    private final static int OSTYPE_MACOSX = 2;
    private final static int OSTYPE_LINUX = 3;

    private static MonitorThread monThread = new MonitorThread();
    private static String uplib_check_angel_prog = null;
    private static String konqueror_path = null;
    private static String nautilus_path = null;
    private static int os_type = 0;

    // JLabel repo_identifier;
    TitledBorder repo_identifier;
    File repo_location;
    String normal_path;
    String canonical_path;
    JPanel buttons_flipper;
    JLabel subproc_identifier;
    JButton start_button;
    JButton stop_button;
    JButton restart_button;
    JButton log_button;
    JButton pending_button;
    JButton clearpassword_button;
    JButton opendeleted_button;
    JButton purgelogs_button;
    JButton open_button;
    JCheckBox auto_restart;
    File angeloutdotlog;
    File metadata;
    long metadata_read;
    File pending_folder;
    File deleted_folder;
    File overhead_folder;
    File docs_folder;
    long docs_folder_read;
    int docs_count;
    int angel_port;
    int stunnel_port;
    String name;
    String fqdn;
    URL ping_URL;
    URL main_URL;
    String main_URL_string;
    WorkThread.SubProc subproc;
    Logger logger = null;
    private boolean has_password;
    private boolean removing_password;
    private boolean not_there;
    private int last_state;
    private Vector listeners = null;
    
    static {
        String osname = Configurator.osName();

        if (osname.equals("win32"))
            os_type = OSTYPE_WINDOWS;
        else if (osname.equals("Darwin"))
            os_type = OSTYPE_MACOSX;
        else if (osname.equals("Linux"))
            os_type = OSTYPE_LINUX;

        Logger l = Logger.getLogger("global");
        try {
            Configurator c = new Configurator();
            uplib_check_angel_prog = c.get("uplib-check-repository-program");
            nautilus_path = c.get("nautilus-browser-program");
            konqueror_path = c.get("konqueror-browser-program");
        } catch (Exception x) {
            LogStackTrace.severe(l, "Exception attempting to locate subsidiary programs", x);
            System.exit(1);
        }
    }

    private static class MonitorThread extends Thread {

        private Vector repos;

        public MonitorThread() {
            super("Repository Monitor Thread");
            repos = new Vector();
            this.setDaemon(true);
        }
    
        public void add(RepositoryMonitor rm) {
            repos.add(rm);
        }

        public void run () {
            while (true) {
                for (int i = 0;  i < repos.size();  i++) {
                    RepositoryMonitor rm = (RepositoryMonitor) repos.get(i);
                    // rm.getLogger().info("checking " + rm.normal_path);
                    try {
                        rm.setState(rm.checkRepository());
                    } catch (IOException x) {
                        rm.getLogger().info("IOException attempting to validate repository " + rm.normal_path + ":  " + x);
                        x.printStackTrace(System.err);
                    }
                }
                try {
                    sleep(15 * 1000);
                } catch (InterruptedException x) {
                    // ignore
                }
            }
        }
    }

    private static class PendingFolderFilenameFilter implements java.io.FilenameFilter {
        public PendingFolderFilenameFilter () {
        }
        public boolean accept (File dir, String name) {
            return (!name.startsWith("."));
        }
    }

    private static class LogFileFilter implements java.io.FileFilter {
        public LogFileFilter () {
        }
        public boolean accept (File f) {
            return ((f.getName().startsWith("angel.log.ends") ||
                     f.getName().startsWith("stunnel.log-")) &&
                    (f.lastModified() < (System.currentTimeMillis() - ONE_MONTH)));
        }
    }

    public static class StateChanged extends ActionEvent {
        public final static String LABEL = "stateChanged";
        public int state;
        public StateChanged (RepositoryMonitor m, int newstate) {
            super(m, ActionEvent.ACTION_PERFORMED, LABEL);
            state = newstate;            
        }
    }

    public static class DocsCountChanged extends ActionEvent {
        public final static String LABEL = "docsCountChanged";
        public int count;
        public DocsCountChanged (RepositoryMonitor m, int newcount) {
            super(m, ActionEvent.ACTION_PERFORMED, LABEL);
            count = newcount;
        }
    }

    static String[] format_check_angel (String path, String action) {
        if (os_type == OSTYPE_WINDOWS) {
            String[] v = new String[(action == null) ? 2 : 3];
            v[0] = uplib_check_angel_prog;
            v[1] = (action == null) ? path : action;
            if (action != null)
                v[2] = path;
            return v;
        } else {
            /*
            String[] v = new String[3];
            v[0] = "/bin/sh";
            v[1] = "-c";
            v[2] = uplib_check_angel_prog + " " + ((action == null) ? "" : action) + " \"" + path + "\" >/dev/console 2>&1";
            return v;
            */
            if ((action == null) || (action.trim().length() == 0)) {
                return new String[] { uplib_check_angel_prog, path };
            } else {
                return new String[] { uplib_check_angel_prog, action, path };
            }
        }
    }

    public void actionPerformed (ActionEvent e) {
        String ac = e.getActionCommand();
        if (ac.equals(start_button.getActionCommand())) {
            try {
                subproc = WorkThread.doInThread(format_check_angel(canonical_path, "--start"), false);
                showSubprocIdentifier("Starting...");
                setState(4);
            } catch (Exception x) {
                getLogger().info("while starting repository daemon for " + canonical_path + ": " + x);
                x.printStackTrace(System.err);
            }
        } else if (ac.equals(stop_button.getActionCommand())) {
            try {
                auto_restart.setSelected(false);
                subproc = WorkThread.doInThread(format_check_angel(canonical_path, "--stop"), false);
                showSubprocIdentifier("Stopping...");
                setState(4);
            } catch (Exception x) {
                getLogger().info("while stopping repository daemon for " + canonical_path + ": " + x);
                x.printStackTrace(System.err);
            }
        } else if (ac.equals(restart_button.getActionCommand())) {
            try {
                subproc = WorkThread.doInThread(format_check_angel(canonical_path, "--restart"), false);
                showSubprocIdentifier("Restarting...");
                setState(4);
            } catch (Exception x) {
                getLogger().info("while restarting repository daemon for " + canonical_path + ": " + x);
                x.printStackTrace(System.err);
            }
        } else if (ac.equals(log_button.getActionCommand())) {
            try {
                openLogFiles();
            } catch (Exception x) {
                getLogger().info("while opening angel.log:  " + x);
                x.printStackTrace(System.err);
            }
        } else if (ac.equals(open_button.getActionCommand())) {
            try {
                getLogger().info("opening " + main_URL_string);
                BrowserLauncher.openURL(main_URL_string);
            } catch (Exception x) {
                getLogger().info("while opening repository:  " + x);
                x.printStackTrace(System.err);
            }
        } else if (ac.equals(pending_button.getActionCommand())) {
            try {
                if (pending_folder.exists() && (pending_folder.listFiles(PFILTER).length > 0))
                    BrowserLauncher.openURL("file:" + pending_folder.getCanonicalPath());
                else
                    JOptionPane.showMessageDialog(this,
                                                  "No documents pending for repository " + this.normal_path
                                                  + ((hostFQDN != null) ? (" on " + hostFQDN) : "") + ".",
                                                  ac, JOptionPane.PLAIN_MESSAGE);
            } catch (Exception x) {
                getLogger().info("while opening pending folder:  " + x);
                x.printStackTrace(System.err);
            }
        } else if (ac.equals(purgelogs_button.getActionCommand())) {
            File[] files = overhead_folder.listFiles(LOGFILE_COUNT_FILTER);
            if (files.length > 0) {
                long total_size = 0;
                for (int i = 0;  i < files.length;  i++)
                    total_size += files[i].length();
                String size_msg;
                if (total_size < BYTES_PER_MB)
                    size_msg = "less than one MB";
                else
                    size_msg = "about " + (total_size/BYTES_PER_MB) + " MB";
                String ename = (files.length == 1) ? "file" : "files";
                int option = JOptionPane.showConfirmDialog(this,
                                                           "<html><p>This will remove " + files.length
                                                           + " old log " + ename + ", " + size_msg + ",<br>"
                                                           + "from the repository at <tt>" + repo_location.getPath() + "</tt>.<br>"
                                                           + "The current log file for both the UpLib server and the stunnel<br>"
                                                           + "server will be kept (about one week, or less), but older<br>"
                                                           + "records of web interaction with the server will be removed.<hr>"
                                                           + "<b>Do you want to remove the old log " + ename + "?</b></html>",
                                                           "Removing old log " + ename + "...",
                                                           JOptionPane.YES_NO_OPTION);
                if (option == JOptionPane.YES_OPTION) {
                    getLogger().info("Purging log files.");
                    for (int i = 0;  i < files.length;  i++) {
                        files[i].delete();
                    }
                }
            }
        } else if (ac.equals(opendeleted_button.getActionCommand())) {
            try {
                if (deleted_folder.exists() && (deleted_folder.listFiles(PFILTER).length > 0)) {
                    if (os_type == OSTYPE_WINDOWS) {
                        Runtime.getRuntime().exec("explorer.exe \"" + deleted_folder.getCanonicalPath() + "\"");
                    } else if (os_type == OSTYPE_MACOSX) {
                        Runtime.getRuntime().exec("open " + deleted_folder.getCanonicalPath());
                    } else if (os_type == OSTYPE_LINUX) {
                        if (nautilus_path != null) {
                            Runtime.getRuntime().exec(new String[] {
                                nautilus_path,
                                "--browser", "--no-desktop", "--no-default-window",
                                "--disable-sound", "--disable-crash-dialog",
                                deleted_folder.getCanonicalPath()});
                        } else if (konqueror_path != null) {
                            Runtime.getRuntime().exec(new String[] {
                                konqueror_path, "--silent", deleted_folder.getCanonicalPath()});
                        } else
                            BrowserLauncher.openURL("file:" + deleted_folder.getCanonicalPath());
                    } else {
                        BrowserLauncher.openURL("file:" + deleted_folder.getCanonicalPath());
                    }
                } else
                    JOptionPane.showMessageDialog(this,
                                                  "No documents pending for repository " + this.normal_path
                                                  + ((hostFQDN != null) ? (" on " + hostFQDN) : "") + ".",
                                                  ac, JOptionPane.PLAIN_MESSAGE);
            } catch (Exception x) {
                getLogger().info("while opening folder of deleted documents:  " + x);
                x.printStackTrace(System.err);
            }
        } else if (ac.equals(clearpassword_button.getActionCommand())) {
            int option = JOptionPane.showConfirmDialog(this,
                                                       "<html><p>This will remove the password from the repository at<br><tt>"
                                                       + repo_location.getPath()
                                                       + "</tt>.<br>  Anyone will be able to access this repository,<br>"
                                                       + " until you set a different password.<br>"
                                                       + "<p>This will also stop the repository server.<hr>"
                                                       + "<b>Do you want to remove the password?</b></html>",
                                                       "Removing password...",
                                                       JOptionPane.YES_NO_OPTION);
            if (option == JOptionPane.YES_OPTION) {
                try {
                    auto_restart.setSelected(false);
                    subproc = WorkThread.doInThread(format_check_angel(canonical_path, "--stop"), false);
                    showSubprocIdentifier("Stopping...");
                    removing_password = true;
                    has_password = false;
                    setState(4);
                } catch (Exception x) {
                    getLogger().info("while starting removing password from " + canonical_path + ": " + x);
                    x.printStackTrace(System.err);
                }
            }
        }
    }

    public void openLogFiles() throws Exception {
	String path;
        if (angeloutdotlog.exists() && (angeloutdotlog.length() > 0)) {
	    path = angeloutdotlog.getCanonicalPath();
	    if (os_type == OSTYPE_WINDOWS) {
		Runtime.getRuntime().exec("NOTEPAD.EXE \"" + path + "\"");
	    } else {
		BrowserLauncher.openURL("file:" + URLEncoder.encode(path, "UTF-8"));
	    }
	}
	path = new File(overhead_folder, "angel.log").getCanonicalPath();
	if (os_type == OSTYPE_WINDOWS) {
	    Runtime.getRuntime().exec("NOTEPAD.EXE \"" + path + "\"");
	} else {
	    BrowserLauncher.openURL("file:" + URLEncoder.encode(path, "UTF-8"));
	}
    }

    private boolean pingAngel () throws IOException {
        try {
            HttpsURLConnection c = (HttpsURLConnection) ping_URL.openConnection();
            int rcode = c.getResponseCode();
            c.disconnect();
            return (rcode == HttpURLConnection.HTTP_OK);
        } catch (java.net.ConnectException x) {
            return false;
        } catch (java.io.IOException x) {
            getLogger().info("while pinging angel for " + ping_URL + ": " + x);
            x.printStackTrace(System.err);
            return false;
        }
    }

    private void clearPassword () throws IOException {
    }

    private boolean hasPassword () throws IOException {
        long modtime = metadata.lastModified();
        if (modtime > metadata_read) {
            // re-read metadata file
            has_password = (new MetadataFile(metadata)).containsKey("password-hash");
            metadata_read = modtime;
        }
        return has_password;
    }

    private void countDocs () throws IOException {
        long modtime = docs_folder.lastModified();
        if (modtime > docs_folder_read) {
            // re-count docs
            int l = docs_folder.listFiles(DOCID_FILTER).length;
            docs_folder_read = modtime;
            if (l != docs_count) {
                docs_count = l;
                notifyListeners(new DocsCountChanged(this, l));
            }
        }
    }

    public int getDocumentCount () {
        return docs_count;
    }

    public int getStunnelPort() {
        return stunnel_port;
    }

    public int getAngelPort() {
        return angel_port;
    }

    public int getState() {
        return last_state;
    }

    public void setState(int state) {
        if (repo_location.exists()) {
            pending_button.setEnabled(pending_folder.exists() && (pending_folder.listFiles(PFILTER).length > 0));
            opendeleted_button.setEnabled(deleted_folder.exists() && (deleted_folder.listFiles(PFILTER).length > 0));
            purgelogs_button.setEnabled(overhead_folder.listFiles(LOGFILE_COUNT_FILTER).length > 0);
            clearpassword_button.setEnabled(has_password);
            log_button.setEnabled(true);
        } else {
            pending_button.setEnabled(false);
            opendeleted_button.setEnabled(false);
            purgelogs_button.setEnabled(false);
            clearpassword_button.setEnabled(false);
            log_button.setEnabled(false);
        }
        if (state == STATE_RUNNING) {
            // normal operating condition
            stop_button.setEnabled(true);
            start_button.setEnabled(false);
            restart_button.setEnabled(true);
            open_button.setEnabled(true);
            // repo_identifier.setBackground(WHITE);
            // repo_identifier.setForeground(BLACK);
            if (repo_identifier != null)
                repo_identifier.setTitleColor(BLACK);
            showSubprocIdentifier(null);
        } else if (state == STATE_TROUBLED) {
            // troubled -- not sure what to do
            stop_button.setEnabled(true);
            start_button.setEnabled(true);
            restart_button.setEnabled(true);
            if (repo_location.exists()) {
                pending_button.setEnabled(true);
                open_button.setEnabled(true);
            }
            // repo_identifier.setBackground(YELLOW);
            // repo_identifier.setForeground(BLACK);
            if (repo_identifier != null)
                repo_identifier.setTitleColor(UPLIB_ORANGE);
            showSubprocIdentifier(null);
        } else if (state == STATE_STOPPED) {
            // doesn't respond -- assume dead
            stop_button.setEnabled(false);
            start_button.setEnabled(true);
            restart_button.setEnabled(false);
            open_button.setEnabled(false);
            // repo_identifier.setBackground(BACKGROUND_COLOR);
            // repo_identifier.setForeground(LEGEND_COLOR);
            if (repo_identifier != null)
                repo_identifier.setTitleColor(DARK_COLOR);
            showSubprocIdentifier(null);
        } else if (state == STATE_TRANSITIONING) {
            // working on stopping or starting
            stop_button.setEnabled(false);
            start_button.setEnabled(false);
            restart_button.setEnabled(false);
            open_button.setEnabled(false);
            // repo_identifier.setBackground(BACKGROUND_COLOR);
            // repo_identifier.setForeground(LEGEND_COLOR);
            if (repo_identifier != null)
                repo_identifier.setTitleColor(DARK_COLOR);
        } else if (state == STATE_MISSING) {
            // working on stopping or starting
            stop_button.setEnabled(false);
            start_button.setEnabled(false);
            restart_button.setEnabled(false);
            open_button.setEnabled(false);
            // repo_identifier.setBackground(BACKGROUND_COLOR);
            // repo_identifier.setForeground(LEGEND_COLOR);
            if (repo_identifier != null)
                repo_identifier.setTitleColor(UPLIB_ORANGE);
            showSubprocIdentifier(null);
        }
        repaint();
        boolean changed = (last_state != state);
        last_state = state;
        if (changed)
            notifyListeners(new StateChanged(this, state));
    }

    public int checkRepository () throws IOException {
        // getLogger().info("checkRepository:  subproc is " + ((subproc == null) ? "null" : "non-null") + ", removing_password is " + removing_password);
        if (!repo_location.exists()) {
            if (!not_there) {
                not_there = true;
                ErrorDialog.say("The directory " + canonical_path + " has disappeared!", null, "No repository directory!", false);
            }
            return STATE_MISSING;
        } else {
            not_there = false;
        }
        if (!removing_password)
            hasPassword();
        countDocs();
        if (subproc != null) {
            if (subproc.isFinished()) {
                int value = subproc.getExitValue();
                if (value == 0) {
                    subproc = null;
                    if (removing_password) {
                        // actually remove it now that the repository has stopped
                        MetadataFile mf = new MetadataFile(this.metadata);
                        mf.remove("password-hash");
                        mf.flush();
                        removing_password = false;
                    }
                    return this.checkRepository();
                } else {
                    String msg = "Subprocess \"" +
                        subproc.getCommandLineAsString() +
                        "\" returned odd exit status " +
                        value + " (should be 0).";
                    String eout = subproc.getErrorOutput();
                    getLogger().info(msg + "\n" + eout);
                    ErrorDialog.say(msg, eout, "While " + subproc_identifier.getText(), false);
                    subproc = null;
                    return STATE_TROUBLED;
                }
            } else {
                // still working on it
                return STATE_TRANSITIONING;
            }
        }
        if (!pingAngel()) {
            if (auto_restart.isEnabled() && auto_restart.isSelected()) {
                subproc = WorkThread.doInThread(format_check_angel(canonical_path, null), false);
                showSubprocIdentifier("Starting...");
                return STATE_TRANSITIONING;
            } else
                return STATE_STOPPED;
        } else if (angeloutdotlog.exists() && (angeloutdotlog.length() > 0)) {
            return STATE_TROUBLED;
        } else {
            return STATE_RUNNING;
        }
    }

    private String readOverheadFile (String filename) throws IOException {
        BufferedReader r = new BufferedReader(new FileReader(new File(this.overhead_folder, filename)));
        String s = r.readLine();
        String q;
        while ((q = r.readLine()) != null)
            s = s + q;
        r.close();
        return s.trim();
    }

    private int readPort (String portFile) throws IOException {
        String portnum = readOverheadFile(portFile);
        if (portnum == null)
            throw new IOException("no port number in " + portFile + " file");
        return Integer.parseInt(portnum);
    }

    public String getCurrentAction () {
        if (subproc != null)
            return subproc_identifier.getText();
        return null;
    }

    public URL getRepositoryURL () {
        return main_URL;
    }

    public File getRepositoryLocation () {
        return repo_location;
    }

    private void showSubprocIdentifier(String label) {
        if (label != null) {
            subproc_identifier.setText(label);
            ((CardLayout)(buttons_flipper.getLayout())).show(buttons_flipper, "subproc");
        } else {
            ((CardLayout)(buttons_flipper.getLayout())).show(buttons_flipper, "nosubproc");
        }
    } 

    public void addActionListener (ActionListener l) {
        if (listeners == null)
            listeners = new Vector();
        listeners.add(l);
    }

    public void removeActionListener (ActionListener l) {
        if (listeners != null)
            listeners.remove(l);
    }

    private void notifyListeners (ActionEvent e) {
        if (listeners != null)
            for (int i = 0;  i < listeners.size();  i++)
                ((ActionListener)(listeners.get(i))).actionPerformed(e);
    }

    public void setLogger (Logger l) {
        logger = l;
    }

    public Logger getLogger () {
        if (logger == null)
            logger = Logger.getLogger("global");
        return logger;
    }

    public RepositoryMonitor (File repository_directory, boolean bordered, Color background) throws IOException {

        this.repo_location = repository_directory;
        this.repo_identifier = null;
        this.not_there = false;
        this.normal_path = repository_directory.getPath();
        this.canonical_path = repository_directory.getCanonicalPath();
        this.overhead_folder = new File(repository_directory, "overhead");
        this.angeloutdotlog = new File(this.overhead_folder, "angelout.log");
        this.angel_port = readPort("angel.port");
        this.stunnel_port = readPort("stunnel.port");
        if ((new File(this.overhead_folder, "host.fqdn")).exists())
            this.fqdn = readOverheadFile("host.fqdn");
        else
            this.fqdn = "127.0.0.1";
        this.ping_URL = new URL("https://127.0.0.1:" + this.stunnel_port + "/ping");
        this.main_URL = new URL("https://" + this.fqdn + ":" + this.stunnel_port + "/");
        this.main_URL_string = this.main_URL.toExternalForm();
        this.pending_folder = new File(repository_directory, "pending/");
        this.deleted_folder = new File(repository_directory, "deleted/");
        this.metadata = new File(this.overhead_folder, "metadata.txt");
        this.metadata_read = this.metadata.lastModified();
        this.docs_folder = new File(repository_directory, "docs");
        this.docs_folder_read = 0;
        MetadataFile mf = new MetadataFile(this.metadata);
        this.name = (String) mf.get("name");
        this.has_password = mf.containsKey("password-hash");
        this.removing_password = false;
        mf = null;

        System.setProperty("sun.net.client.defaultConnectTimeout", "10000");

        setLayout(new BorderLayout());
        setBackground((background == null) ? TOOLS_COLOR : background);

        /*

        repo_identifier = new JLabel(repo_location.getPath());
        repo_identifier.setBorder(BorderFactory.createCompoundBorder(BorderFactory.createLineBorder(LEGEND_COLOR, 2),
                                                                     BorderFactory.createEmptyBorder(5, 5, 5, 5)));
        repo_identifier.setOpaque(true);
        repo_identifier.setBackground(WHITE);
        add(repo_identifier, BorderLayout.WEST);

        */

        if (bordered) {
            repo_identifier = BorderFactory.createTitledBorder(BorderFactory.createLineBorder(LEGEND_COLOR, 5),
                                                               repo_location.getPath(),
                                                               TitledBorder.LEADING,
                                                               TitledBorder.TOP,
                                                               null,        // default font
                                                               LEGEND_COLOR);
            setBorder(repo_identifier);
        }

        Box toplevel = Box.createVerticalBox();
        add(toplevel, BorderLayout.NORTH);

        Box s = Box.createHorizontalBox();

        log_button = new JButton("Show Log");
        log_button.setBackground(TOOLS_COLOR);
        log_button.addActionListener(this);
        s.add(log_button);

        pending_button = new JButton("Show Pending");
        pending_button.setBackground(TOOLS_COLOR);
        pending_button.addActionListener(this);
        s.add(pending_button);

        // we group the buttons with an action identifier

        buttons_flipper = new JPanel();
        buttons_flipper.setBackground(TOOLS_COLOR);
        buttons_flipper.setLayout(new CardLayout());
        s.add(buttons_flipper);

        {
            Box s2 = Box.createHorizontalBox();
            buttons_flipper.add(s2, "nosubproc");
            
            start_button = new JButton("Start");
            start_button.setBackground(TOOLS_COLOR);
            start_button.addActionListener(this);
            s2.add(start_button);

            stop_button = new JButton("Stop");
            stop_button.setBackground(TOOLS_COLOR);
            stop_button.addActionListener(this);
            s2.add(stop_button);

            restart_button = new JButton("Re-start");
            restart_button.setBackground(TOOLS_COLOR);
            restart_button.addActionListener(this);
            s2.add(restart_button);

            Box s3 = Box.createHorizontalBox();
            s3.add(Box.createHorizontalGlue());
            subproc_identifier = new JLabel("");
            subproc_identifier.setForeground(BLACK);
            s3.add(subproc_identifier);
            s3.add(Box.createHorizontalGlue());

            buttons_flipper.add(s3, "subproc");

            showSubprocIdentifier(null);
        }

        s.add(Box.createHorizontalGlue());

        toplevel.add(s);

        s = Box.createHorizontalBox();

        clearpassword_button = new JButton("Clear Password");
        clearpassword_button.setBackground(TOOLS_COLOR);
        clearpassword_button.addActionListener(this);
        s.add(clearpassword_button);

        opendeleted_button = new JButton("Show Deleted Docs");
        opendeleted_button.setBackground(TOOLS_COLOR);
        opendeleted_button.addActionListener(this);
        s.add(opendeleted_button);

        purgelogs_button = new JButton("Purge Log Files");
        purgelogs_button.setBackground(TOOLS_COLOR);
        purgelogs_button.addActionListener(this);
        s.add(purgelogs_button);

        s.add(Box.createHorizontalGlue());

        toplevel.add(s);

        s = Box.createHorizontalBox();

        auto_restart = new JCheckBox("Re-start automatically if stopped.", false);
        auto_restart.setBackground(TOOLS_COLOR);
        s.add(auto_restart);

        s.add(Box.createHorizontalGlue());

        open_button = new JButton("Visit");
        open_button.setBackground(TOOLS_COLOR);
        open_button.addActionListener(this);
        s.add(open_button);

        toplevel.add(s);

//         buttons_flipper = new JPanel();
//         buttons_flipper.setBackground(TOOLS_COLOR);
//         buttons_flipper.setLayout(new CardLayout());
//         s.add(buttons_flipper);
//         add(s, BorderLayout.EAST);

//         start_button = new JButton("Start");
//         start_button.setBackground(TOOLS_COLOR);
//         start_button.addActionListener(this);
//         stop_button = new JButton("Stop");
//         stop_button.setBackground(TOOLS_COLOR);
//         stop_button.addActionListener(this);
//         restart_button = new JButton("Re-start");
//         restart_button.setBackground(TOOLS_COLOR);
//         restart_button.addActionListener(this);

//         s = Box.createHorizontalBox();
//         // s.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
//         s.add(Box.createHorizontalGlue());
//         s.add(start_button);
//         buttons_flipper.add(s, "offpanel");

//         s = Box.createHorizontalBox();
//         // s.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));
//         s.add(Box.createHorizontalGlue());
//         s.add(stop_button);
//         s.add(restart_button);
//         buttons_flipper.add(s, "onpanel");

//         ((CardLayout)buttons_flipper.getLayout()).show(buttons_flipper, "offpanel");

        Dimension d = getPreferredSize();
        setSize(d);
        setMinimumSize(d);
        setOpaque(true);

        countDocs();

        monThread.add(this);

        setEnabled(true);
        setVisible(true);
        setFocusable(true);
    }

    public void paintComponent(Graphics g) {
        super.paintComponent(g);
        g.setColor(getBackground());
        g.fillRect(0, 0, getWidth(), getHeight());
    }

    public static void startMonitoring() {
        monThread.start();
    }

    public static void rescan() {
        monThread.interrupt();
    }

    static File[] repositories;

    static void createGUI () {

        JFrame top;
        Box b;

        try {

            // Create and set up the window.
            top = new JFrame("UpLib repositories" + ((hostFQDN != null) ? " on " + hostFQDN : ""));
            top.setBackground(Color.getColor("pink"));
            top.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
            top.setResizable(false);

            b = Box.createVerticalBox();
            top.getContentPane().add(b);

            // create a panel for each repository
            for (int i = 0;  i < repositories.length;  i++) {
                RepositoryMonitor rm = new RepositoryMonitor(repositories[i], true, null);
                rm.countDocs();
                b.add(rm);
            }
            top.pack();

            // and display the lot of them
            top.setVisible(true);
        } catch (IOException x) {
            System.err.println("IOException thrown trying to build monitor panes:  " + x);
            x.printStackTrace(System.err);
            System.exit(1);
        }
    }

    private static class GUICreator implements Runnable {
        public void run () {
            RepositoryMonitor.createGUI();
        }
    }

    public static void main(String[] argv) {

        repositories = Configurator.knownLocalRepositories();

        if ((repositories == null) || (repositories.length == 0)) {
            System.err.println("No repositories.");
            System.exit(1);
        }

        //Execute a job on the event-dispatching thread:
        //creating this applet's GUI.
        try {
            GUICreator gui_creator = new GUICreator();
	    if (!javax.swing.SwingUtilities.isEventDispatchThread()) {
		javax.swing.SwingUtilities.invokeAndWait(gui_creator);
	    }
	    else {
                gui_creator.run();
	    }
        } catch (Exception e) { 
            System.err.println("createGUI didn't successfully complete:  " + e);
            e.printStackTrace(System.err);
        }

        startMonitoring();
    }
}
