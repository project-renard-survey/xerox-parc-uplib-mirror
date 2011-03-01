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
import java.util.jar.JarFile;
import java.util.regex.*;
import java.nio.charset.*;
import java.nio.ByteBuffer;
import java.net.*;

/**
 * Configurator is a class which knows how to read the configuration files for
 * an UpLib installation. An instance of this class supports search through a
 * list of named sections for values for named properties. All values are
 * <code>String</code>.
 */
public class Configurator {

    private static boolean initialized = false;

    private static String UPLIB_LIB_DIRECTORY = null;

    private static String HOST_FQDN = null;

    private static String OS_NAME = null;

    private static String MACHINE_ID = null;

    private static File user_config_file = null;

    private static File site_config_file = null;

    private final static String MACHINE_CONFIG_FILE_NAME = "machine.config";

    private final static String USER_CONFIG_FILE_NAME = ".uplibrc";

    private final static Pattern section_name_pattern = Pattern
            .compile("\\[([^]]+)\\]");

    private final static Charset default_charset = Charset
            .forName("ISO-8859-1");

    private HashMap values;

    private String[] sections;

    /**
     * Debug the Configurator by printing it to a print stream.
     * 
     * @param ps
     *            the stream to print to
     */
    public void list(PrintStream ps) {
        System.err.println("UPLIB_LIB_DIRECTORY is " + UPLIB_LIB_DIRECTORY);
        System.err.println("HOST_FQDN is " + HOST_FQDN);
        System.err.println("OS_NAME is " + OS_NAME);
        System.err.println("MACHINE_ID is " + MACHINE_ID);
        Iterator i = values.entrySet().iterator();
        while (i.hasNext()) {
            Map.Entry e = (Map.Entry) i.next();
            ps.println("*** " + (String) e.getKey() + ":");
            // ps.println(" (values are " + e.getValue().toString() + ")");
            Properties p = (Properties) e.getValue();
            Iterator i2 = p.entrySet().iterator();
            while (i2.hasNext()) {
                Map.Entry e2 = (Map.Entry) i2.next();
                ps.println("       " + (String) e2.getKey() + " : "
                        + (String) e2.getValue());
            }
            ps.println("");
        }
    }

    /**
     * Set the search sections of the Configurator. <b>Not recommended. </b>
     * 
     * @param section_names
     *            the list of section names to search
     */
    public void setSections(String[] section_names) {
        sections = section_names;
    }

    /**
     * Fetch the section name search list for the Configurator.
     * 
     * @return an array of section names
     */
    public String[] getSections() {
        return sections;
    }

    /**
     * Get the string value associated with the given property name, using the
     * specified list of section names as the search list. If no value for that
     * property is found, return the specified default value.
     * 
     * @param property
     *            the name of the property to look up
     * @param defvalue
     *            a default value to return if no value is found for <i>property
     *            </i>
     * @param section_names
     *            a search list of section names to use. If specified as
     *            <code>null</code>, the default search list for the
     *            Configurator is used.
     * @return the value for <i>property </i>
     * @see #getSections()
     * @see #get(String)
     * @see #get(String, String)
     */
    public String get(String property, String defvalue, String[] section_names) {
        String[] sections_to_use = (section_names == null) ? sections
                : section_names;
        for (int i = 0; i < sections_to_use.length; i++) {
            Properties p = (Properties) values.get(sections_to_use[i]);
            if (p != null) {
                String value = p.getProperty(property);
                if (value != null)
                    return value;
            }
        }
        return defvalue;
    }

    /**
     * Get the string value associated with the given property name, using the
     * default list of section names as the search list. If no value for that
     * property is found, return the specified default value.
     * 
     * @param property
     *            the name of the property to look up
     * @param defvalue
     *            a default value to return if no value is found for <i>property
     *            </i>
     * @return the value for <i>property </i>
     * @see #getSections()
     * @see #get(String, String, String[])
     * @see #get(String)
     */
    public String get(String property, String defvalue) {
        return get(property, defvalue, null);
    }

    /**
     * Get the string value associated with the given property name, using the
     * default list of section names as the search list.
     * 
     * @param property
     *            the name of the property to look up
     * @return the value for <i>property </i>, or <code>null</code> if no
     *         value is found
     * @see #getSections()
     * @see #get(String, String, String[])
     * @see #get(String, String)
     */
    public String get(String property) {
        return get(property, null, null);
    }

