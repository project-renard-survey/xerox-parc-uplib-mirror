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

/*
  This is a server, using the Simple server framework (www.simpleframework.org),
  that handles /office and /web requests, to translate documents in those formats
  to PDF.  It returns PDF documents, upon success.

  It uses JODConverter 3 and OpenOffice to convert Microsoft Office
  documents, and wkpdf (or wkhtmltopdf, or webkit2pdf) to convert Web pages.
  If neither of those is available, it's of no use.
*/

package com.parc.uplib.topdf;

import java.net.InetSocketAddress;
import java.net.SocketAddress;
import java.io.PrintStream;
import java.io.IOException;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.ServerSocket;
import java.nio.channels.FileChannel;
import java.nio.channels.WritableByteChannel;
import java.util.List;
import java.util.logging.Logger;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import org.simpleframework.http.core.Container;
import org.simpleframework.transport.connect.Connection;
import org.simpleframework.transport.connect.SocketConnection;
import org.simpleframework.http.Response;
import org.simpleframework.http.Request;
import org.simpleframework.http.Part;

import com.parc.uplib.util.BaseApp;
import com.parc.uplib.util.Configurator;

import org.artofsolving.jodconverter.document.DefaultDocumentFormatRegistry;
import org.artofsolving.jodconverter.document.DocumentFormatRegistry;
import org.artofsolving.jodconverter.document.DocumentFormat;
import org.artofsolving.jodconverter.office.DefaultOfficeManagerConfiguration;
import org.artofsolving.jodconverter.office.OfficeException;
import org.artofsolving.jodconverter.office.OfficeManager;
import org.artofsolving.jodconverter.office.OfficeConnectionProtocol;
import org.artofsolving.jodconverter.OfficeDocumentConverter;
import org.artofsolving.jodconverter.StandardConversionTask;

