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

import sys, os, re, traceback, time, StringIO, htmlentitydefs

_SEEN_MAX_LENGTH = 1000
_IGNORE_KEYBOARD_INTERRUPTS = True

def find_feeds(url, visited=None):

    import feedparser

    if visited is None:
        visited = []
    feeds = []
    feed = feedparser.parse(url)
    if not feed:
        note("no feeds in %s", url)
        return feeds
    if not feed.version:
        # not an RSS or Atom feed, recurse
        links = feed.feed.get("links")
        if links:
            for link in links:
                href = link.get("href")
                if href not in visited:
                    visited.append(href)
                    feeds = feeds + find_feeds(href, visited)
    else:
        feeds.append(feed)
    return feeds

HTMLENTITIES = re.compile(r"\&(?P<ref>[^;]+);")

def deescape_html(m):
    candidate = m.group("ref")
    # check for character code
    if candidate[0] == '#':
        try:
            v = int(candidate[1:], 10)
        except:
            return m.group(0)
        else:
            return unichr(v)
    else:
        try:
            v = htmlentitydefs.name2codepoint.get(candidate)
        except:
            return m.group(0)
        else:
            if isinstance(v, int):
                return unichr(v)
            else:
                return m.group(0)    

def process_entry (entry):
    """Return a URL and metadata.txt file drawn from the elements in this entry.

    :param: entry the FeedParser entry
    :type: entry a dictionary of metadata about the entry
    :return: a dictionary of UpLib metadata about the entry.  The "original-url" metadata field is guaranteed.
    :rtype: dict
    """
    d = {}
    from uplib.plibUtil import note
    from uplib.webutils import parse_URL
    if "link" not in entry:
        return None
    link = entry.get("origlink") or entry.get("link")
    # some elementary ad filtering
    host, port, path = parse_URL(link)
    if host.startswith("ads."):
        return None
    d["original-url"] = link
    if entry.has_key("title"):
        d["title"] = HTMLENTITIES.sub(deescape_html, entry.get("title"))
    if entry.has_key("summary"):
        summary = HTMLENTITIES.sub(deescape_html, entry.get("summary"))
        summary = re.sub(r"\s", " ", summary)
        if '<' in summary:
            summary = summary[:summary.index('<')]
        d["abstract"] = summary
        d["summary"] = summary
    author = None
    if entry.has_key("author_detail") and entry.get("author_detail").has_key("name"):
        author = entry.get("author_detail").get("name")
    elif entry.has_key("author"):
        author = entry.author
    if author:
        # ny times does bylines strangely
        if host.endswith("nytimes.com"):
            if author.startswith("By "):
                author = author[3:]
            # capitalize properly
            author = author.title()
            # lowercase "And"
            author = author.replace(" And ", " and ")
        d["authors"] = author
    if entry.has_key("updated_parsed"):
        date = entry.updated_parsed
    elif entry.has_key("published_parsed"):
        date = entry.published_parsed
    elif entry.has_key("created_parsed"):
        date = entry.created_parsed
    else:
        date = None
    if date:
        d["date"] = "%s/%s/%s" % (date[1], date[2], date[0])
        d["rss-timestamp"] = str(int(time.mktime(date)))
    d["rss-id"] = entry.get("id") or entry.get("guid") or entry.get("link")
    return d


class FakeResponse(object):

    """This class is a hollow version of uplib.angelHandler.response.  It responds
    to the same methods, but doesn't do much with them.  Will fail if pressed; for
    instance, there's no 'request' attribute.
    """

    def __init__(self, repo):
        self.repo = repo
	self.fp = None
        self.request = None
        self.code = None
        self.message = None
        self.thread = None

    def open (self, content_type = "text/html"):
	self.fp = StringIO.StringIO()
	return self.fp

    def redirect (self, url):
        self.request = url

    def error (self, code, message, content_type=None):
        if self.fp:
            self.fp.discard()
        self.code = code
        self.message = (message, content_type)

    def reply (self, message, content_type=None):
        # calls "error", so no need to check for unicode -- done in "error"
	self.error(200, message, content_type)

    def return_file (self, typ, path, delete_on_close=False):
        raise ValueError("Can't return file from this kind of response")

    def fork_request(self, fn, *args):
        from uplib.plibUtil import uthread, note
        from uplib.service import run_fn_in_new_thread

        def run_fn_in_new_thread(resp, fn, args):
            try:
                fn(*args)
            except:
                excn = sys.exc_info()
                note(0, "Exception calling %s with %s:\n%s", fn, args, ''.join(traceback.format_exception(*excn)))
                resp.error(HTTPCodes.INTERNAL_SERVER_ERROR, ''.join(traceback.format_exception(*excn)), "text/plain")

        self.thread = uthread.start_new_thread(run_fn_in_new_thread, (self, fn, args))

    def __del__(self):
	if self.fp: self.fp.close()