    /**
     * Get the boolean value associated with the given property name, using the
     * default list of section names as the search list.
     * 
     * @param property
     *            the name of the property to look up
     * @param defaultvalue
     *            a default value of boolean type to return if property is not defined
     * @return the value for <i>property </i>, or <code>null</code> if no
     *         value is found
     * @see #getSections()
     * @see #get(String, String, String[])
     * @see #get(String, String)
     */
    public boolean getBool(String property, boolean defaultvalue) {
        String value = get(property, null, null);
        if (value == null)
            return defaultvalue;
        else
            return (value.toLowerCase().equals("true") ||
                    value.toLowerCase().equals("yes") ||
                    value.toLowerCase().equals("on"));
    }

    /**
     * Get the integer value associated with the given property name, using the
     * default list of section names as the search list.
     * 
     * @param property
     *            the name of the property to look up
     * @param defaultvalue
     *            a default value of int type to return if property is not defined
     * @return the value for <i>property </i>, or <code>null</code> if no
     *         value is found
     * @see #getSections()
     * @see #get(String, String, String[])
     * @see #get(String, String)
     */
    public int getInt(String property, int defaultvalue) {
        String value = get(property, null, null);
        if (value == null)
            return defaultvalue;
        else
            return (Integer.valueOf(value).intValue());
    }

    /**
     * Get the floating-point value associated with the given property name, using the
     * default list of section names as the search list.
     * 
     * @param property
     *            the name of the property to look up
     * @param defaultvalue
     *            a default value of type double to return if property is not defined
     * @return the value for <i>property </i>, or <code>null</code> if no
     *         value is found
     * @see #getSections()
     * @see #get(String, String, String[])
     * @see #get(String, String)
     */
    public double getDouble(String property, double defaultvalue) {
        String value = get(property, null, null);
        if (value == null)
            return defaultvalue;
        else
            return (Double.valueOf(value).doubleValue());
    }

    private void addPropertySet(String section_name, String s) {
        // empty current section
        Properties p = (Properties) values.get(section_name);
        if (p == null)
            p = new Properties();

        // System.err.println("\n**** Section is " + section_name + "\n");
        // System.err.println(s.replaceAll("\\\\", "\\\\\\\\"));

        try {
            ByteBuffer b = default_charset.encode(s.replaceAll("\\\\",
                    "\\\\\\\\"));
            p.load(new ByteArrayInputStream(b.array(), 0, b.limit()));
            values.put(section_name, p);
        } catch (IOException x) {
            x.printStackTrace(System.err);
        }
    }

    private void initializeFromInputStream(InputStream f) {

        if (f == null)
            return;

        String line = null;
        String current_section_name = null;
        StringBuffer buffer = new StringBuffer();
        buffer.setLength(0);
        Matcher m;

        try {

            BufferedReader r = new BufferedReader(new InputStreamReader(f,
                    default_charset));
            while ((line = r.readLine()) != null) {
                // System.err.println("line is <" + line + ">");
                m = section_name_pattern.matcher(line.trim());
                if (m.matches()) {
                    if (current_section_name != null)
                        addPropertySet(current_section_name, buffer.toString());
                    // clear buffer
                    buffer.setLength(0);
                    current_section_name = m.group(1);
                    // System.err.println("*** new section: " +
                    // current_section_name);
                } else {
                    if (line.trim().length() > 0)
                        buffer.append(line.trim() + "\n");
                }
            }
            if ((current_section_name != null) && (buffer.length() > 0))
                addPropertySet(current_section_name, buffer.toString());

            r.close();

        } catch (IOException x) {
            x.printStackTrace(System.err);
        }
    }

    /**
     * Construct a new Configurator from the specified input stream. Each
     * configurator has a number of named sections. When the <code>get</code>
     * method is called, each section in the list is searched in turn for a
     * value with the specified name. This constructor will use the default list
     * of client sections, which is
     * <code>{ <i>hostname</i>, <i>osname</i>, "client", "default" }</code>.
     * 
     * @param f
     *            an input stream containing the text of a config file.
     */
    public Configurator(InputStream f) throws IOException {

        initializeMachineConfig();

        values = new HashMap();
        sections = getClientSectionList();

        initializeFromInputStream(f);
    }

    /**
     * Construct a new Configurator from the default files, with the default
     * section list. Each configurator has a number of named sections. When the
     * <code>get</code> method is called, each section in the list is searched
     * in turn for a value with the specified name. This constructor will use
     * the default list of client sections, which is
     * <code>{ <i>hostname</i>, <i>osname</i>, "client", "default" }</code>.
     */
    public Configurator() throws IOException {

        initializeMachineConfig();

        values = new HashMap();
        sections = getClientSectionList();

        initializeFromInputStream(getSystemConfigFileStream());
        initializeFromInputStream(getUserConfigFileStream());
    }