public class ToPDF extends BaseApp
    implements Container {

    static Connection our_server = null;

    static String[] wkpdf_command = null;
    static int wkpdf_input = -1;
    static int wkpdf_output = -1;

    static OfficeManager officeManager = null;

    static DocumentFormatRegistry formatRegistry = null;

    static Logger logger = null;

    private static class ShutdownHandler extends Thread {
        public void run () {
            try {
                if (officeManager != null) {
                    logger.info("Stopping officeManager " + officeManager);
                    officeManager.stop();
                }
                logger.info("Closing ToPDF service port " + our_server);
                our_server.close();
            } catch (Exception x) {
                x.printStackTrace(System.err);
            }
        }
    }

    public static class Task implements Runnable {
       
        private final Response response;
        private final Request request;
        private final String caller;
 
        public Task(Request request, Response response) {
            this.response = response;
            this.request = request;
            InetSocketAddress a = request.getClientAddress();
            this.caller = a.getAddress().getHostAddress() + ":" + a.getPort();
        }

        static private String[] getFileParts (File f) {
            String filename = f.getName();
            int point = filename.lastIndexOf('.');
            if (point < 0)
                return new String[] {filename, null};
            else
                return new String[] {filename.substring(0, point), filename.substring(point)};
        }

        static private String figureSuffix (String mimetype) {
            if (mimetype == null) {
                logger.warning("figureSuffix:  no mimetype specified");
                return null;
            }
            DocumentFormat df = formatRegistry.getFormatByMediaType(mimetype);
            if (df == null) {
                logger.warning("figureSuffix:  unrecognized MIME type:  " + mimetype);
                return null;
            }
            String extension = df.getExtension();
            if (extension == null) {
                logger.warning("figureSuffix:  no registered extension for MIME type " + mimetype);
                return null;
            }
            return "." + extension;
        }

        static private String figureMIMEType (String extension) {
            if (extension == null) {
                logger.warning("figureMIMEType:  no suffix specified");
                return null;
            }
            while (extension.startsWith("."))
                extension = extension.substring(1);
            DocumentFormat df = formatRegistry.getFormatByExtension(extension);
            if (df == null) {
                logger.warning("figureMIMEType:  unrecognized extension:  " + extension);
                return null;
            }
            String mimetype = df.getMediaType();
            if (mimetype == null) {
                logger.warning("figureMIMEType:  no registered MIME type for extension " + extension);
                return null;
            }
            return mimetype;
        }

        public void handleOffice (String extension) {

            try {

                if (officeManager == null) {

                    response.setCode(503);
                    response.setText("No support for OpenOffice-based Office conversions in this server.");
                    response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                    response.close();
                }

                Part filepath_part = request.getForm().getPart("filepath");
                Part filetype_part = request.getForm().getPart("filetype");
                Part filebits_part = request.getForm().getPart("file");

                String filetype = null;
                if (filetype_part != null)
                    filetype = filetype_part.getContent();
                File file = null;
                if (filepath_part != null)
                    file = new File(filepath_part.getContent());
                if (filebits_part != null) {
                    if (file != null) {
                        String[] parts = getFileParts(file);
                        if (parts[1] != null)
                            file = File.createTempFile(parts[0], parts[1]);
                        else
                            file = File.createTempFile(parts[0], figureSuffix(filetype));
                    } else {
                        file = File.createTempFile("ToPDF", figureSuffix(filetype));
                    }
                    // copy bits to temp file
                    FileOutputStream output = new FileOutputStream(file);
                    InputStream input = filebits_part.getInputStream();
                    byte[] buffer = new byte[2 << 16];
                    int count;
                    while (input.available() > 0) {
                        count = input.read(buffer);
                        if (count == 0)
                            break;
                        output.write(buffer, 0, count);
                    }
                    output.close();
                    input.close();
                }
                if (file == null) {
                    response.setCode(401);
                    response.setText("No filepath specified.");
                    response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                    response.close();
                    logger.warning("Bad request from " + caller + "; no filepath specified");
                    return;
                }
                if (!file.exists()) {
                    response.setCode(401);
                    response.setText("Specified filepath '" + filepath_part.getContent() + "' does not exist.");
                    response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                    response.close();
                    logger.warning("Bad request from " + caller + "; specified filepath " + file + " doesn't exist");
                    return;
                }
                File tempfile = File.createTempFile("ToPDF", extension);

                try {
                    /*
                      StandardConversionTask t = new StandardConversionTask(file, tempfile, null);
                      if (filetype != null) {
                      DocumentFormat inputFormat = formatRegistry.getFormatByMediaType(filetype);
                      if (inputFormat == null) {
                      response.setCode(401);
                      response.setText("Unknown filetype '" + filetype + "' specified.");
                      response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                      response.close();
                      return;
                      }
                      t.setInputFormat(inputFormat);
                      }
                      officeManager.execute(t);
                    */
                    (new OfficeDocumentConverter(officeManager)).convert(file, tempfile);
                } catch (Exception x) {
                    if (filebits_part != null)
                        removeFileTree(file);
                    response.setCode(501);
                    response.setText("Exception invoking jodconverter");
                    response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                    PrintStream body = response.getPrintStream();
                    x.printStackTrace(body);
                    body.close();
                    logger.severe("Exception " + x + " invoking jodconverter on " + file);
                    return;
                }
                if (filebits_part != null)
                    removeFileTree(file);
                if (tempfile.length() < 5) {
                    response.setCode(501);
                    response.setText("No output generated by JODConverter");
                    response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                    PrintStream body = response.getPrintStream();
                    body.println("Output file empty (" + tempfile.length() + " bytes)");
                    body.close();
                    logger.warning("No output generated by JODConverter for " + file);
                    return;
                }

                long time = System.currentTimeMillis();
                response.set("Content-Type", figureMIMEType(extension));
                response.setContentLength((int) (tempfile.length()));
                response.set("Server", "HelloWorld/1.0 (Simple 4.0)");
                response.setDate("Date", time);
                response.setDate("Last-Modified", System.currentTimeMillis());

                FileChannel input = new FileInputStream(tempfile).getChannel();
                WritableByteChannel output = response.getByteChannel(2 << 16);
                input.transferTo(0, input.size(), output);
                output.close();
                response.close();

                input.close();
                tempfile.delete();

                logger.info("successfully converted " + ((filepath_part == null) ? file.toString() : filepath_part.getContent()) +
                            " for " + caller);

            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
        }

        private void removeFileTree (File tree) throws IOException {
            if (!tree.exists())
                return;
            if (tree.isDirectory()) {
                File[] files = tree.listFiles();
                for (int i = 0;  i < files.length;  i++) {
                    removeFileTree(files[i]);
                }
            }
            tree.delete();
        }

        private String joinStrings(String[] strings) {
            String rval = "";
            for (int i = 0;  i < strings.length;  i++) {
                if (rval.length() > 0)
                    rval += " ";
                rval += strings[i];
            }
            return rval;
        }

        public void handleWeb () {

            try {

                if (wkpdf_command != null) {

                    Part filepath_part = request.getForm().getPart("filepath");
                    Part filebits_part = request.getForm().getPart("zipfile");
                    File file;
                    File tdir = null;           // if non-null, unpacked a zip file into it

                    if (filepath_part == null) {
                        
                        response.setCode(401);
                        response.setText("No filepath specified.");
                        response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                        response.close();
                        logger.warning("Bad request from " + caller + "; no filepath specified");
                        return;
                    }
                    if (filebits_part != null) {
                        try {
                            // unpack zip file into a temp directory
                            tdir = File.createTempFile("zipfile" + Long.toString(System.nanoTime()), "");
                            tdir.delete();
                            tdir.mkdir();
                            ZipInputStream zipinput = new ZipInputStream(filebits_part.getInputStream());
                            ZipEntry ze;
                            byte[] buffer = new byte[2<<16];
                            while ((ze = zipinput.getNextEntry()) != null) {
                                String name = ze.getName();
                                if (ze.isDirectory()) {
                                    File newdir = new File(tdir, name);
                                    if (!newdir.exists()) {
                                        newdir.mkdirs();
                                    }
                                } else {
                                    File newfile = new File(tdir, name);
                                    File parent = newfile.getParentFile();
                                    if (!parent.exists())
                                        parent.mkdirs();
                                    FileOutputStream out = new FileOutputStream(new File(tdir, name));
                                    int bytecount = 0;
                                    int count;
                                    while (zipinput.available() != 0) {
                                        count = zipinput.read(buffer, 0, buffer.length);
                                        if (count > 0)
                                            out.write(buffer, 0, count);
                                        bytecount += count;
                                    }
                                    out.close();
                                }
                            }
                            file = new File(tdir, filepath_part.getContent());
                        } catch (Exception x) {
                            response.setCode(501);
                            response.setText("Exception unpacking zip file");
                            response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                            PrintStream body = response.getPrintStream();
                            x.printStackTrace(body);
                            body.close();
                            logger.severe("Exception " + x + " unpacking zip file");
                            return;
                        }
                    } else {
                        file = new File(filepath_part.getContent());
                    }
                    if (!file.exists()) {
                        response.setCode(401);
                        response.setText("Specified filepath '" + filepath_part.getContent() + "' does not exist.");
                        response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                        response.close();
                        logger.warning("Bad request from " + caller + 
                                       "; specified filepath '" + filepath_part.getContent() + "' does not exist.");
                        return;
                    }
                    File tempfile = File.createTempFile("ToPDF", ".pdf");
                    String[] newwkpdfcommand = new String[wkpdf_command.length];
                    for (int i = 0;  i < wkpdf_command.length;  i++) {
                        newwkpdfcommand[i] = wkpdf_command[i];
                    }
                    newwkpdfcommand[wkpdf_input] = file.getCanonicalPath();
                    newwkpdfcommand[wkpdf_output] = tempfile.getCanonicalPath();

                    int exitstatus = 0;
                    Exception processing_exception = null;

                    try {
                        Process p = Runtime.getRuntime().exec(newwkpdfcommand);
                        exitstatus = p.waitFor();
                    } catch (Exception x) {
                        processing_exception = x;
                    }
                    if (tdir != null) {
                        // remove temp files
                        removeFileTree(tdir);
                    }
                    if (processing_exception != null) {
                        response.setCode(501);
                        response.setText("Exception invoking wkpdf with '" + joinStrings(newwkpdfcommand) + "'");
                        response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                        PrintStream body = response.getPrintStream();
                        processing_exception.printStackTrace(body);
                        body.close();
                        logger.severe("Exception " + processing_exception + " invoking wkpdf on " + file);
                        return;
                    }
                    if (exitstatus != 0) {
                        response.setCode(501);
                        response.setText("Error " + exitstatus + " invoking wkpdf with '" + joinStrings(newwkpdfcommand) + "'");
                        response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                        PrintStream body = response.getPrintStream();
                        body.println("Bad status code " + exitstatus + " returned.");
                        body.close();
                        logger.warning("Error " + exitstatus + " invoking wkpdf with '" + joinStrings(newwkpdfcommand) + "'");
                        return;
                    } else if (tempfile.length() < 5) {
                        response.setCode(501);
                        response.setText("Exception invoking wkpdf with '" + joinStrings(newwkpdfcommand) + "'");
                        response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                        PrintStream body = response.getPrintStream();
                        body.println("Output file empty (" + tempfile.length() + " bytes)");
                        body.close();
                        logger.warning("No output for wkpdf on " + file);
                        return;
                    }
                    
                    long time = System.currentTimeMillis();
                    response.set("Content-Type", "application/pdf");
                    response.setContentLength((int) (tempfile.length()));
                    response.set("Server", "HelloWorld/1.0 (Simple 4.0)");
                    response.setDate("Date", time);
                    response.setDate("Last-Modified", System.currentTimeMillis());

                    FileChannel input = new FileInputStream(tempfile).getChannel();
                    WritableByteChannel output = response.getByteChannel(2 << 16);
                    input.transferTo(0, input.size(), output);
                    output.close();
                    response.close();
                    
                    input.close();
                    tempfile.delete();
                    
                    logger.info("successfully converted " + filepath_part.getContent() +
                                " for " + caller);

                } else {

                    response.setCode(503);
                    response.setText("No support for Web conversions in this server.");
                    response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                    response.close();

                }

            } catch (IOException x) {
                x.printStackTrace(System.err);
            }
        }

        public void handleShutdown () {

            try {

                response.setCode(200);
                response.setText("OK");
                response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                response.close();

                System.exit(0);

            } catch (Exception x) {
                x.printStackTrace(System.err);
            }
        }

        public void run() {

            String pathname = request.getPath().getPath();

            if (pathname.equals("/office-to-pdf") ||
                pathname.equals("/pdf")) {                      // legacy from old Window service
                handleOffice(".pdf");

            } else if (pathname.equals("/excel-to-csv")) {

                handleOffice(".csv");

            } else if (pathname.equals("/csv-to-excel")) {

                handleOffice(".xls");

            } else if (pathname.equals("/web-to-pdf")) {
                handleWeb();

            } else if (pathname.equals("/shutdown")) {
                logger.info("Shutdown command from " + caller);
                handleShutdown();

            } else if (pathname.equals("/ping")) {
                try {
                    logger.info("Ping from " + caller);
                    response.setCode(200);
                    response.setText("OK");
                    response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                    PrintStream body = response.getPrintStream();
                    if (wkpdf_command != null) {
                        body.print("web ");
                    }
                    if (officeManager != null) {
                        body.print("office ");
                    }
                    body.println("");
                    body.close();
                    response.close();
                } catch (IOException x) {
                    x.printStackTrace(System.err);
                }


            } else {
                logger.info("Invalid request " + pathname + " from " + caller);
                try {
                    response.setCode(404);
                    response.setText("Specified path " + pathname + " not valid in this server.\n");                    
                    response.set("Server", "ToPDF/1.0 (UpLib/Simple 4.0)");
                    response.close();
                } catch (IOException x) {
                    x.printStackTrace(System.err);
                }
            }
        }
          
    } 

    public void handle(Request request, Response response) {
        new Thread(new Task(request, response)).start();
    }

    protected String getHTMLAppInfo () {
        return "UpLibToPDF format renderer service";
    }

    public void exitApplication () {
        System.exit(0);
    }

    public ToPDF () {
        super("ToPDF");
    }

    public static void main(String[] list) throws Exception {

        String libdir = System.getProperty("com.parc.uplib.libdir");
        if (libdir == null) {
            System.err.println("System property com.parc.uplib.libdir not set; can't find UpLib configuration");
            System.exit(1);
        }

        ToPDF app = new ToPDF();

        if (app == null) {
            System.err.println("Null app!");
            System.exit(1);
        }

        logger = app.getLogger();

        // Take a look at the UpLib configuration
        Configurator config = app.getConfigurator();

        if (config == null) {
            System.err.println("Null config!");
            System.exit(1);
        }

        // normally we offer service on port 10880 to be compatible with the Windows service
        int port = 0;
        String portnum = System.getProperty("com.parc.uplib.topdf.port");
        if (portnum != null)
            port = Integer.parseInt(portnum);
        else
            port = config.getInt("topdf-port", 10880);

        // normally, we just bind locally, but this is provided for special uses
        String ipaddr = System.getProperty("com.parc.uplib.topdf.ipaddress");
        if (ipaddr == null)
            ipaddr = config.get("topdf-binding-ip-address", "127.0.0.1");

        logger.info("ipaddr is " + ipaddr + ", port is " + port);

        String wkpdf_binary = config.get("wkpdf");
        String wkpdfcommand = null;

        if ((wkpdf_binary == null) || (wkpdf_binary.trim().length() == 0)) {
            // try wkpdftohtml (uses QtWebKit) instead
            wkpdf_binary = config.get("wkhtmltopdf");
            logger.info("wkpdftohtml is '" + wkpdf_binary + "'");
            if ((wkpdf_binary != null) && (wkpdf_binary.trim().length() > 0)) {
                wkpdfcommand = config.get("wkhtmltopdf-command");
            } else {
                // try webkit2html (uses GTKWebKit) instead
                wkpdf_binary = config.get("webkit2pdf");
                logger.info("webkit2pdf is '" + wkpdf_binary + "'");
                if ((wkpdf_binary != null) && (wkpdf_binary.trim().length() > 0)) {
                    wkpdfcommand = config.get("webkit2pdf-command");
                } else {
                    wkpdf_binary = null;
                }
            }
        } else {
            wkpdfcommand = config.get("wkpdf-command");
        }
            
        logger.info("wkpdf binary is '" + wkpdf_binary + "' and wkpdfcommand is '" + wkpdfcommand + "'");

        if ((wkpdf_binary != null) && (wkpdfcommand != null)) {
            // now we need to break it into individual elements
            
            wkpdfcommand = wkpdfcommand.replaceFirst("\"%s\"", wkpdf_binary.replace(" ", "\\ "));
            wkpdf_command = wkpdfcommand.split("\\s");

            for (int i = 0;  i < wkpdf_command.length;  i++) {
                if (wkpdf_command[i].equals("\"%s\"")) {
                    if (wkpdf_input < 0) {
                        wkpdf_input = i;
                    } else if (wkpdf_output < 0) {
                        wkpdf_output = i;
                    }
                }
            }
            if ((wkpdf_output < 0) || (wkpdf_input < 0)) {
                wkpdf_binary = null;
                logger.info("Can't understand wkpdfcommand string: " + wkpdfcommand);
                logger.info("No support for Web page rendering.");
                wkpdfcommand = null;
            } else {
                logger.info("Handling Web rendering with '" + wkpdfcommand + "', input at index " +
                            wkpdf_input + " and output at index " + wkpdf_output);
            }
        }

        String openoffice = config.get("soffice");
        if (openoffice != null) {
            openoffice = openoffice.trim();
            if (openoffice.length() > 0) {
                File oofile = new File(openoffice);
                if (oofile.exists()) {
                    int ooport = -1;
                    // find an unused port to talk to OpenOffice on
                    String ooportnum = System.getProperty("com.parc.uplib.topdf.ooport");
                    if (ooportnum != null)
                        ooport = Integer.parseInt(ooportnum);
                    else
                        ooport = config.getInt("topdf-ooport", -1);
                    if (ooport < 0) {
                        ServerSocket s = new ServerSocket(0);
                        ooport = s.getLocalPort();
                        s.close();
                    }
                    File oohome = oofile.getParentFile().getParentFile();
                    officeManager = new DefaultOfficeManagerConfiguration()
                        .setOfficeHome(oohome)
                        .setPortNumber(ooport)
                        .setTaskExecutionTimeout(120000L)
                        .buildOfficeManager();
                    try {
                        officeManager.start();
                    } catch (OfficeException x) {
                        logger.log(java.util.logging.Level.SEVERE, "Can't start OpenOffice", x);
                        officeManager.stop();
                        officeManager = null;
                        System.exit(1);
                    }
                    formatRegistry = new DefaultDocumentFormatRegistry();
                    logger.info("Handling Microsoft Office rendering with " + officeManager);
                }
            }
        }

        Runtime.getRuntime().addShutdownHook(new ShutdownHandler());
        
        our_server = new SocketConnection(app);
        SocketAddress address = new InetSocketAddress(ipaddr, port);

        our_server.connect(address);
        logger.info("Listening on " + ipaddr + ":" + port);

        app.declareAvailable();
    }
}
