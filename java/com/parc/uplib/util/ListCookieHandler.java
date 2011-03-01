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

  This code is derived from code in http://java.sun.com/developer/JDCTechTips/2005/tt0913.html.
  It's under Sun's version of the BSD licence, at http://developer.java.sun.com/berkeley_license.html.
*/

package com.parc.uplib.util;

import java.io.*;
import java.net.*;
import java.util.*;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.text.ParseException;

public class ListCookieHandler extends CookieHandler {
       
    static class Cookie {

        String name;
        String value;
        URI uri;
        String domain;
        Date expires;
        String path;

        private static DateFormat expiresFormat1
            = new SimpleDateFormat("E, dd MMM yyyy k:m:s 'GMT'", Locale.US);

        private static DateFormat expiresFormat2
            = new SimpleDateFormat("E, dd-MMM-yyyy k:m:s 'GMT'", Locale.US);

        /**
         * Construct a cookie from the URI and header fields
         *
         * @param uri URI for cookie
         * @param header Set of attributes in header
         */
        public Cookie(URI uri, String header) {
            String attributes[] = header.split(";");
            String nameValue = attributes[0].trim();
            this.uri = uri;
            this.name = 
                nameValue.substring(0, nameValue.indexOf('='));
            this.value = 
                nameValue.substring(nameValue.indexOf('=')+1);
            this.path = "/";
            this.domain = uri.getHost();

            for (int i=1; i < attributes.length; i++) {
                nameValue = attributes[i].trim();
                int equals = nameValue.indexOf('=');
                if (equals == -1) {
                    continue;
                }
                String name = nameValue.substring(0, equals);
                String value = nameValue.substring(equals+1);
                if (name.equalsIgnoreCase("domain")) {
                    String uriDomain = uri.getHost();
                    if (uriDomain.equals(value)) {
                        this.domain = value;
                    } else {
                        if (!value.startsWith(".")) {
                            value = "." + value;
                        }
                        uriDomain = uriDomain.substring(uriDomain.indexOf('.'));
                        if (!uriDomain.equals(value)) {
                            throw new IllegalArgumentException("Trying to set foreign cookie");
                        }
                        this.domain = value;
                    }
                } else if (name.equalsIgnoreCase("path")) {
                    this.path = value;
                } else if (name.equalsIgnoreCase("expires")) {
                    try {
                        this.expires = expiresFormat1.parse(value);
                    } catch (ParseException e) {
                        try {
                            this.expires = expiresFormat2.parse(value);
                        } catch (ParseException e2) {
                            throw new IllegalArgumentException("Bad date format in header: " + value);
                        }
                    }
                }
            }
        }

        public boolean hasExpired() {
            if (expires == null) {
                return false;
            }
            Date now = new Date();
            return now.after(expires);
        }

        public String getName() {
            return name;
        }

        public String getDomain() {
            return domain;
        }

        public URI getURI() {
            return uri;
        }

        /**
         * Check if cookie isn't expired and if URI matches,
         * should cookie be included in response.
         *
         * @param uri URI to check against
         * @return true if match, false otherwise
         */
        public boolean matches(URI uri) {

            if (hasExpired()) {
                return false;
            }

            String uriDomain = uri.getHost();
            if (!uriDomain.endsWith(this.domain)) {
                // System.err.println("no match: cookie domain is " + this.domain + ", while URI domain is " + uriDomain);
                return false;
            }

            String path = uri.getPath();
            if (path == null) {
                path = "/";
            }

            return path.startsWith(this.path);
        }

        public String toString() {
            StringBuilder result = new StringBuilder(name);
            result.append("=");
            result.append(value);
            return result.toString();
        }
    }

    // "Long" term storage for cookies, not serialized so only
    // for current JVM instance
    private List<Cookie> cache = new LinkedList<Cookie>();

    /**
     * Saves all applicable cookies present in the response 
     * headers into cache.
     * @param uri URI source of cookies
     * @param responseHeaders Immutable map from field names to 
     * lists of field
     *   values representing the response header fields returned
     */

    public void put(URI uri, Map<String, List<String>> responseHeaders)
        throws IOException {

        // System.err.println("put called; Set-Cookie responseHeaders are " + responseHeaders.get("Set-Cookie"));

        List<String> setCookieList = 
            responseHeaders.get("Set-Cookie");
        if (setCookieList != null) {
            for (String item : setCookieList) {
                Cookie cookie = new Cookie(uri, item);
                // Remove cookie if it already exists
                // New one will replace
                for (Cookie existingCookie : cache) {
                    if((cookie.getURI().equals(
                                               existingCookie.getURI())) &&
                       (cookie.getName().equals(
                                                existingCookie.getName()))) {
                        cache.remove(existingCookie);
                        break;
                    }
                }
                System.err.println("Adding to cookies cache: " + cookie.getDomain() + ": " + cookie);
                cache.add(cookie);
            }
        }
    }

    /**
     * Gets all the applicable cookies from a cookie cache for 
     * the specified uri in the request header.
     *
     * @param uri URI to send cookies to in a request
     * @param requestHeaders Map from request header field names 
     * to lists of field values representing the current request 
     * headers
     * @return Immutable map, with field name "Cookie" to a list 
     * of cookies
     */

    public Map<String, List<String>> get(URI uri, Map<String, List<String>> requestHeaders)
        throws IOException {

        // System.err.println("ListCookieHandler::get(" + uri + "):");

        // Retrieve all the cookies for matching URI
        // Put in comma-separated list
        StringBuilder cookies = new StringBuilder();
        for (Cookie cookie : cache) {
            // Remove cookies that have expired
            if (cookie.hasExpired()) {
                cache.remove(cookie);
            } else if (cookie.matches(uri)) {
                if (cookies.length() > 0) {
                    cookies.append(", ");
                }
                // System.err.println("    adding cookie " + cookie);
                cookies.append(cookie.toString());
            }
        }

        // Map to return
        Map<String, List<String>> cookieMap =
            new HashMap<String, List<String>>(requestHeaders);

        // Convert StringBuilder to List, store in map
        if (cookies.length() > 0) {
            List<String> list =
                Collections.singletonList(cookies.toString());
            cookieMap.put("Cookie", list);
        }
        // System.out.println("returning from get, requestHeaders are now " + cookieMap);
        return Collections.unmodifiableMap(cookieMap);
    }

    public static CookieHandler setDefaultHandler () {
        CookieHandler old = CookieHandler.getDefault();
        CookieHandler.setDefault(new ListCookieHandler());
        return old;
    }
}
