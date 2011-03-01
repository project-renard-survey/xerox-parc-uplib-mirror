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

package com.parc.uplib.indexing;

import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.index.TermDocs;
import org.apache.lucene.document.Document;
import org.apache.lucene.search.Searcher;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.search.PhraseQuery;
import org.apache.lucene.search.FuzzyQuery;
import org.apache.lucene.search.WildcardQuery;
import org.apache.lucene.search.PrefixQuery;
import org.apache.lucene.search.PhraseQuery;
import org.apache.lucene.search.RangeQuery;
import org.apache.lucene.search.BooleanQuery;
import org.apache.lucene.search.BooleanClause;
import org.apache.lucene.search.Hits;
import org.apache.lucene.queryParser.QueryParser;
import org.apache.lucene.queryParser.FastCharStream;
import org.apache.lucene.queryParser.TokenMgrError;
import org.apache.lucene.queryParser.ParseException;
import org.apache.lucene.queryParser.MultiFieldQueryParser;

import java.io.File;
import java.io.IOException;
import java.io.FileReader;
import java.io.BufferedReader;
import java.io.StringReader;
import java.util.Date;
import java.util.Map;
import java.util.HashMap;
import java.util.Iterator;
import java.util.ArrayList;
import java.util.StringTokenizer;
import java.util.AbstractSet;
import java.util.Vector;

class UpLibQueryParser extends MultiFieldQueryParser {

    private HeaderField[] fields;
    private Analyzer analyzer;
    private Map abbreviations;
    public boolean debug_mode;

    static private String[] extractFieldNames (HeaderField[] f) {
        String[] tmp = new String[f.length];
        for (int i = 0;  i < f.length;  i++)
            tmp[i] = f[i].name;
        return tmp;
    }

    public UpLibQueryParser (HeaderField[] f, Analyzer a, Map abbrevs) {

        super(extractFieldNames(f), a);

        analyzer = a;
        fields = f;
        abbreviations = abbrevs;
    }

    public Query parse (String query) throws ParseException {
        Query q = super.parse(query);
        if ((q instanceof BooleanQuery) && (((BooleanQuery)q).getClauses().length > 0)) {
            BooleanClause[] clauses = ((BooleanQuery)q).getClauses();
            boolean all_negative = true;
            for (int i = 0;  i < clauses.length;  i++) {
                if (!clauses[i].isProhibited()) {
                    all_negative = false;
                    break;
                }
            }
            if (all_negative) {
                Query q2 = getFieldQuery("categories",
                                         "_(any)_");
                if (q2 instanceof Query)
                    ((BooleanQuery)q).add(q2, BooleanClause.Occur.SHOULD);
            }
        }
        if ((q instanceof BooleanQuery) && (((BooleanQuery)q).getClauses().length == 0))
            return null;
        else
            return q;                
    }

    protected void addClause(Vector clauses,
                             int conj,
                             int mods,
                             Query q) {
        if (debug_mode && (q != null))
            System.err.println("addClause: " + q.getClass() + " " + q);
        if (q instanceof PhraseQuery) {
            Term[] terms = ((PhraseQuery)q).getTerms();
            boolean modified = false;
            for (int i = 0;  i < terms.length;  i++) {
                String f = terms[i].field();
                // System.err.println("term is " + terms[i]);
                if ((f != null) && (f.length() > 0) && (f.charAt(0) == '$')) {
                    // System.err.println("f is \"" + f + "\", f.substring(1) is \"" + f.substring(1) + "\", map has " + abbreviations.get(f.substring(1)));
                    if ((f.length() > 1) && (f.charAt(1) == '$')) {
                        terms[i] = new Term(f.substring(1), terms[i].text());
                        modified = true;
                    } else if (abbreviations.containsKey(f.substring(1))) {
                        terms[i] = new Term((String) abbreviations.get(f.substring(1)), terms[i].text());
                        modified = true;
                    }
                }
            }
            if (modified) {
                q = new PhraseQuery();
                for (int i = 0;  i < terms.length;  i++) {
                    ((PhraseQuery)q).add(terms[i]);
                }
                // System.err.println("new q is " + q);
            }
        } else if (q instanceof TermQuery) {
            Term t = ((TermQuery)q).getTerm();
            String f = t.field();
            if ((f != null) && (f.length() > 0) && (f.charAt(0) == '$')) {
                if ((f.length() > 1) && (f.charAt(1) == '$')) {
                    q = new TermQuery(new Term(f.substring(1), t.text()));
                } else if (abbreviations.containsKey(f.substring(1))) {
                    q = new TermQuery(new Term((String) abbreviations.get(f.substring(1)), t.text()));
                }
            }
        }
        // System.err.println("adding " + q);
        super.addClause(clauses, conj, mods, q);
        /*
        for (int i = 0;  i < clauses.size();  i++)
            System.err.println("clause[" + i + "] is " + clauses.get(i));
        (new Throwable()).printStackTrace(System.err);
        */
    }

