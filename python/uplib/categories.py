#
# This file is part of the "UpLib 1.7.11" release.
# Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

import sys, os, re, traceback, time, tempfile, math, urllib
from xml.dom.minidom import getDOMImplementation

from uplib.plibUtil import note, update_metadata, configurator
from uplib.webutils import HTTPCodes, htmlescape

_CONFIGURATION = None

def excluded_categories (repo):
    """Return a dict mapping category name strings to whether or not they
    match the "excluded-categories" RE.

    :param repo: the repository
    :type repo: uplib.repository.Repository
    :return: mapping of category names to whether they are excluded
    :rtype: dict
    """
    conf = configurator.default_configurator()
    excluded_pattern = re.compile(conf.get("excluded-categories") or "email/.*")
    categories = {}
    for category in repo.categories():
        categories[category] = (excluded_pattern.match and True) or False
    return categories

def test_algorithms (repo, *algs):

    from uplib.collection import PrestoCollection

    # find or create a test set
    c = repo.get_collection("categorize algorithms test set")
    if not c:
        c = PrestoCollection(repo, None, query="uplibdate:[1/1/2005 TO 5/1/2008]")
        repo.add_collection("categorize algorithms test set", c)

    # get "ground truth"
    id_to_categories_mapping = repo.get_docids_with_categories()

    # now run the tests
    algresults = []
    for alg in algs:
        # for each document, see how many tags are in first 10,
        # and how many are missed
        docs = {}
        untagged = 0
        tagged = 0
        for doc in c.docs():
            dtags = id_to_categories_mapping.get(doc.id, ())[:]
            # ignore untagged docs
            if dtags:
                tagged += 1
                found = []
                missed = []
                tags = find_likely_tags(doc, score_adjust=alg) or []
                for i in range(min(10, len(tags))):
                    if tags[i][0] in dtags:
                        found.append(tags[i])
                        dtags.remove(tags[i][0])
                missed = dtags
                text = doc.text()
                textlen = (text and len(text.strip())) or 0
                docs[doc.id] = (found, missed, int(doc.get_metadata("page-count") or doc.get_metadata("pagecount")),
                                textlen, doc.get_metadata("title") or "")
            else:
                untagged += 1
        note(3, "%s:  %d untagged docs, %d tagged docs", alg, untagged, tagged)
        algresults.append((alg, docs,))
    return algresults

def _run_test(repo, response, params):
    results = test_algorithms(repo,
                              lambda score, ndocs: (score * score /ndocs) * (math.log(ndocs) + 1),
                              )
    fp = response.open("text/plain; charset=utf-8")
    fp.write('%d documents\n' % len(results[0][1]))
    for alg, docs in results:
        nfound = sum([len(x[0]) for x in docs.values()])
        nmissed = sum([len(x[1]) for x in docs.values()])
        algname = unicode(alg).encode("UTF-8", "strict")
        fp.write("%s:\n  %d / %d    %f\n" % (algname, nfound, nmissed, float(nfound)/float(nfound+nmissed)))
        nfound = sum([len(x[0]) for x in docs.values() if (x[2] == 1)])
        nmissed = sum([len(x[1]) for x in docs.values() if (x[2] == 1)])
        fp.write("  %d / %d  (single-page)    %f\n" % (nfound, nmissed, float(nfound)/float(nfound+nmissed)))
        nfound = sum([len(x[0]) for x in docs.values() if (x[3] == 0)])
        nmissed = sum([len(x[1]) for x in docs.values() if (x[3] == 0)])
        fp.write("  %d / %d  (non-textual)    %f\n" % (nfound, nmissed, float(nfound)/float(nfound+nmissed)))
        nfound = sum([len(x[0]) for x in docs.values() if (x[3] > 100)])
        nmissed = sum([len(x[1]) for x in docs.values() if (x[3] > 100)])
        fp.write("  %d / %d  (100 characters or more of text)    %f\n" % (nfound, nmissed, float(nfound)/float(nfound+nmissed)))
        
    for alg, docs in results:
        fp.write("%s:\n" % unicode(alg).encode("UTF-8", "strict"))
        for id in docs:
            found, missed, pagecount, textlen, title = docs[id]
            fp.write("%s: %s, %s, pages=%s, chars=%d, %s\n" % (id, unicode(found).encode("UTF-8", "strict"),
                                                   unicode(list(missed)).encode("UTF-8", "strict"),
                                                   pagecount, textlen, unicode(title).encode("UTF-8", "strict")))
    fp.close()


