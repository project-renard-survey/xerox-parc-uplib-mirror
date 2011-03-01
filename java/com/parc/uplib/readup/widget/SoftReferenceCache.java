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

import java.lang.ref.*;
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

import java.util.zip.CRC32;

/**
 * This interface is used to fetch an instance of some resource -- a
 * PageText object, a page thumbnail, whatever, from storage.
 */
public class SoftReferenceCache {

    /**
     * DocViewerCallbacks can implement this interface to
     * indicate to the loading thread whether loading is still necessary at
     * the point when the thread is ready to load the resource
     * @author good
     */    
    public static interface FinalLoadChecker {
        public boolean shouldLoad();
    }
    
    private static class StrongRefs extends LinkedList {

        private int max_size;

        public StrongRefs (int max_size) {
            super();
            this.max_size = max_size;
        }

        public boolean add (Object o) {
            super.add(o);
            while (size() > max_size) {
                removeFirst();
            }
            return true;
        }
    }

    static class ResourceID implements Comparable {

        public String                  doc_id;
        public int                     page_no;
        public int                     selector;
        public DocViewerCallback       callback;
        private int                    hash;

        ResourceID (String doc_id, int page_no, int selector, DocViewerCallback callback) {
            this.doc_id = doc_id;
            this.page_no = page_no;
            this.selector = selector;
            this.callback = callback;
            CRC32 h = new CRC32();
            h.update(new String(doc_id + ":" + page_no + ":" + selector).getBytes());
            this.hash = (int) h.getValue();
        }

        public int compareTo (Object o) {
            ResourceID k2 = (ResourceID) o;
            int val = doc_id.compareTo(k2.doc_id);
            if (val == 0) {
                val = (page_no - k2.page_no);
                if (val == 0) {
                    val = (selector - k2.selector);
                }
            }
            System.err.println("" + this + " is " + ((val < 0) ? "less than" : ((val == 0) ? "equal to" : "greater than")) + " " + o);
            return val;
        }

        public boolean equals(Object o) {
            return ((o instanceof ResourceID) && this.doc_id.equals(((ResourceID)o).doc_id) && (this.page_no == ((ResourceID)o).page_no) && (this.selector == ((ResourceID)o).selector));
        }

        public int hashCode () {
            return hash;
        }

        public String toString () {
            return "<ResourceID " + doc_id + "/" + page_no + "/" + selector + ((callback != null) ? "*" : "") + " " + Integer.toHexString(hashCode()) + ">";
        }
    }

    static class FetchThread extends Thread {

        private ResourceLoader  loader;
        private Vector          request_queue;
        private Map             cache;
        private StrongRefs      strong_refs;

        FetchThread (String name, ResourceLoader loader, Map cache, StrongRefs strong_refs) {
            super(name);
            this.loader = loader;
            this.request_queue = new Vector();
            this.cache = cache;
            this.strong_refs = strong_refs;
            setDaemon(true);
        }
        
        public boolean hasRequest(String docID, int pageno, int selector) {
        	synchronized(this) {
        		for (int i = 0, m = request_queue.size(); i<m; i++) {
        			ResourceID rID = (ResourceID) request_queue.get(i);
        			if (rID.doc_id.equals(docID) && rID.page_no == pageno && rID.selector==selector) return true;
        		}
        	}
        	return false;
        }

        public void add (ResourceID req) {
            synchronized(this) {
                request_queue.add(0, req);
                notify();
            }
        }

        public void run () {
            int i;
            ResourceID current = null, tmp;
            try {
                while (true) {
                    try {
                        current = null;
                        synchronized(this) {
                            if (request_queue.size() > 0) {

                                // callback requests are prioritized above non-callback requests
                                for (i = 0;  (current == null) && (i < request_queue.size());  i++) {
                                    tmp = (ResourceID) request_queue.get(i);
                                    if (tmp.callback != null) {
                                        request_queue.remove(i);
                                        current = tmp;
                                    }
                                }
                                // no callback requests
                                if (current == null) {
                                    current = (ResourceID) request_queue.remove(0);
                                }
                            }
                            if (current == null) {
                                wait();
                            }
                        }
                        if (current != null) {

                            Exception fetch_exception = null;
                            Object o = null;

                            // see if it's now in the cache
                            synchronized(cache) {
                                SoftReference ref;
                                if ((ref = (SoftReference) cache.get(current)) != null)
                                    o = ref.get();
                            }

                            // if not, load it
                            if (o == null) {
                                // load the resource
                                try {
                                    // We make one final check before loading the resource
                                    // to see if the call back still wants this resource loaded
                                    if (current.callback == null ||
                                        !(current.callback instanceof FinalLoadChecker) ||
                                        ((FinalLoadChecker)current.callback).shouldLoad()) {
                                        o = loader.getResource(current.doc_id, current.page_no, current.selector);
                                    }
                                    // System.err.println("%%% loaded " + o + " from loader");
                                } catch (Exception x) {
                                    fetch_exception = x;
                                }
                            }

                            try {
                                if (o != null) {
                                    synchronized(cache) {
                                        cache.put(current, new SoftReference(o));
                                        // System.err.println("%%% " + o + " now in cache as " + current);
                                        strong_refs.add(o);
                                    }
                                    if (current.callback != null) {
                                        // System.err.println("%%% calling callback for " + o);
                                        current.callback.call((fetch_exception == null) ? o : fetch_exception);
                                        current.callback = null;
                                    }
                                }
                            } catch (Exception x) {
                                System.err.println("Exception fetching " + current);
                                x.printStackTrace(System.err);
                            }
                        }
                    } catch (InterruptedException x) {
                        // ignore it
                    } catch (Exception x) {
                        System.err.println("Unexpected exception in loader fetch thread for " + loader);
                        x.printStackTrace(System.err);
                    }
                }
            } catch (Exception x) {
                System.err.println("Exiting loader fetch thread for " + loader + " due to exception:");
                x.printStackTrace(System.err);
            }
        }
    }