    /**
     * Construct a new Configurator from the default files with the specified
     * sections search list. Each configurator has a number of named sections.
     * When the <code>get</code> method is called, each section in the list is
     * searched in turn for a value with the specified name.
     * 
     * @param sections
     *            specifies the section search list.
     */
    public Configurator(String[] sections) throws IOException {

        initializeMachineConfig();

        values = new HashMap();
        this.sections = sections;

        initializeFromInputStream(getSystemConfigFileStream());
        initializeFromInputStream(getUserConfigFileStream());
    }

    private static String[] getClientSectionList() throws IOException {

        initializeMachineConfig();

        String hostname = fqdnName();
        String osname = osName();

        Vector v = new Vector();

        if (MACHINE_ID != null) {
            v.add(MACHINE_ID);
        }
        if (hostname != null) {
            v.add(hostname);
        }
        if (osname != null) {
            v.add(osname);
        }
        v.add("client");
        v.add("default");

        return (String[]) v.toArray(new String[v.size()]);
    }

    private static InputStream getUserConfigFileStream() {
        try {
            String rcfile = System.getProperty("com.parc.uplib.rcfile");
            if (rcfile == null) {
                rcfile = System.getenv("UPLIBRC");
                if (rcfile == null) {
                    String homedir = System.getProperty("user.home");
                    if (homedir == null)
                        return null;
                    user_config_file = new File(homedir, USER_CONFIG_FILE_NAME);
                    if ((!user_config_file.exists()) || (!user_config_file.canRead()))
                        return null;
                } else {
                    user_config_file = new File(rcfile);
                    if ((!user_config_file.exists()) || (!user_config_file.canRead())) {
                        System.err.println("Config file specified by environment variable UPLIBRC does not exist or is not readable!");
                        return null;
                    }
                }
            } else {
                user_config_file = new File(rcfile);
                if ((!user_config_file.exists()) || (!user_config_file.canRead())) {
                    System.err.println("Config file specified by system property \"com.parc.uplib.rcfile\" does not exist or is not readable!");
                    return null;
                }
            }
            return new FileInputStream(user_config_file);
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
        return null;
    }

    private static InputStream getSystemConfigFileStream() throws IOException {

        initializeMachineConfig();

        try {
            site_config_file = new File(UPLIB_LIB_DIRECTORY, "site.config");
            if ((!site_config_file.exists()) || (!site_config_file.canRead()))
                return null;
            return new FileInputStream(site_config_file);
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
        return null;
    }

    /**
     * Reads the specified file and returns a Configurator object containing the
     * contents of that file. The section list is set to
     * <code>{ "client", "default" }</code>.
     * 
     * @param filename
     *            the name of the file to read
     * @return the config info in that file
     */
    public static Configurator readConfigFile(String filename) {
        try {
            String homedir = System.getProperty("user.home");
            if (homedir == null)
                return null;
            File configfile = new File(homedir, filename);
            if ((!configfile.exists()) || (!configfile.canRead()))
                return null;
            Configurator newv = new Configurator(
                    new FileInputStream(configfile));
            newv.setSections(new String[] { "client", "default" });
            return newv;
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
        return null;
    }

    private static Configurator readConfigFile() {
        return readConfigFile(".uplibrc");
    }

    /**
     * Returns the type of operating system the current machine is running. For
     * Windows (2000, NT, XP, or Me), this is "win32". For Mac OS X, this is
     * "Darwin". For Linux, this is "Linux". May return null if unknown.
     * 
     * @return the operating system descriptor (may be null)
     */
    public static String osName() {
        try {
            initializeMachineConfig();
        } catch (IOException x) {
            return null;
        }
        return OS_NAME;
    }

    /**
     * Returns the hostname of the current machine, along with the
     * fully-qualified domain name. For example, will return "foo.company.com",
     * instead of just "foo". May return null if not known.
     * 
     * @return the hostname (may be null)
     */
    public static String fqdnName() {
        try {
            initializeMachineConfig();
        } catch (IOException x) {
            return null;
        }
        return HOST_FQDN;
    }

    /**
     * Returns the UUID of the current machine, if present.
     * 
     * @return the UUID (may be the FQDN)
     */
    public static String machineID() {
        try {
            initializeMachineConfig();
        } catch (IOException x) {
            return null;
        }
        return MACHINE_ID;
    }

    ///////////////////////////////////////////////////////////////////
    // Code that reads manifest formatted files outside the jar
    ///////////////////////////////////////////////////////////////////

    public static class Parse822 {

        private java.util.jar.Attributes attrs;

        public Parse822(InputStream i) throws IOException {

            java.util.jar.Manifest m = new java.util.jar.Manifest(i);
            attrs = m.getMainAttributes();
            i.close();
        }

        public String getValue(String name) {
            return attrs.getValue(name);
        }

        public static Parse822 readFile(File f) throws IOException {
            return new Parse822(new FileInputStream(f));
        }
    }

    public static String replaceEncodedSpaces(String path) {
        return path.replaceAll("%20", " ");
    }

    public static File getClassDirectory(Class aClass) {
        String classEntry = aClass.getName().replaceAll("\\.","/") + ".class";
        
        URL[] roots = ((URLClassLoader) Configurator.class.getClassLoader()).getURLs();

        String path = null;
        for(int i=0; i < roots.length; i++) {
            URL cur = roots[i];
            if (cur.getProtocol().equals("file")) {
                if (cur.getPath().toLowerCase().endsWith("jar")) {
                    try {
                        JarFile f = new JarFile(replaceEncodedSpaces(cur.getPath()));
		        
                        // System.err.println("f is " + f + ", f.getEntry(\"" + classEntry + "\") is " + f.getEntry(classEntry));

                        if (f.getEntry(classEntry) != null) {
                            path = replaceEncodedSpaces(cur.getPath());
                            break;
                        }
                    }
                    catch (Exception e) {
                        e.printStackTrace(System.err);
                    }            
                }
                else {
                    File f = new File(replaceEncodedSpaces(cur.getPath())+"/"+classEntry);
                    // System.err.println("f is " + f);

                    if (f.exists()) {
                        path = replaceEncodedSpaces(cur.getPath());
                        break;
                    }
                }
            }
        }

        if (path == null) {
            return null;
        }
        
        File f = new File(path);
        if (!f.isDirectory()) {
            f = f.getParentFile();
        }

        return f;
    }

    public static File getFileInClassDirectory(String fileName) {
        File classParent = getClassDirectory(Configurator.class);
        return new File(classParent, fileName);
    }

    public static Parse822 getProperties(File f) throws IOException {
        return new Parse822(new FileInputStream(f));
    }

    public static String getProperty(String name, Parse822 locs, String defalt) {
        String r = System.getProperty(name);
        if (r == null) {
            r = locs.getValue(name.replace('.', '-'));
        }
        if (r == null) {
            r = defalt;
        }
        // System.err.println(name + ": " + r);
        return r;
    }

    private static synchronized void initializeMachineConfig()
            throws IOException {
        if (!initialized) {
            File machine_config_file = null;
            UPLIB_LIB_DIRECTORY = System.getProperty("com.parc.uplib.libdir");
            String mc_prop = System.getProperty("com.parc.uplib.machine-config-file");
            if (mc_prop != null) {
                File f = new File(mc_prop);
                if (f.exists())
                    machine_config_file = f;
            }
            if (machine_config_file == null)
                machine_config_file = new File(UPLIB_LIB_DIRECTORY, MACHINE_CONFIG_FILE_NAME);
            if (machine_config_file.exists()) {
                Parse822 locs = getProperties(machine_config_file);
                HOST_FQDN = getProperty("FQDN", locs, null);
                OS_NAME = getProperty("OS", locs, null);
                initialized = true;
            }
            boolean is_windows = System.getProperty("os.name").toLowerCase().startsWith("win");
            File idfile;
            if ((!is_windows) && (idfile = new File("/etc/uplib-machine-id")).canRead()){
                try {
                    BufferedReader r = new BufferedReader(new FileReader(idfile));
                    MACHINE_ID = r.readLine();
                    r.close();
                } catch (IOException x) {
                    System.err.println("" + x);
                    x.printStackTrace(System.err);
                }
            }
            if (MACHINE_ID == null)
                MACHINE_ID = HOST_FQDN;
        }
    }

    public static HashMap getEnvironment() {

        try {
            Process p = null;
            HashMap envVars = new HashMap();
            Runtime r = Runtime.getRuntime();
            String OS = System.getProperty("os.name").toLowerCase();

            if (OS.indexOf("windows 9") > -1) {
                p = r.exec( "command.com /c set" );
            }
            else if ( (OS.indexOf("nt") > -1) ||
                      (OS.indexOf("windows 2000") > -1) ||
                      (OS.indexOf("windows xp") > -1) ||
                      (OS.indexOf("windows vista") > -1) ||
                      (OS.indexOf("windows 7") > -1) ||
		      (OS.indexOf("windows ") > -1) ) {
                // thanks to JuanFran for the xp fix!
                p = r.exec( "cmd.exe /c set" );
            }
            else {
                // our last hope, we assume Unix (thanks to H. Ware for the fix)
                p = r.exec( "env" );
            }
            BufferedReader br = new BufferedReader
                ( new InputStreamReader( p.getInputStream() ) );
            String line;
	    while( (line = br.readLine()) != null ) {
		try {
		    int idx = line.indexOf( '=' );
		    String key = line.substring( 0, idx );
		    String value = line.substring( idx+1 );
		    envVars.put( key, value );
		} catch (Exception x) {
		    System.err.println("Error parsing line <" + line + ">");
		    x.printStackTrace(System.err);
		}
	    }
            return envVars;
        } catch (IOException x) {
            System.err.println("IOException reading environment variables:  " + x);
            x.printStackTrace(System.err);
            return null;
        }
    }
    
    public static File[] knownLocalRepositories () {
	boolean is_mac = System.getProperty("os.name").toLowerCase().startsWith("mac");
	boolean is_windows = System.getProperty("os.name").toLowerCase().startsWith("win");
        String machine_id = machineID();

        // locate file with list of repositories
        File listfile = null;
        File homedir = new File(System.getProperty("user.home"));

        if (is_mac) {
            listfile = new File(homedir, "Library/Application Support/com.parc.uplib/" + machine_id + "-repositories");
        } else if (is_windows) {
            HashMap env = getEnvironment();
            if (env.containsKey("APPDATA")) {
                listfile = new File((String) env.get("APPDATA"), "UpLib-config/repositories");
            } else if (env.containsKey("USERPROFILE")) {
                listfile = new File((String) env.get("USERPROFILE"), "Application Data/UpLib-config/repositories");
            } else if (env.containsKey("HOMEDIR") && env.containsKey("HOMEPATH")) {
                listfile = new File((String) env.get("HOMEDIR") + "/" + (String) env.get("HOMEPATH"), "UpLib-config/repositories");
            } else {
                listfile = new File(homedir, ".uplib/" + machine_id + "-repositories");
            }
        } else {
            listfile = new File(homedir, ".uplib/" + machine_id + "-repositories");
        }

        if (!listfile.canRead())
            return new File[0];
        try {
            Vector v = new Vector();
            String s;
            BufferedReader r = new BufferedReader(new FileReader(listfile));
            while ((s = r.readLine()) != null) {
                String[] tokens = s.trim().split("\\s+");
                if ((tokens.length > 0) && (tokens[0].length() > 0)) {
                    File f = new File(URLDecoder.decode(tokens[0], "UTF-8"));
                    boolean already_there = false;
                    for (int i = 0;  i < v.size();  i++) {
                        File f2 = (File) v.get(i);
                        if (f.getCanonicalPath().equals(f2.getCanonicalPath()))
                            already_there = true;
                    }
                    if (f.exists() && (!already_there))
                        v.add(f);
                }
            }
            r.close();
            File[] repodirs = new File[v.size()];
            return (File[]) v.toArray(repodirs);
        } catch (IOException x) {
            System.err.println("" + x);
            x.printStackTrace(System.err);
        }
        return new File[0];
    }

    /**
     * For debugging config files. Invoke this class alone, and it will read
     * your init file and the system-wide init file, and print all the sections
     * found and the values contained in each section.
     */
    public static void main(String[] argv) {
        try {
            System.err.println("UPLIBRC is " + System.getenv("UPLIBRC"));
            System.err.println("user.home is " + System.getProperty("user.home"));

            Configurator mapping = null;
            if (argv.length < 1 || argv[0].equals("$")) {
                mapping = new Configurator();
	    }
            else
                mapping = new Configurator(new FileInputStream(argv[0]));
            System.err.println("User config file is " + user_config_file);
            System.err.println("Site config file is " + site_config_file);
            String[] client_sections = getClientSectionList();
            System.err.println("Client section list:");
            for (int i = 0;  i < client_sections.length;  i++) {
                System.err.println("    " + client_sections[i]);
            }
            String[] conf_sections = mapping.getSections();
            System.err.println("Configurator sections:");
            for (int i = 0;  i < conf_sections.length;  i++) {
                System.err.println("    " + conf_sections[i]);
            }
            if (argv.length < 2) {
                String[] sections = mapping.getSections();
                System.err.print("Sections are");
                for (int i = 0; i < sections.length; i++)
                    System.err.print(" \"" + sections[i] + "\"");
                System.err.println("");
                mapping.list(System.err);
            } else
                for (int i = 1; i < argv.length; i++)
                    System.err.println(argv[i] + ":  " + mapping.get(argv[i]));

        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
    }
}