def run_test(repo, response, params):
    response.fork_request(_run_test, repo, response, params)

def _adjust_score(score, ndocs):
    return ((score*score)/ndocs) * math.log(ndocs + math.e)

def _quote_quotes(s):
    return re.sub(r'"', r'\\"', re.sub(r'\\', r'\\\\', s))

def _flatten_notes(ann):
    for page in ann:
        t = ""
        notes = ann[page]
        for note in notes:
            if note[1]:
                t +=  ' '.join([x for x in note[1] if x])
        ann[page] = t
    return '\n'.join(ann.values())

def find_likely_tags (doc, score_adjust=None, count=None):

    """
    Return a list of category suggestions for the given document.

    :param doc: the document under consideration
    :type doc: document.Document
    :param score_adjust: a function taking two arguments, the raw score and the number of documents, which will produce a floating point number which is the adjusted score.
    :type score_adjust: fn(float, int) => float
    :param count: number of results to return, defaults to all
    :type count: int
    :return: list of categories and scores for each category
    :rtype: list(string, float)
    """

    note(4, "find_likely_tags:  getting search context (%s)", time.ctime())
    c = doc.repo.search_context()
    note(4, "find_likely_tags:  have search context (%s)", time.ctime())
    if not c:
        return None
    t = doc.text()
    if (not t) or (len(t.strip()) < 20):
        t = doc.get_metadata("summary")
    else:
        t = t.strip()
    if (not t) or (len(t.strip()) < 20):
        t = doc.get_metadata("abstract")
    else:
        t = t.strip()
    if (not t) or (len(t.strip()) < 20):
        t = ""
    t2 = doc.get_metadata("comments")
    if t2 and t2.strip():
        t = t + "\n" + t2.strip()
    t2 = _flatten_notes(doc.get_notes())
    if t2 and t2.strip():
        t = t + "\n" + t2.strip()
    if t and len(t) > 20:
        qstring, hits = c.like_this(t, fieldnames=["contents"])
    else:
        qstring, hits = "", []
    qstring, hits = c.like_this(t, fieldnames=["contents", "notes", "comments", "abstract"])
    note(4, "find_likely_tags:  have %d hits (%s)", len(hits), time.ctime())
    keywords = doc.get_metadata("keywords")
    if keywords:
        keywords = " OR ".join([('keywords:"' + _quote_quotes(x.strip()) + '"') for x in keywords.split(',')])
        note(4, "find_likely_tags:  searching for keywords... (%s)", time.ctime())
        keywords = c.search(keywords)
        note(4, "find_likely_tags:  found %d keywords... (%s)", len(keywords), time.ctime())
    title = doc.get_metadata("title")
    if title:
        title = [x.strip() for x in title.split() if x.strip()]
        if title:
            title = " OR ".join([('title:"' + _quote_quotes(x) + '"') for x in title if ((len(x) > 5) or
                                                                                        ((len(x) > 2) and x.strip().isupper()))])
            if title:
                note(4, "find_likely_tags:  searching for title words %s... (%s)", repr(title), time.ctime())
                title = c.search(title)
                note(4, "find_likely_tags:  found %d title words... (%s)", len(title), time.ctime())
    if not hits and not title and not keywords:
        return None
    else:
        note(4, "find_likely_tags:  creating tags...  (%s)", time.ctime())
        tags = {}
        id_to_categories_mapping = doc.repo.get_docids_with_categories()
        for id, score, pageno in hits:
            if pageno != '*':
                continue
            if id == doc.id:
                continue
            for category in id_to_categories_mapping.get(id, []):
                if category in tags:
                    tags[category][0] += score
                    tags[category][1] += 1
                else:
                    tags[category] = [score, 1]
        if title:
            for id, score in title:
                if id == doc.id:
                    continue
                for category in id_to_categories_mapping.get(id, []):
                    if category in tags:
                        tags[category][0] += score
                        tags[category][1] += 1
                    else:
                        tags[category] = [score, 1]
        if keywords:
            for id, score in title:
                if id == doc.id:
                    continue
                for category in id_to_categories_mapping.get(id, []):
                    if category in tags:
                        tags[category][0] += score * 2
                        tags[category][1] += 1
                    else:
                        tags[category] = [score * 2, 1]
        if not tags:
            return None
        note(4, "find_likely_tags:  sorting tags...  (%s)", time.ctime())
        tags = tags.items()
        # sort by tag names
        tags.sort(lambda x, y: cmp(x[0].lower(), y[0].lower()))
        # remove duplicate tags
        for i in range(1, len(tags)):
            if tags[i][0].lower() == tags[i-1][0].lower():
                tags[i-1] = ('', [0.0, 0])
        tags = [x for x in tags if x[0] and x[1][1] > 0]
        # now sort by score, adjusted for ndocs
        note(4, "find_likely_tags:  sorting tags by score...  (%s)", time.ctime())
        if score_adjust is None:
            score_adjust = _adjust_score
        for tag in tags:
            tag[1].append(score_adjust(*tag[1]))
        tags.sort(lambda x, y: cmp(y[1][2], x[1][2]))
        if tags and isinstance(count, int):
            tags = tags[:min(len(tags), count)]
        note(4, "find_likely_tags:  returning %d tags  (%s)", len(tags), time.ctime())
        return tags