    protected Query getPrefixQuery (String field,
                                   String queryText)
        throws ParseException {

        if (debug_mode)
            System.err.println("getPrefixQuery:  field is <" + field + ">, queryText is <" + queryText + ">");

        Query x = super.getPrefixQuery(field, queryText);
        return x;
    }

    protected Query getWildcardQuery (String field,
                                      String queryText)
        throws ParseException {

        if (debug_mode)
            System.err.println("getWildcardQuery:  field is <" + field + ">, queryText is <" + queryText + ">");

        Query x = super.getWildcardQuery(field, queryText);
        return x;
    }

    protected Query getFuzzyQuery (String field,
                                   String queryText,
                                   float minsim)
        throws ParseException {

        if (debug_mode)
            System.err.println("getFuzzyQuery:  field is <" + field + ">, queryText is <" + queryText + ">");

        Query x = super.getFuzzyQuery(field, queryText, minsim);
        return x;
    }

    protected Query getFieldQuery (String field,
                                   String queryText)
        throws ParseException {

        if (debug_mode)
            System.err.println("getFieldQuery:  field is <" + field + ">, queryText is <" + queryText + ">");

        Query x = super.getFieldQuery(field, queryText);
        HeaderField f = HeaderField.findField(fields, field);

        if (field != null) {

            if ((field.equals("categories") || field.equals("keywords"))
                || ((f != null) && (!f.tokenized))) {
                Term t;
                if (field.equals("categories")) {
                    String text = queryText.toLowerCase();
                    String[] parts = text.split("/");
                    text = parts[0].trim();
                    for (int jdx = 1;  jdx < parts.length;  jdx++) {
                        text = text + "/" + parts[jdx].trim();
                    }
                    t = new Term(field, text);
                }
                else
                    t = new Term(field, queryText);
                return new TermQuery(t);

            } else if (field.equals("date") || field.equals("uplibdate") ||
                       ((f != null) && (f.date))) {
                if (queryText.indexOf('/') >= 0) {
                    String newdate = ExtractIndexingInfo.convert_date(queryText);
                    if (newdate != null)
                        queryText = newdate;
                }
                return new TermQuery(new Term(field, queryText));
            } else if ((field.length() > 0) && (field.charAt(0) == '$')) {
                if ((field.length() > 1) && (field.charAt(1) == '$'))
                    return new TermQuery(new Term(field.substring(1), queryText));
                else if (abbreviations.containsKey(field.substring(1))) {
                    return getFieldQuery((String) abbreviations.get(field.substring(1)), queryText);
                }
            }
            
        } else if ((queryText.length() > 0) && (queryText.charAt(0) == '$')) {
            if (((queryText.length() > 1) && (queryText.charAt(1) == '$')) ||
                (abbreviations.containsKey(queryText.substring(1))))
                return new UpLibQueryParser(fields, analyzer, abbreviations).parse((String) abbreviations.get(queryText.substring(1)));            
        }

        return x;
    }

