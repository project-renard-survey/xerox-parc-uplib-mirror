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
import java.util.Vector;

public abstract class AnnotationStreamHandler {

    public static interface Listener {

        public void newAnnotation(Annotation a);

    }

    private ByteArrayOutputStream bstream;
    private int capacity;
    protected Vector listeners;
    private boolean initialized;

    public AnnotationStreamHandler (int bufsize) {
        capacity = bufsize;
        bstream = new ByteArrayOutputStream(bufsize);
        listeners = null;
        initialized = false;
    }

    abstract protected void initializeOutputStream (OutputStream os) throws IOException;

    abstract public byte[] encode (String doc_id, int page_no, int selector, Annotation o, int format_version) throws IOException;

    abstract protected void emptyBuffer (ByteArrayOutputStream b);

    public void addListener (Listener listener) {
        synchronized(listeners) {
            if (listeners == null)
                listeners = new Vector();
            listeners.add(listener);
        }
    }

    public void removeListener (Listener listener) {
        synchronized(listeners) {
            if (listeners != null)
                listeners.remove(listener);
        }
    }

    protected void notifyListeners (Object ann) {
        if (listeners != null) {
            for (int i = 0;  i < listeners.size();  i++) {
                ((Listener)(listeners.get(i))).newAnnotation((Annotation)ann);
            }
        }
    }

    public void addAnnotation (Annotation ann, String document_id, int page_no, int selector) throws IOException {
        if (!initialized) {
            initializeOutputStream(bstream);
            initialized = true;
        }

        try {
            byte[] outbuffer = encode(document_id, page_no, selector, ann, 0);
            synchronized(bstream) {
                if ((outbuffer.length + bstream.size()) >= capacity) {
                    System.err.println("outbuffer is full (" + (capacity - bstream.size()) + ", need "
                                       + outbuffer.length + "), flushing");
                    emptyBuffer(bstream);
                    initializeOutputStream(bstream);
                }
            }
            bstream.write(outbuffer, 0, outbuffer.length);
            notifyListeners(ann);
        } catch (IOException e) {
            System.err.println("Exception writing scribble to output stream:  " + e);
            e.printStackTrace(System.err);
        }
    }

    public void flush() throws IOException {
        synchronized(bstream) {
            if (bstream.size() > 0) {
                emptyBuffer(bstream);
                initializeOutputStream(bstream);
            }            
        }
    };
}