def doc_suggest_categories (repo, response, params):

    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return
    doc = repo.valid_doc_id(doc_id) and repo.get_document(doc_id)
    if not doc:
        response.error(HTTPCodes.NOT_FOUND, "Invalid doc_id parameter '%s' specified." % doc_id)
        return
    n = int(params.get("count") or 0)
    cutoff = float(params.get("cutoff") or 0)
    rettype = params.get("rettype")

    text = doc.text()
    if text:
        terms = repo.search_context().interesting_terms(doc.text(), fieldnames=["contents", "notes", "comments", "abstract"])
        tags = find_likely_tags(doc)
    else:
        terms = []
        tags = []

    if response.xml_request or (rettype == "xml"):
        retval = getDOMImplementation().createDocument(None, "result", None)
        e = retval.createElement('query')
        e.setAttribute('doc_id', doc_id)
        title = doc.get_metadata("title")
        if title:
            e.setAttribute('title', title)
        if n:
            e.setAttribute('count', str(n))
        if cutoff > 0:
            e.setAttribute('cutoff', str(cutoff))
        e.setAttribute('terms', ' '.join(terms))
        retval.documentElement.appendChild(e)
        count = 0
        if tags:
            for tagname, (score, ndocs, ascore) in tags:
                if (score < cutoff) or ((n > 0) and (count >= n)):
                    continue
                e = retval.createElement('tag')
                e.setAttribute('name', tagname)
                e.setAttribute('score', str(ascore))
                retval.documentElement.appendChild(e)
                count += 1
        fp = response.open("application/xml; charset=utf-8")
        fp.write(retval.toxml("UTF-8") + "\n")
        fp.close()

    elif not tags:
        response.reply("No hits found for %s." % doc)
        return
    else:
        categories = [x.lower() for x in doc.get_category_strings()]
        fp = response.open("text/plain; charset=utf-8")
        fp.write("%s\n%s\n\n" % ((doc.get_metadata("title") or str(doc)).encode("UTF-8", "strict"),
                                 (doc.get_metadata("authors") or "").encode("UTF-8", "strict")))
        count = 0
        if tags:
            for tagname, (score, ndocs, ascore) in tags:
                if (not tagname) or (ascore < cutoff) or ((n > 0) and (count >= n)):
                    continue
                fp.write("%s: %f%s    (%f, %d, %f)\n" % (tagname, ascore,
                                                         ((tagname.lower() in categories) and " *") or "",
                                                         score, ndocs, score/ndocs))
                count += 1
                if count == 10:
                    fp.write("----------------------------\n")
            fp.write("----------------------------\n")
        if terms:
            fp.write("Search words:\n")
            for term in terms:
                fp.write("  %s\n" % term.encode("UTF-8", "strict"))
        fp.close()

