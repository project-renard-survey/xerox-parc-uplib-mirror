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
import java.net.URL;

/**
 * This interface is used to fetch an instance of some resource -- a
 * PageText object, a page thumbnail, whatever, from storage.
 */
public class CachingLoader implements ResourceLoader {

    static private File cache_location = null;

    private String repo_id;
    protected String cache_type;

    public CachingLoader (URL repository, String cache_type) {
    	this.cache_type = cache_type;
        if ((repository != null) && (cache_type != null)) {
            //this.cache_type = cache_type;
            this.repo_id = repository.getHost() + "-" + repository.getPort();
        } else {
            //this.cache_type = null;
            this.repo_id = null;
        }
    }

    public boolean caching() {
        return ((repo_id != null) && (cache_location != null));
    }

    public Object getResource (String document_id, int page_index, int selector)
        throws IOException {

        // System.err.println("looking for " + repo_id + "/" + document_id + "/" + page_index + "/" + selector + "...");

        if ((cache_location == null) || (repo_id == null))
            return null;
        try {
            File cache_file = new File(new File(new File(new File(new File(cache_location,
                                                                           repo_id),
                                                                  document_id),
                                                         cache_type),
                                                Integer.toString(page_index)),
                                       Integer.toString(selector));
            if (!cache_file.exists())
                return null;
            ObjectInputStream oos = new ObjectInputStream(new FileInputStream(cache_file));
            Object o = null;
            try {
                o = oos.readObject();
            } catch (ClassNotFoundException x) {
                System.err.println("ClassNotFoundException for " + cache_type + " " + repo_id + "/" + document_id + "/" + page_index + "/" + selector + " in file cache");
            } catch (InvalidClassException x) {
                System.err.println("InvalidClassException for " + cache_type + " " + repo_id + "/" + document_id + "/" + page_index + "/" + selector + " in file cache");
            } catch (OptionalDataException x) {
                System.err.println("InvalidClassException for " + cache_type + " " + repo_id + "/" + document_id + "/" + page_index + "/" + selector + " in file cache");
            } catch (StreamCorruptedException x) {
                System.err.println("StreamCorruptedException for " + cache_type + " " + repo_id + "/" + document_id + "/" + page_index + "/" + selector + " in file cache");
            }
            oos.close();
            // System.err.println("loaded " + cache_type + " " + repo_id + "/" + document_id + "/" + page_index + "/" + selector + " from file cache");
            return o;
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
        return null;
    }

    public void cacheResource (String document_id, int page_index, int selector, java.io.Serializable resource)
        throws IOException {

        if ((cache_location == null) || (repo_id == null))
            return;

        File cache_dir = new File(new File(new File(new File(cache_location,
                                                             repo_id),
                                                    document_id),
                                           cache_type),
                                  Integer.toString(page_index));
        if (!cache_dir.exists())
            cache_dir.mkdirs();
        File cache_file = new File(cache_dir, Integer.toString(selector));
        if (cache_file.exists())
            return;
        ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream(cache_file));
        oos.writeObject(resource);
        oos.flush();
        oos.close();
        return;
    }

    public static boolean setCacheDirectory (File dir) throws java.io.IOException, java.lang.SecurityException {

        try {
            if (!dir.exists())
                dir.mkdirs();
            else if (!dir.isDirectory()) {
                System.err.println("Specified cache location " + dir + " is not a directory.");
                return false;
            }
            if (dir.canWrite()) {
                cache_location = dir;
                return true;
            } else {
                System.err.println("Can't write in specified directory " + dir);
                return false;
            }
        } catch (java.security.AccessControlException x) {
            // can't read machine.config, because in an applet
            System.err.println("Can't use " + dir + " because of exception " + x);
            return false;
        }
    }
}
