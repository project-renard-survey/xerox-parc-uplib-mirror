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

package com.parc.uplib.readup.uplibbinding;

import java.io.*;
import java.lang.ref.WeakReference;
import java.util.zip.*;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;
import java.util.AbstractCollection;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Hashtable;
import java.util.TreeMap;
import java.util.Calendar;
import java.util.Date;
import java.util.Enumeration;
import java.util.GregorianCalendar;
import java.util.Properties;
import java.util.Iterator;
import java.util.Map;
import java.util.Set;
import java.util.Vector;
import java.util.NoSuchElementException;
import java.util.regex.Pattern;
import java.util.regex.Matcher;
import java.net.URL;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.net.URI;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;

import com.parc.uplib.util.MetadataFile;
import com.parc.uplib.util.CertificateHandler;
import com.parc.uplib.readup.widget.SoftReferenceCache;
import com.parc.uplib.readup.widget.ResourceLoader;
import com.parc.uplib.readup.widget.ResourceLoader.CommunicationFailure;
import com.parc.uplib.readup.widget.ResourceLoader.PrivilegeViolation;
import com.parc.uplib.readup.widget.AnnotationStreamHandler;
import com.parc.uplib.readup.widget.Scribble;
import com.parc.uplib.readup.widget.HotSpot;
import com.parc.uplib.readup.widget.DocViewerCallback;

/**
   This class provides an interface to an UpLib repository and the documents in it.
   It provides easy ways to retrieve the various data loaders for a document, and
   provides for search over the repository.
*/
public class Repository implements Serializable {

    /* This variable keeps track of the known repositories as weak refs,
       so that they can be GCed.
    */
    private static HashMap known_repositories = new HashMap();

    private URL repository_url;
    private transient String repository_password = null;
    private String repository_cookie;

    private transient SoftReferenceCache hi_res_cache = null;
    private transient SoftReferenceCache icon_cache = null;
    private transient SoftReferenceCache page_image_cache = null;
    private transient SoftReferenceCache thumbnail_cache = null;
    private transient SoftReferenceCache pagetext_cache = null;
    private transient SoftReferenceCache notes_cache = null;

    private transient HashMap rep_documents;
    private transient TreeMap rep_categories;
    private transient TreeMap rep_collections;
    private transient TreeMap rep_authors;
    private transient Action[] document_functions = null;
    private transient Action[] user_actions = null;
    private transient MetadataFile rep_metadata = null;
    private transient String url_string;
    private String rep_name;

    private transient Long index_file_read_time = null;

    /**
       Convert a date in "mm/dd/yy" or "mm/dd/yyyy" format to a java Date instance.
       @param slashed_date the date in "mm/dd/yy" or "mm/dd/yyyy" format.  Either "mm" or "dd" may be 0.
    */
    public static Date convert_date (String slashed_date) {
        int year, month, day;
        try {
            String[] parts = slashed_date.split("/");
            int current_year = Calendar.getInstance().get(Calendar.YEAR);
            int current_century = (current_year - (current_year % 100));
            if (parts.length == 3) {
                month = Integer.parseInt(parts[0]);
                day = Integer.parseInt(parts[1]);
                year = Integer.parseInt(parts[2]);
            } else if (parts.length == 2) {
                day = 0;
                month = Integer.parseInt(parts[0]);
                year = Integer.parseInt(parts[1]);
            } else {
                day = 0;
                month = 0;
                year = Integer.parseInt(parts[0]);
                if (year > 3000)
                    return null;
            }
            if (year < (current_year % 100))
                year += current_century;
            else if (year < 100)
                year += (current_century - 100);
            return new GregorianCalendar(year, (month == 0) ? 0 : month-1, (day == 0) ? 1 : day).getTime();
        } catch (Exception e) {
            return null;
        }
    }

    /**
       This class provides an abstraction of an UpLib document.
     */

    public class Document {
        private transient MetadataFile metadata = null;
        private String doc_id = null;
        private transient Properties parameters = null;
        private transient Action[] cached_document_functions = null;
        
        private String title;
        private transient ArrayList authors;
        private transient ArrayList categories;
        private GregorianCalendar date;
        private int pagecount;

        private transient UpLibScribbleHandler scribble_handler = null;
        private transient UpLibHotspotHandler hotspot_handler = null;
        private transient UpLibActivityLogger activity_logger = null;

        /**
           Constructor for a new document.
           @param id the document id for this document
        */
        public Document (String id) {
            doc_id = id;
            metadata = null;
            parameters = null;
            title = null;
            authors = null;
            categories = null;
            date = null;
            pagecount = -1;
        }

        /**
           Constructor for a new document.
           @param id the document id for this document
           @param title the title of the document
           @param authors the authors of the document
           @param date the date the document was published
        */
        public Document (String id, String title, Date date) {
            doc_id = id;
            metadata = null;
            parameters = null;
            this.title = title;
            this.authors = null;
            this.categories = null;
            if (date != null) {
                this.date = new GregorianCalendar();
                this.date.setTime(date);
            } else {
                this.date = null;
            }
            this.pagecount = -1;
        }

        /**
           @return a human-readable string name for the document
        */
        public String toString() {
            if (title == null) {
                if (metadata != null)
                    title = metadata.get("title");
            }
            return "<Document " + ((title == null) ? "" : "\"" + title + "\" ") + Repository.this.toString() + " " + doc_id + ">";
        }

        /**
           @return the title of the document, or null
        */
        public String getTitle() {
            if (title == null)
                title = getMetadataProperty("title");
            return title;
        }

        /**
           @return the date of the document, or null if it doesn't have one
        */
        public Date getDate() {
            if (date == null) {
                String v = getMetadataProperty("date");
                if (v != null) {
                    Date v2 = convert_date(v);
                    if (v2 != null) {
                        date = new GregorianCalendar();
                        date.setTime(v2);
                    } else {
                        System.err.println("null Date for date string \"" + v2 + "\", docid = " + doc_id);
                    }
                }
            }
            if (date != null)
                return date.getTime();
            else
                return null;
        }

        /**
           Convenience function to return the year of a document, because the dopey Java
           interface is so clumsy.
           @return the year the document was published, or -1 if no year is known.
        */
        public int getYear() {
            getDate();
            if (this.date != null)
                return this.date.get(Calendar.YEAR);
            else
                return -1;
        }

        /**
           @return the number of pages in the document
        */
        public int getPageCount() {
            if (pagecount == -1) {
                String a = getMetadataProperty("page-count");
                try {
                    pagecount = Integer.parseInt(a);
                } catch (Exception x) {
                    System.err.println("Can't get page-count for document " + getID() + " (" + getTitle() + ") from string value \"" + a + "\".");
                    x.printStackTrace(System.err);
                    pagecount = 0;
                }
            }
            return pagecount;
        }

        private void calcCategories() {
            if ((categories == null) && (metadata != null)) {
                String s = metadata.get("categories");
                if (s != null) {
                    String[] v = s.split(",");
                    categories = new ArrayList(v.length);
                    for (int i = 0;  i < v.length;  i++) {
                        String cname = v[i].trim();
                        Category c;
                        if ((rep_categories != null) && ((c = (Category) (rep_categories.get(cname))) != null)) {
                            if (!categories.contains(c)) {
                                categories.add(c);
                            }
                        } else {
                            c = new Category(cname);
                            c.addDocument(this);
                            if (rep_categories == null)
                                rep_categories = new TreeMap();
                            rep_categories.put(cname, c);
                            categories.add(c);
                        }
                    }
                }
            }
        }

        private String figureAuthorNameString (String original) {
            // must repeat Python algorithm here
            return original;
        }

        private void calcAuthors() {
            if ((authors == null) && (metadata != null)) {
                String astr = getMetadataProperty("authors");
                if (astr != null) {
                    String[] alist = astr.split(" and ");
                    authors = new ArrayList(alist.length);
                    for (int i = 0;  i < alist.length;  i++) {
                        Author a;
                        String aname = figureAuthorNameString(alist[i].trim());
                        if (aname.length() > 0) {
                            if ((rep_authors != null) && ((a = (Author)(rep_authors.get(aname))) != null)) {
                                if (!authors.contains(a)) {
                                    authors.add(a);
                                }
                            } else {
                                a = new Author(alist[i].trim());
                                a.addDocument(this);
                                if (rep_authors == null)
                                    rep_authors = new TreeMap();
                                rep_authors.put(aname, a);
                                authors.add(a);
                            }
                        }
                    }
                }
            }
        }

        /**
           @return whether or not the document is in the specified Category
        */
        public boolean inCategory(Category c) {
            calcCategories();
            return ((categories != null) ? categories.contains(c) : false);
        }

        /**
           @return an iterator over the document's categories
        */
        public Iterator getCategories() {
            calcCategories();
            return ((categories != null) ? categories.iterator() : null);
        }

        /**
           @param category add this category to the document
        */
        public void addCategory (Category c) {
            if ((c == null) || (categories == null))
                System.err.println("Adding category " + c + " to document categories " + categories);
            if (!inCategory(c)) {
                if (categories == null)
                    categories = new ArrayList();
                categories.add(c);
                // TODO:  Preserve category info back at server, by calling "doc_update"
            }
        }

        /**
           @param category remove this category from the document
        */
        public void removeCategory (Category c) {
            if (inCategory(c)) {
                categories.remove(c);
                // TODO:  Preserve category info back at server, by calling "doc_update"
            }
        }

        /**
           @return an iterator over the document's authors
        */
        public Iterator getAuthors() {
            calcAuthors();
            return ((authors != null) ? authors.iterator() : null);
        }

        /**
           @return whether the document has the specified author
        */
        public boolean hasAuthor(Author a) {
            calcAuthors();
            return ((authors != null) ? authors.contains(a) : false);
        }