    protected Query getRangeQuery (String field,
                                   String part1,
                                   String part2,
                                   boolean inclusive)
        throws ParseException
    {
        HeaderField f = HeaderField.findField(fields, field);

        if ((field != null) && ((field.equals("date") || field.equals("uplibdate")) ||
                                ((f != null) && (f.date)))) {
                
            if (part1.indexOf('/') >= 0) {
                String new_part1 = ExtractIndexingInfo.convert_date(part1);
                if (new_part1 != null)
                    part1 = new_part1;
            }

            if (part2.indexOf('/') >= 0) {
                String new_part2 = ExtractIndexingInfo.convert_date(part2);
                if (new_part2 != null)
                    part2 = new_part2;
            }

            return new RangeQuery (new Term(field, part1),
                                   new Term(field, part2), inclusive);
        }
        return super.getRangeQuery(field, part1, part2, inclusive);
    }

}

class UpLibPageQueryParser extends UpLibQueryParser {

    public UpLibPageQueryParser (HeaderField[] f, Analyzer a, Map abbrevs) {

        super(f, a, abbrevs);
    }

    protected Query getFieldQuery (String field,
                                   String queryText)
        throws ParseException {

        if (debug_mode)
            System.err.println("page: getFieldQuery:  field is <" + field + ">, queryText is <" + queryText + ">");

        if (field == null)
            return super.getFieldQuery(field, queryText);
        else
            return null;
    }
}

class LuceneIndexing {

    static private final int   INVALID_ARGS = 1;
    static private final int   INVALID_REPOSITORY_DIRECTORY = 2;
    static private final int   BAD_INDEX_DIRECTORY = 3;
    static private final int   INVALID_SEARCH_EXPRESSION = 4;
    static private final int   JAVA_EXCEPTION = 5;

    private static final String STANDARD_TERMS = "contents:title:authors:comment:abstract:keywords*";
    private static HashMap userAbbrevs = new HashMap();

    public static boolean debug_mode = false;

    private static ExtractIndexingInfo.DocumentIterator build_document_iterator (File doc_root_dir, String id) {

        ExtractIndexingInfo.DocumentIterator doc = null;

        try {
            doc = new ExtractIndexingInfo.DocumentIterator(doc_root_dir, id);
        } catch (Exception e) {
            System.out.println("* LuceneIndexing 'build_document_iterator' raised " + e.getClass() + " with message " + e.getMessage());
            e.printStackTrace(System.err);
            System.out.flush();
            System.exit(JAVA_EXCEPTION);
        }

        return doc;
    }

    private static void initialize_user_abbrevs (String a) {

        if (a != null) {
            String[] parts = a.split(";");
            for (int i = 0;  i < parts.length;  i++) {
                String[] keyvalue = parts[i].trim().split("=");
                if (keyvalue.length != 2) {
                    System.err.println("* LuceneIndexing:  invalid abbreviation \"" + parts[i].trim() + "\" specified.");
                    System.exit(INVALID_ARGS);
                }
                if (debug_mode)
                    System.err.println("adding abbreviation $" + keyvalue[0].trim() + " for \"" + keyvalue[1].trim() + "\"");
                userAbbrevs.put(keyvalue[0].trim(), keyvalue[1].trim());
            }
        }
    }

    private static String[] read_docids_file (File f) throws IOException {
        ArrayList ids = new ArrayList();
        BufferedReader r = null;
        String l;
        try {
            r = new BufferedReader(new FileReader(f));
            while ((l = r.readLine()) != null)
                ids.add(l);
        } finally {
            if (r != null)
                r.close();
        }
        return (String[]) ids.toArray(new String[ids.size()]);
    }

    private static void remove (File index_file, String[] doc_ids, int start) {

        String number;
        String list;
        Term term;
        TermDocs matches;

        if (debug_mode)
            System.err.println("index file is " + index_file + " and it " + (index_file.exists() ? "exists." : "does not exist."));

        try {

            if (index_file.exists() && (doc_ids.length > start)) {
                IndexReader reader = IndexReader.open(index_file);
                try {
                    for (int i = start;  i < doc_ids.length;  i++) {
                        term = new Term("id", doc_ids[i]);
                        int deleted = reader.deleteDocuments(term);
                        System.out.println("Deleted " + deleted + " existing instances of " + doc_ids[i]);
                    }
                } finally {
                    reader.close();
                }
            }

        } catch (Exception e) {
            if (debug_mode) {
                e.printStackTrace(System.err);
            } else {
                System.out.println("* LuceneIndexing 'remove' raised " + e.getClass() + " with message " + e.getMessage());
                System.err.println("LuceneIndexing 'remove': caught a " + e.getClass() +
                                   "\n with message: " + e.getMessage());
                System.out.flush();
            }
            System.exit(JAVA_EXCEPTION);
        }
        System.out.flush();
    }

