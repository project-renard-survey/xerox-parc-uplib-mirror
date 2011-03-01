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

public abstract class WorkThread extends Thread {
        
    public interface DialogCounter {
        public void incrementDialogCount();
        public void decrementDialogCount();
    }

    public static class DialogError extends Exception {
        public DialogError (String msg) {
            super(msg);
        }
    }

    public final static int PROCSTATE_INITIALIZATION = 1;
    public final static int PROCSTATE_RUNNING = 2;
    public final static int PROCSTATE_FINISHED = 3;
    public final static int PROCSTATE_COMPLETE = 4;

    protected static boolean is_mac;
    protected static boolean is_windows;

    static {
        is_mac = System.getProperty("os.name").toLowerCase().startsWith("mac");
        is_windows = System.getProperty("os.name").toLowerCase().startsWith("win");
    }

    public int exitval;

    protected Process proc;
    protected InputStream stdout;
    protected InputStream stderr;
    protected OutputStream stdin;
    protected String[] cmds;
    protected StringBuffer standard_output;
    protected StringBuffer error_output;
    protected WorkPopup dialog = null;
    protected Logger the_logger = null;
    protected DialogCounter counter = null;

    protected String thePassword;

    protected boolean cancelled = false;
    private boolean exitted = false;
    private boolean finished = false;
    
    private HashMap moreEnvProps = new HashMap();

    public WorkThread (Logger l, DialogCounter c) {
        proc = null;
        exitval = -1;
        thePassword = "";
        the_logger = l;
        counter = c;
    }

    public WorkThread () {
        proc = null;
        exitval = -1;
        thePassword = "";
        the_logger = null;
        counter = null;
    }

    // may leave dialog as null if no user-interaction is required
    // Should throw DialogError to abort task.
    public abstract void createDialog() throws DialogError;

    public abstract Vector getCommandLine();

    public void sendStdin() {
    };

    public Logger getLogger() {
        return ((the_logger == null) ? Logger.getLogger("global") : the_logger);
    }

    public String quoteit(String str, String headername) {
            
        String v = str;
        if (headername != null)
            try {
                v = MetadataFile.encode_header_value(headername, str);
            } catch (Exception x) {
                x.printStackTrace(System.err);
            }

        if (!is_windows)
            return v.replaceAll("\"", "\\\\\"");
        else
            return v;
    }

    public String quoteit(String str) {
        return quoteit(str, null);
    }

    public void run () {

        if (counter != null) counter.incrementDialogCount();

        try {
            createDialog();
        } catch (DialogError x) {
            if (counter != null) counter.decrementDialogCount();
            cancelled = true;
            finalCleanup();
            return;
        }

        if (dialog != null) {

            /*
            //make sure it's on-screen
            Rectangle screenbounds = dialog.getGraphicsConfiguration().getBounds();
            Point desired_location = dialog.getLocation();
            int x_pos = Math.min(Math.max(screenbounds.x, desired_location.x - (dialog.getWidth()/2)),
            screenbounds.x + screenbounds.width - dialog.getWidth());
            int y_pos = Math.min(Math.max(screenbounds.y, desired_location.y - (dialog.getHeight()/2)),
            screenbounds.y + screenbounds.height - dialog.getHeight());
            dialog.setLocation(x_pos, y_pos);
            */
            dialog.requestFocus();
            windowToFront(dialog);

            dialog.setVisible(true);

            while (!(dialog.submitted || dialog.cancelled)) {
                try {
                    Thread.sleep(10);
                } catch (InterruptedException x) {};
            }

            if (counter != null) counter.decrementDialogCount();

            if (dialog.cancelled) {
                cancelled = true;
                finalCleanup();
                return;
            }
        } else if (counter != null)
            counter.decrementDialogCount();

        Vector c = getCommandLine();

        cmds = new String[c.size()];
        String ds = "";
        for (int i = 0;  i < c.size();  i++) {
            cmds[i] = (String) c.get(i);
            ds += cmds[i] + " ";
        }

        standard_output = new StringBuffer();
        error_output = new StringBuffer();

        stdin = null;
        try {
            getLogger().info("command line is <" + ds + ">");
            if (moreEnvProps.size() > 0) {                
                proc = Runtime.getRuntime().exec(cmds, getEnvironment());
            }
            else {
                proc = Runtime.getRuntime().exec(cmds);
            }
            stdout = proc.getInputStream();
            stderr = proc.getErrorStream();
            stdin = proc.getOutputStream();
        } catch (Exception x) {
            getLogger().warning("Couldn't run command " + ds + ":\n" + x);
        }

        if (stdin != null) {
            try {
                sendStdin();
                // send an EOF to the underlying subprocess stdin
                stdin.close();
            } catch (IOException x) {
                getLogger().warning("IOException " + x + " closing stdin to " + proc);
            };
        }

        int count;
        byte[] buffer;
        int retval;
        String temp;
        int out_count = 0;
        int err_count = 0;

        // Now read text from the underlying process
        while ((! exitted) && ((stdout != null) || (stderr != null))) {

            try {
                Thread.sleep(10);   // sleep 10 ms
            } catch (InterruptedException x) {};

            try {
                if (stdout != null) {
                    out_count = stdout.available();
                    if (out_count > 0) {
                        count = stdout.available();
                        buffer = new byte[count];
                        retval = stdout.read(buffer);
                        // keep and print output string
                        temp = new String(buffer);
                        standard_output.append(temp);
                        getLogger().info(temp);
                        if (retval < count) {
                            stdout.close();
                            stdout = null;
                        }
                    }
                }
            } catch (IOException x) {
                getLogger().warning("IOException " + x + " reading stdout from " + proc);
            };
                    
            try {
                if (stderr != null) {
                    err_count = stderr.available();
                    if (err_count > 0) {
                        count = stderr.available();
                        buffer = new byte[count];
                        retval = stderr.read(buffer);
                        // just discard the output for now
                        temp = new String(buffer);
                        error_output.append(temp);
                        getLogger().info(temp);
                        if (retval < count) {
                            stderr.close();
                            stderr = null;
                        }
                    }
                }
            } catch (IOException x) {
                getLogger().warning("IOException " + x + " reading stderr from " + proc);
            };

            if (err_count == 0 && out_count == 0) {
                try {
                    exitval = proc.exitValue();
                    exitted = true;
                } catch (IllegalThreadStateException x) {
                    /* ignore */
                }
            }
        }

        while (getWorkerState() != PROCSTATE_FINISHED)
            ;
        finalCleanup();
        finished = true;
    }