_ADDED_SITES = []
_REMOVED_SITES = []

def add_site(site):
    global _ADDED_SITES
    if site not in _ADDED_SITES:
        _ADDED_SITES.append(site)

def remove_site(site):
    global _REMOVED_SITES
    if site not in _REMOVED_SITES:
        _REMOVED_SITES.append(site)

def _scan_rss_sites(repo):

    global _ADDED_SITES, _REMOVED_SITES

    try:
        from uplib.plibUtil import configurator, note, write_metadata, id_to_time, create_new_id
        from uplib.extensions import find_and_load_extension
        conf = configurator.default_configurator()

        if repo:
            sys_inits_path = os.path.join(conf.get('uplib-lib'), 'site-extensions')
            repo_inits_path = os.path.join(repo.root(), "overhead", "extensions", "active")
            upload_m = find_and_load_extension("UploadDocument", "%s|%s" % (repo_inits_path, sys_inits_path), None, True)
            if not upload_m:
                note(0, "Can't load UploadDocument extension!")
                sys.exit(1)
            else:
                note("UploadDocument extension is %s", upload_m)

        scan_period = conf.get_int("rss-scan-period", 60 * 2)
        startup_delay = conf.get_int("rss-startup-delay", 0)
        del conf

        import feedparser

        if startup_delay > 0:
            note(3, "startup delay is %d", startup_delay)
            time.sleep(startup_delay)

    except:
        note(0, "RSSReader:  exception starting RSS scan thread:\n%s",
             ''.join(traceback.format_exception(*sys.exc_info())))
        return

    rss_sites = -1
    while True:
        try:
            conf = configurator()       # re-read uplibrc file
            old_rss_sites = rss_sites
            rss_sites = conf.get("rss-sites")
            if old_rss_sites == -1 or (old_rss_sites != rss_sites):
                note(2, "rss_sites are %s", rss_sites)
            scan_period = conf.get_int("rss-scan-period", scan_period)
            expiration_period = conf.get_int("rss-expiration-period", 30 * 24 * 60 * 60)        # 30 days
            if rss_sites:
                rss_sites = rss_sites.split() + _ADDED_SITES
            else:
                rss_sites = _ADDED_SITES[:]
            if rss_sites:
                for site in _REMOVED_SITES:
                    if site in rss_sites:
                        rss_sites.remove(site)
            if rss_sites:
                feeds = []
                for site in rss_sites:
                    if site.startswith("feed:"):
                        feeds.append(feedparser.parse(site))
                    elif site.startswith("http:") or site.startswith("https:"):
                        feeds += find_feeds(site)
                note("feeds are:\n%s", [(x.feed.title, x.href, len(x.entries)) for x in feeds])
                for feed in feeds:
                    note("RSSReader:  %s: %s entries in feed %s", time.ctime(), len(feed.entries), feed.feed.title)
                    for entry in feed.entries:
                        d = process_entry(entry)
                        if not d:
                            continue
                        id = d.get("rss-id")
                        hits = repo.do_query('+rss-id:"%s"' % id)
                        if hits:
                            # already in repo
                            continue
                        if repo:
                            response = FakeResponse(repo)
                            mdoutput = StringIO.StringIO()
                            write_metadata(mdoutput, d)
                            md = mdoutput.getvalue()
                            mdoutput.close()
                            upload_m.add(repo, response, { 'URL': d.get("original-url"),
                                                           'wait': "true",
                                                           'no-redirect': "true",
                                                           'metadata': md,
                                                           'md-categories': "RSSReader/%s" % feed.feed.title,
                                                           })
                            if response.thread:
                                while response.thread.isAlive():
                                    response.thread.join(1.0)
                            note("RSSReader:  %s:  %s (%s: %s)", time.ctime(), repr(d.get("title")), response.code, response.message)
                        else:
                            note("RSSReader:  %s:  %s (%s)\n    %s", time.ctime(), repr(d.get("title")), d.get("date"), d.get("summary"))
            # now do expiries
            old_id = create_new_id(time.time() - expiration_period)[:-5]
            hits = repo.do_query("categories:RSSReader AND id:[00000-00-0000-000 TO %s] AND NOT categories:RSSReader/_noexpire_" % old_id)
            for score, doc in hits:
                # check to see if the user has looked at it
                if os.path.exists(os.path.join(doc.folder(), "activity")):
                    doc.add_category("RSSReader/_noexpire_", True)
                # and if not, remove it
                else:
                    repo.delete_document(doc.id)
            time.sleep(scan_period)
        except KeyboardInterrupt:
            if _IGNORE_KEYBOARD_INTERRUPTS:
                note(0, "RSSReader:  %s", ''.join(traceback.format_exception(*sys.exc_info())))
            else:
                sys.exit(0)                
        except:
            note(0, "RSSReader:  %s", ''.join(traceback.format_exception(*sys.exc_info())))