        /**
           @return an AnnotationStreamHandler suitable for use with this document.  It's
           constructed if necessary.
        */
        public AnnotationStreamHandler getScribbleHandler () {
            if (scribble_handler == null) {
                try {
                    URL source_url = null;
                    URL sink_url = null;
                    String source = getParameter("scribble-source-url", null);
                    String sink = getParameter("scribble-sink-url", null);
                    if (source != null)
                        source_url = new URL(repository_url, source);
                    if (sink != null)
                        sink_url = new URL(repository_url, sink);
                    scribble_handler = new UpLibScribbleHandler(doc_id, repository_password, sink_url, source_url);
                } catch (MalformedURLException e) {
                    e.printStackTrace(System.err);
                }
                scribble_handler.setCookie(repository_cookie);
            }
            return (AnnotationStreamHandler) scribble_handler;
        }
        
        /**
           @return the scribbles for this document
        */
        public Scribble[] getScribbles() {
            UpLibScribbleHandler ulsh = (UpLibScribbleHandler) getScribbleHandler();
            if (ulsh != null)
                return ulsh.readScribbles();
            else
                return null;
        }

        /**
           @return an AnnotationStreamHandler suitable for use with this document.  It's
           constructed if necessary.
        */
        public AnnotationStreamHandler getHotspotHandler () {
            if (hotspot_handler == null) {
                try {
                    URL source_url = null;
                    URL sink_url = null;
                    String source = getParameter("hotspots-source-url", null);
                    String sink = getParameter("hotspots-sink-url", null);
                    if (source != null)
                        source_url = new URL(repository_url, source);
                    if (sink != null)
                        sink_url = new URL(repository_url, sink);
                    hotspot_handler = new UpLibHotspotHandler(doc_id, repository_password, sink_url, source_url, null);
                } catch (IOException x) {
                    x.printStackTrace(System.err);
                }
                hotspot_handler.setCookie(repository_cookie);
            }
            return (AnnotationStreamHandler) hotspot_handler;
        }

        /**
           @param an optional callback used to invoke the "open" operation on the URL, if clicked upon.  May be null.
           @return the HotSpots for this document
        */
        public HotSpot[] getHotspots(DocViewerCallback cb) {
            UpLibHotspotHandler ulhh = (UpLibHotspotHandler) getHotspotHandler();
            if (ulhh != null)
                return ulhh.readHotspots(cb);
            else
                return null;
        }

        /**
           @return a DocViewerCallback suitable for use logging activities on
           this document.  It's constructed if necessary.
        */
        public DocViewerCallback getActivityLogger () {
            if (activity_logger == null) {
                try {
                    URL sink_url = null;
                    String sink = getParameter("activity-sink-url", null);
                    if (sink != null)
                        sink_url = new URL(repository_url, sink);
                    activity_logger = new UpLibActivityLogger(doc_id, sink_url, repository_password);
                } catch (IOException x) {
                    x.printStackTrace(System.err);
                }
                activity_logger.setCookie(repository_cookie);
            }
            return (DocViewerCallback) activity_logger;
        }

        /**
           @return The SoftReferenceCache for loading the notes for this document.
        */
        public SoftReferenceCache getNotesLoader() {
            return notes_cache;
        }

        /**
           @return The AnnotationStreamHandler for saving the notes for this document.
        */
        public AnnotationStreamHandler getNotesHandler() {
            return (AnnotationStreamHandler) (notes_cache.getLoader());
        }

        /**
           @return The SoftReferenceCache for loading the standard page images (big thumbnails) for this document.
        */
        public SoftReferenceCache getPageImageLoader() {
            return page_image_cache;
        }

        /**
           @return The SoftReferenceCache for loading the page texts for this document.
        */
        public SoftReferenceCache getPageTextLoader() {
            return pagetext_cache;
        }

        /**
           @return The SoftReferenceCache for loading the small page thumbnails for this document.
        */
        public SoftReferenceCache getPageThumbnailLoader() {
            return thumbnail_cache;
        }

        /**
           @return The SoftReferenceCache for loading the high-resolution page images for this document.
        */
        public SoftReferenceCache getPageHiResLoader() {
            return hi_res_cache;
        }

        /**
           Fetches the document icon for this document.  May return null if the icon is not
           in the cache.
           @return a BufferedImage containing the icon, or null
        */
        public BufferedImage getIcon () {
            return (BufferedImage) (icon_cache.get(doc_id, -1, 0, null));
        }

        /**
           Fetches the document icon for this document.  May return null if the icon is not
           in the cache.
           @param callback A DocViewerCallback to invoke later when the icon becomes available
           @return a BufferedImage containing the icon, or null
        */
        public BufferedImage getIcon (DocViewerCallback callback) {
            return (BufferedImage) (icon_cache.get(doc_id, -1, 0, callback));
        }

        /**
           Stores a BufferedImage version of the document in the icon cache.
           @param icon a BufferedImage containing the icon image
        */
        public void setIcon (BufferedImage icon) {
            icon_cache.put(doc_id, -1, 0, icon);
        }

        /**
           Looks up a particular metadata item in the document's metadata, and returns
           the value for it, or null if it has no value.  The metadata will be fetched
           from the repository if necessary.
           @param pname the metadata item to fetch
           @return a String giving the value of the item, or null if it's not present.
        */
        public String getMetadataProperty(String pname) {
            MetadataFile mfile = getMetadata();
            if (mfile == null)
                return null;
            else
                return mfile.get(pname);
        }

        /**
           Sets the current metadata file for the document to be m.
           @param m a MetadataFile to use
        */
        void setMetadata(MetadataFile m) {
            metadata = m;
        }

        /**
           Returns the metadata for the document.
        */
        public MetadataFile getMetadata() {
            if (metadata == null) {

                try {
                    URL u = new URL(repository_url, "/action/externalAPI/doc_metadata?doc_id=" + doc_id);
                    // System.err.println("getMetadata URL is " + u.toExternalForm() + ", password is " + repository_password);
                    HttpURLConnection h = (HttpURLConnection) u.openConnection();
                    if (repository_password != null)
                        h.setRequestProperty("Password", repository_password);
                    if (repository_cookie != null)
                        h.setRequestProperty("Cookie", repository_cookie);
                    int rcode = h.getResponseCode();
                    if (rcode != 200) {
                        System.err.println("Response code is " + rcode);
                        System.err.println("Content is: " + h.getResponseMessage());
                        if (rcode == 401)
                            throw new ResourceLoader.PrivilegeViolation("Server returned UNAUTHORIZED HTTP code");
                    } else {
                        metadata = new MetadataFile(new InputStreamReader((java.io.InputStream) (h.getContent())));
                    }
                } catch (Exception e) {
                    System.err.println("Exception raised for document " + doc_id + ":  " + e);
                    e.printStackTrace(System.err);
                }
            }
            return metadata;
        }

        public Action[] getDocumentFunctions() {
            if (cached_document_functions == null) {
                String u = "/action/basic/doc_functions?doc_id=" + doc_id;
                cached_document_functions = readActions(u);
            }
            return cached_document_functions;
        }


        /**
           @return the document id for this document
        */
        public String getID() {
            return doc_id;
        }

        /**
           Retrieves and returns the parameters of the document.  They
           are cached on the client side.  This is mainly useful for opening
           ReadUp windows on the document.
           @return the document parameters
        */
        public Properties getParameters()
            throws IOException {

            if (parameters == null) {

                parameters = new Properties();

                try {
                    URL u = new URL(repository_url, "/action/basic/dv_doc_parameters?doc_id=" + doc_id);
                    // System.err.println("getDocParameters URL is " + u.toExternalForm() + ", password is " + repository_password);
                    HttpURLConnection h = (HttpURLConnection) u.openConnection();
                    if (repository_password != null)
                        h.setRequestProperty("Password", repository_password);
                    if (repository_cookie != null)
                        h.setRequestProperty("Cookie", repository_cookie);
                    int rcode = h.getResponseCode();
                    if (rcode != 200) {
                        System.err.println("Response code is " + rcode);
                        System.err.println("Content is: " + h.getResponseMessage());
                        if (rcode == 401)
                            throw new ResourceLoader.PrivilegeViolation("Server returned UNAUTHORIZED HTTP code");
                        else if (rcode == 404)
                            throw new ResourceLoader.ResourceNotFound("No such document " + doc_id);
                    } else {
                        parameters.load((java.io.InputStream) h.getContent());
                    }
                } catch (java.net.ConnectException x) {
                    throw new ResourceLoader.CommunicationFailure("Can't connect to repository:  " + x);
                } catch (ResourceLoader.PrivilegeViolation x) {
                    throw x;
                } catch (ResourceLoader.CommunicationFailure x) {
                    throw x;
                } catch (ResourceLoader.ResourceNotFound x) {
                    throw x;
                } catch (Exception e) {
                    System.err.println("Exception raised:  " + e);
                    e.printStackTrace(System.err);
                }
            }
            return parameters;
        }