    private static void update (File index_file, File doc_root_dir, String[] ids, int start) {

        ExtractIndexingInfo.DocumentIterator docit;
        String number;

        remove (index_file, ids, start);

        try {

            // Now add the documents to the index
            IndexWriter writer = new IndexWriter(index_file, new StandardAnalyzer(), !index_file.exists());
            if (debug_mode)
                writer.setInfoStream(System.err);
            writer.setMaxFieldLength(Integer.MAX_VALUE);

            try {
                for (int i = start;  i < ids.length;  i ++) {
                    docit = build_document_iterator(doc_root_dir, ids[i]);
                    int count = 0;
                    while (docit.hasNext()) {
                        writer.addDocument((Document)(docit.next()));
                        count += 1;
                    }
                    System.out.println("Added " + docit.id + " (" + count + " versions)");
                    System.out.flush();
                }
            } finally {
                // And close the index
                System.out.println("Optimizing...");
                // See http://www.gossamer-threads.com/lists/lucene/java-dev/47895 about optimize
                // Can fail if low on disk space
                writer.optimize();
                writer.close();
            }

        } catch (Exception e) {
            if (debug_mode) {
                e.printStackTrace(System.err);
            } else {
                System.out.println("* Lucene search engine raised " + e.getClass() + " with message " + e.getMessage());
                System.err.println(" 'update' caught a " + e.getClass() +
                                   "\n with message: " + e.getMessage());
                System.out.flush();
            }
            System.exit(JAVA_EXCEPTION);
        }
        System.out.flush();
    }


    private static Searcher search (File index_file, String querystring) {

        StringBuffer query_buffer = new StringBuffer();
        HeaderField[] query_terms;
        String[] header_names =  null;
        QueryParser.Operator search_operator = QueryParser.AND_OPERATOR;

        String z = System.getProperties().getProperty("com.parc.uplib.indexing.defaultSearchProperties");
        if (z != null) {
            query_terms = HeaderField.parseUserHeaders(z);
        } else {
            query_terms = HeaderField.parseUserHeaders(STANDARD_TERMS);
        }
        z = System.getProperties().getProperty("com.parc.uplib.indexing.defaultSearchOperator");
        if (z != null) {
            if (z.equalsIgnoreCase("or"))
                search_operator = QueryParser.OR_OPERATOR;
            else if (z.equalsIgnoreCase("and"))
                search_operator = QueryParser.AND_OPERATOR;
        }

        try {
            Searcher s = new IndexSearcher(index_file.getCanonicalPath());
            StandardAnalyzer analyzer = new StandardAnalyzer();

            // form the query
            query_buffer.append(querystring);
            
            // run the query
            UpLibQueryParser p = new UpLibQueryParser(query_terms, analyzer, userAbbrevs);
            if (debug_mode)
                p.debug_mode = true;
            p.setDefaultOperator(search_operator);
            Query query = p.parse(query_buffer.toString());
            if (debug_mode)
                System.err.println("query is " + query);
            Hits hits = s.search(query);
            if (debug_mode)
                System.err.println("" + hits.length() + " hits");
            
            // output the results
            for (int i = 0;  i < hits.length();  i++) {
                Document doc = hits.doc(i);
                float score = hits.score(i);
                String number = doc.get("id");
                if (number != null) {
                    String type = doc.get("uplibtype");
                    if ((type == null) || type.equals("whole"))
                        if (debug_mode) {
                            // explanations still fairly useless
                            // org.apache.lucene.search.Explanation explanation = s.explain(query, i);
                            // System.out.println(number + " " + score + " <" + explanation.toString() + ">");
                            System.out.println(number + " " + score);
                        } else {
                            System.out.println(number + " " + score);
                        }
                } else {
                    System.out.println("* No document ID in result returned from Lucene");
                }
            }
            return s;
                
        } catch (ParseException e) {
            System.out.println("* Invalid search expression '" + query_buffer.toString() + "' specified");
            System.err.println(" caught a " + e.getClass() +
                               "\n with message: " + e.getMessage());
            System.out.flush();
            System.exit(INVALID_SEARCH_EXPRESSION);
            return null;

        } catch (Exception e) {
            System.out.println("* Lucene search engine raised " + e.getClass() + " with message " + e.getMessage());
            System.err.println(" 'search' caught a " + e.getClass() +
                               "\n with message: " + e.getMessage());
            e.printStackTrace(System.err);
            System.out.flush();
            System.exit(JAVA_EXCEPTION);
            return null;
        }
    }