CRAWLER_THREAD = None

def start(repo):
    from uplib.plibUtil import note, configurator, uthread

    global CRAWLER_THREAD

    try:
        import feedparser
    except ImportError:
        note("RSSReader:  Python feedparser module not available -- can't run RSS scanner")
        return

    from uplib.indexing import HeaderField, initialize
    initialize()                # make sure the indexing headers are present
    HeaderField.HEADERS["rss-id"] = HeaderField("rss-id", True, False, False, False, None)

    if CRAWLER_THREAD is None:
        CRAWLER_THREAD = uthread.start_new_thread(_scan_rss_sites, (repo,), name="RSS feed scanner")

def after_repository_instantiation(repo):
    from uplib.plibUtil import note, configurator, uthread
    conf = configurator.default_configurator()
    rss_enabled = conf.get_bool("enable-rss-reader", True)
    if not rss_enabled:
        note("RSSReader:  explicitly disabled -- not initializing.")
        return
    start(repo)

def main(argv):
    global _IGNORE_KEYBOARD_INTERRUPTS
    try:
        import feedparser
    except ImportError:
        sys.stderr.write("RSSReader:  Python feedparser module not available -- can't run RSS scanner.\n")
        sys.exit(1)
    if argv[0] == "run":
        sys.path.append("/local/share/UpLib-1.7.9/code")
        from uplib.plibUtil import set_verbosity, set_note_sink, uthread
        from uplib.repository import Repository
        uthread.initialize()
        set_note_sink(sys.stderr)
        set_verbosity(4)
        _IGNORE_KEYBOARD_INTERRUPTS = False
        if len(argv) > 1:
            repo = Repository("1.7.9", argv[1], {})
        else:
            repo = None
        _scan_rss_sites(repo)
    elif argv[0] == "scan":
        sys.path.append("/local/share/UpLib-1.7.9/code")
        from uplib.plibUtil import write_metadata
        for arg in argv[1:]:
            for feed in find_feeds(arg):
                print feed.feed.title, feed.href, len(feed.entries)
                for entry in feed.entries:
                    d = process_entry(entry)
                    if d:
                        print (u'%s, by %s, at %s' % (d.get("title"), d.get("authors"), time.ctime(int(d.get("rss-timestamp"))))).encode("UTF-8", "strict")
                        if "'" in d.get("title"):
                            mdoutput = StringIO.StringIO()
                            write_metadata(mdoutput, d)
                            md = mdoutput.getvalue()
                            mdoutput.close()
                            for line in md.split("\n"):
                                line = line.strip()
                                print '    ' + line

    else:
        sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])