def doc_add_category (repo, response, params):

    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return
    doc = repo.valid_doc_id(doc_id) and repo.get_document(doc_id)
    if not doc:
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter '%s' specified." % doc_id)
        return
    tag = params.get("tag")
    if not tag:
        response.error(HTTPCodes.BAD_REQUEST, "No 'tag' parameter specified.")
        return
    doc.add_category(tag, reindex=True)
    referer = response.request.get_header('referer')
    defaultaction = '/'.join(response.request_path.split('/')[:3]) + "/doc_categorize?doc_id=%s" % doc_id
    response.redirect(referer or defaultaction)

def doc_remove_category (repo, response, params):

    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return
    doc = repo.valid_doc_id(doc_id) and repo.get_document(doc_id)
    if not doc:
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter '%s' specified." % doc_id)
        return
    tag = params.get("tag")
    if not tag:
        response.error(HTTPCodes.BAD_REQUEST, "No 'tag' parameter specified.")
        return
    doc.remove_category(tag, reindex=True)
    referer = response.request.get_header('referer')
    defaultaction = '/'.join(response.request_path.split('/')[:3]) + "/doc_categorize?doc_id=%s" % doc_id
    response.redirect(referer or defaultaction)


def doc_categorize (repo, response, params):

    from uplib.basicPlugins import show_abstract, _is_sensible_browser
    from uplib.basicPlugins import show_title, STANDARD_BACKGROUND_COLOR, STANDARD_TOOLS_COLOR, STANDARD_LEGEND_COLOR
    from uplib.basicPlugins import __issue_javascript_head_boilerplate as issue_javascript_head_boilerplate
    from uplib.basicPlugins import __issue_menu_definition as issue_menu_definition
    from uplib.basicPlugins import __issue_title_styles as issue_title_styles

    global _CONFIGURATION
    if _CONFIGURATION is None:
        _CONFIGURATION = { "exclusions": [
            re.compile(x.strip()) for x in configurator.default_configurator().get("categorize-excluded-categories", "").split(",") if x.strip()]}

    def figure_size(count, avgsize):
        if avgsize < 0.0001:
            return 0.0001
        return math.sqrt(math.log((count * (math.e - 1))/avgsize + 1))

    doc_id = params.get("doc_id")
    if not doc_id:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id parameter specified.")
        return
    doc = repo.valid_doc_id(doc_id) and repo.get_document(doc_id)
    if not doc:
        response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id parameter '%s' specified." % doc_id)
        return
    fp = response.open()
    title = (doc.get_metadata("title") or doc.id).encode("UTF-8", "strict")
    fp.write("<head><title>Categorizing '%s'</title>\n" % htmlescape(title))
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link REL="SHORTCUT ICON" HREF="/favicon.ico">\n')
    fp.write('<link REL="ICON" type="image/ico" HREF="/favicon.ico">\n')
    issue_javascript_head_boilerplate(fp)
    issue_title_styles(fp)
    fp.write('</head><body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
    issue_menu_definition(fp)
    show_abstract(repo, doc, fp, _is_sensible_browser(response.user_agent), showpagesearch=False)
    fp.write("<hr />\n")
    doccats = [x.lower() for x in doc.get_category_strings()]
    for cat in doccats[:]:
        if cat.find('/') >= 0:
            parts = cat.split('/')
            for i in range(1, len(parts)):
                doccats.append('/'.join(parts[:i]))
    tags = find_likely_tags(doc)
    if tags:
        # try to remove duplicates
        stags = min(10, len(tags))
#         tagnames = [tag[0].split('/')[0] for tag in tags[:stags] if tag[0].find('/') >= 0]
#         count = 0
#         i = 0
#         while tagnames and (i < stags):
#             if tags[i][0] in tagnames:
#                 del tags[i]
#                 stags = min(10, len(tags))
#                 tagnames = [tag[0].split('/')[0] for tag in tags[:stags] if tag[0].find('/') >= 0]
#             else:
#                 i += 1

        fp.write("<center><small><i>Likely categories</i></small><br />")
        count = 0
        topscore = _adjust_score(*tags[0][1][:2])
        exclusions = _CONFIGURATION and _CONFIGURATION.get("exclusions")
        for name, (score, ndocs, ascore) in tags:

            if count > stags:
                break

            skip = False
            for exclusion in exclusions:
                if exclusion.match(name.lower()):
                    skip = True
                    break
            if skip:
                continue

            if count > 0:
                fp.write(" &middot; ")
            #size = max(0.5, (2/topscore) * ascore)
            size = 1
            color = (name.lower() in doccats) and "red" or "black"
            action = '/'.join(response.request_path.split('/')[:3]) + '/doc_%s_category?doc_id=%s&tag=%s' % (
                (name.lower() in doccats) and "remove" or "add", doc.id, urllib.quote_plus(name))
            fp.write('<a style="font-size: %fem; color: %s;" href="%s" title="%s the \'%s\' category (score=%.3f)">%s</a>' % (
                size, color, action,
                (name.lower() in doccats) and "remove" or "add",
                htmlescape(name), ascore, htmlescape(name)))
            count += 1
        fp.write("</center></p><hr />\n")
    fp.write('<form action="%s" method=get><center>Add a new category to this document: ' %
             ('/'.join(response.request_path.split('/')[:3]) + '/doc_add_category'))
    fp.write('<input type=hidden name="doc_id" value="%s">\n' % doc.id)
    fp.write('<input type=text name="tag" value="" size=40></form></center>\n')
    note(4, "doc_categorize:  retrieving repository categories... (%s)", time.ctime())
    cats = repo.get_categories_with_docs()
    note(4, "doc_categorize:  have categories (%s)", time.ctime())
    if cats:
        fp.write("<hr>\n<center><small><i>All categories</i></small><br />")
        avgsize = sum([len(x) for x in cats.values()]) / float(len(cats))
        catkeys = cats.keys()
        catkeys.sort(lambda x, y: cmp(x.lower(), y.lower()))
        first = True
        exclusions = _CONFIGURATION and _CONFIGURATION.get("exclusions")
        for name in catkeys:
            skip = False
            for exclusion in exclusions:
                if exclusion.match(name.lower()):
                    skip = True
                    break
            if skip:
                continue

            if not first:
                fp.write(" &middot; ")
            else:
                first = False
            size = max(0.5, figure_size(len(cats[name]), avgsize))
            color = (name.lower() in doccats) and "red" or "black"
            action = '/'.join(response.request_path.split('/')[:3]) + '/doc_%s_category?doc_id=%s&tag=%s' % (
                (name.lower() in doccats) and "remove" or "add", doc.id, urllib.quote_plus(name))
            actionsee = '/action/basic/repo_search?query=%s' % (
                urllib.quote_plus('categories:"%s"' % name))
            fp.write('<a style="font-size: %fem; color: %s;" href="%s" title="%s the \'%s\' category">%s</a>' % (
                size, color, action,
                (name.lower() in doccats) and "remove" or "add",
                htmlescape(name), htmlescape(name)))
            fp.write('<a style="font-size: %fem; color: %s; vertical-align: super;" href="%s" ' % (
                max(0.4, size/2), STANDARD_LEGEND_COLOR, actionsee) +
                     'title="see the %s document%s in the \'%s\' category" target="_blank">%d</a>' % (
                         (len(cats[name]) == 1) and "one" or str(len(cats[name])),
                         (len(cats[name]) != 1) and "s" or "", htmlescape(name), len(cats[name])))
                     
    fp.write("</body>\n")

category_actions = {
    "doc_suggest_categories":   doc_suggest_categories,
    "doc_categorize":           doc_categorize,
    "doc_add_category":         doc_add_category,
    "doc_remove_category":      doc_remove_category,
    "test_categorize":          run_test,
    }