    private static void pagesearch (Object index_file, String querystring, boolean show_whole_docs) {

        StringBuffer query_buffer = new StringBuffer();
        HeaderField[] query_terms;
        String[] header_names =  null;
        QueryParser.Operator search_operator = QueryParser.AND_OPERATOR;

        query_terms = HeaderField.parseUserHeaders("pagecontents");

        String z = System.getProperties().getProperty("com.parc.uplib.indexing.defaultPageSearchOperator");
        if (z != null) {
            if (z.equalsIgnoreCase("or"))
                search_operator = QueryParser.OR_OPERATOR;
            else if (z.equalsIgnoreCase("and"))
                search_operator = QueryParser.AND_OPERATOR;
        }

        try {
            IndexSearcher s;

            if (index_file instanceof IndexSearcher)
                s = (IndexSearcher) index_file;
            else if (index_file instanceof File)
                s = new IndexSearcher(((File)index_file).getCanonicalPath());
            else
                throw new java.io.IOException("index_file " + index_file + " must be either File or IndexSearcher");

            StandardAnalyzer analyzer = new StandardAnalyzer();

            // form the query
            query_buffer.append(querystring);
            
            // run the query
            UpLibQueryParser p = new UpLibPageQueryParser(query_terms, analyzer, userAbbrevs);
            if (debug_mode)
                p.debug_mode = true;
            p.setDefaultOperator(search_operator);
            Query query = p.parse(query_buffer.toString());
            if (query != null) {
                if (debug_mode)
                    System.err.println("query.class is " + query.getClass());
                if (debug_mode)
                    System.err.println("query is " + query);
                Hits hits = s.search(query);
                if (debug_mode)
                    System.err.println("" + hits.length() + " hits");
            
                // output the results
                for (int i = 0;  i < hits.length();  i++) {
                    Document doc = hits.doc(i);
                    float score = hits.score(i);
                    String number = doc.get("id");
                    String type = doc.get("uplibtype");
                    if (number != null) {
                        if ((type == null) || type.equals("whole")) {
                            if (show_whole_docs)
                                System.out.println(number + "/* " + score);
                        } else if (type.equals("page")) {
                            String pageid = doc.get("pagenumber");
                            System.out.println(number + "/" + pageid + " " + score);
                        }
                    } else {
                        System.out.println("* No document ID in result returned from Lucene");
                    }
                }
            } else {
                if (debug_mode)
                    System.err.println("no valid page query");
            }
            s.close();
                
        } catch (ParseException e) {
            System.out.println("* Invalid search expression '" + query_buffer.toString() + "' specified");
            System.err.println(" caught a " + e.getClass() +
                               "\n with message: " + e.getMessage());
            System.out.flush();
            System.exit(INVALID_SEARCH_EXPRESSION);
        } catch (Exception e) {
            System.out.println("* Lucene search engine raised " + e.getClass() + " with message " + e.getMessage());
            System.err.println(" 'search' caught a " + e.getClass() +
                               "\n with message: " + e.getMessage());
            e.printStackTrace(System.err);
            System.out.flush();
            System.exit(JAVA_EXCEPTION);
        }
    }