        /**
           Retrieves, from the client-side cache, the named parameter, or the defalt
           value if there is no value for that name.
           @param pname the name of the parameter to fetch
           @param defalt the default value to return
           @return a string value for the specified parameter
        */
        public String getParameter (String pname, String defalt) {
            try {
                Properties map = getParameters();
                if (map != null)
                    return map.getProperty(pname, defalt);
            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
            return defalt;
        }

        /**
           Retrieves, from the client-side cache, the named parameter, or the defalt
           value if there is no value for that name.
           @param pname the name of the parameter to fetch
           @param defalt the default value to return
           @return a boolean value for the specified parameter
        */
        public boolean getBooleanParameter (String pname, boolean defalt) {
            try {
                Properties map = getParameters();
                if (map != null) {
                    String tmp = map.getProperty(pname);
                    if (tmp != null)
                        return Boolean.valueOf(tmp).booleanValue();
                    else
                        return defalt;
                } else {
                    return defalt;
                }
            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
            return defalt;
        }

        /**
           Retrieves, from the client-side cache, the named parameter, or the defalt
           value if there is no value for that name.
           @param pname the name of the parameter to fetch
           @param defalt the default value to return
           @return an integer value for the specified parameter
        */
        public int getIntegerParameter (String pname, int defalt) {
            try {
                Properties map = getParameters();
                if (map != null) {
                    String tmp = map.getProperty(pname);
                    if (tmp != null)
                        return Integer.valueOf(tmp).intValue();
                    else
                        return defalt;
                } else {
                    return defalt;
                }
            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
            return defalt;
        }

        /**
           Retrieves, from the client-side cache, the named parameter, or the defalt
           value if there is no value for that name.
           @param pname the name of the parameter to fetch
           @param defalt the default value to return
           @return a double value for the specified parameter
        */
        public double getRealParameter (String pname, double defalt) {
            try {
                Properties map = getParameters();
                if (map != null) {
                    String tmp = map.getProperty(pname);
                    if (tmp != null)
                        return Double.valueOf(tmp).doubleValue();
                    else
                        return defalt;
                } else {
                    return defalt;
                }
            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
            return defalt;
        }

        /**
           @return repository to which the document belongs
        */
        public Repository getRepository () {
            return Repository.this;
        }

        synchronized void setCategories(ArrayList c) {
            categories = c;
        }

        synchronized void setAuthors(ArrayList c) {
            authors = c;
        }

        public File getPDFVersion () throws IOException {

            File f = File.createTempFile(doc_id + "-", ".pdf");

            try {
                URL u = new URL(repository_url, "/action/basic/doc_pdf?doc_id=" + doc_id);
                // System.err.println("getPDFVersion URL is " + u.toExternalForm() + ", password is " + repository_password);
                HttpURLConnection h = (HttpURLConnection) u.openConnection();
                if (repository_password != null)
                    h.setRequestProperty("Password", repository_password);
                if (repository_cookie != null)
                    h.setRequestProperty("Cookie", repository_cookie);
                int rcode = h.getResponseCode();
                if (rcode != 200) {
                    System.err.println("Response code is " + rcode);
                    System.err.println("Content is: " + h.getResponseMessage());
                    if (rcode == 401)
                        throw new ResourceLoader.PrivilegeViolation("Server returned UNAUTHORIZED HTTP code");
                    else if (rcode == 404)
                        throw new ResourceLoader.ResourceNotFound("No such document " + doc_id);
                } else {
                    OutputStreamWriter fos = new OutputStreamWriter(new FileOutputStream(f));
                    InputStreamReader is = new InputStreamReader((java.io.InputStream) h.getContent());
                    char[] buffer = new char[1000];
                    int i;
                    while ((i = is.read(buffer, 0, 1000)) >= 0) {
                        fos.write(buffer, 0, i);
                    }
                    is.close();
                    fos.close();
                    return f;
                }
            } catch (java.net.ConnectException x) {
                f.deleteOnExit();
                throw new ResourceLoader.CommunicationFailure("Can't connect to repository:  " + x);
            } catch (ResourceLoader.PrivilegeViolation x) {
                f.deleteOnExit();
                throw x;
            } catch (ResourceLoader.CommunicationFailure x) {
                f.deleteOnExit();
                throw x;
            } catch (ResourceLoader.ResourceNotFound x) {
                f.deleteOnExit();
                throw x;
            } catch (IOException x) {
                f.deleteOnExit();
                throw x;
            } catch (Exception e) {
                f.deleteOnExit();
                System.err.println("Exception raised:  " + e);
                e.printStackTrace(System.err);
            }
            return null;
        }
    }

    public abstract class DocumentGroup extends java.util.AbstractCollection {

        protected Document[] docs;
        protected transient ArrayList qdocs;

        public DocumentGroup () {
            docs = null;
            qdocs = new ArrayList();
        }

        /**
           Return those documents the collection currently knows about.  This list may not be exhaustive.
           @return a list of the documents in the collection
        */
        public Document[] getDocuments() {
            if (docs == null) {
                Document[] d = new Document[qdocs.size()];
                return (Document[]) (qdocs.toArray(d));
            } else
                return docs;
        }

        void addDocument(Document d) {
            if (d == null) {
                docs = new Document[qdocs.size()];
                docs = (Document[]) (qdocs.toArray(docs));
                qdocs = null;
            } else {
                qdocs.add(d);
            }
        }

        public boolean hasDocument (Document d) {
            if (docs != null) {
                for (int i = 0;  i < docs.length;  i++)
                    if (docs[i].equals(d))
                        return true;
                return false;
            } else if (qdocs != null) {
                for (int i = 0;  i < qdocs.size();  i++)
                    if (((Document)(qdocs.get(i))).equals(d))
                        return true;
                return false;
            } else
                return false;
        }

        /**
           Support the Collection size method.
           @return the number of documents in the category
        */
        public int size() {
            if (docs == null)
                return qdocs.size();
            else
                return docs.length;
        }

        /**
           Support the Collection iterator method.
           @return an interator over the documents in the category.
        */
        public Iterator iterator() {
            return (docs == null) ? new DocumentIterator (qdocs) : new DocumentIterator(docs);
        }

        /**
           Returns true if this Collection overlaps the parameter Collection
        */
        public boolean overlaps (DocumentGroup totest) {
            HashSet h = new HashSet(totest);
            h.retainAll(this);
            return (!h.isEmpty());
        }

        /**
           Returns the intersection of this group with the "totest" group
        */
        public Set intersection (DocumentGroup totest) {
            HashSet h = new HashSet(totest);
            h.retainAll(this);
            return h;
        }

        /**
           Returns the union of this group and the "totest" group
        */
        public Set union (DocumentGroup totest) {
            HashSet h = new HashSet(totest);
            h.addAll(this);
            return h;
        }

        /**
           Makes sure all the icons for this DG are loaded into the cache.
        */
        public void loadIcons() {
            int i = 0;
            boolean needs_load = false;
            if (docs != null) {
                for (i = 0;  i < docs.length;  i++) {
                    if (icon_cache.check(docs[i].getID(), -1, 0) == null) {
                        needs_load = true;
                        break;
                    }
                }
            } else if (qdocs != null) {
                for (i = 0;  i < qdocs.size();  i++) {
                    Repository.Document d = (Repository.Document) qdocs.get(i);
                    if (icon_cache.check(d.getID(), -1, 0) == null) {
                        needs_load = true;
                        break;
                    }
                }
            }
            if (needs_load) {
                // need to load one or more; fetch them all!
                fetchDocumentInfo(getDocuments());
            }
        }

        /**
           @return Return URL string for this item.
        */
        abstract public String getURLString ();

        /**
           @return Return name string for this item.
        */
        abstract public String getName ();
    }

    private class DocumentIterator implements java.util.Iterator {

        private Document[] doclist;
        private transient int docptr;

        public DocumentIterator (Document[] docs) {
            doclist = docs;
            docptr = 0;
        }

        public DocumentIterator (ArrayList docs) {
            doclist = (Document[]) docs.toArray(new Document[docs.size()]);
            docptr = 0;
        }

        public boolean hasNext () {
            return (docptr < doclist.length);
        }
        public Object next() throws NoSuchElementException {
            if (docptr < doclist.length) {
                Document d = doclist[docptr];
                docptr += 1;
                return d;
            } else
                throw new NoSuchElementException();
        }
        public void remove () {
            throw new UnsupportedOperationException();
        }
    }

    public class Category extends DocumentGroup {

        private String name;
        private Vector subcategories;
        private Category parent;

        /**
           Create a Cagegory with the given name.
           @param n name of the category
        */
        public Category (String n) {
            super();
            this.name = n;
            subcategories = new Vector();
            this.parent = null;
        }

        /**
           @return the name of the category
        */
        public String getName() {
            return name;
        }

        /**
           @return a human-readable name for the repository
        */
        public String toString() {
            return "<Category '" + this.name + "' " + ((docs != null) ? docs.length : qdocs.size()) +
                ((subcategories.size() > 0) ? (" (" + subcategories.size() + " subcategories)") : "") + ">";
        }

        /**
           @return the category's subcategories
        */
        public Vector getSubcategories () {
            return subcategories;
        }

        /**
           @param c Add a subcategory
        */
        private void addSubcategory (Category c) {
            subcategories.add(c);
        }

        /**
           @param parent set the parent of this category
        */
        private void setParent (Category parent) {
            this.parent = parent;
        }

        /**
           @return the parent of this category, or null if none
        */
        public Category getParent () {
            return this.parent;
        }

        /**
           @return the URL string for this item
        */
        public String getURLString () {
            return Repository.this.getURLString() + "category/" + URLEncoder.encode(this.name);
        }

        /**
           Makes sure the specified document is in this category.
        */
        public void addDocument (Document d) {
            if (qdocs != null)
                super.addDocument(d);
            else if (!hasDocument(d)) {
                Document[] olddocs = docs;
                docs = new Document[1 + olddocs.length];
                int i = 0;
                for (;  i < olddocs.length;  i++) {
                    docs[i] = olddocs[i];
                }
                docs[i] = d;
                // This should call the update code back at the server
                d.addCategory(this);
            }
        }
    }
    
    public class Author extends DocumentGroup {

        private String name;

        /**
           Create an Author with the given name.
           @param n name of the category
        */
        public Author (String n) {
            super();
            this.name = n;
        }

        /**
           @return the name of the category
        */
        public String getName() {
            return name;
        }

        /**
           @return a human-readable name for the repository
        */
        public String toString() {
            return "<Author '" + this.name + "' " + ((docs != null) ? docs.length : qdocs.size()) + ">";
        }

        /**
           @return the URL string for this item
        */
        public String getURLString () {
            return Repository.this.getURLString() + "author/" + URLEncoder.encode(this.name);
        }
    }
    
    public class Collection extends DocumentGroup {

        protected String name;

        Collection (String n) {
            super();
            name = n;
        }

        /**
           @return the name of the collection
        */
        public String getName() {
            return name;
        }

        /**
           @return a human-readable name for the repository
        */
        public String toString() {
            return "<Collection '" + this.name + "' " + ((docs != null) ? docs.length : qdocs.size()) + ">";
        }

        /**
           @return the URL string for this item
        */
        public String getURLString () {
            return Repository.this.getURLString() + "collection/" + URLEncoder.encode(this.name);
        }

        /**
           Makes sure the specified document is in this collection
        */
        public void addDocument (Document d) {
            if (qdocs != null)
                super.addDocument(d);
            else if (!hasDocument(d)) {
                Document[] olddocs = docs;
                docs = new Document[1 + olddocs.length];
                int i = 0;
                for (;  i < olddocs.length;  i++) {
                    docs[i] = olddocs[i];
                }
                docs[i] = d;
                // This should call the update code back at the server
            }
        }
    }

    public class QueryCollection extends Collection {

        protected String query;

        QueryCollection (String n, String q) {
            super(n);
            this.query = q;
        }

        /**
           @return the query string of the Collection
        */
        public String getQuery() {
            return query;
        }

        /**
           @return a human-readable name for the repository
        */
        public String toString() {
            return "<QueryCollection '" + this.name + "' " + "\"" + query + "\" " + ((docs != null) ? docs.length : qdocs.size()) + ">";
        }

        /**
           Makes sure the specified document is in this collection
        */
        public void addDocument (Document d) throws IllegalArgumentException {
            if (qdocs != null)
                super.addDocument(d);
            else if (!hasDocument(d)) {
                throw new IllegalArgumentException("Can't modify contents of a QueryCollection");
            }
        }
    }
    

    public class PrestoCollection extends QueryCollection {

        PrestoCollection (String n, String q) {
            super(n, q);
        }

        /**
           @return the query string of the Collection
        */
        public String getQuery() {
            return query;
        }

        /**
           @return a human-readable name for the repository
        */
        public String toString() {
            return "<QueryCollection '" + this.name + "' " + "\"" + query + "\" " + ((docs != null) ? docs.length : qdocs.size()) + ">";
        }

        /**
           Makes sure the specified document is in this collection
           @param d the document to add
        */
        public void includeDocument (Document d) throws IllegalArgumentException {
            ((Collection) this).addDocument(d);
        }

        /**
           Makes sure the specified document is in this collection
           @param d the document to add
        */
        public void excludeDocument (Document d) throws IllegalArgumentException {
            ((Collection) this).addDocument(d);
        }
    }
    
    private void initFields(URL u, String password, String cookie) {
        repository_url = u;
        repository_password = password;

        System.err.println("repository_url is " + repository_url + ", repository_password is " + repository_password);

        hi_res_cache = new SoftReferenceCache(new UpLibPageImageLoader("hi-res-page-image", u, password, 0), 0);
        page_image_cache = new SoftReferenceCache(new UpLibPageImageLoader("page-image", u, password, 25), 50);
        thumbnail_cache = new SoftReferenceCache(new UpLibPageImageLoader("page-thumbnail", u, password, 0), 200);
        pagetext_cache = new SoftReferenceCache(new UpLibPageTextLoader("page-text", u, password), 10);
        notes_cache = new SoftReferenceCache(new UpLibNoteHandler(u, password, (1 << 16)), 40);
        icon_cache = new SoftReferenceCache(new UpLibPageImageLoader("document-icon", u, password, 0), 2000);

        rep_metadata = null;
        rep_documents = new HashMap();
        rep_categories = null;
        rep_collections = null;
        url_string = u.toExternalForm();
        rep_name = null;

        if (cookie == null) {
            try {
                cookie = getCookieTheHardWay();
                if (cookie != null)
                    setCookie(cookie);
            } catch (Exception x) {
                x.printStackTrace(System.err);
            }
        } else {
            setCookie(cookie);
        }
    }

    /**
       Returns the repository cookie.
       @return the cookie, in the standard KEY=VALUE format
    */
    public String getCookie () {
        return repository_cookie;
    }

    /**
       Sets the cookie for the repository.
       @param cookie the cookie, in the standard KEY=VALUE format
    */
    public void setCookie (String cookie) {
        repository_cookie = cookie;
        if (repository_cookie != null) {
            try {
                ((UpLibPageImageLoader)(hi_res_cache.getLoader())).setCookie(repository_cookie);
                ((UpLibPageImageLoader)(page_image_cache.getLoader())).setCookie(repository_cookie);
                ((UpLibPageImageLoader)(thumbnail_cache.getLoader())).setCookie(repository_cookie);
                ((UpLibPageTextLoader)(pagetext_cache.getLoader())).setCookie(repository_cookie);
                ((UpLibNoteHandler)(notes_cache.getLoader())).setCookie(repository_cookie);
                ((UpLibPageImageLoader)(icon_cache.getLoader())).setCookie(repository_cookie);
            } catch (Exception x) {
                System.err.println("Can't set repository cookie!");
                x.printStackTrace(System.err);
            }
        }
    }

    public static URL getCanonicalRepositoryURL (String url) throws MalformedURLException {
        URL u = null;
        try {
            u = new URL(url);
        } catch (MalformedURLException x) {
            // we also support host:port
            // strip off leading or trailing slashes first, though
            String[] parts = url.replaceAll("(^/+)|(/+$)", "").split(":");
            if (parts.length == 2) {
                u = new URL("https", parts[0], Integer.parseInt(parts[1]), "/");
            } else if (parts.length == 1) {
                // I usually use 8090 as a repo port, so...
                u = new URL("https", parts[0], 8090, "/");
            } else
                throw x;
        }
        return new URL(u.getProtocol(), u.getHost(), u.getPort(), "/");
    }

    /**
       A constructor for Repository.
       @param u the URL for the repository.
       @param password the password for the repository, or null if no password.
    */
    public Repository (URL u, String password) throws java.net.MalformedURLException {
        URL u2 = getCanonicalRepositoryURL(u.toExternalForm());
        initFields(u2, password, null);
    }

    /**
       A constructor for Repository.
       @param u the string URL for the repository.
       @param password the password for the repository, or null if no password.
    */
    public Repository (String u, String password) throws java.net.MalformedURLException {
        URL u2 = getCanonicalRepositoryURL(u);
        initFields(u2, password, null);
    }

    /**
       Obtain a human-readable string name for the repository.
       @return a name for the repository
    */
    public String toString() {
        String n = getName();
        return "<Repository " + ((n != null) ? ("\"" + n + "\", ") : "") + url_string
            + (((repository_password != null) && (repository_password.length() > 0)) ? ", <password>" : "")
            + ">";
    }

    /**
       Obtain the URL of the repository as a string.
       @return a String containing the external form of the name of the repository
    */
    public String getURLString() {
        return url_string;
    }

    /**
       @return the password for the repository
    */
    public String getPassword() {
        return repository_password;
    }

    /**
       @return the name of the repository
    */
    public String getName() {
        if (rep_name == null) {
            rep_name = getProperty("name");
        }
        return rep_name;
    }

    /**
       @return the URL for the repository
    */
    public URL getURL () {
        return repository_url;
    }

    /**
       Return the document for the given id.  Return null if no such document in repository.
       @param id the document id for the requested document
       @return the document or null if there is no document in the repository with the specified ID
    */
    public Document getDocument(String id) {
        if (rep_documents.containsKey(id))
            return (Document) (rep_documents.get(id));
        else {
            try {
                Document d = new Document(id);
                d.getParameters();
                rep_documents.put(id, d);
                return d;
            } catch (IOException x) {
                return (Document) null;
            }
        }
    }

    /**
       Returns an iterator over the repository's documents.  This may be a subset of the
       documents known at the server.  If a full listing is required, call readIndexFile()
       before calling this function.
       @return an iterator over the repository's documents
    */
    public Iterator getDocuments() {
        if (rep_documents.size() == 0)
            readIndexFile();
        return rep_documents.values().iterator();
    }

    /**
       Returns the number of documents in the repository.  This returns the number
       known at the client side; if an accurate count is desired, readIndexFile() should
       be called before this function.
       @return the number of documents in the repository
    */
    public int getDocumentCount() {
        if (rep_documents.size() == 0)
            readIndexFile();
        return rep_documents.size();
    }

    /**
       Retrieve a metadata property associated with the repository.
       @param pname the property to retrieve
       @return a String or null if the property was not present
    */
    public String getProperty (String pname) {
        if (rep_metadata == null) {
            try {
                URL u = new URL(repository_url, "/action/externalAPI/repo_properties");
                System.err.println("repo_properties URL is " + u.toExternalForm() + ", password is " + repository_password);
                HttpURLConnection h = (HttpURLConnection) u.openConnection();
                if (repository_password != null)
                    h.setRequestProperty("Password", repository_password);
                if (repository_cookie != null)
                    h.setRequestProperty("Cookie", repository_cookie);
                int rcode = h.getResponseCode();
                if (rcode != 200) {
                    System.err.println("Response code is " + rcode);
                    System.err.println("Content is: " + h.getResponseMessage());
                    if (rcode == 401)
                        throw new ResourceLoader.PrivilegeViolation("Server returned UNAUTHORIZED HTTP code");
                } else {
                    rep_metadata = new MetadataFile(new InputStreamReader((java.io.InputStream) (h.getContent())));
                }
            } catch (Exception e) {
                System.err.println("Exception raised:  " + e);
                e.printStackTrace(System.err);
            }
        }
        if (rep_metadata != null)
            return rep_metadata.get(pname);
        else
            return null;
    }

    /**
       @return A list of the repository's categories (tags) as strings.
    */
    public String[] getCategoryNames () {
        String s = getProperty("categories");
        if (s != null)
            return s.split(",");
        else
            return null;
    }

    /**
       This function reads the repository's index file, if necessary, and may require a
       round-trip to the server.
       The categories returned are in lexicographic order by category name (case-sensitive).
       @return An iterator over the repository's categories, or null if no index file for the repository.
    */
    public Iterator getCategories () {
        if (rep_categories == null)
            readIndexFile();
        if (rep_categories != null)
            return rep_categories.values().iterator();
        else
            return null;
    }

    /**
       This function reads the repository's index file, if necessary, and may require a
       round-trip to the server.
       Returns null if no such category exists, otherwise the specified category.
       @param name the name of the category to return
       @return The specified category, or null if not found.
    */
    public Category getCategory (String name) {
        if (rep_categories == null)
            readIndexFile();
        if (rep_categories != null)
            return (Category) (rep_categories.get(name));
        else
            return null;
    }

    /**
       This function reads the repository's index file, if necessary, and may require a
       round-trip to the server.
       The hashtable returned maps category names to Category objects.
       @return A hashtable containing the known categories of the repository.
    */
    public Category[] getCategoriesList () {
        if (rep_categories == null)
            readIndexFile();
        return (Category[]) rep_categories.values().toArray(new Category[rep_categories.size()]);
    }

    /**
       This function reads the repository's index file, if necessary, and may require a
       round-trip to the server.
       The collections returned are in lexicographic order by collection name (case-sensitive).
       @return An iterator over the repository's collections, or null if no index file for the repository.
    */
    public Iterator getCollections () {
        if (rep_collections == null)
            readIndexFile();
        if (rep_collections != null)
            return rep_collections.values().iterator();
        else
            return null;
    }

    /**
       This function reads the repository's index file, if necessary, and may require a
       round-trip to the server.
       Returns null if no such collection exists, otherwise the specified collection.
       @param name the name of the collection to return
       @return The specified collection, or null if not found.
    */
    public Collection getCollection (String name) {
        if (rep_collections == null)
            readIndexFile();
        if (rep_collections != null)
            return (Collection) (rep_collections.get(name));
        else
            return null;
    }

    /**
       This function reads the repository's index file, if necessary, and may require a
       round-trip to the server.
       The authors returned are in lexicographic order by author last name (case-sensitive).
       @return An iterator over the repository's authors, or null if no index file for the repository.
    */
    public Iterator getAuthors () {
        if (rep_authors == null)
            readIndexFile();
        if (rep_authors != null)
            return rep_authors.values().iterator();
        else
            return null;
    }

    /**
       This function reads the repository's index file, if necessary, and may require a
       round-trip to the server.
       Returns null if no such author exists, otherwise the specified author.
       @param name the name of the author to return
       @return The specified author, or null if not found.
    */
    public Author getAuthor (String name) {
        if (rep_authors == null)
            readIndexFile();
        if (rep_authors != null)
            return (Author) (rep_authors.get(name));
        else
            return null;
    }

    private static class IndexInputStream extends ByteArrayInputStream {
        
        private DataInputStream dstream;
        private final static Matcher header_pattern = Pattern.compile("UpLib Repository Index ([0-9]*)\\.([0-9]*)").matcher("");

        public IndexInputStream (int length, InputStream istream) throws IOException {
            super(new byte[length]);
            new DataInputStream(istream).readFully(this.buf);
            String header = new String(this.buf, 0, 32, "US-ASCII");
            header_pattern.reset(header);
            if (!header_pattern.lookingAt()) {
                throw new IOException("Invalid index file header");
            } else {
                int major = Integer.parseInt(header_pattern.group(1));
                int minor = Integer.parseInt(header_pattern.group(2));
                // System.err.println("Index file version is " + major + "." + minor);
                if ((minor != 0) || (major != 1))
                    throw new IOException("Can't handle index file version " + major + "." + minor);
            }
            this.pos = 0;
            dstream = new DataInputStream(this);
        }
        public void seek(int pos) throws IOException {
            this.pos = pos;
        }            
        public void skip(int count) throws IOException {
            dstream.skipBytes(count);
        }
        public long readS4 () throws IOException {
            return dstream.readInt();
        }
        public long readU4 () throws IOException {
            long v = dstream.readInt();
            if (v < 0) {
                return v + (0x100000000L);
            } else
                return v;            
        }
        public int readU2 () throws IOException {
            return dstream.readUnsignedShort();
        }
        public String readString() throws IOException, UnsupportedEncodingException {
            int v = readU2();
            if (v > 1) {
                byte[] v2 = new byte[v-1];
                dstream.readFully(v2);
                dstream.readByte();         // extra nul byte
                return new String(v2, 0, v2.length, "UTF-8");
            } else {
                dstream.readByte();
                return "";
            }
        }
        public Date readDate() throws IOException {
            long v = readU4();
            if (v == 0)
                return null;
            else {
                int year = (int) (v / (long) (13 * 32));
                int month = (int) ((v / 32L) % 13);
                int day = (int) (v % 32L);
                return new GregorianCalendar(year, (month == 0) ? 0 : month-1, (day == 0) ? 1 : day).getTime();
            }
        }
        public Date readTime() throws IOException {
            long v = readU4();
            return new Date(v * 1000);
        }
    }

    public String getCookieTheHardWay () throws IOException {
        String cookie = null;
        Object handler = null;

        // set up a cookie handler, if possible
        try {
            // now look for the CookieHandler class
            // we're doing this all with reflection in case we're running under Java 1.4
            Class c = Class.forName("java.net.CookieHandler");
            if (c != null) {
                // java 1.5 or better
                java.lang.reflect.Method m = c.getMethod("getDefault", (Class[]) null);
                handler = m.invoke (null, (Object[]) null);
                if (handler == null) {
                    Class lch = Class.forName("com.parc.uplib.util.ListCookieHandler");
                    if (lch != null) {
                        m = lch.getMethod("setDefaultHandler", (Class[]) null);
                        if (m != null) {
                            m.invoke(null, (Object[]) null);
                            m = c.getMethod("getDefault", (Class[]) null);
                            handler = m.invoke(null, (Object[]) null);
                        }
                    }
                }
            }
        } catch (ClassNotFoundException x) {
            System.err.println("no CookieHandler class");
        } catch (NoSuchMethodException x) {
            x.printStackTrace(System.err);
        } catch (java.lang.reflect.InvocationTargetException x) {
            x.printStackTrace(System.err);
        } catch (IllegalAccessException x) {
            x.printStackTrace(System.err);
        } catch (java.security.AccessControlException x) {
            x.printStackTrace(System.err);
        }

        if (cookie == null) {
            cookie = System.getProperty("com.parc.uplib.sessionCookie");
        }

        if ((cookie == null) && (repository_password != null)) {
            String content =
                "--000000000000000000000000000\r\n" +
                "Content-Disposition: form-data; name=\"originaluri\"\r\n\r\n" +
                "/login\r\n" +
                "--000000000000000000000000000\r\n" +
                "Content-Disposition: form-data; name=\"password\"\r\n\r\n" +
                repository_password + "\r\n" +
                "--000000000000000000000000000--\r\n";
            URL u = new URL(repository_url, "/login");
            HttpURLConnection h = (HttpURLConnection) (u.openConnection());
            h.setRequestMethod("POST");
            h.setDoOutput(true);
            h.setUseCaches(false);
            h.setRequestProperty("Content-Type", "multipart/form-data; boundary=000000000000000000000000000");
            h.setInstanceFollowRedirects(false);
            OutputStream os = h.getOutputStream();
            os.write(content.getBytes());
            int rcode = h.getResponseCode();
            cookie = h.getHeaderField("Set-Cookie");
            System.err.println("getCookie:  cookie is \"" + cookie + "\"");
            if (rcode != 302) {
                if (rcode == 401)
                    throw new ResourceLoader.PrivilegeViolation("Server returned UNAUTHORIZED HTTP code");
                else if (rcode/100 != 2)
                    throw new IOException("Can't login to remote server " + repository_url + " with password " + repository_password);
            }
            h.disconnect();
        }

        if ((handler != null) && (cookie != null)) {
            try {
                java.net.URI u2 = new java.net.URI(repository_url.toExternalForm());
                HashMap map1 = new HashMap();
                ArrayList valueslist = new ArrayList();
                valueslist.add(cookie);
                map1.put("Set-Cookie", valueslist);
                Class c = handler.getClass();
                java.lang.reflect.Method m = c.getMethod("put", new Class[] {Class.forName("java.net.URI"),
                                                                             Class.forName("java.util.Map")});
                if (m != null) {
                    m.invoke(handler, new Object[] {u2, java.util.Collections.unmodifiableMap(map1)});
                } else {
                    System.err.println("null method for java.net.CookieHandler.put(java.net.URI, java.util.Map)");
                }
            } catch (java.net.URISyntaxException x) {
                x.printStackTrace(System.err);
            } catch (ClassNotFoundException x) {
                x.printStackTrace(System.err);
            } catch (NoSuchMethodException x) {
                x.printStackTrace(System.err);
            } catch (java.lang.reflect.InvocationTargetException x) {
                x.printStackTrace(System.err);
            } catch (IllegalAccessException x) {
                x.printStackTrace(System.err);
            }
        }

        return cookie;
    }

    /**
       Read the repository's index file, and make sure the Java representation of the
       repository is in sync with the index file.  The index file is re-generated automatically
       on the server when the repository is changed.
       <p>
       This routine should be called when an application wants to work with all the documents
       or categories on the client side, as it incarnates client-side Java instances for all
       documents, categories, and collections in the repository.  Applications that want to
       work with just some explicit documents, or search results, may not need to call it.
       @return the repository instance
    */
    public Repository readIndexFile () {
        try {
            String urlpath = "/action/externalAPI/repo_index";
            if (index_file_read_time != null)
                urlpath += "?modtime=" + index_file_read_time.intValue();
            URL u = new URL(repository_url, urlpath);
            
            // System.err.println("repo_properties URL is " + u.toExternalForm() + ", password is " + repository_password);
            HttpURLConnection h = (HttpURLConnection) u.openConnection();
            if (repository_password != null)
                h.setRequestProperty("Password", repository_password);
            if (repository_cookie != null)
                h.setRequestProperty("Cookie", repository_cookie);
            int rcode = h.getResponseCode();
            if (rcode == 304) {
                // not modified
                return this;
            } else if (rcode != 200) {
                System.err.println("Response code is " + rcode);
                System.err.println("Content is: " + h.getResponseMessage());
                if (rcode == 401)
                    throw new ResourceLoader.PrivilegeViolation("Server returned UNAUTHORIZED HTTP code");
                System.err.println("Can't read index file for repository.");
            } else {
                IndexInputStream s = new IndexInputStream(h.getContentLength(), (InputStream) h.getContent());

                s.skip(32);
                int ndocs = (int) s.readU4();
                int nauths = (int) s.readU4();
                Date modtime = s.readTime();
                index_file_read_time = new Long(h.getHeaderFieldDate("Date", 0)/1000);
                int ncats = s.readU2();
                int ncolls = s.readU2();
                // System.err.println("ndocs is " + ndocs + ", nauths is " + nauths + ", ncats is " + ncats + ", ncolls is " + ncolls);
                int first_doc_pos = (int) s.readU4();
                int first_cat_pos = (int) s.readU4();
                int first_coll_pos = (int) s.readU4();
                int first_auth_pos = (int) s.readU4();
                s.skip(20); // don't read password hash
                rep_name = s.readString();
                System.err.println("Repo name is \"" + rep_name + "\"");
                    
                HashMap docs = new HashMap(ndocs);
                HashMap doccats = new HashMap(ndocs);
                HashMap docauths = new HashMap(ndocs);
                HashMap cats = new HashMap(ncats);
                HashMap catdocs = new HashMap(ncats);
                HashMap colls = new HashMap(ncolls);
                HashMap colldocs = new HashMap(ncolls);
                HashMap collincluded = new HashMap(ncolls);
                HashMap collexcluded = new HashMap(ncolls);
                HashMap auths = new HashMap(nauths);
                HashMap authdocs = new HashMap(nauths);

                // now read and create the documents
                int loc = first_doc_pos;
                //System.err.println("reading documents at " + first_doc_pos);
                for (int i = 0;  i < ndocs;  i++) {
                    s.seek(loc);
                    int rlength = s.readU2();
                    int pagecount = s.readU2();
                    int ndoccats = s.readU2();
                    int ndocauths = s.readU2();
                    Date published = s.readDate();
                    Date last_used = s.readTime();
                    Date added = s.readTime();
                    long[] dcats = new long[ndoccats];
                    long[] dauths = new long[ndocauths];
                    for (int j = 0;  j < ndocauths;  j++) {
                        dauths[j] = s.readU4();
                    }
                    for (int j = 0;  j < ndoccats;  j++) {
                        dcats[j] = s.readU4();
                    }
                    String did = s.readString();
                    String title = s.readString();
                    String[] authors = new String[ndocauths];
                    Document d = new Document(did, title, published);
                    // System.err.println("Document '" + did + "' at " + loc + " date is " + published);
                    docs.put(new Integer(loc), d);
                    doccats.put(d, dcats);
                    docauths.put(d, dauths);
                    loc += rlength;
                }

                // now read and create the categories
                loc = first_cat_pos;
                // System.err.println("reading categories at " + first_cat_pos);
                for (int i = 0;  i < ncats;  i++) {
                    s.seek(loc);
                    int rlength = s.readU2();
                    int ncatdocs = s.readU2();
                    long[] cdocs = new long[ncatdocs];
                    for (int j = 0;  j < ncatdocs;  j++) {
                        cdocs[j] = s.readU4();
                    }
                    String cname = s.readString();
                    // System.err.println("Category '" + cname + "' at " + loc + " read");
                    Category c = new Category(cname);
                    catdocs.put(c, cdocs);
                    cats.put(new Integer(loc), c);
                    loc += rlength;
                }

                // now read and create the collections
                loc = first_coll_pos;
                // System.err.println("reading collections at " + first_coll_pos);
                for (int i = 0;  i < ncolls;  i++) {
                    s.seek(loc);
                    int rlength = s.readU2();
                    int ncolldocs = s.readU2();
                    long[] cdocs = new long[ncolldocs];
                    for (int j = 0;  j < ncolldocs;  j++) {
                        cdocs[j] = s.readU4();
                    }
                    int nincludes = s.readU2();
                    int nexcludes = s.readU2();
                    // System.err.println("nincludes are " + nincludes + ", nexcludes are " + nexcludes);
                    long[] idocs = new long[nincludes];
                    for (int j = 0;  (nincludes != 0xFFFF) && (j < nincludes);  j++) {
                        idocs[j] = s.readU4();
                    }
                    long[] edocs = new long[nexcludes];
                    for (int j = 0;  (nexcludes != 0xFFFF) && (j < nexcludes);  j++) {
                        edocs[j] = s.readU4();
                    }
                    String cname = s.readString();
                    String query = s.readString();
                    // System.err.println("Collection '" + cname + "' at " + loc + " read");
                    Collection c;
                    if (query.length() == 0) {
                        c = new Collection(cname);
                    } else if ((nincludes == 0xFFFF) || (nexcludes == 0xFFFF)) {
                        c = new QueryCollection(cname, query);
                    } else {
                        c = new PrestoCollection(cname, query);
                        collexcluded.put(c, edocs);
                        collincluded.put(c, idocs);
                    }
                    colldocs.put(c, cdocs);
                    colls.put(new Integer(loc), c);
                    loc += rlength;
                }

                // now read and create the authors
                loc = first_auth_pos;
                // System.err.println("reading authors at " + first_cat_pos);
                for (int i = 0;  i < nauths;  i++) {
                    s.seek(loc);
                    int rlength = s.readU2();
                    int nauthdocs = s.readU2();
                    long[] cdocs = new long[nauthdocs];
                    for (int j = 0;  j < nauthdocs;  j++) {
                        cdocs[j] = s.readU4();
                    }
                    String aname = s.readString();
                    // System.err.println("Author '" + cname + "' at " + loc + " read");
                    Author a = new Author(aname);
                    authdocs.put(a, cdocs);
                    auths.put(new Integer(loc), a);
                    loc += rlength;
                }

                for (Iterator di = docs.entrySet().iterator();  di.hasNext(); ) {
                    Document d = (Document) ((Map.Entry)(di.next())).getValue();

                    long[] dcats = (long[]) doccats.get(d);
                    if (dcats != null) {
                        ArrayList newcats = new ArrayList(dcats.length);
                        for (int j = 0;  j < dcats.length;  j++) {
                            Integer key = new Integer((int) (dcats[j]));
                            if (cats.containsKey(key)) {
                                newcats.add(cats.get(key));
                            }
                        }
                        d.setCategories(newcats);
                    }

                    long[] dauths = (long[]) docauths.get(d);
                    if (dauths != null) {
                        ArrayList newauths = new ArrayList(dauths.length);
                        for (int j = 0;  j < dauths.length;  j++) {
                            Integer key = new Integer((int) (dauths[j]));
                            if (auths.containsKey(key)) {
                                newauths.add(auths.get(key));
                            }
                        }
                        d.setAuthors(newauths);
                    }
                    rep_documents.put(d.getID(), d);
                }
                
                rep_categories = new TreeMap();
                for (Iterator i = catdocs.entrySet().iterator();  i.hasNext();) {
                    Map.Entry e = (Map.Entry) (i.next());
                    Category c = (Category) e.getKey();
                    long[] cdocs = (long[]) e.getValue();
                    for (int j = 0;  j < cdocs.length;  j++) {
                        Integer key = new Integer((int) (cdocs[j]));
                        if (docs.containsKey(key)) {
                            Document d = (Document) docs.get(key);
                            if (d == null)
                                System.err.println("No document found for position " + cdocs[j]);
                            else
                                c.addDocument(d);
                        }
                    }
                    c.addDocument(null);
                    rep_categories.put(c.getName(), c);
                }

                // process subcategories
                for (Iterator i = ((TreeMap)(rep_categories.clone())).values().iterator();  i.hasNext(); ) {
                    Category c = (Category) (i.next());
                    String[] parts = c.getName().split("/");
                    if (parts.length > 1) {
                        String cname = "";
                        Category old_cv = null;
                        for (int k = 0;  k < parts.length - 1;  k++) {
                            cname += ((cname.length() > 0) ? "/" : "") + parts[k].trim();
                            Category cv = (Category) rep_categories.get(cname);
                            if (cv == null) {
                                cv = new Category(cname);
                                rep_categories.put(cname, cv);
                            }
                            if (old_cv != null) {
                                cv.setParent(old_cv);
                                old_cv.addSubcategory(cv);
                            }
                            old_cv = cv;
                        }
                        c.setParent(old_cv);
                        old_cv.addSubcategory(c);
                        // System.err.println("Added \"" + c.getName() + "\" as a child of " + old_cv);
                    }
                }
                
                rep_collections = new TreeMap();
                for (Iterator i = colldocs.entrySet().iterator();  i.hasNext();) {
                    Map.Entry e = (Map.Entry) (i.next());
                    Collection c = (Collection) e.getKey();
                    long[] cdocs = (long[]) e.getValue();
                    for (int j = 0;  j < cdocs.length;  j++) {
                        Integer key = new Integer((int) (cdocs[j]));
                        if (docs.containsKey(key)) {
                            Document d = (Document) docs.get(key);
                            if (d == null)
                                System.err.println("No document found for position " + cdocs[j]);
                            else
                                c.addDocument(d);
                        }
                    }
                    long[] idocs = (long[]) (collincluded.get(c));
                    for (int j = 0;  (idocs != null) && (j < idocs.length);  j++) {
                        Integer key = new Integer((int) (idocs[j]));
                        if (docs.containsKey(key)) {
                            Document d = (Document) docs.get(key);
                            if (d == null)
                                System.err.println("No document found for position " + cdocs[j]);
                            else
                                ((PrestoCollection)c).includeDocument(d);
                        }
                    }
                    long[] edocs = (long[]) (collexcluded.get(c));
                    for (int j = 0;  (edocs != null) && (j < edocs.length);  j++) {
                        Integer key = new Integer((int) (edocs[j]));
                        if (docs.containsKey(key)) {
                            Document d = (Document) docs.get(key);
                            if (d == null)
                                System.err.println("No document found for position " + cdocs[j]);
                            else
                                ((PrestoCollection)c).excludeDocument(d);
                        }
                    }
                    c.addDocument(null);
                    rep_collections.put(c.getName(), c);
                }

                rep_authors = new TreeMap();
                for (Iterator i = authdocs.entrySet().iterator();  i.hasNext();) {
                    Map.Entry e = (Map.Entry) (i.next());
                    Author a = (Author) e.getKey();
                    long[] cdocs = (long[]) e.getValue();
                    for (int j = 0;  j < cdocs.length;  j++) {
                        Integer key = new Integer((int) (cdocs[j]));
                        if (docs.containsKey(key)) {
                            Document d = (Document) docs.get(key);
                            if (d == null)
                                System.err.println("No document found for position " + cdocs[j]);
                            else
                                a.addDocument(d);
                        }
                    }
                    a.addDocument(null);
                    rep_authors.put(a.getName(), a);
                }
                // finished
            }
        } catch (Exception e) {
            System.err.println("Exception raised:  " + e);
            e.printStackTrace(System.err);
        }
        return this;
    }

    /**
       @return The SoftReferenceCache for loading document icons for the documents in the repository.
    */
    public SoftReferenceCache getIconLoader() {
        return icon_cache;
    }

    /**
       @return The SoftReferenceCache for loading notes for the documents in the repository.
    */
    public SoftReferenceCache getNotesLoader() {
        return icon_cache;
    }

    /**
       @return The SoftReferenceCache for loading standard page images (big thumbnails) for the documents in the repository.
    */
    public SoftReferenceCache getPageImageLoader() {
        return page_image_cache;
    }

    /**
       @return The SoftReferenceCache for loading page texts for the documents in the repository.
    */
    public SoftReferenceCache getPageTextLoader() {
        return pagetext_cache;
    }

    /**
       @return The SoftReferenceCache for loading small page thumbnails for the documents in the repository.
    */
    public SoftReferenceCache getPageThumbnailLoader() {
        return thumbnail_cache;
    }

    /**
       @return The SoftReferenceCache for loading high-resolution page images for the documents in the repository.
    */
    public SoftReferenceCache getPageHiResLoader() {
        return hi_res_cache;
    }

    private synchronized static Repository fetchOrCreate (String url) throws MalformedURLException {
        Repository r = null;
        if (known_repositories.containsKey(url)) {
            WeakReference ref = (WeakReference) known_repositories.get(url);
            r = (Repository) ref.get();
            if (r != null)
                return r;
            else
                known_repositories.remove(url);
        }
        r = new Repository(url, null);
        known_repositories.put(url, new WeakReference(r));
        return r;
    }
        

    /**
       @return the set of known repositories
    */
    public static Vector knownRepositories () {
        Vector result = new Vector();
        Iterator i = known_repositories.values().iterator();
        while (i.hasNext()) {
            Repository r = (Repository) ((WeakReference)(i.next())).get();
            if (r != null) {
                System.err.println("Repository " + r);
                result.add(r);
            }
        }
        return result;
    }

    /**
       @parameter the URL for the repository
       @return the Repository instance for that repository
    */
    public static Repository fetchOrCreate (URL u) throws MalformedURLException {
        return fetchOrCreate(u.getProtocol() + "://" + u.getAuthority() + "/");
    }

    /**
       @parameter the URL to fetch
       @return the document, category, or collection specified by the URL
    */
    static public Object get (URL u) {
        // System.err.println("looking at URL " + u);
        Repository r = null;
        try {
            r = fetchOrCreate(u);
        } catch (MalformedURLException x) {
            x.printStackTrace(System.err);
            return null;
        }
        String path = URLDecoder.decode(u.getPath());
        if (path.startsWith("/"))
            path = path.substring(1);
        if (path.length() < 1)
            return r;
        // System.err.println("path is \"" + path + "\"");
        if (path.startsWith("document/"))
            return r.getDocument(path.substring("document/".length()));
        else if (path.startsWith("category/"))
            return r.getCategory(path.substring("category/".length()));
        else if (path.startsWith("collection/"))
            return r.getCollection(path.substring("collection/".length()));
        else if (path.startsWith("author/")) {
            return r.getAuthor(path.substring("author/".length()));
        }
        else {
            // System.err.println("No match found, returning null for " + u);
            return null;
        }
    }

    private static byte[] readbytes (ZipInputStream zs, int size) throws IOException {
        byte[] buf = new byte[size];
        int count = 0;
        while (count < size) {
            int l = zs.read(buf, count, size - count);
            count += l;
        }
        return buf;
    }
 
   /**
       Fetch the metadata and icons for the specified documents, and associate
       that data with the respective Document objects.
    */
    public void fetchDocumentInfo (Document[] docs) {

        try {
            String doclist = "";
            for (int i = 0;  i < docs.length;  i++)
                doclist += docs[i].getID() + "\n";
            URL u = new URL(repository_url, "/action/externalAPI/fetch_document_info");
            // System.err.println("repo_properties URL is " + u.toExternalForm() + ", password is " + repository_password);
            HttpURLConnection h = (HttpURLConnection) u.openConnection();
            h.setRequestMethod("POST");
            if (repository_password != null)
                h.setRequestProperty("Password", repository_password);
            if (repository_cookie != null)
                h.setRequestProperty("Cookie", repository_cookie);
            h.setRequestProperty("Content-Type", "text/plain");
            h.setDoOutput(true);
            OutputStream output = h.getOutputStream();
            output.write(doclist.getBytes());
            output.flush();
            int rcode = h.getResponseCode();
            if (rcode != 200) {
                System.err.println("Response code is " + rcode);
                System.err.println("Content is: " + h.getResponseMessage());
                if (rcode == 401)
                    throw new ResourceLoader.PrivilegeViolation("Server returned UNAUTHORIZED HTTP code");
                System.err.println("Can't read data for documents.");
            } else {
                ZipInputStream zs = new ZipInputStream((InputStream) h.getContent());
                ZipEntry e;
                Document doc = null;
                while ((e = zs.getNextEntry()) != null) {
                    // top-level entries are document info folders
                    String name = e.getName();
                    int size = (int) e.getSize();
                    //System.err.println("- - - e.getName() is " + name + ", and e.getSize() is " + size + " - - -");
                    if (name.endsWith("/first.png")) {
                        if (doc != null) {
                            byte[] buf = readbytes(zs, size);
                            doc.setIcon((BufferedImage) ImageIO.read(new ByteArrayInputStream(buf, 0, buf.length)));
                        } else {
                            zs.closeEntry();
                        }
                    } else if (name.endsWith("/metadata.txt")) {
                        if (doc != null) {
                            byte[] buf = readbytes(zs, size);
                            doc.setMetadata(new MetadataFile(new StringReader(new String(buf))));
                        } else {
                            zs.closeEntry();
                        }
                    } else if (size == 0) {
                        String doc_id = name.substring(0, name.length() - 1);
                        doc = (Document) rep_documents.get(doc_id);
                        if (doc == null) {
                            doc = new Document(doc_id);
                            rep_documents.put(doc_id, doc);
                        }
                    } else {
                        System.err.println("odd file " + name + " encountered.");
                    }
                }
                zs.close();
            }
        } catch (Exception e) {
            e.printStackTrace(System.err);
        }
    }

    /**
       This class represents a document function or user button.
    */
    public class Action {

        private String key;
        private String actionurl;
        private String target;
        private String label;

        Action (String key, String actionurl, String target, String label) {

            this.key = key;
            this.actionurl = actionurl;
            this.target = target;
            this.label = label;
        }

        public String getURLString () {
            try {
                return new URL(repository_url, actionurl).toExternalForm();
            } catch (MalformedURLException x) {
                return null;
            }
        }

        public HttpURLConnection invoke (Repository.Document doc) {
            try {
                String path = this.actionurl;
                if (doc != null)
                    path = this.actionurl.replaceAll("%s", doc.getID());
                URL u = new URL(repository_url, path);
                HttpURLConnection h = (HttpURLConnection) u.openConnection();
                h.setRequestMethod("GET");
                if (repository_password != null)
                    h.setRequestProperty("Password", repository_password);
                if (repository_cookie != null)
                    h.setRequestProperty("Cookie", repository_cookie);
                int rcode = h.getResponseCode();
                if (rcode != 200) {
                    System.err.println("Response code is " + rcode);
                    System.err.println("Content is: " + h.getResponseMessage());
                    if (rcode == 401)
                        throw new ResourceLoader.PrivilegeViolation("Server returned UNAUTHORIZED HTTP code");
                    System.err.println("Can't read invoke action function for \"" + this.label + "\" with URL \"" + actionurl + "\"");
                } else {
                    return h;
                }
            } catch (Exception e) {
                e.printStackTrace(System.err);
            }
            return null;
        }

        public String getLabel() {
            return label;
        }
    }
        
    private Action[] readActions (String path) {
        ArrayList actions = new ArrayList();
        try {
            URL u = new URL(repository_url, path);
            // System.err.println("repo_properties URL is " + u.toExternalForm() + ", password is " + repository_password);
            HttpURLConnection h = (HttpURLConnection) u.openConnection();
            h.setRequestMethod("GET");
            if (repository_password != null)
                h.setRequestProperty("Password", repository_password);
            if (repository_cookie != null)
                h.setRequestProperty("Cookie", repository_cookie);
            h.setRequestProperty("Content-Type", "text/plain");
            int rcode = h.getResponseCode();
            if (rcode != 200) {
                System.err.println("Response code is " + rcode);
                System.err.println("Content is: " + h.getResponseMessage());
                if (rcode == 401)
                    throw new ResourceLoader.PrivilegeViolation("Server returned UNAUTHORIZED HTTP code");
                System.err.println("Can't read doc functions for " + this);
            } else {
                BufferedReader bf = new BufferedReader(new InputStreamReader((InputStream) h.getContent()));
                String line;
                while ((line = bf.readLine()) != null) {
                    // System.err.println("action read from " + path + " is \"" + line.trim() + "\"");
                    String[] parts = line.trim().split(",");
                    if (parts.length < 4)
                        continue;
                    // why doesn't Java have a static method "String join(String[], String glue)"?
                    String label = parts[3];
                    for (int i = 4;  i < parts.length;  i++)
                        label += ("," + parts[i]);                    
                    actions.add(new Action(parts[0].trim(), parts[1].trim(), parts[2].trim(), label.trim()));
                }
                bf.close();
            }
        } catch (Exception e) {
            e.printStackTrace(System.err);
        }
        return (Action[]) actions.toArray(new Action[actions.size()]);
    }

    public Action[] getUserActions () {
        String u = "/action/basic/repo_user_actions";
        return readActions(u);
    }

    private void writeObject (ObjectOutputStream s) throws IOException {
        s.defaultWriteObject();
    }

    private void readObject (ObjectInputStream s) throws IOException, ClassNotFoundException {
        s.defaultReadObject();
        initFields(repository_url, repository_password, repository_cookie);
    }

    /**
       this class represents a query of the repository.
    */
    public class Search {

        /**
           This class represents the results of a search.
        */
        public class Hit {
            /**
               The score assigned by Lucene to this document, for the specified query.
            */
            public float score;
            /**
               An UpLib document.
            */
            public Document doc;
        }

        private Hit[] hits;
        private String query;
        private float cutoff;
        private boolean showall;
        private long search_time;

        /**
           Construct an instance
           @param query A string containing an UpLib query.
           @param cutoff A float value giving the lowest score to include in the results.
           @param showall A boolean saying whether to include all results.  If false, only the highest scoring result will be returned.
        */
        public Search (String query, float cutoff, boolean showall) {
            this.query = query;
            this.cutoff = cutoff;
            this.showall = showall;
            this.hits = null;
            this.search_time = 0;
        }

        private ArrayList readHits (InputStream is, String query) {
            ArrayList hits = new ArrayList();
            try {
                ZipInputStream zs = new ZipInputStream(is);
                ZipEntry e;
                Hit current_hit = null;
                while ((e = zs.getNextEntry()) != null) {
                    // top-level entries are document info folders
                    String name = e.getName();
                    int size = (int) e.getSize();
                    //System.err.println("- - - e.getName() is " + name + ", and e.getSize() is " + size + " - - -");
                    if (name.endsWith("/first.png")) {
                        // png image -- read and ignore
                        if (current_hit != null) {
                            byte[] buf = readbytes(zs, size);
                            current_hit.doc.setIcon((BufferedImage) ImageIO.read(new ByteArrayInputStream(buf, 0, buf.length)));
                        } else {
                            zs.closeEntry();
                        }
                    } else if (name.endsWith("/score")) {
                        if (current_hit != null) {
                            byte[] buf = readbytes(zs, size);
                            current_hit.score = Float.parseFloat(new String(buf).trim());
                        } else {
                            zs.closeEntry();
                        }
                    } else if (name.endsWith("/metadata.txt")) {
                        if (current_hit != null) {
                            byte[] buf = readbytes(zs, size);
                            current_hit.doc.setMetadata(new MetadataFile(new StringReader(new String(buf))));
                        } else {
                            zs.closeEntry();
                        }
                    } else if (size == 0) {
                        String doc_id = name.substring(0, name.length() - 1);
                        // System.err.println("********** " + doc_id + " ***************");
                        Document d = (Document) rep_documents.get(doc_id);
                        if (d == null) {
                            d = new Document(doc_id);
                            rep_documents.put(doc_id, d);
                        }
                        current_hit = new Hit();
                        current_hit.doc = d;
                        hits.add(current_hit);
                    } else {
                        System.err.println("odd file " + name + " encountered.");
                    }
                }
                zs.close();
            } catch (Exception e) {
                e.printStackTrace(System.err);
            }
            return hits;
        }

        private Hit[] doSearch (String query, float cutoff, boolean showall)
            throws IOException {

            try {
                String querypart = new URI(null, null, null, "format=ziplist&query=" + query, null).toString();
                URL url = new URL(repository_url, "/action/externalAPI/search_repository" + querypart);
                // System.err.println("query URI is " + url);
                HttpURLConnection c = (HttpURLConnection) url.openConnection();
                if (repository_password != null)
                    c.setRequestProperty("Password", repository_password);
                if (repository_cookie != null)
                    c.setRequestProperty("Cookie", repository_cookie);
                search_time = System.currentTimeMillis();
                int rcode = c.getResponseCode();
                if (rcode != 200) {
                    System.err.println("Response code is " + rcode);
                    System.err.println("Content is: " + c.getResponseMessage());
                    if (rcode == 401)
                        throw new ResourceLoader.PrivilegeViolation("Server returned UNAUTHORIZED HTTP code");
                    return null;
                } else {
                    ArrayList l = readHits(c.getInputStream(), query);
                    if (cutoff > 0) {
                        for (int i = 0;  i < l.size();  i++) {
                            Hit h = (Hit) l.get(i);
                            if (h.score < cutoff)
                                l.remove(i);
                        }
                    }
                    if (showall)
                        return (Hit[]) l.toArray(new Hit[l.size()]);
                    else if (l.size() > 0)
                        return new Hit[] { ((Hit) l.get(0)) };
                    else
                        return new Hit[0];
                }
            } catch (java.net.ConnectException x) {
                throw new ResourceLoader.CommunicationFailure("Can't connect to repository:  " + x);
            } catch (ResourceLoader.PrivilegeViolation x) {
                throw x;
            } catch (ResourceLoader.CommunicationFailure x) {
                throw x;
            } catch (Exception e) {
                System.err.println("Exception raised:  " + e);
                e.printStackTrace(System.err);
            }
            return null;
        }

        /**
           If the query has not been issued yet, this will cause a round-trip to the UpLib server.
           If it has been issued, this will give the cached results of the query if research is
           "false", or a new set of results if research is "true".
           @param research if the query has already been performed on the server, discard the cached results and perform it again
           @return the results of the search.
         */
        public synchronized Hit[] getHits (boolean research) throws IOException {
            if (hits == null) {
                // System.err.println("getting hits for \"" + query + "\"...");
                hits = doSearch(query, cutoff, showall);
                // System.err.println("" + hits.length + " hits found");
            }
            return hits;
        }

        /**
           If the query has not been issued yet, this will cause a round-trip to the UpLib server.
           If it has been issued, this will give the cached results of the query.
           @return the results of the search.
         */
        public Hit[] getHits () throws IOException {
            return getHits(false);
        }

        /**
           Returns the query string for the Search.
           @return the query string
        */
        public String getQuery () {
            return query;
        }

        /**
           Returns the repository the query is being made on.
           @return the repository object
        */
        public Repository getRepository () {
            return Repository.this;
        }
    }

    /**
       Construct and return a Search object embodying the specified query.  A standard
       way of using this might be
       <pre>
       Hit[] hits = repo.search("my search query", 0.0F, true).getHits();
       </pre>
       @param query A string containing an UpLib query.
       @param cutoff A float value giving the lowest score to include in the results.
       @param showall A boolean saying whether to include all results.  If false, only the highest scoring result will be returned.
    */       
    public Search search (String query, float cutoff, boolean showall) {
        return new Search(query, cutoff, showall);
    }

    /**
       A simple test case for the Repository instance.  It creates an instance, using
       the repository URL specified as the first argument on the command line, displays
       its categories (thereby reading the index file), then performs a search, using the second
       command line argument as the query string, and displays the results.
    */
    public static void main (String[] argv) {
        if (argv.length != 2) {
            System.err.println("Usage: java -classpath UpLib.jar com.parc.uplib.readup.uplibbinding.Repository REPOURL QUERY");
            System.exit(1);
        }

        try {
            // don't do cert validation for this
            CertificateHandler.ignoreCerts();

            Repository r = new Repository(new URL(argv[0]), (String) null);
            System.err.println("Repository is " + r + ", hash " + r.hashCode());

            // try serializing the repo
            ObjectOutputStream fos = new ObjectOutputStream(new FileOutputStream("/tmp/serialized.sj"));
            fos.writeObject(r);
            fos.close();
            ObjectInputStream fis = new ObjectInputStream(new FileInputStream("/tmp/serialized.sj"));
            r = (Repository) fis.readObject();
            fis.close();
            System.err.println("Re-internalized repository is " + r + ", hash " + r.hashCode());

            Iterator authors;
            Iterator categories = r.getCategories();
            if ((categories != null) && categories.hasNext()) {
                System.out.print("Categories:");
                while(categories.hasNext())
                    System.out.print("  " + categories.next());
                System.out.println("");
            }

            Search.Hit[] hits = r.search(argv[1], 0.0f, true).getHits();
                
            if ((hits == null) || (hits.length < 1))
                System.out.println("No hits for " + argv[1] + ".");
            else {
                for (int i = 0;  i < hits.length;  i++) {
                    Search.Hit h = hits[i];
                    System.out.println(h.doc.toString() + "     Score:  " + h.score);
                    authors = h.doc.getAuthors();
                    while (authors.hasNext()) {
                        System.out.println("     " + authors.next());
                    }
                    categories = h.doc.getCategories();
                    while (categories.hasNext()) {
                        System.out.println("     " + categories.next());
                    }
                }
            }
        } catch (Exception x) {
            x.printStackTrace(System.err);
        }
    }
}