    private StrongRefs strong_refs;
    private Map soft_cache;
    private FetchThread fetch_thread;
    private int capacity;
    private ResourceLoader loader;

    public SoftReferenceCache (ResourceLoader loader, int min_capacity) {
        this.loader = loader;
        this.capacity = min_capacity;
        this.strong_refs = new StrongRefs(min_capacity);
        this.soft_cache = Collections.synchronizedMap(new HashMap());
        this.fetch_thread = new FetchThread(this.toString(), loader, this.soft_cache, this.strong_refs);
        fetch_thread.start();
    }

    public ResourceLoader getLoader() {
        return this.loader;
    }

    public String toString () {
        return "<SoftReferenceCache " + this.capacity + " " + this.loader + " " + Integer.toHexString(hashCode()) + ">";
    }

    public void put (String doc_id, int pageno, int selector, Object o) {
        ResourceID id = new ResourceID(doc_id, pageno, selector, null);
        synchronized (soft_cache) {
            soft_cache.remove(id);
            soft_cache.put(id, new SoftReference(o));
            strong_refs.add(o);
        }
    }

    public Object get (String doc_id, int pageno, int selector, DocViewerCallback callback) {
        Object retval = null;
        ResourceID id = new ResourceID(doc_id, pageno, selector, callback);
        SoftReference ref = null;
        /*
        // some debugging code to look at the stack
        System.err.println("*** " + id + " requested.");
        Throwable t = new Throwable();
        t.fillInStackTrace();
        t.printStackTrace(System.err);
        */
        // System.err.println(this.toString() + ":  strong_refs size is " + strong_refs.size());
        synchronized (soft_cache) {
            ref = (SoftReference) soft_cache.get(id);
            if (ref != null) {
            	retval = ref.get();
                if (retval != null) {
                    strong_refs.add(retval);
                    if (callback != null) callback.call(retval);
                    return retval;
                } else {
                    System.err.println("" + id + " was GC'ed; re-fetching...");
                }
            }
        }
        // queue a request for this resource
        fetch_thread.add(id);
        return null;
    }
    
    public boolean fetchThreadHasRequest(String doc_id, int pageno, int selector) {
    	boolean result = false;
    	result = fetch_thread.hasRequest(doc_id, pageno, selector);
    	return result;
    }

    public Object check (String doc_id, int pageno, int selector) {
        Object retval = null;
        ResourceID id = new ResourceID(doc_id, pageno, selector, null);
        SoftReference ref = null;
        /*
        // some debugging code to look at the stack
        System.err.println("*** " + id + " requested.");
        Throwable t = new Throwable();
        t.fillInStackTrace();
        t.printStackTrace(System.err);
        */
        // System.err.println(this.toString() + ":  strong_refs size is " + strong_refs.size());
        synchronized (soft_cache) {
            if ((ref = (SoftReference) soft_cache.get(id)) != null) {
                if ((retval = ref.get()) != null) {
                    strong_refs.add(retval);
                    return retval;
                }
            }
        }
        return null;
    }

    public void clear () {
        // hold the lock on the fetch thread so that it stops at the top of its loop
        synchronized(fetch_thread) {
            // hold the lock on the soft_cache so nothing else can affect it.
            // This effectively locks the strong_refs as well.
            synchronized(soft_cache) {
                strong_refs.clear();
                for (Iterator iter = soft_cache.values().iterator();  iter.hasNext();  ) {
                    SoftReference r = (SoftReference) (iter.next());
                    // only remove actual values, not potential values
                    if (r.get() != null)
                        iter.remove();
                }
            }
        }
    }
}