    private static void usage () {
        // print usage message to stderr
        System.err.println("Usage:  LuceneIndexing INDEXDIR search 'QUERY'");
        System.err.println("   or:  LuceneIndexing INDEXDIR pagesearch 'QUERY'");
        System.err.println("   or:  LuceneIndexing INDEXDIR bothsearch 'QUERY'");
        System.err.println("   or:  LuceneIndexing INDEXDIR update DOCROOTDIR DOCID [DOCID...]");
        System.err.println("   or:  LuceneIndexing INDEXDIR batchupdate DOCROOTDIR TEMPFILENAME");
        System.err.println("   or:  LuceneIndexing INDEXDIR remove DOCID [DOCID...]");
    }

    public static void main(String[] args) {

        if (args.length < 3) {
            usage();
            System.exit(INVALID_ARGS);
        }

        File index_file = new File(args[0]);
        if (index_file.exists() && !index_file.isDirectory()) {
            System.err.println("Error:  Indicated INDEXDIR " + args[0] + " is not a directory");
            System.exit(BAD_INDEX_DIRECTORY);
        }

        debug_mode = false;
        String z2 = System.getProperties().getProperty("com.parc.uplib.indexing.debugMode");
        if (z2 != null) {
            debug_mode = (z2.equals("true"));
        }
        
        z2 = System.getProperties().getProperty("org.apache.lucene.writeLockTimeout");
        if (z2 != null) {
        }

        z2 = System.getProperties().getProperty("com.parc.uplib.indexing.userAbbrevs");
        if (z2 != null) {
            initialize_user_abbrevs(z2);
        }

        if (args[1].equals("update")) {

            System.err.println("updating");
            if (args.length < 4) {
                usage();
                System.exit(INVALID_ARGS);
            }
            File doc_root_dir = new File (args[2]);
            System.err.println("doc_root_dir is " + doc_root_dir);
            if (!(doc_root_dir.exists() && doc_root_dir.isDirectory())) {
                System.err.println("Error:  Specified directory " + doc_root_dir + " is not a directory");
                System.exit(INVALID_REPOSITORY_DIRECTORY);
            }

            String z = System.getProperties().getProperty("com.parc.uplib.indexing.indexProperties");
            if (z != null)
                ExtractIndexingInfo.addIndexingFields(z);

            update (index_file, doc_root_dir, args, 3);

        } else if (args[1].equals("batchupdate")) {

            System.err.println("batch updating");
            if (args.length < 4) {
                usage();
                System.exit(INVALID_ARGS);
            }
            File doc_root_dir = new File (args[2]);
            System.err.println("doc_root_dir is " + doc_root_dir);
            if (!(doc_root_dir.exists() && doc_root_dir.isDirectory())) {
                System.err.println("Error:  Specified directory " + doc_root_dir + " is not a directory");
                System.exit(INVALID_REPOSITORY_DIRECTORY);
            }
            File doc_ids_file = new File (args[3]);

            String z = System.getProperties().getProperty("com.parc.uplib.indexing.indexProperties");
            if (z != null)
                ExtractIndexingInfo.addIndexingFields(z);

            try {
                String[] ids = read_docids_file(doc_ids_file);
                update (index_file, doc_root_dir, ids, 0);

            } catch (IOException x) {
                System.err.println("Can't read doc_ids file " + args[3]);
                x.printStackTrace(System.err);
                System.exit(JAVA_EXCEPTION);
            }

        } else if (args[1].equals("remove")) {

            remove (index_file, args, 2);

        } else if (args[1].equals("search")) {

            if (args.length != 3) {
                usage();
                System.exit(INVALID_ARGS);
            }
            Searcher s = search (index_file, args[2]);
            try {
                s.close();
            } catch (java.io.IOException x) {
                // ignore
            }

        } else if (args[1].equals("pagesearch")) {

            if (args.length != 3) {
                usage();
                System.exit(INVALID_ARGS);
            }
            pagesearch (index_file, args[2], true);

        } else if (args[1].equals("bothsearch")) {

            if (args.length != 3) {
                usage();
                System.exit(INVALID_ARGS);
            }
            Searcher s = search (index_file, args[2]);
            pagesearch (s, args[2], false);
            try {
                s.close();
            } catch (java.io.IOException x) {
                // ignore
            }

        } else {
            usage();
            System.exit(INVALID_ARGS);
        }

        System.exit(0);
    }
}