    public void addEnvironmentProperty(String key, String value)
    {
        moreEnvProps.put(key, value);
    }
    
    private String[] getEnvironment()
    {
        HashMap props = Configurator.getEnvironment();

        String[] vars = new String[props.size() + moreEnvProps.size()];
        
        addPropsToArray(props, vars, 0);
        addPropsToArray(moreEnvProps, vars, props.size());
        
        return vars;
    }
    
    private void addPropsToArray(HashMap props, String[] vars, int startIndex)
    {
        int index = startIndex;
        
        for(Iterator iter = props.keySet().iterator(); iter.hasNext(); index++) {
            String key = (String)iter.next();
            vars[index] = key + "=" + props.get(key);
        }
    }
    
    public void finalCleanup() {
        getLogger().info("in default finalCleanup");
    }

    public synchronized int getWorkerState () {
        if (finished || cancelled)
            return PROCSTATE_COMPLETE;
        if (exitted)
            return PROCSTATE_FINISHED;
        if (proc == null)
            return PROCSTATE_INITIALIZATION;
        try {
            exitval = proc.exitValue();
            exitted = true;
            return PROCSTATE_FINISHED;
        } catch (IllegalThreadStateException x) {
            return PROCSTATE_RUNNING;
        }
    }

    public void windowToFront (Window w) {
        w.toFront();
        if (is_mac) {
            // Java 6 on the Mac includes a built-in AppleScript interpreter
            boolean handled = false;
            try {
                Class<?> d = Class.forName("javax.script.ScriptEngineManager");
                if (d != null) {
                    java.lang.reflect.Constructor c = d.getConstructor();
                    Object manager = c.newInstance();
                    if (manager != null) {
                        java.lang.reflect.Method m = manager.getClass().getDeclaredMethod("getEngineByName", new Class[] {String.class});
                        if (m != null) {
                            Object engine = m.invoke(manager, "AppleScript");
                            if (engine != null) {
                                engine.getClass().getDeclaredMethod("eval", new Class[] {String.class}).invoke(engine, "activate me");
                                handled = true;
                            }
                        }
                    }
                }
            } catch (Exception x) {
                // ignore it
            }
            if (!handled) {
                try {
                    w.setAlwaysOnTop(true);
                } catch (Exception e) {
                    LogStackTrace.warning(getLogger(), "Exception while attempting to make application active!", e);
                }
            }
        }
        w.toFront();
    }

    public static class SubProc extends WorkThread {
        
        String[] args;

        public SubProc (String[] args, Logger l) {
            super(l, null);
            this.args = args;
        }

        public void createDialog() throws DialogError {
            // we don't need no steeenkeeeng dialogs...
        }

        public Vector getCommandLine() {

            Vector c = new Vector(args.length);
            for (int i = 0;  i < args.length;  i++)
                c.add(args[i]);

            return c;
        }

        public String getCommandLineAsString () {
            String r = "";
            for (int i = 0;  i < args.length;  i++)
                r += (((r.length() == 0) ? "" : " ") + args[i]);
            return r;
        }

        public String getErrorOutput() {
            return error_output.toString();
        }

        public String getStandardOutput() {
            return standard_output.toString();
        }

        public boolean getCancelled() {
            return (cancelled);
        }

        public int getExitValue() {
            return ((cancelled) ? -1 : exitval);
        }

        public boolean isFinished() {
            return (getWorkerState() == PROCSTATE_COMPLETE);
        }

        public void finalCleanup () {
            // override to remove log message
        }
    }

    public static SubProc doInThread (String[] argv, boolean block) {
        SubProc t = new SubProc(argv, Logger.getLogger("global"));
        t.start();
        if (block) {
            while (!t.isFinished()) {
                try {
                    Thread.sleep(100);
                } catch (InterruptedException x) {
                    // ignore
                }
            }
        }
        return t;
    }
}

