# -*- Python -*-
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
"""
This module provides an Web application API for working with the documents in the
repository.  It provides basic tools for viewing and editing metadata, working
with collections, searching in various ways, and several different ways of displaying
a set of documents.

@author Bill Janssen
"""
__docformat__ = "restructuredtext"
__version__ = "$Revision: 1.322 $"


import sys, os, re, string, cgi, time, traceback, urllib, types, zipfile, tempfile, shutil, codecs, struct, urlparse, hashlib

from uplib.plibUtil import subproc, configurator, Error, read_metadata, true, false, note, update_metadata, split_categories_string, id_to_time, read_metadata, MutexLock, wordboxes_page_iterator, uthread, get_fqdn, find_JAVAHOME
from uplib.plibUtil import MONTHNAMES, format_date, parse_date, next_day, ensure_file, LimitedOrderedDict

from uplib.webutils import HTTPCodes, parse_URL, http_post_multipart, htmlescape

from uplib.collection import Collection, QueryCollection, PrestoCollection

VERSION = "$Id: basicPlugins.py,v 1.322 2011/02/13 06:55:19 janssen Exp $"

############################################################
###
###  Global variables
###
############################################################

KNOWN_LISTING_FORMATS = ('Icon MRU', 'Abstract MRU', 'Title MRU',
                         'Icon DA', 'Icon DP', 'Title DA',
                         'Title DP', 'Abstract DP', 'Abstract DA')
KNOWN_RATINGS = [("0 (unrated)", "0"), ("1 (less relevant)", "1"), ("2 (relevant)", "2"), ("3 (important)", "3"), ("4 (seed document)", "4")]
READING_AMOUNTS = [("0 (none)", "0"), ("1", "1"), ("2", "2"), ("3 (all)", "3")]
LISTING_FORMAT = None

USING_DOCVIEWER = false

EXTERNAL_URL = "http://uplib.parc.com/"
PARC_URL = "http://www.parc.com/"
PARCLINK_TEXT = "PARC"

TEMPORARY_COLLECTIONS = LimitedOrderedDict(20)

USER_BUTTONS = {}       # maps BUTTON-KEY to tuple (LABEL, FN, SCOPE, WEB-PAGE-TARGET-FRAME, URL, DOC-SELECTION-CRITERIA)
USER_BUTTONS_KEYVAL = 0

NEED_STATS = True               # for large collections, this is very expensive
NEED_STATS_PAGES = False        # fun for demo repos, but generally unnecessary
STATS_DOCS = None
STATS_PAGES = None
STATS_TIME = 0
STATS_LOCK = MutexLock('CalculateRepoStats')

SENSIBLE_BROWSERS = re.compile("Safari|Camino|Firefox|Konqueror|Gecko/|Opera")
WANTS_DOC_ICON_MENUS = true

SIMPLE_PAGE_NUMBER = re.compile(r"^-?[0-9]+$")
PAGE_RANGE = re.compile(r"^([0-9]+)(-|--)([0-9]+)$")
PAGE_NUMBERS = re.compile(r"^((b,[0-9]*,[0-9]+(-[0-9]+)*)|(d,[0-9]+,[0-9]+(-[0-9]+)*)|(r,[0-9]+,[0-9]+(-[0-9]+)*))(;"
                          r"((b,[0-9]*,[0-9]+(-[0-9]+)*)|(d,[0-9]+,[0-9]+(-[0-9]+)*)|(r,[0-9]+,[0-9]+(-[0-9]+)*)))*$")

MONTHNAMES_SHORT = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sept", "Oct", "Nov", "Dec")

FN_REPOSITORY_SCOPE = 0
FN_COLLECTION_SCOPE = 1
FN_DOCUMENT_SCOPE = 2

############################################################
###
###  configuration parameters
###
############################################################

STANDARD_BACKGROUND_COLOR = '#e0f0f8'
STANDARD_TOOLS_COLOR = '#c0d8e8'
STANDARD_LEGEND_COLOR = '#99acb9'
STANDARD_DARK_COLOR = '#70797d'
UPLIB_ORANGE_COLOR = '#ef280e'

SEARCH_RESULTS_FORMAT = None
DEFAULT_QUERY_CUTOFF = 0.0
DEFAULT_PAGE_QUERY_CUTOFF = 0.0

SECONDS_PER_DAY = (24 * 60 * 60)
SECONDS_PER_HOUR = (60 * 60)
SECONDS_PER_SIX_MINUTES = (60 * 6)

SWIRLIMG = '<img width=24 height=24 src="/html/images/swirl.gif">'
SWIRLSPACER = '<img width=24 height=24 src="/html/images/transparent.png">'

PAGE_UPDATING_JAVASCRIPT = """
<script type="text/javascript" language="javascript" src="/html/javascripts/prototype.js">
</script>
<script type="text/javascript" language="javascript">

var counter = 0;
var URL = '/action/basic/repo_status_json';
var known_history = null;
var swirlimg = '<img width=24 height=24 src="/html/images/swirl.gif">';
var swirlspacer = '<img width=24 height=24 src="/html/images/transparent.png">';
var pagescount = 0;
var docscount = 0;
var pending_initialized = false;
var was_pending = false;

function formatPendingInfo (o) {
    if (o.pending.length > 0) {
        html = "Documents being incorporated:<br><ul>\\n";
        for (i = 0;  i < o.pending.length;  i++) {
            id = o.pending[i].id;
            title = o.pending[i].title;
            authors = o.pending[i].authors;
            status = o.pending[i].status;
            ripper = (((status == "ripping") || (status == "error")) && o.rippers[o.pending[i].ripper]);
            pagecount = o.pending[i].pagecount;
            html = html + "<li>" +
            ((title.length < 1) ? ("<i>" + id + "</i>") : ("<b>" + unescape(title) + "</b>")) +
            ((authors.length < 1) ? "" : ( " &middot " + unescape(authors) )) +
            " <i>(" + pagecount + " pages)</i><br>" +
            "<font color=red>" + unescape(status) + "</font> "
            if (status == "error") {
                html = html + "<br><pre>" + unescape(o.pending[i].error) + "</pre>";
            } else if (status == "ripping") {
                html = html +
                "<i>(" + unescape(ripper) + ", " + (o.pending[i].ripper + 1) + " of " + o.rippers.length + ")</i>";
            }
        }
        html = html + "</ul>";
    } else {
        html = "No documents pending.";
    }
    // alert("html is " + html);
    return html;
}

function showInfo (req)
{
   responseObj = eval("(" + req.responseText + ")");
   if (responseObj != null) {
       if (known_history == null) {
          known_history = responseObj.history;
       } else if (known_history != responseObj.history) {
          known_history = responseObj.history;
          window.location.reload();
       }
       pending = responseObj.pending;
       if (pending.length > 0) {
           var nonerror = 0;
           for (i = 0;  i < pending.length;  i++) {
               status = pending[i].status;
               if (status != "error") {
                   nonerror += 1;
               }
           }
           if (nonerror > 0) {
              if (!pending_initialized) {
                 $("swirlspan").innerHTML = swirlimg;
                 pending_initialized = true;
              } else if (!was_pending)
                 $("swirlspan").innerHTML = swirlimg;
              was_pending = true;
              $("PendingStatusPanel").innerHTML = formatPendingInfo(responseObj);
           } else {
              if (!pending_initialized) {
                 $("swirlspan").innerHTML = swirlspacer;
                 pending_initialized = true;
              } else if (was_pending)
                 $("swirlspan").innerHTML = swirlspacer;
              was_pending = false;
              $("PendingStatusPanel").innerHTML = "No documents pending incorporation.\\n";
           }
       }
       if ((responseObj.docs != 0) || (responseObj.pages != 0)) {
           if (responseObj.docs != 0) {
              docscount = responseObj.docs;
           }
           if (responseObj.pagescount != 0) {
              pagescount = responseObj.pages;
           }
           if (docscount != 0) {
              if (pagescount != 0) {
                 $("statstext").innerHTML = "" + docscount + " / " + pagescount;
              } else {
                 $("statstext").innerHTML = "" + docscount;
              }
           }
       }
   }
}

function unshowStatusPanel (event) {
    var p = $("PendingStatusPanel");
    document.removeEventListener("mouseup", unshowStatusPanel, true);
    event.stopPropagation();
    event.preventDefault();
    p.style.visibility = "hidden";
}

function showStatusPanel (event) {
    var p = $("PendingStatusPanel");
    p.style.left = 20;
    p.style.top = 20;
    p.style.width = window.innerWidth - 40;
    p.style.visibility = "visible";
    // alert("showStatusPanel " + event + " " + p);
    document.addEventListener("mouseup", unshowStatusPanel, true);
    event.stopPropagation();
    event.preventDefault();
}

function reportError (req) {
    known_history = null;
    window.location.reload();
}

function fetchInfo () {
   var myAjax = new Ajax.Request(URL, { method: 'get',
                                        onComplete: showInfo,
                                        onFailure: reportError });
}

var refresher = null;

function startInfo () {
  refresher = new PeriodicalExecuter(fetchInfo, 5);
  fetchInfo();
}

function pageLoad () {
  startInfo();
  document.searchrepo.query.focus();
}

</script>
"""

JAVASCRIPT_BOILERPLATE = """
<script type="text/javascript" language="javascript" src="/html/javascripts/prototype.js"></script>
<script type="text/javascript" language="javascript">

    var currentElement = null;
    var savedAlt = null;
    var currentMenu = null;
    var currentFunction = null;
    var currentDoc = null;
    var menu_highlight_color = "%(menu-highlight-color)s";
    var menu_background_color = "%(menu-background-color)s";
    var debug_string = '';

function visitPage (docid, elmt) {
    if (elmt != null) {
      url = elmt.url;
      target = elmt.target;
      key = elmt.id;
      if ((url == null) || (url == "null")) {
        if (key == "showMenuButton") {
          // special-case Visit
          url = "/action/basic/dv_show?doc_id=" + docid;
        } else {
          url = "/action/basic/repo_userbutton?uplib_userbutton_key=" + key + "&doc_id=" + docid;
        }
      } else {
        url = url.replace(/%%s/g, docid);
      }
      if ((target != null) && (target != "null")) {
        // do something smart here
        w = window;
      } else {
        w = window;
      }
      // alert("w is " + w + ", url is " + url);
      w.location = url;
    }
}

function upHandler(event) {
  document.removeEventListener("mouseup", upHandler, true);
  event.stopPropagation();
  event.preventDefault();
  if (currentElement != null) {
    currentElement.alt = savedAlt;
    currentElement.title = savedAlt;
  }
  if (currentMenu != null) {
    currentMenu.style.visibility="hidden";
    if ((currentDoc != null) && (currentFunction != null)) {
      var doc = currentDoc;
      var fn = currentFunction;
      currentDoc = null;
      currentFunction = null;
      visitPage(doc, fn);
    }
  }
  debug_string = "";
}

function highlight (menuelement, hl) {
  debug_string = debug_string + "highlight(" + menuelement.id + ", " + hl + ")\\n";
  if (hl == true) {
    menuelement.style.backgroundColor = menu_highlight_color;
    menuelement.style.color = "%(menu-text-color-selected)s";
    currentFunction = menuelement;
  } else {
    menuelement.style.backgroundColor = menu_background_color;
    menuelement.style.color = "%(menu-text-color-unselected)s";
    currentFunction = null;
  }
}

function ignoreHandler (event) {
    event.stopPropagation();
    event.preventDefault();
}

function menushow(id, menuName, element, event) {

  var indexcounter;
  var childnode;
  var showentry = null;

  // alert("shiftKey is " + event.shiftKey + ", altKey is " + event.altKey + ", controlKey is " + event.ctrlKey + ", metaKey is " + event.metaKey);

  if ((event.which != 1) || (event.button > 1))
      return true;

  currentDoc = id;
  currentElement = element;
  savedAlt = element.alt;
  element.alt = null;
  element.title = null;
  currentMenu = document.getElementById(menuName);
  currentMenu.style.backgroundColor = menu_background_color;
  currentMenu.style.left = event.pageX - 10;
  //currentMenu.style.left = event.clientX + window.pageXOffset - 10;
  //currentMenu.style.left = event.offsetX + event.srcElement.style.left - 10;
  currentMenu.style.top = event.pageY - 10;
  //currentMenu.style.top = event.clientY + window.pageYOffset - 10;
  //currentMenu.style.top = event.offsetY + event.srcElement.style.top - 10;
  currentMenu.style.visibility = "visible";
  for (indexcounter = 0;  indexcounter < currentMenu.childNodes.length;  indexcounter++) {
      childnode = currentMenu.childNodes.item(indexcounter);
      if (childnode.className == 'menuentry') {
        highlight(childnode, false);
        if (childnode.id == "showMenuButton")
           showentry = childnode;
      }
  }
  document.addEventListener("mouseup", upHandler, true);
  event.stopPropagation();
  event.preventDefault();
  if (showentry != null)
    highlight(showentry, true);
}

function menuhide(m) {
  if (currentMenu == m) {
    currentDoc = null;
    currentFunction = null;
    document.removeEventListener("mouseup", upHandler, true);
    currentMenu.style.visibility = "hidden";
    event.stopPropagation();
    event.preventDefault();
  }
}

function removeClassName(item, classname) {

  if (item.className == null)
    return;

  var newNames = new Array();
  var currentNames = item.className.split(" ");
  for (var i = 0; i < currentNames.length; i++) {
    if (currentNames[i] != classname)
      newNames.push(currentNames[i]);
  }
  item.className = newNames.join(" ");
}

function addClassName(item, classname) {
  item.className += " " + classname;
}

function hasClassName (item, classname) {
  if (item.className == null)
    return false;
  return (item.className.indexOf(classname) >= 0);
}

var highlightedIcon = null;

function highlightIcon (icon) {
  if ((highlightedIcon != null) && (highlightedIcon != icon)) {
      removeClassName(highlightedIcon, "highlighted");
  }
  if (icon) {
      addClassName(icon, "highlighted");
  }
  highlightedIcon = icon;
}

function submitCollectionButton (url, target, collid, collname) {
  var marks = document.getElementsByName("marked");
  var marknames = "";
  var count = 0;
  if (collid != null)
    url = url + "&coll=" + collid;
  if (collname != null)
    url = url + "&collname=" + escape(collname);
  for (i = 0;  i < marks.length;  i++) {
    if (marks[i].checked) {
      marknames = marknames + "&doc_id=" + marks[i].value;
      count = count + 1;
    }
  }
  url = url + marknames;
  if ((target == "_top") || (target == window.name)) {
    window.location = url;
  } else {
    window.open(url, target);
  }
}

</script>
<style type="text/css">

img.documentIcon {
    border: solid %(icon-border-color)s 1px;
    padding: 0px;
    }

img.documentIcon.highlighted {
    border: solid %(icon-highlight-border-color)s 1px;
    }

img.documentIcon.remote {
    border: solid %(remote-icon-border-color)s 1px;
    padding: 0px;
    }

img.documentIcon.remote.highlighted {
    border: solid %(remote-icon-highlight-border-color)s 1px;
    padding: 0px;
    }

div.documentActionsMenu {
    border: solid %(menu-border-color)s 1px;
    padding: 0px;
    position: absolute;
    left:100;
    top:100;
    visibility: hidden;
    }

div.menuentry {
    background-color: %(menu-background-color)s;
    border-color: #f0f0f0 #909090 #909090 #f0f0f0;
    cursor: default;
    display: block;
    text-decoration: none;
    white-space: nowrap;
    font-family: sans-serif;
    font-size: small;
    color: %(menu-text-color-unselected)s;
    padding: 2px;
    }

#PendingStatusPanel {
    background-color: %(status-background-color)s;
    border: solid %(status-border-color)s 2px;
    color: %(status-text-color)s;
    font-family: sans-serif;
    font-size: small;
    padding: 2px;
    display: block;
    text-decoration: none;
    position: absolute;
    left: 100;
    top: 100;
    visibility: hidden;
    }

div.menuentry div.menuItemSep {
    border-top: 1px solid #909090;
    border-bottom: 1px solid #f0f0f0;
    margin: 4px 2px;
    }

a.parclink {
    color: %(parclink-color)s;
    text-decoration: none;
    font-family: Arial, sans-serif;
    font-size: smaller;
    }

a.parclink:hover {
    text-decoration: underline;
    }

a.statslink:link {
    color: %(statslink-color)s;
    text-decoration: none;
    }

a.statslink:hover {
    color: %(statslink-color)s;
    text-decoration: underline;
    }

a.statslink:active {
    color: %(statslink-active-color)s;
    text-decoration: none;
    }

a.statslink:visited {
    color: %(statslink-color)s;
    text-decoration: none;
    }

a.statslink:visited:hover {
    color: %(statslink-color)s;
    text-decoration: underline;
    }

</style>
"""

JOBS_JAVASCRIPT = """
<script type="text/javascript" language="javascript">

/*
  The model here is that a user starts a Job, a background thread, to
  perform some operation, and returns a page that contains a Javascript
  bit with the job ID in it.  That code periodically checks back and
  re-fetches the output from the job, and updates part of the page with
  that output.

  For instance, a Job could be re-indexing each document in a repository,
  and the job could be adding the title and ID of that document to a list
  as the output.  The Javascript code on the page could fetch that and update
  the progress of the job on the page as it progresses.

  The Job could also post formatted data, JSON or XML, as its output, which
  could be interpreted by the page-side code to form a status display, for
  example a progress meter.
*/

Jobs = {

    light_image: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH1wMDFQoH6JxPuwAAAB10RVh0Q29tbWVudABDcmVhdGVkIHdpdGggVGhlIEdJTVDvZCVuAAAADElEQVQI12P4//8/AAX+Av7czFnnAAAAAElFTkSuQmCC",

    dark_image: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH1wMDFQwOxxpQmQAAAB10RVh0Q29tbWVudABDcmVhdGVkIHdpdGggVGhlIEdJTVDvZCVuAAAADElEQVQI12MoqKwFAALDAWczbgO5AAAAAElFTkSuQmCC",

    bgcolor_image: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH1wMDFRYxwVGHfwAAAB10RVh0Q29tbWVudABDcmVhdGVkIHdpdGggVGhlIEdJTVDvZCVuAAAADElEQVQI12N48OEHAAV8AsnmfUO2AAAAAElFTkSuQmCC",

    known_jobs: {},

    monitor: function (jobid, callback, period, reportError) {
        var fetchInfo = function () {
            var params = "jobid=" + jobid;
            new Ajax.Request("/action/externalAPI/fetch_job_output",
                         { method: 'get',
                           parameters: params,
                           onSuccess: function(req) {
                               jobstatus = eval("(" + req.responseText + ")");
                               if (jobstatus != null) {
                                   if (jobstatus.finished) {
                                       // stop the periodic fetch
                                       Jobs.known_jobs[jobid].stop();
                                       // remove the refresher object
                                       delete Jobs.known_jobs[jobid];
                                   }
                                   callback(jobid, jobstatus.finished ? 100 : jobstatus.percentage, jobstatus.output);
                               }
                            },
                           onFailure: reportError
                           });
        }
        var refresher = new PeriodicalExecuter(fetchInfo, period);
        Jobs.known_jobs[jobid] = refresher;
        refresher.onTimerEvent();
    }
}

</script>
"""

############################################################
###
###  Utility functions
###
############################################################

def _sort_collections (c1, c2):
    if c1[0].lower() < c2[0].lower():
        return -1
    elif c1[0].lower() > c2[0].lower():
        return 1
    else:
        return 0

def _compare_docs_by_score(doc1, doc2, scores):
    score1 = scores.get(doc1.id, 0)
    score2 = scores.get(doc2.id, 0)
    if score1 < score2: return 1
    if score2 < score1: return -1
    return 0

def _caseless_string_sort(s1, s2):
    return cmp(s1.lower(), s2.lower())

def __issue_visitPage_javascript (fp):
    return
    fp.write('<script type="text/javascript" language="javascript">\n'
             'function visitPage(docid, whatToDo) {\n'
             '  debug_string = "";\n'
             '  if (whatToDo == "showMenuButton") {\n'
             '    if (use_doc_viewer)\n'
             '      location = actionPrefix + "/action/basic/dv_show?doc_id=" + docid;\n'
             '    else\n'
             '      location = actionPrefix + "/docs/" + docid + "/index.html";\n'
             '  }\n')
    buttons = get_buttons_sorted(FN_DOCUMENT_SCOPE)
    if len(buttons) > 0:
        for button in buttons:
            label = button[1][0]
            key = button[0]
            fp.write('  else if (whatToDo == "%s") {\n' % key +
                     '    location = actionPrefix + "/action/basic/repo_userbutton?uplib_userbutton_key=%s&doc_id=" + docid;\n' % key +
                     '  }\n')
    fp.write('  else\n'
             '    alert("Unrecognized action \'" + whatToDo + "\'!");\n'
             '}\n'
             '</script>\n')

def __issue_javascript_head_boilerplate(fp):
    if USING_DOCVIEWER:
	dv_value = "true";
    else:
	dv_value = "false";
    fp.write('<script type="text/javascript" language="javascript">\nvar use_doc_viewer = %s;\n</script>\n' % dv_value)
    fp.write(JOBS_JAVASCRIPT);
    fp.write(PAGE_UPDATING_JAVASCRIPT)
    fp.write(JAVASCRIPT_BOILERPLATE % {'menu-background-color' : STANDARD_TOOLS_COLOR,
                                       'menu-highlight-color' : STANDARD_DARK_COLOR,
                                       'menu-border-color' : STANDARD_DARK_COLOR,
                                       'menu-text-color-selected' : "white",
                                       'menu-text-color-unselected' : "black",
                                       'icon-border-color' : STANDARD_LEGEND_COLOR,
                                       'icon-highlight-border-color' : STANDARD_DARK_COLOR,
                                       'remote-icon-border-color' : "pink",
                                       'remote-icon-highlight-border-color' : UPLIB_ORANGE_COLOR,
                                       'status-background-color' : STANDARD_BACKGROUND_COLOR,
                                       'status-border-color': STANDARD_DARK_COLOR,
                                       'status-text-color': "black",
                                       'statslink-active-color': UPLIB_ORANGE_COLOR,
                                       'statslink-color': STANDARD_LEGEND_COLOR,
                                       'parclink-color': "white",
                                       })
    __issue_visitPage_javascript(fp)

def __issue_title_styles (fp):
    fp.write("""<style type="text/css">
             a.titlelink:link { color: %(titlelink-color)s; text-decoration: none }
             a.titlelink:active { color: red; text-decoration: none }
             a.titlelink:hover { color: %(titlelink-color)s; text-decoration: underline }
             a.titlelink:visited { color: %(titlelink-color)s; text-decoration: none }
             a.titlelink:visited:hover { color: %(titlelink-color)s; text-decoration: underline }
             a.sublink:link { color: %(sublink-color)s; text-decoration: none }
             a.sublink:active { color: red; text-decoration: none }
             a.sublink:hover { color: %(sublink-color)s; text-decoration: underline }
             a.sublink:visited { color: %(sublink-color)s; text-decoration: none }
             a.sublink:visited:hover { color: %(sublink-color)s; text-decoration: underline }
             a.idlink:link { color: %(idlink-color)s; text-decoration: none }
             a.idlink:active { color: red; text-decoration: none }
             a.idlink:hover { color: %(idlink-color)s; text-decoration: underline }
             a.idlink:visited { color: %(idlink-color)s; text-decoration: none }
             a.idlink:visited:hover { color: %(idlink-color)s; text-decoration: underline }
             </style>\n""" % { "titlelink-color": "black",
                             "sublink-color": STANDARD_DARK_COLOR,
                             "idlink-color": STANDARD_LEGEND_COLOR}) 

def __issue_pending_status_panel (fp):
    fp.write('<div id="PendingStatusPanel">No documents pending incorporation.</div>\n')

def full_issue_menu_definition (fp, menuid, buttons, actionPrefix):
    visit_url = urlparse.urljoin(actionPrefix, "/action/basic/dv_show?doc_id=%s")
    fp.write('<div id="%s" class="documentActionsMenu" actionPrefix="%s">\n' % (menuid, htmlescape(actionPrefix)) +
             '<div id="showMenuButton" class="menuentry" onmouseover="highlight(this, true)" ' +
             'url="%s" target="%s" ' % (htmlescape(visit_url), "") +
             'onmouseout="highlight(this, false)">Visit</div>\n')
    if len(buttons) > 0:
        fp.write('<div class="menuItemSep"></div>\n')
        for button in buttons:
            label = button[1][0]
            key = button[0]
            url = button[1][4]
            if url:
                url = urlparse.urljoin(actionPrefix, url)
            else:
                url = "null";
            target = button[1][3] or "null"
            fp.write('<div id="%s" class="menuentry" onmouseover="highlight(this, true)" ' % htmlescape(key, true) +
                     'url="%s" target="%s" ' % (htmlescape(url), htmlescape(target)) +
                     'onmouseout="highlight(this, false)">%s</div>\n' % htmlescape(label, true))
    fp.write('</div>\n')

def __issue_menu_definition (fp):
    buttons = get_buttons_sorted(FN_DOCUMENT_SCOPE)
    full_issue_menu_definition(fp, "DocumentIconClickMenu", buttons, "")
    __issue_pending_status_panel(fp)

def __beginpage (fp, title, extra_metas=None):
    fp.write("<html><head><title>%s</title>\n" % htmlescape(title))
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
    fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
    fp.write('<!--\nThe following is for buggy IE browsers\n -->')
    fp.write('<head><meta http-equiv="Pragma" content="no-cache">\n')
    fp.write('<meta http-equiv="Expires" content="-1">\n')
    __issue_title_styles(fp);
    if extra_metas:
        fp.write(extra_metas)
    __issue_javascript_head_boilerplate (fp)
    fp.write('</head>\n')
    __issue_menu_definition(fp)

def __endpage (fp):
    fp.write('</body><!--\nThe following is for buggy IE browsers\n -->')
    fp.write('<head><meta http-equiv="Pragma" content="no-cache">\n')
    fp.write('<meta http-equiv="Expires" content="-1"></head></html>\n')

def _doc_show_URL (id, pageno=None, selection=None):
    if USING_DOCVIEWER:
        if pageno is not None:
            if selection is not None:
                return "/action/basic/dv_show?doc_id=" + id + "&page=%d" % pageno + "&selection-start=%d&selection-end=%d" % selection
            else:
                return "/action/basic/dv_show?doc_id=" + id + "&page=%d" % pageno
        else:
            return "/action/basic/dv_show?doc_id=" + id
    else:
        if pageno is not None:
            return "/docs/" + id + "/page%d.html" % pageno
        else:
            return "/docs/" + id + "/index.html"

def __output_document_icon(doc_id, title, fp, sensible_browser=false, width=None, height=None, menuid=None):
    if menuid is None: menuid = "DocumentIconClickMenu"
    if (sensible_browser and WANTS_DOC_ICON_MENUS):
        fp.write('<img class="documentIcon" src="/docs/%s/thumbnails/first.png" ' % doc_id +
                 'alt="%s" title="%s" %s%s' % (title, title, (width and 'width="%s" ' % width) or "", (height and 'height="%s" ' % height) or "") +
                 'onMouseOver="highlightIcon(this)" '
                 'onMouseOut="highlightIcon(null)" '
                 'onMouseDown="menushow(\'%s\', \'%s\', this, event)">\n' % (doc_id, menuid))
    else:
        fp.write('<a href="%s" border=0 title="%s">' % (_doc_show_URL(doc_id), title) +
                 '<img class="documentIcon" src="/docs/%s/thumbnails/first.png" ' % doc_id +
                 '%s%s' % ((width and 'width="%s" ' % width) or "", (height and 'height="%s" ' % height) or "") +
                 'onMouseOver="highlightIcon(this)" ' +
                 'onMouseOut="highlightIcon(null)" ' +
                 'alt="%s" %s></a>\n' % (title, (width and 'width="%s"' % width) or (height and 'height="%s"' % height) or ""))

def __output_document_title(doc_id, title, fp, sensible_browser=false, menuid=None):
    if menuid is None: menuid = "DocumentIconClickMenu"
    if (sensible_browser and WANTS_DOC_ICON_MENUS):
        fp.write('<a class="titlelink" href="%s"\n' % _doc_show_URL(doc_id) +
                 'alt="%s"\ntitle="%s"\n' % (htmlescape("Read \"%s\"" % title, true), htmlescape(title)) +
                 'onMouseDown="menushow(\'%s\', \'%s\', this, event)"\n>' % (doc_id, menuid) +
                 '%s</a>\n' % htmlescape(title))
    else:
        fp.write('<a href="%s" class="titlelink" title="%s">%s</a>' %
                 (_doc_show_URL(doc_id), htmlescape("Read \"%s\"" % title, true), htmlescape(title)))


def _is_sensible_browser (user_agent):
    return (SENSIBLE_BROWSERS.search(user_agent) != None)

def __show_stats (repo, response, params):

    from math import log10, floor, pow

    conf = configurator.default_configurator()
    DIRUSE = conf.get("diruse-program")

    def diskspace(location):
        if sys.platform.startswith("win"):
            size = 0.0
            try:
                s, o, t = subproc("%s /K \"%s\"" % (DIRUSE, location))
                if s != 0:
                    raise Error("Bad status %d from call to DIRUSE /K.\nOutput was <%s>." % (s, o))
                lines = o.split('\n')
                for line in lines:
                    m = re.match("^\s*([0-9\.]*)\s*[0-9]+\s*TOTAL: .*$", line)
                    if m:
                        size = float(m.group(1))
            except:
                typ, value, tb = sys.exc_info()
                msg = string.join(traceback.format_exception(typ, value, tb))
                raise Error("Exception in call to DIRUSE: "+msg)
            return size
        else:
            while os.path.islink(location):
                location = os.readlink(location)
            s, o, t = subproc("du -s -k %s" % location)
            if s != 0:
                raise Error("Bad status %d from call to du -s -k.\nOutput was <%s>." % (s, o))
            kblocks = int(string.split(o)[0])
            return float(kblocks)

    def round (x):
        return int(floor(x + 0.5))

    def logfn(x, scaling=10.0):
        return round(scaling * log10(x))

    def invlogfn(x, scaling=10.0):
        return round(pow(10, x/scaling))

    root = os.path.dirname(repo.docs_folder())
    total_disk = diskspace(root)
    deleted_disk = diskspace(repo.deleted_folder())
    pending_disk = diskspace(repo.pending_folder())

    pending = os.listdir(repo.pending_folder())
    deleted = os.listdir(repo.deleted_folder())

    colls = repo.list_collections()
    
    lightcolor = "#c0d8e8"
    darkcolor = "#99acb9"
    black = "#000000"

    size = 0
    sizes = {}
    dcount = 0
    for doc in repo.generate_docs():
        dsize = int(doc.get_metadata("pagecount") or doc.get_metadata("page-count") or 1)
        sizes[dsize] = sizes.get(dsize, 0) + 1
        size = size + dsize
        dcount += 1
    avg_size = float(size)/max(1, dcount)
    if not sizes:
        max_pages = 0
        max_docs = 0
    else:
        max_pages = max(sizes.keys())
        max_docs = max(sizes.values())

    fp = response.open()
    name = htmlescape(repo.name())
    __beginpage(fp, "Stats for repository \"%s\"" % name)
    fp.write('</head><body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
    format = repo.get_param("default-listing-format", "Icon MRU")
    output_tools_block (repo, fp, 'Stats for Repository "%s"' % name, format, None, None)
    fp.write('<p>%d documents, %d pages -- average page size %.1f, max page size %d, %d one-page documents\n' % (dcount, size, avg_size, max_pages, sizes.get(1, 0)))

    if 0:
        fp.write('<p><pre><font color="red">\n')
        for row in range(max_docs, 0, -1):
            if (row % 5) == 0:
                fp.write('%3d +' % row)
            else:
                fp.write('    |')
            for col in range(1, max_pages + 1):
                if row <= sizes.get(col, 0):
                    fp.write('*')
                else:
                    fp.write(' ')
            fp.write('\n')
        fp.write('    +' + ((max_pages + 5)/5) * '----|' + '\n')
        fp.write('     ')
        for i in range(5, max_pages + 4, 5):
            pagecount = '%d' % i
            fp.write(((5 - len(pagecount)) * ' ') + pagecount)
        fp.write('\n')    
        fp.write('</font></pre>\n')

    if 0:
        fp.write('<p><pre><font color="red">\n')
        cols = []
        for row in range(logfn(max_docs) + 1, 0, -1):
            if (row % 3) == 0:
                fp.write('%3d +' % invlogfn(row))
            else:
                fp.write('    |')
            note(2, "row is %s", row)
            for col in range(0, logfn(max_pages + 1, 30.0)):
                colval = invlogfn(col, 30.0)
                col1val = invlogfn(col + 1, 30.0)
                if (col1val < 2) and (col1val == colval):
                    note(0, "skipping col %d (%d)", col, colval)
                    continue
                cols.append(col)
                count = 0
                for i in range(colval, col1val):
                    count = count + sizes.get(i, 0)
                note(2, "col is %d (%s-%s), count is %d", col, colval, col1val, count)
                if row <= count:
                    fp.write('*')
                else:
                    fp.write(' ')
            fp.write('\n')
        fp.write('    +' + ((len(cols) + 5)/5) * '----|' + '\n')
        fp.write('     ')
        for i in range(5, len(cols), 5):
            col = cols[i]
            pagecount = str(invlogfn(col, 30.0))
            fp.write(((5 - len(pagecount)) * ' ') + pagecount)
        fp.write('\n')
        fp.write('</font></pre>\n')

    from PIL import Image, ImageDraw, ImageFont
    NUMBERING_FONT = conf.get("numbering-font-file")
    MARGIN = 40
    YSCALE = 200.0
    XSCALE = 250.0
    width = 2 * MARGIN + logfn(max_pages + 1, XSCALE) + 6
    height = 2 * MARGIN + logfn(max_docs + 1, YSCALE)
    im = Image.new('RGB', (width, height))
    map = ImageDraw.Draw(im)
    numberingfont = ImageFont.load_default()
    if NUMBERING_FONT:
        numberingfont = ImageFont.load(NUMBERING_FONT)
    map.rectangle(((0,0), im.size), fill=(0xff, 0xff, 0xff))
    for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200):
        if i < max_docs:
            y = height - (logfn(i + 1, YSCALE) + MARGIN)
            map.line(((MARGIN - 5, y), (width - MARGIN, y)), fill=lightcolor)
            if (i == 1 or i == 5 or (i % 10 == 0)):
                s = str(i)
                tw, th = map.textsize(s)
                map.text((30 - tw, y - th/2), s, fill=darkcolor, font=numberingfont)
    for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 300, 400, 500, 750, 1000):
        if i < max_pages:
            x = logfn(i, XSCALE) + MARGIN + 3
            map.line(((x, height - (MARGIN - 5)), (x, MARGIN)), fill=lightcolor)
            if (i < 6) or ((i < 50) and (i % 10 == 0)) or ((i < 500) and (i % 100 == 0)) or ((i < 1500) and (i % 250 == 0)):
                s = str(i)
                tw, th = map.textsize(s)
                map.text((x - tw/2, height - MARGIN + 10), s, fill=darkcolor, font=numberingfont)
    map.line(((MARGIN, MARGIN), (MARGIN, height - MARGIN), (width - MARGIN, height - MARGIN)), fill=black)
    s = "Document size (pages)"
    tw, th = map.textsize(s)
    map.text(((width - tw)/2, height - (th + 2)), s, fill=black, font=numberingfont)
    s = "# Documents"
    tw, th = map.textsize(s)
    top = (height - (len(s) * (th + 2)))/2
    for c in s:
        map.text((1, top), c, fill=black, font=numberingfont)
        top = top + th + 2
    for i in range(1, max_pages + 1):
        count = sizes.get(i, 0)
        if (count > 0):
            x = logfn(i, XSCALE) + MARGIN + 3
            y = logfn(count + 1, YSCALE) + MARGIN
            map.rectangle(((x - 2, height - MARGIN - 1), (x + 2, height - y)), fill=darkcolor)
    mapfile = open(os.path.join(root, "html", "images", "usage.png"), 'wb')
    im.save(mapfile, 'PNG')

    fp.write('<p><img src="/html/images/usage.png"><p>\n')

    # s = sizes.keys()
    #s.sort()
    #for v in s:
    #    fp.write('<br>%d pages:  %d\n' % (v, sizes.get(v, 0)))

    fp.write('<p>%d collections\n' % len(colls))
    fp.write('<p>Pending:  %d (%d MB)<br>\n' % (len(pending), (pending_disk + 511)/1024))
    fp.write('Deleted:  %d (%d MB)\n' % (len(deleted), (deleted_disk + 511)/1024))
    fp.write('<hr>\n')
    fp.write('<p>Root is %s.' % root)
    if sizes:
        fp.write('<br>Disk space used:  %.3f MB (%.3f MB/doc, %.1f KB/page)\n' %
                 (float((total_disk)/1024), float((total_disk)/ (1024 * dcount)),
                  (float(total_disk)/size)))

    output_footer(repo, fp, None)
    __endpage(fp)

    fp.close()

############################################################
###
###  repo_show
###
############################################################

def figure_stats (repo):

    # in the background, figure out how many docs we have, and how many pages
    global STATS_PAGES, STATS_TIME, STATS_LOCK, STATS_DOCS, NEED_STATS_PAGES, NEED_STATS

    if NEED_STATS:
        STATS_LOCK.acquire()
        # we are holding STATS_LOCK, so be sure to release it upon finishing
        try:
            STATS_TIME = repo.mod_time()
            if NEED_STATS_PAGES:
                size = 0
                sizes = {}
                dcount = 0
                for doc in repo.generate_docs():
                    dsize = int(doc.get_metadata("pagecount") or doc.get_metadata("page-count") or 1)
                    sizes[dsize] = sizes.get(dsize, 0) + 1
                    size = size + dsize
                    dcount += 1
                STATS_DOCS = dcount
                if dcount > 0:
                    max_pages = max(sizes.keys())
                    max_docs = max(sizes.values())
                    avg_size = float(size)/dcount
                else:
                    max_pages = 0
                    max_docs = 0
                    avg_size = 0
                STATS_PAGES = size
                note("finished counting pages -- %d" % STATS_PAGES)
            else:
                STATS_DOCS = repo.docs_count()
        finally:
            STATS_LOCK.release()

def output_tools_block(repo, fp, page_title, listing_format, coll, name, existing_query="", datekind=None):

    global STATS_TIME, STATS_DOCS, STATS_PAGES, STATS_LOCK, NEED_STATS, NEED_STATS_PAGES

    # if the repo is huge, figuring out the document count might be very time-consuming
    if NEED_STATS:
        if STATS_DOCS == None or repo.mod_time() > STATS_TIME:
            STATS_DOCS = repo.docs_count()
        if NEED_STATS_PAGES and (STATS_PAGES == None or repo.mod_time() > STATS_TIME):
            if NEED_STATS_PAGES:
                # new thread will acquire and release STATS_LOCK when done
                uthread.start_new_thread(figure_stats, (repo,))
        if STATS_PAGES == None:
            stats = "%d" % STATS_DOCS
        else:
            stats = "%d / %d" % (STATS_DOCS, STATS_PAGES)
    else:
        stats = "(stats disabled)"

    if isinstance(coll, QueryCollection) and not existing_query:
        existing_query = coll.query

    # figure out whether there's anything in pending
    pending = repo.list_pending()
    actualpending = len([x for x in pending if x.get("status") != "error"])
    if actualpending > 0:
        init_spacer = SWIRLIMG
    else:
        init_spacer = SWIRLSPACER

    fp.write('<table bgcolor="%s" width=100%%><tr>' % STANDARD_TOOLS_COLOR)

    fp.write('<td><table width=100%><tr valign=baseline>')
    fp.write('<td width=60%% align=left><font size=+2 style="color: black"><b>%s</b></font></td>' % page_title)
    fp.write('<td width=15%% align=center><a class=statslink href="/action/basic/repo_stats" title="See repository statistics"><span id="statstext">%s</span></a></td>' % stats)
    fp.write('<td width=24px align=center><span id="swirlspan" onMouseDown="showStatusPanel(event)">%s</span></td>\n' % init_spacer)
    fp.write('<td width=23%% align=right><font size="-1" color="#ffffff">'
             '<a href="%s" class="sublink">UpLib %s</a></font>' % (htmlescape(EXTERNAL_URL), repo.get_version()))
    fp.write('<font size="-2" color="%s">&nbsp;&middot;&nbsp;<a href="%s" class=parclink>%s</a></font>'
             % (STANDARD_BACKGROUND_COLOR, PARC_URL, htmlescape(PARCLINK_TEXT)));
    fp.write('</td></tr></table></td></tr>\n')

    fp.write('<tr valign=bottom><td><table width=100%><tr valign=top>')
    fp.write('<td width=50% align=center>'
             '<font size=-2 style="color: ' + STANDARD_LEGEND_COLOR + '">Search</font><br>'
             '<form action="/action/basic/repo_search" method=get name=searchrepo enctype="multipart/form-data" accept-charset="%s">' % INTERACTION_CHARSET)
    fp.write('<input type=text name=query size=50 value="%s">\n</form>\n</td>\n' % htmlescape(existing_query, true))

    fp.write('<td align=center>'
             '<font size=-2 style="color: ' + STANDARD_LEGEND_COLOR + '">Help</font><br>\n'
             '<a href="/html/helppages/info.html" target="_top" title="Help">'
             '<img src="/html/images/info.png" border=0 alt="Help" align=bottom vspace=4></a>\n</td>')

    fp.write('<td align=center><font size=-2 color="' + STANDARD_LEGEND_COLOR
             + '">Categories</font><br><form action="/action/basic/repo_show_category" method=get name=categories>\n')
    category_names = repo.categories()
    category_names.sort(_caseless_string_sort)
    if isinstance(coll, QueryCollection) and re.match(r'\+categories:"[^"]+"', coll.query):
        selected_category_name = re.match(r'\+categories:"([^"]+)"', coll.query).group(1)
    else:
        selected_category_name = None
    if isinstance(coll, Collection):
        fp.write('<input type=hidden name="coll" value="%s">\n' % coll.name())
    fp.write('<select name="category_name" size=1 onchange="{document.categories.submit();}">\n')
    fp.write('<option value="(any)">(any)</option>\n')
    for cname in category_names:
        if cname == selected_category_name:
            fp.write('<option selected value="%s">%s</option>\n' % (htmlescape(cname, true), htmlescape(cname)))
        else:
            fp.write('<option value="%s">%s</option>\n' % (htmlescape(cname, true), htmlescape(cname)))
    fp.write('<option value="(none)">(Uncategorized)</option>\n')
    fp.write('<option value="(edit)">(Categorize)</option>\n')
    if datekind is not None:
        fp.write('<input type=hidden name="datekind" value="%s">\n' % datekind)
    fp.write('</select></form></td>\n')

    fp.write('<td align=center><font size=-2 color="' + STANDARD_LEGEND_COLOR
             + '">Collections</font><br><form action="/action/basic/repo_show" method=get name=collections>\n')

    selected_collection = None
    colls = repo.list_collections()
    colls.sort(_sort_collections)
    editing_collections = (coll is not None) and (string.find(page_title, "Collections in ") == 0)
    fp.write('<select name="collname" size=1 onchange="{document.collections.submit();}">\n')
    if coll is not None and not editing_collections:
        fp.write('<option selected value="">(All Documents)</option>\n')
    else:
        fp.write('<option value="">(All Documents)</option>\n')
    for cname, icoll in colls:
        if icoll == coll:
            selected_collection = cname
            fp.write('<option selected value="%s">%s</option>\n' % (htmlescape(cname, true), htmlescape(cname)))
        else:
            fp.write('<option value="%s">%s</option>\n' % (htmlescape(cname, true), htmlescape(cname)))
    if editing_collections:
        fp.write('<option selected value="(edit)">(Edit Collections)</option>\n')
    else:
        fp.write('<option value="(edit)">(Edit Collections)</option>\n')
    if datekind is not None:
        fp.write('<input type=hidden name="datekind" value="%s">\n' % datekind)
    fp.write('</select></form></td>\n')

    fp.write('<td align=center><font size=-2 color="' + STANDARD_LEGEND_COLOR + '">Listing Format</font><br>'
             '<form action="/action/basic/repo_show" method=GET name=listingformats>\n')
    if selected_collection:
        fp.write('<input type=hidden name="collname" value="%s">\n' % selected_collection)
    elif isinstance(coll, Collection):
        fp.write('<input type=hidden name="coll" value="%s">\n' % coll.name())
    if name:
        fp.write('<input type=hidden name="name" value="%s">\n' % name)
    fp.write('<select name="format" size=1 onchange="{document.listingformats.submit();}">\n')
    for format in KNOWN_LISTING_FORMATS:
        if listing_format == format:
            fp.write('<option selected value="%s" label="%s">%s</option>\n' % (format, format, format))
        else:
            fp.write('<option value="%s" label="%s">%s</option>\n' % (format, format, format))
    if datekind is not None:
        fp.write('<input type=hidden name="datekind" value="%s">\n' % datekind)
    fp.write('</select></form></td>\n')

    fp.write('</tr></table>')
    # find all the non-document buttons
    buttons = get_buttons_sorted(FN_REPOSITORY_SCOPE)
    if isinstance(coll, Collection) and repo.get_collection_name(coll):
        # named collection being displayed
        buttons2 = get_buttons_sorted(FN_COLLECTION_SCOPE)
        if buttons2:
            if buttons:
                buttons = buttons + buttons2
            else:
                buttons = buttons2
    if len(buttons) > 0:
        fp.write('<table width=100%><tr>')
        size = min(10, 100 / len(buttons))
        for button in buttons:
            criteria = button[1][5]
            scope = button[1][2]
            if (scope == FN_COLLECTION_SCOPE) and (isinstance(coll, Collection)) or (criteria and not criteria(coll)):
                # skip this button
                continue
            key = button[0]
            label = button[1][0]
            target = button[1][3] or "_self"
            fp.write('<td width=%d%%>' % size)
            fp.write('<form action="/action/basic/repo_userbutton" target="%s">' % target +
                     '<input type=hidden name="uplib_userbutton_key" value="%s">' % key)
            if (scope == FN_COLLECTION_SCOPE):
                fp.write('<input type=button value="%s" onClick="{submitCollectionButton(' % htmlescape(label) +
                         "'/action/basic/repo_userbutton?uplib_userbutton_key=%s', '%s', '%s'" % (key, target, coll.id) +
                         ', null)}"></form>')
            else:
                fp.write('<input type=submit value="%s"></form>' % htmlescape(label))
            fp.write('</td>')
        if (100 - len(buttons) * size) > 0:
            fp.write('<td width=%d%%>&nbsp;</td>' % (100 - len(buttons) * size))
        fp.write('</tr></table>')
    fp.write('</td></tr></table><hr>\n')

def output_footer(repo, fp, coll, logged_in = true):

    global STATS_TIME, STATS_DOCS, STATS_PAGES, STATS_LOCK

    registered_collection = isinstance(coll, Collection) and repo.get_collection(coll.id, true)

    fp.write('<hr>')

    if isinstance(coll, Collection):
        fp.write('<p><table width=100%% bgcolor="%s">' % STANDARD_TOOLS_COLOR)
        buttons = get_buttons_sorted(FN_COLLECTION_SCOPE)
        note(4, "collection is %s, collection buttons are %s", coll, buttons)
        if len(buttons) > 0:
            fp.write('<tr>')
            size = min(10, 100 / len(buttons))
            for button in buttons:
                key = button[0]
                label = button[1][0]
                target = button[1][3] or "_self"
                criteria = button[1][5]
                if (criteria and not criteria(coll)):
                    # skip this button
                    continue

                fp.write('<td width=%d%%>' % size)
                fp.write('<form action="/action/foo">' +
                         '<input type=button value="%s" onClick="{submitCollectionButton(' % htmlescape(label) +
                         "'/action/basic/repo_userbutton?uplib_userbutton_key=%s', '%s', '%s'" % (key, target, coll.id) +
                         ', null)}"></form>')
                fp.write('</td>')
            if (100 - len(buttons) * size) > 0:
                fp.write('<td width=%d%%>&nbsp;</td>' % (100 - len(buttons) * size))
            fp.write('</tr>')

        if not registered_collection and isinstance(coll, QueryCollection):

            fp.write('<tr valign=center>')
            fp.write('<td align=center colspan=10><form action="/action/basic/repo_addqcoll" method=get>\n')
            fp.write('<input type=hidden name="query" value="%s">' % htmlescape(coll.query, true))
            fp.write('Save search as: '
                     '<input type=text name="label" value="" size=60>')
            fp.write('<input type=submit value="Save"></form></td>\n')
            fp.write('</tr>')

        fp.write('</table>\n<hr>\n')

    fp.write('<table bgcolor="%s" width=100%%><tr>' % STANDARD_TOOLS_COLOR)

    if not logged_in:
        fp.write('<td align=center><form action="/action/basic/login" method=get>\n'
                 '<input type=submit value="Login" style="{background-color:white; color:black}"></form></td>\n')

    fp.write('<td align=center><form action="/action/basic/repo_password" method=get>\n'
             '<input type=submit value="Change Repository Password" style="{background-color:red; color:white}"></form></td>\n')

    fp.write('<td align=center><form action="/action/basic/repo_changename" method=get>\n'
             '<input type=submit value="Change Repository Name" style="{background-color:blue; color:white}"></form></td>\n')

    fp.write('<td align=center><form action="/action/basic/ext_list" method=get>\n'
             '<input type=submit value="Manage Extensions" style="{background-color:blue; color:white}"></form></td>\n')

    uptime = repo.up_time()
    daysup = int(uptime) / SECONDS_PER_DAY
    hoursup = (int(uptime) % SECONDS_PER_DAY) / SECONDS_PER_HOUR
    partial_hours_up = (int(uptime) % SECONDS_PER_HOUR) / SECONDS_PER_SIX_MINUTES
    timestats = "%d day%s, %d.%d hour%s" % (daysup, ((daysup != 1) and "s") or "",
                                            hoursup, partial_hours_up,
                                            (((hoursup != 1) or (partial_hours_up != 0)) and "s") or "")
    fp.write('<td align=center><font size="-1" color="%s">%s</font></td>' % (STANDARD_LEGEND_COLOR, timestats))

    if registered_collection:
        fp.write('<td align=center><form action="/action/basic/coll_delete" method=get>\n')
        fp.write('<input type=hidden name="nexturl" value="/action/basic/repo_colls">')
        fp.write('<input type=hidden name="coll" value="%s">' % coll.name())
        fp.write('<input type=submit value="Delete Collection" '
                 'style="{background-color:red; color:white}"></form></td>\n')

    fp.write('</tr></table>\n')

def collections_docs (repo, cids):

    global TEMPORARY_COLLECTIONS

    def _compare_docs(doc1, doc2):
        # return in most-recent first order
        if doc1.id < doc2.id: return 1
        if doc1.id > doc2.id: return -1
        return 0

    if type(cids) == types.StringType:
        cids = [ cids ]
    docs = []
    scores = None
    for cid in cids:
        c = repo.get_collection(cid, true) or TEMPORARY_COLLECTIONS.get(cid)
        if not c:
            raise Error("Can't find collection '%s'" % cid)
        for doc in c.docs():
            if not doc in docs:
                docs.append(doc)
        if len(cids) == 1 and isinstance(c, QueryCollection):
            scores = c.xscores
    if scores:
        docs.sort(lambda x, y, z=scores: _compare_docs_by_score(x, y, z))
    else:
        docs.sort(_compare_docs)
    return docs

def repo_show_timescale (repo, format, response, form_values, coll, docs, name, title, scores):

    def figure_years (docs, coll, form_values, format):

        def addtime (doc):
            t = doc.add_time()
            v = time.localtime(doc.add_time())
            return (v.tm_year, v.tm_mon, v.tm_mday)

        if format.endswith(" DP"):
            import uplib.document
            datefn = uplib.document.Document.get_date
        elif format.endswith(" DA"):
            datefn = addtime
        else:
            raise ValueError("bad value %s for parameter 'format'" % format)
        years = {}
        for doc in docs:
            date = datefn(doc)
            if date:
                if years.has_key(date[0]):
                    years[date[0]].append((date, doc,))
                else:
                    years[date[0]] = [(date, doc)]
            else:
                if years.has_key(0):
                    years[0].append(((0, 0, 0), doc,))
                else:
                    years[0] = [((0, 0, 0), doc,)]
        return years

    def figure_months (docs):
        months = {}
        maxmonth = 0
        for docentry in docs:
            date, doc = docentry
            if months.has_key(date[1]):
                months[date[1]].append(docentry)
            else:
                months[date[1]] = [ docentry ]
            if len(months[date[1]]) > maxmonth:
                maxmonth = len(months[date[1]])
        return months, maxmonth

    def docsortfn (d1, d2):
        date1, doc1 = d1
        date2, doc2 = d2
        if (date1 < date2):
            return -1
        elif (date1 > date2):
            return 1
        elif (doc1.id < doc2.id):
            return -1
        elif (doc1.id > doc2.id):
            return 1
        else:
            return 0

    def issue_textual_month_mark (fp, monthindex):
        #fp.write('<font color="%s" size=-1>&middot; &middot; &middot; &middot; &middot; &nbsp; &nbsp; '
        #         '<i>%s</i></font><br>' % (STANDARD_LEGEND_COLOR, MONTHNAMES[monthindex-1]))
        fp.write('<table width=100%% border=0><tr><td width=5%% align=left><hr color="%s"></td>'
                 % STANDARD_LEGEND_COLOR +
                 '<td align=left width=1%%><font color="%s" size=-1><i>%s</i></font></td><td><hr color="%s"></td></tr></table>\n'
                 % (STANDARD_LEGEND_COLOR, MONTHNAMES[monthindex-1], STANDARD_LEGEND_COLOR))

    def issue_month_tombstone (fp, monthindex):
        fp.write(' <img class="documentIcon" src="/html/images/%s.png">\n'
                 % time.strftime("%B", (2004, monthindex, 1, 0, 0, 0, 0, 1, 0)).lower())

    # create something to write to
    fp = response.open()

    # return an HTML view of the documents in the collection

    fp.write("<head><title>%s</title>\n" % htmlescape(title))
    refresh_period = int(repo.get_param('overview-refresh-period', 0))
    if refresh_period:
        fp.write('<meta http-equiv="Refresh" content="%d">\n' % refresh_period)
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
    fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
    __issue_javascript_head_boilerplate(fp)
    __issue_title_styles(fp)
    fp.write('</head>\n')
    fp.write('<body bgcolor="%s" onload="javascript:pageLoad();">\n' % STANDARD_BACKGROUND_COLOR)
    __issue_menu_definition(fp);

    output_tools_block(repo, fp, title, format, coll, form_values and form_values.get('name'))

    output_query_stats (repo, fp, coll, docs)

    if docs:
        years = figure_years(docs, coll, form_values, format)
        yearkeys = years.keys()
        yearkeys.sort()
        yearkeys.reverse()
        for key in yearkeys:
            docs = years[key]
            docs.sort(docsortfn)
            fp.write('<p><table width=100%% bgcolor="%s"><tr><td width=100%% align=left><font color="white"><b>%s</b></font></td></tr></table>\n' % (STANDARD_LEGEND_COLOR, (key and str(key)) or "unknown"))
            months, maxmonth = figure_months(docs)
            if (len(docs) > 20 or maxmonth > 4):
                showmonths = 0
            else:
                showmonths = None
            count = 0
            if format.startswith("Title"):
                fp.write("<UL>\n")
            for docentry in docs:
                date, doc = docentry
                while showmonths is not None and showmonths <= date[1]:
                    if (format.startswith("Thumbnails") or format.startswith("Icon")) and (showmonths > 0):
                        issue_month_tombstone(fp, showmonths)
                    elif format.startswith("Title") and (showmonths > 0):
                        issue_textual_month_mark(fp, showmonths)
                    showmonths = showmonths + 1
                if format.startswith("Title"):
                    show_title(fp, doc, scores, _is_sensible_browser(response.user_agent), coll)
                elif format.startswith("Thumbnails") or format.startswith("Icon"):
                    title = _get_thumbnail_tooltip(doc, scores)
                    iwidth, iheight = doc.icon_size()
                    __output_document_icon(doc.id, htmlescape(title, True), fp, _is_sensible_browser(response.user_agent), width=iwidth, height=iheight)
                elif format.startswith("Abstract"):
                    if (count > 0):
                        fp.write('<hr>\n')
                    show_abstract(repo, doc, fp, _is_sensible_browser(response.user_agent),
                                  score = scores and scores.get(doc.id))
                count = count + 1
                    
            while (showmonths is not None and showmonths < 12):
                if format.startswith("Thumbnails") or format.startswith("Icon"):
                    issue_month_tombstone(fp, showmonths)
                elif format.startswith("Title"):
                    issue_textual_month_mark(fp, showmonths)
                showmonths = showmonths + 1

            if format.startswith("Title"):
                fp.write("</UL>\n")
            else:
                fp.write("<br>")
    else:
        fp.write("No documents in " + ((isinstance(coll, Collection) and "collection") or "repository") + ".\n")
    output_footer(repo, fp, coll, response.logged_in)
    fp.write("</body>\n")
    fp.close()

def _get_thumbnail_tooltip (doc, scores=None):
    dict = doc.get_metadata()
    doc_date = doc.get_date()
    year = doc_date and doc_date[0]
    title = ""
    scored = false
    if dict:
        if dict.has_key('title'):
            title = title + dict['title']
            if dict.has_key('authors'):
                title = title + '\n' + dict['authors']
        elif dict.has_key('summary'):
            s = re.sub(' / ', '\n', dict['summary'])
            title = title + s[:min(len(s), 100)]
        if scores and scores.has_key(doc.id):
            title = title + '\nscore:  %.2f' % (scores[doc.id] * 100)
            scored = true
        # 'page-count' is the approved version, 'pagecount' is deprecated
        if dict.has_key('page-count') or dict.has_key('pagecount'):
            pagecount = int(dict.get('page-count') or dict.get('pagecount'))
            if scored:
                title = title + ' '
            else:
                title = title + '\n'
            title = title + '(' + str(pagecount) + ' page%s)' % (((pagecount > 1) and "s") or "")
            if year:
                title = title + ' * '
        if year:
            title = title + str(year)
        title = title + '\n'
    return (title or doc.id)

def repo_show_thumbnails (repo, format, response, form_values, coll, docs, name, title, scores):

    # create something to write to
    fp = response.open()

    # return an HTML view of the documents in the collection

    fp.write("<head><title>%s</title>\n" % htmlescape(title))
    refresh_period = int(repo.get_param('overview-refresh-period', 0))
    if refresh_period:
        fp.write('<meta http-equiv="Refresh" content="%d">\n' % refresh_period)
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
    fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
    __issue_javascript_head_boilerplate(fp)
    __issue_title_styles(fp)
    fp.write('</head>\n')
    fp.write('<body bgcolor="%s" onload="javascript:pageLoad();">\n' % STANDARD_BACKGROUND_COLOR)
    __issue_menu_definition(fp);

    output_tools_block(repo, fp, title, format, coll, form_values and form_values.get('name'))

    output_query_stats (repo, fp, coll, docs)

    fp.write('<p>')
    if docs:
        count = 0
        for doc in docs:
            tooltip = htmlescape(_get_thumbnail_tooltip(doc, scores), true)
            iwidth, iheight = doc.icon_size()
            __output_document_icon(doc.id, tooltip, fp, _is_sensible_browser(response.user_agent), width=iwidth, height=iheight)
    else:
        fp.write("No documents in " + ((isinstance(coll, Collection) and "collection") or "repository") + ".\n")
    output_footer(repo, fp, coll, response.logged_in)
    fp.write("</body>\n")
    fp.close()

def show_abstract (repo, doc, fp, sensible_browser, score=None, pages=None, query=None, maxpages=10, showpagesearch=true, showid=False):
    dict = doc.get_metadata()
    pubdate = dict.get("date")
    date = re.sub(" 0|^0", " ",
                  time.strftime("%d %b %Y, %I:%M %p",
                                time.localtime(id_to_time(doc.id))))
    name = doc.id
    page_count = dict.get('page-count')
    summary = '<i>(No summary available.)</i>'
    iwidth, iheight = doc.icon_size()
    if dict.has_key('title'):
        name = htmlescape(dict.get('title'), True)
    elif dict.has_key('name'):
        name = htmlescape('[' + dict.get('name') + ']', True)
    fp.write('<table border=0><tr><td>')
    fp.write('<center>')
    if score != None:
        fp.write('<small>score:</small> <font color="red">%5.2f</font><br>&nbsp;<br>' % (score * 100))
    __output_document_icon(doc.id, name, fp, sensible_browser, width=iwidth, height=iheight)
    fp.write('<br><small><font color="%s">(added %s)</font></small></center></td><td>&nbsp;</td>'
             % (STANDARD_DARK_COLOR, date))
    fp.write('<td valign=top><h3>%s</h3>' % name)
    if dict.has_key('authors') or pubdate:
        fp.write('<p><small>')
        if dict.has_key('authors'):
            authors = dict["authors"]
            authors = authors.split(" and ")
            notfirst = False
            for author in authors:
                if notfirst: fp.write("<font color=\"%s\">, </font>" % STANDARD_DARK_COLOR)
                fp.write("<a href=\"/action/basic/repo_search?cutoff=0&query=authors:%s\" " %
                         urllib.quote_plus((u'"%s"~3' % author).encode("ASCII", "xmlcharrefreplace")) +
                         "class=titlelink title=\"%s\"><b>%s</b></a>" %
                         (htmlescape("All documents by %s" % author, true), htmlescape(author)))
                notfirst = True
        if pubdate:
            formatted_date = format_date(pubdate, true)
            fp.write('&nbsp;&nbsp;&nbsp;&nbsp;<i><font color="%s">%s</font></i>' % (STANDARD_DARK_COLOR,
                                                                                    formatted_date))
        fp.write('</small>\n')
    if dict.has_key('comment') and dict['comment'].strip():
        summary = htmlescape(dict.get('comment', ''))
    elif dict.has_key('abstract') and dict['abstract'].strip():
        summary = "<i>" + htmlescape(dict.get('abstract', '')) + '</i>'
    elif dict.has_key('summary') and dict['summary'].strip():
        summary = '<font color="%s">' % STANDARD_DARK_COLOR + htmlescape(dict.get('summary')) + '</font>'
    fp.write('<P>%s' % summary)
    if page_count:
        fp.write('<small><i><font color="%s"> &middot; (%s page%s)'
                 % (STANDARD_DARK_COLOR, page_count, ((int(page_count) != 1) and "s") or ""))
        if score or query:
            fp.write(' &middot; <input type=checkbox name="marked" value="%s"%s>'
                     % (doc.id, " checked"))
        fp.write('</font></i></small>\n')
    categories = doc.get_category_strings()
    if categories:
        fp.write('<small> &middot; ')
        notfirst = false
        fp.write('<span style="color: %s">(categories: </span>' % STANDARD_LEGEND_COLOR)
        for category in categories:
            if notfirst: fp.write('<font color="%s">, </font>' % STANDARD_DARK_COLOR)
            fp.write("<a href=\"/action/basic/repo_search?query=categories:%%22%s%%22\" " %
                     urllib.quote_plus(category.encode("ASCII", "xmlcharrefreplace")) +
                     'style="color: %s" title="%s">%s</a>' % (STANDARD_DARK_COLOR,
                                                              htmlescape("All documents in category '%s'" % category, true),
                                                              htmlescape(category)))
            notfirst = true
        fp.write(')</small>\n')

    if showid:
        fp.write('<small> &middot; <span style="color: %s">%s</span></small>' % (STANDARD_LEGEND_COLOR, doc.id))

    def sort_by_scores(d):
        def compare (a, b):
            return cmp(a[1], b[1])
        l = d.items()
        l.sort(compare)
        l.reverse()
        return l

    if page_count and (int(page_count) > 1) and showpagesearch:
        fp.write('<P><table border=0 width=100%><tr>')
        thumbnails = 0
        if pages:
            fp.write('<td valign=top align=left>')
            for page, score in sort_by_scores(pages):
                if thumbnails >= maxpages:
                    break
                fp.write('<a href="%s" alt="page %d, %5.2f" ' % (_doc_show_URL(doc.id, page), page+1, score) +
                         'title="page %d, %5.2f" border=0>' % (page+1, score) +
                         '<img src="/docs/%s/thumbnails/%d.png" height="100" alt="%5.2f" title="%5.2f" ' % (doc.id, page+1, score, score) +
                         'style="border: solid %s 1px"></a>\n' % STANDARD_LEGEND_COLOR)
                thumbnails += 1
            if len(pages) > maxpages:
                fp.write('&nbsp;<font color="%s">' % STANDARD_LEGEND_COLOR +
                         '<a class=sublink '
                         'href="/action/basic/doc_search?doc_id=%s&query=%s">' % (doc.id, urllib.quote_plus(query.encode("ASCII", "xmlcharrefreplace"))) +
                         '(more...)</a></font>')
            fp.write('</td>')
        fp.write('<td align=right valign=top>\n')
        fp.write('<font color="%s">' % STANDARD_LEGEND_COLOR +
                 '<small><i>Search within this document:</i></small></font>\n' +
                 '<form action="/action/basic/doc_search" method=get name=searchdoc>\n' +
                 '<input type=hidden name=doc_id value="%s">\n' % doc.id +
                 '<input type=text name=query size=30 value="">\n</form>')
        fp.write('</td></tr></table>\n')

    fp.write('</td></tr></table>\n')

def output_query_stats (repo, fp, coll, docs):

    if coll and isinstance(coll, QueryCollection) and not repo.get_collection(coll.id, true):
        existing_query = coll.query
        cutoff = coll.cutoff
        if (repo.get_param("show-search-timing") == "true"):
            st_bit = ' <font color="%s">(%.3f sec)</font>' % (STANDARD_LEGEND_COLOR, coll.scanduration)
        else:
            st_bit = ""
        fp.write('<table width=100% border=0><tr><td colspan=2>' +
                 '<center><small><b>%d</b> hits for query <i>"%s"</i> above cutoff of %5.2f%s</small></center>\n</td></tr>'
                 % (len(docs), htmlescape(existing_query), cutoff * 100, st_bit))
        fp.write('<tr>' +
                 '<td align=left><form action="/action/basic/repo_search" method=get name=search_narrow>' +
                 '<small><input type=hidden name=query value="%s\">' % htmlescape(existing_query) +
                 'Narrow search: <input type=text size=30 name=narrow value=""></small></form></td>')
        fp.write('<td align=right><form action="/action/basic/repo_search" method=get name=search_widen>' +
                 '<small><input type=hidden name=query value="%s\">' % htmlescape(existing_query) +
                 'Widen search: <input type=text size=30 name=widen value=""></small></form></td></tr>')

        buttons = get_buttons_sorted(FN_COLLECTION_SCOPE)
        note(4, "collection is %s, collection buttons are %s", coll, buttons)
        if len(buttons) > 0:
            fp.write('<tr>')
            size = min(10, 100 / len(buttons))
            for button in buttons:
                key = button[0]
                label = button[1][0]
                target = button[1][3] or "_self"
                criteria = button[1][5]
                if (criteria and not criteria(coll)):
                    # skip this button
                    continue
                fp.write('<td width=%d%%>' % size)
                fp.write('<form action="/action/foo">' +
                         '<input type=button value="%s" onClick="{submitCollectionButton(' % htmlescape(label) +
                         "'/action/basic/repo_userbutton?uplib_userbutton_key=%s', '%s', '%s'" % (key, target, coll.id) +
                         ', null)}"></form>')
                fp.write('</td>')
            if (100 - len(buttons) * size) > 0:
                fp.write('<td width=%d%%>&nbsp;</td>' % (100 - len(buttons) * size))
            fp.write('</tr>')

        fp.write('</table><hr>\n')

def repo_show_abstracts (repo, format, response, form_values, coll, docs, name, title, scores):

    # create something to write to
    fp = response.open()

    # return an HTML view of the documents in the collection

    fp.write("<head><title>%s</title>\n" % htmlescape(title))
    refresh_period = int(repo.get_param('overview-refresh-period', 0))
    if refresh_period:
        fp.write('<meta http-equiv="Refresh" content="%d">\n' % refresh_period)
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link REL="SHORTCUT ICON" HREF="/favicon.ico">\n')
    fp.write('<link REL="ICON" type="image/ico" HREF="/favicon.ico">\n')
    __issue_javascript_head_boilerplate(fp)
    __issue_title_styles(fp);
    fp.write('</head><body bgcolor="%s" onload="javascript:pageLoad();">\n' % STANDARD_BACKGROUND_COLOR)
    __issue_menu_definition(fp)

    output_tools_block (repo, fp, htmlescape(title), format, coll, name)

    output_query_stats (repo, fp, coll, docs)

    if docs:
        count = 0
        for doc in docs:
            score = scores and scores.get(doc.id)
            if count > 0:
                fp.write('<hr>\n')
            pages = isinstance(coll, QueryCollection) and coll.pages(doc)
            query = isinstance(coll, QueryCollection) and coll.query
            show_abstract(repo, doc, fp, _is_sensible_browser(response.user_agent), score, pages, query)
            count = count + 1
    else:
        fp.write("No documents in " + ((isinstance(coll, Collection) and "collection") or "repository") + ".\n")
    output_footer(repo, fp, coll, response.logged_in)
    fp.write("</body>\n")
    fp.close()

def show_title (fp, doc, scores, sensible_browser = false, coll = None, short_display=False):
    line = doc.get_metadata("name") or doc.get_metadata("title") or doc.get_metadata("summary") or doc.id
    date = doc.get_metadata("date")
    if short_display:
        fp.write("&bull; ")
    else:
        fp.write("<li>")
    __output_document_title(doc.id, line, fp, sensible_browser)
    if scores and scores.has_key(doc.id):
        fp.write(' <small><font color=red>%.2f</font></small>' % (100 * scores[doc.id]))
    if isinstance(coll, Collection):
        fp.write('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<input type=checkbox name=marked value=\"%s\" checked>' % doc.id)
    notfirst = false
    authors = doc.get_metadata("authors") or []
    if authors:
        authors = authors.split(" and ")
        fp.write('<br>\n<small>')
        for author in authors:
            if notfirst: fp.write("<font color=\"%s\">, </font>" % STANDARD_DARK_COLOR)
            fp.write("<a href=\"/action/basic/repo_search?cutoff=0&query=authors:%s\" " %
                     urllib.quote_plus(('"%s"~3' % author).encode("ASCII", "xmlcharrefreplace")) +
                     "class=sublink title=\"%s\">%s</a>" %
                     (htmlescape("All documents by %s" % author, true), htmlescape(author)))
            notfirst = true
            if short_display:
                if len(authors) > 1:
                    fp.write("<font color=\"%s\">...</font>" % STANDARD_DARK_COLOR)
                break
    if date:
        if authors:
            fp.write("<font color=\"%s\"> &middot; </font>" % STANDARD_DARK_COLOR)
        else:
            fp.write('<br>\n<small>')
        parsed_date = parse_date(date)
        if parsed_date:
            year, month, day = parsed_date
        else:
            year, month, day = 0, 0, 0
        fp.write("<i>");
        try:
            if day != 0:
                nextday = next_day((year, month, day))
                fp.write("<a href=\"/action/basic/repo_search?cutoff=0&query=date:%s\" " %
                         urllib.quote_plus("[%04d%02d%02d TO %04d%02d%02d]"
                                           % (year, month, day,
                                              nextday[0], nextday[1], nextday[2])) +
                         'class=sublink title="%s">%d</a> ' %
                         (htmlescape("Other documents written on %s" % format_date(date), true), day))
            if month != 0:
                fp.write("<a href=\"/action/basic/repo_search?cutoff=0&query=date:%s\" " %
                         urllib.quote_plus("[%04d%02d00 TO %04d%02d00]"
                                           % (year, month,
                                              ((month == 12) and (year + 1)) or year,
                                              ((month < 12) and (month + 1)) or 1)) +
                         'class=sublink title="%s">%s</a> ' %
                         (htmlescape("Other documents written in %s, %04d" % (MONTHNAMES_SHORT[month-1], year)),
                          MONTHNAMES_SHORT[month-1]))
            if year != 0:
                fp.write("<a href=\"/action/basic/repo_search?cutoff=0&query=date:%s\" " %
                         urllib.quote_plus("[%04d0000 TO %04d0000]" % (year, year + 1)) +
                         'class=sublink title="Other documents written in %04d">%04d</a>' % (year, year))
        except ValueError, x:
            note("%s on year, month, day is %s, %s, %s", x, year, month, day)
        fp.write("</i>")
    if not short_display:
        if date or authors:
            fp.write("<font color=\"%s\"> &middot; </font>" % STANDARD_TOOLS_COLOR)
        else:
            fp.write('<br>\n<small>')
        fp.write("<a href=\"/action/basic/doc_meta?doc_id=%s\" " % doc.id +
                 "class=idlink title=\"%s\">%s</a>" %
                 (htmlescape("Edit metadata for \"%s\"" % line, true), doc.id))
    categories = doc.get_category_strings()
    if categories and not short_display:
        fp.write('<font color="%s"> &middot; (' % STANDARD_DARK_COLOR)
        notfirst = false
        for category in categories:
            if notfirst: fp.write(', ')
            fp.write("<a href=\"/action/basic/repo_search?query=categories:%%22%s%%22\" " %
                     urllib.quote_plus(category.encode("ASCII", "xmlcharrefreplace")) +
                     'style="color: %s" title="%s">%s</a>' % (STANDARD_DARK_COLOR,
                                                              htmlescape("All documents in category '%s'" % category, true),
                                                              htmlescape(category)))
            notfirst = true
        fp.write(')</font>\n')

    if date or authors or (not short_display):
        fp.write("</small>")
    if not short_display:
        fp.write("</li>\n")

def repo_show_titles (repo, format, response, form_values, coll, docs, name, title, scores):

    # create something to write to
    fp = response.open()

    fp.write("<head><title>%s</title>\n" % htmlescape(title))
    refresh_period = int(repo.get_param('overview-refresh-period', 0))
    if refresh_period:
        fp.write('<meta http-equiv="Refresh" content="%d">\n' % refresh_period)
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link REL="SHORTCUT ICON" HREF="/favicon.ico">\n')
    fp.write('<link REL="ICON" type="image/ico" HREF="/favicon.ico">\n')
    __issue_javascript_head_boilerplate(fp)
    __issue_title_styles(fp)
    fp.write('</head>\n<body bgcolor="%s" onload="javascript:pageLoad();">\n' % STANDARD_BACKGROUND_COLOR)
    __issue_menu_definition(fp)

    note(3, "repo_show_titles:  coll is %s, name is \"%s\"", (isinstance(coll, Collection ) and coll.id) or "(null)", name)

    output_tools_block (repo, fp, htmlescape(title), format, coll, name)

    output_query_stats (repo, fp, coll, docs)

    if docs:
        fp.write('<ul>\n')
        for doc in docs:
            show_title (fp, doc, scores, _is_sensible_browser(response.user_agent), coll)
        fp.write('</ul>\n')
    else:
        fp.write("No documents in " + ((isinstance(coll, Collection) and "collection") or "repository") + ".\n")
    output_footer(repo, fp, coll, response.logged_in)
    fp.write("</body>\n")
    fp.close()

def _figure_format (repo, form):

    global LISTING_FORMAT
    if LISTING_FORMAT == None:
        LISTING_FORMAT = repo.get_param("default-listing-format", "Thumbnails MRU")
    format = (form and form.get('format')) or LISTING_FORMAT
    if format == 'Thumbnails':
        format = 'Thumbnails MRU'
    if LISTING_FORMAT != format:
        LISTING_FORMAT = format
    return format

def _repo_show (repo, response, form):

    # return an HTML view of the documents in the collection

    global TEMPORARY_COLLECTIONS, LISTING_FORMAT

    note(3, "user_agent is %s", response.user_agent)
    note(3, "sensible_browser is %s", _is_sensible_browser(response.user_agent))

    coll_id = form and form.get('coll')
    coll_name = form and form.get('collname')
    if coll_name and coll_name == "(edit)":
        response.redirect('/action/basic/repo_colls')
    coll = None
    scores = None

    format = _figure_format(repo, form)

    if coll_id:
        named = repo.get_collection(coll_id, true)
        coll = named or TEMPORARY_COLLECTIONS.get(coll_id)
        docs = collections_docs(repo, coll_id)
        if isinstance(coll, QueryCollection):
            scores = coll.xscores
        name = str(coll_id)
        if named:
            typ = "Collection"
        else:
            typ = "Search"
    elif coll_name:
        coll = repo.get_collection(coll_name);
        if isinstance(coll, Collection):
            docs = collections_docs(repo, coll.name())
            if isinstance(coll, QueryCollection):
                scores = coll.xscores
            name = coll_name
            typ = "Collection"

    # note("coll is %s, re.match is %s", coll, (coll and re.match(r'\+categories:"[^"]+"', coll.query)) or "")

    defcount = repo.get_param('default-listing-count')
    if defcount and not defcount == "all":
        defcount = int(defcount)
    elif defcount is None:
        defcount = 50

    if not isinstance(coll, Collection):
        coll = None
        docsorder = (form and form.get("listorder")) or repo.get_param("default-listing-order")
        if docsorder == "lastadded":
            docs = [x for x in repo.generate_docs(count=(isinstance(defcount, int) and defcount or 0))]
        elif docsorder == "lastused":
            docs = repo.history()
        else:
            docs = repo.history()
        name = repo.name()
        typ = "Repository"

    elif isinstance(coll, QueryCollection) and re.match(r'\+categories:"[^"]+"', coll.query):
        selected_category_name = re.match(r'\+categories:"([^"]*)"', coll.query).group(1)
        # note("category name is %s", selected_category_name)
        typ = "%s, category" % repo.name()
        name = selected_category_name

    if form and form.has_key('name'):
        name = form['name']

    if typ == "Repository":
        title = name
    else:
        title = "%s '%s'" % (typ, name)

    count = (not form and defcount and ((defcount == "all") and len(docs) or defcount)
             or (form.get('count') == None and isinstance(coll, Collection) and len(docs))
             or (form.get('count') == None and ((defcount == "all") and len(docs) or defcount))
             or (form.get('count') == 'all' and len(docs))
             or (form.get('count') and int(form.get('count'))))
    note("defcount is %s, count is %s, form.get('count') is %s", defcount, count, repr(form.get('count')))
    docs = docs[:min(count,len(docs))]

    note(3, "repo_show:  coll is %s, name is \"%s\", title is \"%s\"",
         (isinstance(coll, Collection) and coll.id) or "(none)", name, title)

    if (format.endswith(" DP") or format.endswith(" DA")):
        repo_show_timescale(repo, format, response, form, coll, docs, name, title, scores)
    elif format.startswith('Abstract'):
        repo_show_abstracts(repo, format, response, form, coll, docs, name, title, scores)
    elif format.startswith('Thumbnails') or format.startswith('Icon'):
        repo_show_thumbnails(repo, format, response, form, coll, docs, name, title, scores)
    elif format.startswith('Title'):
        repo_show_titles(repo, format, response, form, coll, docs, name, title, scores)
    else:
        raise Error("Unrecognized listing format '%s'" % format)

def _repo_show_categories (repo, response, form):

    # return an HTML view of the documents in the specified category

    global TEMPORARY_COLLECTIONS

    cname = form.get('category_name')
    if not cname:
        response.error(HTTPCodes.BAD_REQUEST, 'Badly formed call to repo_show_category:  no category_name parameter')

    if cname == '(Categorize)' or cname == "(edit)":
        params = {}
        if form.has_key('coll'):
            params['coll'] = form['coll']
        return _repo_categorize(repo, response, params)

    if cname == '(any)':
        return _repo_show(repo, response, {})

    if cname == '(none)':
        cquery = '_(none)_'
    else:
        cquery = cname

    coll = QueryCollection(repo, None, '+categories:"%s"' % cquery)
    TEMPORARY_COLLECTIONS[coll.id] = coll
    
    title = "%s, category '%s'" % (repo.name(), cname)
    
    docs = coll.docs()
    docsorder = (form and form.get("listorder")) or repo.get_param("default-listing-order")
    if docsorder == "lastadded":
        docs = repo.sort_doclist_by_adddate(docs)
    elif docsorder == "lastused":
        docs = repo.sort_doclist_by_mru(docs)
    elif docsorder == "pubdate":
        docs = repo.sort_doclist_by_pubdate(docs)
    else:
        docs = repo.sort_doclist_by_adddate(docs)

    scores = None

    format = _figure_format(repo, form)

    if (format.endswith(" DP") or format.endswith(" DA")):
        repo_show_timescale(repo, format, response, form, coll, docs, cname, title, scores)
    elif format.startswith('Abstract'):
        repo_show_abstracts(repo, format, response, form, coll, docs, cname, title, scores)
    elif format.startswith('Thumbnails') or format.startswith('Icon'):
        repo_show_thumbnails(repo, format, response, form, coll, docs, cname, title, scores)
    elif format.startswith('Title'):
        repo_show_titles(repo, format, response, form, coll, docs, cname, title, scores)
    else:
        raise Error("Unrecognized listing format '%s'" % format)


############################################################
###
###  "login" -- login to the repo
###
############################################################

def _login (repo, response, params):
    response.redirect("/login")

############################################################
###
###  "repo_userbutton" -- handle user button push
###
############################################################

__BUTTON_ADDITION_ENABLED = true

# basic data structure is
#  (BUTTON-KEY, (LABEL, FN, SCOPE, WEB-PAGE-TARGET-FRAME, URL, DOC-SELECTION-CRITERIA))

def get_buttons_sorted(scope):

    _initialize()

    def _caseless_button_sort(b1, b2):
        return 

    buttons = [x for x in list(USER_BUTTONS.items()) if (x[1][2] == scope)]
    if scope == FN_REPOSITORY_SCOPE:
        buttons = [x for x in buttons if ((x[1][5] is None) or (x[1][5]()))]
    # note(3, "raw buttons are %s, filtered(%s) => %s", USER_BUTTONS, scope, buttons)
    if len(buttons) > 0:
        buttons.sort(lambda b1, b2: cmp(b1[1][0].lower(), b2[1][0].lower()))
    return buttons

def set_button_addition_allowed(mode):
    global __BUTTON_ADDITION_ENABLED
    __BUTTON_ADDITION_ENABLED = mode

def _repo_userbutton(repo, response, params):
    global USER_BUTTONS

    key = params.get('uplib_userbutton_key')
    if not key:
        response.error(HTTPCodes.BAD_REQUEST, "No 'key' parameter specified.")

    button = USER_BUTTONS.get(key)
    if button:
        button[1](repo, response, params)
    else:
        response.error(HTTPCodes.BAD_REQUEST, "No user function matching key '%s'." % key)

def add_user_button (label, fn, target=None, url=None, criteria=None):
    global USER_BUTTONS, USER_BUTTONS_KEYVAL

    if not __BUTTON_ADDITION_ENABLED:
        return

    for b in USER_BUTTONS:
        if (USER_BUTTONS[b][0] == label) and (USER_BUTTONS[b][2] == FN_REPOSITORY_SCOPE):
            note(3, "Not adding user button '%s' because it's overridden by %s",
                 label, USER_BUTTONS[b][1])
            return

    if type(label) != types.StringType:
        raise Error("Invalid type for user-button label (%s)" % (label))
    if type(fn) != types.FunctionType:
        raise Error("Invalid type for user-button function \"%s\" (%s)" % (label, fn))
    USER_BUTTONS_KEYVAL = USER_BUTTONS_KEYVAL + 1
    key = 'buttonkey' + str(USER_BUTTONS_KEYVAL)
    USER_BUTTONS[key] = (label, fn, FN_REPOSITORY_SCOPE, target, url, criteria)

def add_document_function (label, fn, target=None, url=None, criteria=None):
    global USER_BUTTONS, USER_BUTTONS_KEYVAL

    for b in USER_BUTTONS:
        if (USER_BUTTONS[b][0] == label) and (USER_BUTTONS[b][2] == FN_DOCUMENT_SCOPE):
            note(3, "Not adding document function '%s' because it's overridden by %s",
                 label, USER_BUTTONS[b][1])
            return

    if type(label) != types.StringType:
        raise Error("Invalid type for document-function label (%s)" % (label))
    if type(fn) != types.FunctionType:
        raise Error("Invalid type for document-function function \"%s\" (%s)" % (label, fn))
    USER_BUTTONS_KEYVAL = USER_BUTTONS_KEYVAL + 1
    key = 'buttonkey' + str(USER_BUTTONS_KEYVAL)
    USER_BUTTONS[key] = (label, fn, FN_DOCUMENT_SCOPE, target, url, criteria)

def add_group_operation (label, fn, target=None, url=None, criteria=None):
    """
    Add a function that operates on a group of documents.

    :param: label The name for the operation
    :type: string
    :param: fn The function to be invoked
    :type: function that takes the standard three arguments repo, response, params.  It should
    require that the params include either one or more "doc_id" parameters, or a "coll" parameter specifying
    a collection ID, in which case the the docs in the collection will be used as the documents to compare.
    If both "doc_id" and "coll" parameters are provided, the "doc_id" parameter takes preference.
    :param: target The page target in which to display the results of the operation.  Optional.
    :type: a standard page target string, such as "_top" (to replace the current pages contents with the results), or "_blank" (to open a new window to show the results in).
    :param: url The URL form of the operation command.  Optional.
    :type: partial or full URL string
    :param: criteria a function to call on the set of documents or collection, which returns a boolean value.  If specified, it's invoked to see if this collection of documens can be operated on with this function.
    """    

    global USER_BUTTONS, USER_BUTTONS_KEYVAL

    if not __BUTTON_ADDITION_ENABLED:
        return

    for b in USER_BUTTONS:
        if (USER_BUTTONS[b][0] == label) and (USER_BUTTONS[b][2] == FN_COLLECTION_SCOPE):
            note(3, "Not adding group operation '%s' because it's overridden by %s",
                 label, USER_BUTTONS[b][1])
            return

    if type(label) != types.StringType:
        raise Error("Invalid type for group-operation label (%s)" % (label))
    if type(fn) != types.FunctionType:
        raise Error("Invalid type for group-operation function \"%s\" (%s)" % (label, fn))
    USER_BUTTONS_KEYVAL = USER_BUTTONS_KEYVAL + 1
    key = 'buttonkey' + str(USER_BUTTONS_KEYVAL)
    USER_BUTTONS[key] = (label, fn, FN_COLLECTION_SCOPE, target, url, criteria)


############################################################
###
###  "search" (search_repository)
###
############################################################

def _repo_search (repo, response, form_values):

    global TEMPORARY_COLLECTIONS

    try:
        query = form_values.get('query')
        if not query:
            response.reply("No query specified.")
            return

        cutoff = form_values.get('cutoff')
        if cutoff is None:
            cutoff = DEFAULT_QUERY_CUTOFF;
        else:
            cutoff = float(cutoff);
        cutoff = cutoff/100.0;

        narrow = form_values.get("narrow")
        if narrow:
            query = "+( " + query + ") +( " + narrow + " )"

        widen = form_values.get("widen")
        if widen:
            query = "( " + query + " ) OR ( " + widen + " )"

        format = form_values.get("format") or SEARCH_RESULTS_FORMAT

        note(4, "repo_search:  query is '%s', format is '%s', cutoff is %s", query, format, cutoff)

        coll = PrestoCollection(repo, None, query, None, None, cutoff)
        TEMPORARY_COLLECTIONS[coll.id] = coll

        name = query
        title = 'Search \'%s\'' % name
        if len(title) > 40:
            title = title[:40] + "..."

        scores = coll.scores()
        scores.sort(lambda x, y: cmp(y[1], x[1]))       # largest first
        docs = []
        for doc_id, score in scores:
            doc = repo.get_document(doc_id)
            note(4, "  %10f: %s", score, doc)
            if score < cutoff:
                break
            docs.append(doc)
        # we need scores as a dict to proceed
        scores = dict(scores)

        if (format.endswith(' DP') or format.endswith(' DA')):
            repo_show_timescale(repo, format, response, None, coll, docs, name, title, scores)
        elif format.startswith('Icon') or format.startswith('Thumbnails'):
            repo_show_thumbnails(repo, format, response, None, coll, docs, name, title, scores)
        elif format.startswith('Title'):
            repo_show_titles(repo, format, response, None, coll, docs, name, title, scores)
        else:
            repo_show_abstracts(repo, format, response, None, coll, docs, name, title, scores)

    except Error, x:
        fp = response.open("text/plain")
        fp.write('The application signalled the following error:\n')
        fp.write(str(x) + '\n')
        fp.close()

    except:
        fp = response.open("text/plain")
        fp.write('The application signalled the following error:\n')
        traceback.print_exc(None, fp)
        fp.close()

############################################################
###
###  "doc_search" (Search within a document)
###
############################################################

def _doc_search (repo, response, form_values):

    global TEMPORARY_COLLECTIONS

    try:
        query = form_values.get('query')
        if not query:
            response.error(HTTPCodes.BAD_REQUEST, "No query specified.")
            return

        doc_id = form_values.get('doc_id')
        if not doc_id:
            response.error(HTTPCodes.BAD_REQUEST, "No document ID specified.")
            return
        if not repo.valid_doc_id(doc_id):
            response.error(HTTPCodes.NOT_FOUND, "No document with ID %s in repository." % doc_id)
            return

        cutoff = form_values.get('cutoff')
        if cutoff is None:
            cutoff = DEFAULT_PAGE_QUERY_CUTOFF;
        else:
            cutoff = float(cutoff);
        cutoff = cutoff/100.0;

        doc = repo.get_document(doc_id)
        hits = doc.do_page_search(query)

        # return an HTML view of the documents in the collection

        title = doc.get_metadata('title') or doc.get_metadata('summary') or doc.id
        fp = response.open()
        fp.write("<head><title>%s</title>\n" % htmlescape(title))
        fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
        fp.write('<link REL="SHORTCUT ICON" HREF="/favicon.ico">\n')
        fp.write('<link REL="ICON" type="image/ico" HREF="/favicon.ico">\n')
        __issue_javascript_head_boilerplate(fp)
        __issue_title_styles(fp)
        fp.write('</head><body bgcolor="%s" onload="javascript:pageLoad();">\n' % STANDARD_BACKGROUND_COLOR)
        __issue_menu_definition(fp)

        output_tools_block (repo, fp, htmlescape(title), 'Abstract MRU', None, title)

        pages = {}
        for hit in hits:
            pages[hit[1]] = hit[0]
        note(4, "pages are %s", pages)
        show_abstract(repo, doc, fp, _is_sensible_browser(response.user_agent), None, pages, query, len(pages))
        output_footer(repo, fp, None, response.logged_in)
        fp.write("</body>\n")
        fp.close()

    except Error, x:
        fp = response.open("text/plain")
        fp.write('The application signalled the following error:\n')
        fp.write(str(x) + '\n')
        fp.close()

    except:
        fp = response.open("text/plain")
        fp.write('The application signalled the following error:\n')
        traceback.print_exc(None, fp)
        fp.close()

############################################################
###
###  show_metadata_form
###
############################################################

def show_metadata_form (repo, response, fields, error_message, camefrom=None):

    fp = response.open()

    # send back a form to add a report.  Use the fields specified, if
    # 'fields' has any data in it.

    if fields and fields.has_key("doc_id"):
        doc_id = fields['doc_id']
        if not repo.valid_doc_id(doc_id):
            response.error(HTTPCodes.BAD_REQUEST, "Invalid doc_id specified.")
            return

        doc = repo.get_document(doc_id)
        pagename = fields.get('name') or fields.get('title') or doc_id
        __beginpage(fp, pagename)

        # output a script to use with categories
        fp.write('<script type="text/javascript" language="javascript">\n'
                 'function addtag(tagname, text_field_id) {\n'
                 '  tf = $(text_field_id);\n'
                 '  if (tf.value.length == 0) {\n'
                 '    tf.value = tagname;\n'
                 '  } else {\n'
                 '    tf.value = tf.value + ", " + tagname;\n'
                 '  }\n'
                 '}\n'
                 '</script>\n')

        fp.write('<BODY bgcolor="%s">' % STANDARD_BACKGROUND_COLOR)

        if error_message:
            fp.write('<blockquote><font fgcolor="red"><pre>%s</pre></font></blockquote>\n' % htmlescape(error_message))

        fp.write('<table border=0 width=100%%><tr width=100%%><td><center>')
        title = htmlescape(_get_thumbnail_tooltip(doc), true)
        __output_document_icon(doc_id, title, fp, _is_sensible_browser(response.user_agent))
        fp.write('<br><small>'
                 '<a href="%s" target="_blank">(OPEN)</a><br>' % _doc_show_URL(doc_id) +
                 '<a href="/docs/%s/metadata.txt" type="text/plain" target="_blank">(RAW METADATA)</a>' % doc_id +
                 '</small></center>')
        fp.write('</td><td>&nbsp;</td>')
        fp.write('<td valign=top><i>Update metadata for</i><br><h3>"%s"</h3>' % pagename)
        summary = htmlescape(fields.get('summary', ''))
        if fields.has_key('abstract'):
            summary = "<i>" + htmlescape(fields.get('abstract', '')) + '</i>'
        fp.write('<p><object width=100%% type="text/plain" data="/docs/%s/contents.txt">%s</object>' % (doc_id, summary))
        #fp.write('</td><td><a href="/action/basic/repo_delete?doc_id=%s" target="_top"><img src="/html/images/delete.gif"></a>')
        fp.write('</td></tr></table><hr><P>\n')
    else:
        doc_id = None
        __beginpage(fp, "Add a New Document")
	fp.write('<BODY BGCOLOR="%s">' % STANDARD_BACKGROUND_COLOR)

        if error_message:
            fp.write('<blockquote><font fgcolor="red"><pre>%s</pre></font></blockquote>\n' % htmlescape(error_message))

	fp.write('<H3><center>Add a New Document</center></H3><P>\n')
        fp.write('<center>Please separate author names with "and", as in "Pat Smith '
                 'and D. H. Lawrence and ...".<P>\n')

    if doc_id:
        fp.write('<FORM ACTION="/action/basic/doc_update" method=POST enctype="multipart/form-data" accept-charset="%s">\n' % INTERACTION_CHARSET)
        fp.write('<input type=hidden name="doc_id" value="%s">\n' % htmlescape(doc_id, true))
    else:
        #fp.write('<FORM ACTION="/action/basic/repo_add" method=POST enctype="multipart/form-data">\n')
        fp.write('<FORM ACTION="/action/basic/repo_add" method=POST>\n')

    fp.write('<table width="100%">')

    if doc_id:

        date = re.sub(" 0|^0", " ",
                      time.strftime("%d %b %Y, %I:%M %p",
                                    time.localtime(id_to_time(doc_id))))
        fp.write('<tr><td>Doc ID:</td><td><span align="left">%s</span>' % htmlescape(doc_id) +
                 '&nbsp;' * 10 +
                 '<span align="right"><small>(added %s)</small></span></td><tr>\n' % htmlescape(date))

    else:

        # file to upload
        fp.write('<tr bgcolor="#FFAAAA" border=5 bdcolor="#FF0000"><td>File:</td>'
                 '<td><INPUT TYPE=FILE SIZE=70 NAME=newfile VALUE="File to upload"></td></tr>')

        # file type
        fp.write('<tr bgcolor="#FFAAAA" border=5 bdcolor="#FF0000"><td>File type:</td>'
                 '<td><SELECT NAME=filetype>')

        note("fields are %s", fields)
        selected_type = fields.get('filetype')
        for type in repo.content_types():
            if selected_type == type:
                fp.write('<OPTION SELECTED>%s</OPTION>' % type)
            else:
                fp.write('<OPTION>%s</OPTION>' % type)
        fp.write('</SELECT></td></tr>\n')

    # title
    fp.write('<tr><td>Title:</td>'
             '<td><input TYPE=text NAME=title value="%s" size=80></td></tr>\n' % htmlescape(fields.get('title', ''), True))

    # authors
    fp.write('<tr><td>Authors:<br><small><i>"and"-separated</i></small></td>'
             '<td><INPUT TYPE=TEXT NAME=authors VALUE="%s" size=80></td></tr>\n' % htmlescape(fields.get('authors', ''), True))

    # source
    fp.write('<tr><td>Source:</td>'
             '<td><INPUT TYPE=TEXT NAME=source VALUE="%s" size=80></td></tr>\n' % htmlescape(fields.get('source', ''), True))

    # date
    fp.write('<tr><td>Date:<br><small><i>mm/dd/yy</i></small></td>'
             '<td><INPUT TYPE=TEXT NAME=date VALUE="%s"></td></tr>\n' % htmlescape(fields.get('date', ''), True))

    # keywords
    fp.write('<tr><td>Keywords:<br><small><i>comma-separated</i></small></td>'
             '<td><INPUT TYPE=TEXT NAME=keywords VALUE="%s" size=80></td></tr>\n' % htmlescape(fields.get('keywords', ''), True))

    # categories
    #   we do this import here because it's circular
    from uplib.categories import find_likely_tags
    doctags = [x.lower() for x in doc.get_category_strings()]
    tags = find_likely_tags(doc, count=20-len(doctags))
    i = 0
    while tags and (i < len(tags)):
        if tags[i][0] in doctags:
            del tags[i]
        else:
            i += 1
    fp.write('<tr><td>Categories:<br><small><i>comma-separated</i></small>'
		     '</td><td><INPUT TYPE=TEXT id="tfcategories" NAME=categories VALUE="%s" size=40>' % htmlescape(fields.get('categories', ''), True))
    if tags and (len(tags) > 1):
        fp.write('&nbsp;&nbsp;&nbsp;<SELECT name="likelycategories" '
                 'onchange="javascript:addtag(this.value, \'tfcategories\');">')
        fp.write('<OPTION value="*">(Likely categories)</OPTION>')
        for name, stats in tags[:min(12, len(tags))]:
            fp.write('<OPTION value="' + htmlescape(name, True) + '">%s (%.3f)</OPTION>' % (htmlescape(name), stats[2]))
        fp.write('</SELECT>')
    action = "/action/basic/doc_categorize?doc_id=%s" % doc_id
    fp.write('&nbsp;&nbsp;&nbsp;<input type=button value="Categorize" onclick="javascript:window.location=\'%s\'">' % action)
    fp.write('</td></tr>\n')

    # reading status
    fp.write('''<tr><td>Personal Ratings:</td>''')
    fp.write('''<td>''')
    fp.write('''<small><i>How much you've read:</i></small> <SELECT name="readamount">''')
    current_amount_str = fields.get('readamount', '')
    if current_amount_str:
        current_amount = string.atoi(current_amount_str)
        thisPair = READING_AMOUNTS[current_amount]
        fp.write('<OPTION value="' + thisPair[1] + '">' + thisPair[0] + '</OPTION>')
    for pair in READING_AMOUNTS:
        fp.write('<OPTION value="' + pair[1] + '">' + pair[0] + '</OPTION>')
    fp.write('</SELECT>')
    
    # personal rating
    fp.write('''<small><i>, and your rating:</i></small> <SELECT name="rating">''')
    current_rating_str = fields.get('rating', '')
    if current_rating_str:
        current_rating = string.atoi(current_rating_str)
        thisPair = KNOWN_RATINGS[current_rating]
        fp.write('<OPTION value="' + thisPair[1] + '">' + thisPair[0] + '</OPTION>')
    for pair in KNOWN_RATINGS:
        fp.write('<OPTION value="' + pair[1] + '">' + pair[0] + '</OPTION>')
    fp.write('</SELECT>')
    fp.write('</td></tr>\n')

    # abstract
    fp.write('<tr><td>Abstract:<br><small><i>or Description</i></small></td><td><TEXTAREA NAME=abstract cols=80 rows=5>%s</TEXTAREA></td></tr>\n'
		     % htmlescape(fields.get('abstract', ''), True))

    # publication citation
    fp.write('<tr><td>Publication reference:<br><small><i>if applicable</i></small></td>'
                     '<td><TEXTAREA NAME=citation cols=80 rows=5>%s</TEXTAREA></td></tr>\n'
		     % htmlescape(fields.get('citation', ''), True))

    # comment
    fp.write('<tr><td>Comments:</td>'
             '<td><TEXTAREA NAME=comment cols=80 rows=5>%s</TEXTAREA></td></tr>\n' % htmlescape(fields.get('comment', ''), True))

    # DPI
    dpi = fields.get('images-dpi', '') or fields.get('tiff-dpi', '')
    fp.write('<tr><td>DPI:</td>'
             '<td><INPUT TYPE=TEXT NAME=images-dpi VALUE="%s" size=5>\n' % dpi)

    # first-page-number
    numbers = fields.get('page-numbers') or fields.get('first-page-number', '')
    fp.write('<span width=30px>&nbsp;</span>'
             'Page numbers: <INPUT TYPE=TEXT NAME=page-numbers VALUE="%s" size=20></td></tr>\n' % htmlescape(numbers, True))

    # label
    legend = fields.get('document-icon-legend', '')
    fp.write('<tr><td>Icon label:</td>'
             '<td><INPUT TYPE=TEXT NAME="document-icon-legend" VALUE="%s" size=30></td></tr>\n' % htmlescape(legend, True))

    # submit button
    if fields:
	fp.write('<tr><td colspan=2><center><table><tr>')
        fp.write('<td><INPUT TYPE=SUBMIT NAME="update" Value="Submit Changes" style="padding: 10px"></td>')
        fp.write('<td><INPUT TYPE=SUBMIT NAME="share" Value="Share Metadata" style="padding: 10px"></td>')
        fp.write('<td><INPUT TYPE=SUBMIT NAME="lookup" Value="Find Metadata" style="padding: 10px"></td>')
        fp.write('<td><INPUT TYPE=SUBMIT NAME="recache" Value="Reload Metadata" style="padding: 10px"></td>')
        fp.write('<td><INPUT TYPE=SUBMIT NAME="delete" Value="Delete Document" style="{background-color:red; color:white; padding: 10px}"></td>')
        fp.write('</tr><tr><td colspan=5><CENTER><INPUT TYPE=SUBMIT NAME="raw" Value="Show Raw Metadata"></CENTER></td>')
        fp.write('</tr></table></td></tr>')
    else:
	fp.write('<tr><td colspan=2 align=center><INPUT TYPE=SUBMIT NAME="submit" Value="Submit Document"  style="padding: 10px"></td></tr>')

    fp.write('</table>')
    if camefrom:
        fp.write('<input type=hidden name="camefrom" value="%s">\n' % htmlescape(camefrom, True))
    fp.write('</FORM>')
    __endpage(fp);
    fp.close()

############################################################
###
###  ensure_categories_in_repo
###
############################################################

def ensure_categories_in_repo (repository, categories_value):
    cleaned_categories = (categories_value and split_categories_string(categories_value)) or []
    db_categories = repository.categories()
    for category in cleaned_categories:
        if not category in db_categories:
            repository.add_category(category)
    note("Calling ensure_categories_in_repo with [%s].", categories_value)

############################################################
###
###  process_metadata_submission_changes
###
############################################################

INTERACTION_CHARSET = None

def process_metadata_submission_changes (repository, doc_id, response, fields):

    global INTERACTION_CHARSET
    if not INTERACTION_CHARSET:
        conf = configurator.default_configurator()
        INTERACTION_CHARSET = conf.get('interaction-charset', 'UTF-8')

    def possibly_set (db, fields, valuename, unfold_lines, original_metadata):
        if fields.has_key(valuename):
            if unfold_lines:
                value = string.replace(string.replace(fields[valuename], '\n', ' '), '\r', ' ')
            else:
                value = fields[valuename]
            value = unicode(value, INTERACTION_CHARSET, "replace")
            db[valuename] = value.strip()
            if (valuename == "title") and (original_metadata.get("title") != value):
                db["title-is-original-filepath"] = ""
        elif original_metadata.has_key(valuename):
            db[valuename] = ""

    msgtag = ""
    try:

        # handle changes to document metadata, or even a new document
        if not doc_id:
            from uplib.externalAPI import upload_document
            upload_document (repository, response, fields)
            return

        msgtag = "updating document metadata"
        if not repository.valid_doc_id(doc_id):
            response.error(HTTPCodes.NOT_FOUND, "Invalid document ID")
            return

        if fields.has_key("delete"):
            note(3, "Deleting document %s", doc_id)
            _doc_delete (repository, response, fields)
            return

        if fields.has_key("recache"):
            note(3, "Re-caching information for document %s", doc_id)
            doc = repository.get_document(doc_id)
            doc.recache()
            response.redirect("/action/basic/doc_meta?doc_id=" + doc_id)
            return

        if fields.has_key("share"):
            note(3, "Sharing metadata for document %s", doc_id)
            doc = repository.get_document(doc_id)
            share_metadata(doc, true)
            response.redirect("/action/basic/doc_meta?doc_id=" + doc_id)
            return

        if fields.has_key("lookup"):
            note(3, "Finding shared metadata for document %s", doc_id)
            doc = repository.get_document(doc_id)
            find_shared_metadata(doc)
            response.redirect("/action/basic/doc_meta?doc_id=" + doc_id)
            return

        if fields.has_key("raw"):
            if not repository.valid_doc_id(doc_id):
                response.error(HTTPCodes.NOT_FOUND, "Invalid document id:  %s" % doc_id)
                return
            response.redirect("/docs/%s/metadata.txt" % doc_id)
            return

        camefrom = fields.get("camefrom")

        doc = repository.get_document(doc_id)
        original_metadata = doc.get_metadata()
        metadata = {}

        rerip = false
        changed_fields = set()

        if fields.has_key("page-numbers"):
            v = fields.get("page-numbers")
            if not v:
                metadata["first-page-number"] = ""
                metadata["page-numbers"] = ""
                if original_metadata.get("first-page-number") or original_metadata.get("page-numbers"):
                    rerip = "page numbers removed"
                    changed_fields.add("page-numbers")
            v = v.strip()
            if SIMPLE_PAGE_NUMBER.match(v):
                metadata["first-page-number"] = v
                dv = doc.get_metadata("first-page-number")
                if dv: dv = dv.strip()
                if v != dv:
                    rerip = "metadata element 'first-page-number' added"
                    changed_fields.add("first-page-number")
            elif PAGE_RANGE.match(v):
                m = PAGE_RANGE.match(v)
                metadata["page-numbers"] = v
                dv = doc.get_metadata("first-page-number")
                if dv: dv = dv.strip()
                if v != dv:
                    rerip = "metadata element 'page-numbers' added or changed"
                    changed_fields.add("page-numbers")
            elif PAGE_NUMBERS.match(v):
                metadata["page-numbers"] = v
                dv = doc.get_metadata("first-page-number")
                if dv: dv = dv.strip()
                if v != dv:
                    rerip = "metadata element 'page-numbers' added or changed"
                    changed_fields.add("page-numbers")
        else:
            metadata["first-page-number"] = ""
            metadata["page-numbers"] = ""
            if original_metadata.get("first-page-number") or original_metadata.get("page-numbers"):
                rerip = "metadata element 'page-numbers' or 'first-page-number' removed"
                changed_fields.add("page-numbers")
                changed_fields.add("first-page-number")

        odpi = original_metadata.get("images-dpi")
        if odpi: odpi = odpi.strip()
        ndpi = fields.get("images-dpi")
        if ndpi: ndpi = ndpi.strip()
        if ndpi and (ndpi != odpi):
            rerip = "document 'images-dpi' changed from %s to %s" % (odpi, ndpi)
            changed_fields.add("images-dpi")

        if fields.has_key("document-icon-legend"):
            if fields.get("document-icon-legend", '') != original_metadata.get("document-icon-legend", ''):
                rerip = "'document-icon-legend' changed from \"%s\" to \"%s\"" % (original_metadata.get("document-icon-legend", ""),
                                                                                  fields.get("document-icon-legend", ""))
                changed_fields.add("document-icon-legend")

        possibly_set(metadata, fields, "title", true, original_metadata)
        possibly_set(metadata, fields, "authors", true, original_metadata)
        possibly_set(metadata, fields, "source", false, original_metadata)
        possibly_set(metadata, fields, "date", false, original_metadata)
        possibly_set(metadata, fields, "keywords", true, original_metadata)
        possibly_set(metadata, fields, "categories", false, original_metadata)
        possibly_set(metadata, fields, "readamount", false, original_metadata)
        possibly_set(metadata, fields, "rating", false, original_metadata)
        possibly_set(metadata, fields, "abstract", false, original_metadata)
        possibly_set(metadata, fields, "citation", true, original_metadata)
        possibly_set(metadata, fields, "comment", true, original_metadata)
        possibly_set(metadata, fields, "images-dpi", false, original_metadata)
        possibly_set(metadata, fields, "document-icon-legend", false, original_metadata)
        doc.update_metadata(metadata, not rerip)
        
        # update the global list of categories
        categories_value = fields.has_key('categories') and fields['categories']
        ensure_categories_in_repo(repository, categories_value)
        repository.touch_doc(doc)

        if rerip:
            t = doc.rerip(changed_fields=changed_fields)
            fp = response.open()
            fp.write("<head><title>%s</title></head>\n" % (doc.get_metadata("title") or "Document %s" % doc.id))
            fp.write("<body bgcolor=\"%s\">\n" % STANDARD_BACKGROUND_COLOR)
            fp.write("<form action=\"%s\">\n" % (camefrom or "/"))
            fp.write("<input type=hidden name=\"doc_id\" value=\"%s\">\n" % doc_id)
            fp.write("Re-ripping document %s in new thread to incorporate changed metadata\n" % doc +
                     "because %s.\n" % rerip)
            fp.write("<p><hr><p><input type=submit name=\"junk\" value=\"Return\" style=\"padding: 10px\">\n");
            fp.write("</form></body>\n")
            fp.close()
        else:
            response.redirect(camefrom or "/action/basic/doc_meta?doc_id=" + doc_id)
        return

    except:

        if doc_id:
            errmsg = ''.join(traceback.format_exception(*sys.exc_info()))
            show_metadata_form(repository, response, fields, errmsg)
        else:
	    typ, ex, tb = sys.exc_info()
	    raise ex, None, tb
            
############################################################
###
###  find_shared_metadata
###
############################################################

def _calculate_folder_hash (folder):

    doc_path = None
    originals_dir = os.path.join(folder, "originals")
    if os.path.isdir(originals_dir):
        files = os.listdir(originals_dir)
        if len(files) == 1:
            fname, ext = os.path.splitext(files[0])
            if ext == '.pdf' or ext == '.PDF':
                doc_path = os.path.join(originals_dir, files[0])

    if not doc_path or not os.path.exists(doc_path):
        doc_path = os.path.join(doc.folder(), "document.tiff")
        if not os.path.exists(doc_path):
            prefix = os.path.join(folder, "page-images")
            if os.path.isdir(prefix):
                files = os.listdir(prefix)
                files.sort()
            else:
                return 0
        else:
            prefix = folder
            files = ("document.tiff", )
    else:
        files = (os.path.split(doc_path)[1], )
        prefix = os.path.split(doc_path)[0]

    s = hashlib.sha1()
    for filename in files:
        fp = open(os.path.join(prefix, filename), 'rb')
        data = fp.read()
        fp.close()
        s.update(data)
    key = s.hexdigest()
    return key

def find_folder_shared_metadata(folder, override=false):

    def _parse_metadata (d):
        import StringIO
        fp = StringIO.StringIO(d)
        dict = read_metadata(fp)
        fp.close()
        return dict

    conf = configurator.default_configurator()
    url = conf.get('metadata-sharing-url')
    if not url:
        return None
    host, port, path = parse_URL(url)

    preferred_submitters = conf.get('metadata-sharing-preferred-submitters') or ()
    if preferred_submitters:
        preferred_submitters = split_categories_string(preferred_submitters)

    key = _calculate_folder_hash(folder)

    status, status_msg, headers, msg = http_post_multipart(host, port, None, path, (('lookup', key),), ())
    if status == 200:
        matches = string.split(msg, '\n')
        best_match = None
        for match in matches:
            note("checking match %s", match)
            if not string.strip(match):
                continue
            key, subtime, submitter, file = string.split(match, ':')
            subtime = float(subtime)
            if not best_match:
                best_match = (subtime, submitter, file, match)
            elif subtime > best_match[0] and ((best_match[1] not in preferred_submitters) or
                                              (submitter in preferred_submitters)):
                best_match = (subtime, submitter, file, match)
        if best_match:
            status, status_msg, headers, msg = http_post_multipart(host, port, None, path, (('fetch', best_match[3]),), ())
            if status != 200:
                note("Fetch of shared metadata for match %s signalled %s -- %s.  Message was:\n%s\n",
                     best_match[3], status, status_msg, msg)
            else:
                metadata_path = os.path.join(folder, "metadata.txt")
                existing_metadata = read_metadata(metadata_path)
                new_metadata = _parse_metadata(msg)
                if override:
                    existing_metadata.update(new_metadata)
                    md = existing_metadata
                else:
                    new_metadata.update(existing_metadata)
                    md = new_metadata
                note(3, "updating metadata for %s to %s", folder, md)
                update_metadata(metadata_path, md)

    else:
        note("Lookup of shared metadata for %s signalled %s -- %s.  Message was:\n%s\n",
             folder, status, status_msg, msg)

def _calculate_doc_hash (doc):
    return _calculate_folder_hash(doc.folder())

def find_shared_metadata(doc, override=false):
    md = find_folder_shared_metadata(doc.folder(), override)
    doc.repo.touch_doc(doc)
    return md
    

############################################################
###
###  share_metadata
###
############################################################

def share_metadata(doc, force=false):

    conf = configurator.default_configurator()
    url = conf.get('metadata-sharing-url')
    if not url:
        return
    host, port, path = parse_URL(url)

    if not force:
        categories = conf.get('metadata-sharing-categories')
        if categories:
            categories = split_categories_string(categories)
            my_categories = split_categories_string(doc.get_metadata('categories') or '')
            note(3, "sharing categories are %s, my categories are %s", categories, my_categories)
            for category in categories:
                if category in my_categories:
                    force = true
                    break

    if not force:
        note(3, "not metadata-sharing document %s", doc.id)
        return

    properties = string.split(conf.get('metadata-sharing-properties') or
                              conf.get('metadata-sharing-default-properties'), ':')
    metadata = ""
    name = None
    for prop in properties:
        v = doc.get_metadata(prop)
        if v:
            metadata = metadata + prop + ': ' + v + '\n'
            if prop == 'title':
                name = v
    if metadata:
        key = _calculate_doc_hash(doc)
        parms = [ ('submit', key), ('data', metadata) ]
        files = []
        iconpath = os.path.join(doc.folder(), "thumbnails", "first.png")
        if os.path.exists(iconpath):
            files.append(('icon', iconpath))
        if name:
            parms.append(('name', name))
        submitter = conf.get("metadata-sharing-username")
        if submitter:
            parms.append(('submitter', submitter))
        status, status_msg, headers, msg = http_post_multipart(host, port, None, path, parms, files)
        if status != 200:
            note("Post of shared metadata to %s signalled %s -- %s.  Message was:\n%s\n",
                 url, status, status_msg, msg)
        else:
            note(3, "shared metadata for %s", doc.id)
    else:
        note(3, "no shareable metadata for %s", doc.id)

############################################################
###
###  repo_add_document
###
############################################################

def _repo_add_document (r, response, form):
    if form:
        process_metadata_submission_changes(r, None, response, form)
    else:
        show_metadata_form(r, response, {}, None)

############################################################
###
###  repo_delete_document
###
############################################################

def _repo_delete_document (r, response, form):
    if not form or not form.has_key("doc_id"):
	response.error(HTTPCodes.BAD_REQUEST, "No document ID specified.")
    else:
        doc_id = form["doc_id"]
        camefrom = form.get("camefrom")
        if not r.valid_doc_id(doc_id):
	    response.error(HTTPCodes.NOT_FOUND, "Document ID '%s' is not a valid document ID for this repository.\n" % doc_id)
            return
        others = form.get("marked")
        r.delete_document(doc_id)
        if others:
            note(3, "   documents associated with %s to delete are %s", doc_id, repr(others))
            if type(others) in types.StringTypes:
                others = (others,)
            for other in others:
                if r.valid_doc_id(other):
                    r.delete_document(other)
                else:
                    note(3, "   invalid document %s", other)
        # be careful not to redirect to another page using this document
        if (not camefrom) or (doc_id in camefrom):
            response.redirect("/")
        else:
            response.redirect(camefrom)


def _repo_multidelete (repo, response, form):
    doc_ids = form.get('doc_id')
    if not doc_ids:
        response.error(HTTPCodes.BAD_REQUEST, "No doc_id values specified in URL");
        return
    if type(doc_ids) in types.StringTypes:
        doc_ids = ( doc_ids, )
    fp = response.open()

    referer = response.request.get_header('referer')
    confirmed = form.get('confirmed')
    camefrom = form.get("camefrom")

    if confirmed == "yes":
        for id in doc_ids:
            if repo.valid_doc_id(id):
                repo.delete_document(id)
        response.redirect(camefrom or "/")
        return

    # not confirmed -- put up confirmer page

    __beginpage(fp, 'Deleting documents...')
    fp.write("<body bgcolor=\"%s\">\n" % STANDARD_BACKGROUND_COLOR)
    fp.write('<p><b>%s document%s selected for deletion...</b>' % (len(doc_ids), (len(doc_ids) != 1) and "s" or ""))
    for id in doc_ids:
        if repo.valid_doc_id(id):
            fp.write('<hr>\n')
            show_abstract(repo, repo.get_document(id), fp, _is_sensible_browser(response.user_agent))
            fp.write('Document %s will be deleted if checked: <input type=checkbox name="marked" value="%s" checked>\n' % (id, id))
        else:
            fp.write('<hr>Invalid doc id:  %s' % id)
    fp.write('<hr><p>Delete these documents?<br>'
             '<input type=button value="Yes, delete them"' +
             "onClick=\"{submitCollectionButton(\'/action/basic/repo_multidelete?camefrom=%s&confirmed=yes\', \'_self\', null, null)}\">" % (camefrom or referer or "/") +
             "<span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>"
             '<input type=button value="No, cancel deletion"'
             "onClick=\"{window.location = '%s'}\"></body>\n" % (camefrom or referer or "/"))
             

############################################################
###
###  repo_categorize
###
############################################################

def _repo_categorize (repo, response, form):

    # three states:
    #   1.  if form is blank, just send out the template.
    #   2.  if form has "categories", send out a list of documents.
    #   3.  if form has "specifiedcategories", process modifications.

    note("form is %s", form)
    note("form['coll'] is %s", form.get('coll'))

    if not form or (not (form.has_key('categories') or form.has_key('specifiedcategories'))):

        fp = response.open()
        categories = string.join(repo.categories(), ', ')
        fp.write('<head><title>Categorize \'%s\'</title></head><body bgcolor="%s">\n' %
                 (htmlescape(repo.name()), STANDARD_BACKGROUND_COLOR))
        fp.write('<form action="./repo_categorize" method=POST><center>\n')
        fp.write('Enter categories to work with below, comma-separated:<br>\n')
        fp.write('<P><input type=text size=80 value="%s" name="categories"><br>\n' % categories)
        if form.has_key('coll'):
            fp.write('<input type=hidden name="coll" value="%s">\n' % form['coll'])
        if form.has_key('name'):
            fp.write('<input type=hidden name="name" value="%s">\n' % form['name'])
        fp.write('<P><input type=submit value="Go"></center></form></body>')
        fp.close()
        return

    elif form.has_key('categories'):

        note(3, "categories are %s", str(form['categories']))
        fp = response.open()
        categories = split_categories_string(form['categories'])
        if not categories:
            fp.write("<body>No categories specified.</body>")
            fp.close()
            return

        coll_id = form and form.get('coll')
        if coll_id:
            named = repo.get_collection(coll_id, true)
            coll = named or TEMPORARY_COLLECTIONS.get(coll_id)
            docs = collections_docs(repo, coll_id)
            name = str(coll_id)
            if named:
                typ = "Collection"
            else:
                typ = "Search"
        else:
            coll = None
            docs = repo.generate_docs()
            name = repo.name()
            typ = "Repository"
        if form and form.has_key('name'):
            name = form['name']

        fp.write('<head><title>Categorize \'%s\'</title></head><body bgcolor="%s">\n' %
                 (htmlescape(typ + ' ' + name), STANDARD_BACKGROUND_COLOR))
        fp.write('<P><center><H3>Categories:  %s</h3></center><hr>\n<p>' % form.get('categories'))
        fp.write('<form action="./repo_categorize" method=POST enctype="multipart/form-data">\n')
        if coll_id:
            fp.write('<input type=hidden name="coll" value="%s">\n' % coll_id)
        fp.write('<input type=hidden name="specifiedcategories" value="%s">\n' % form.get('categories'))
        for doc in docs:
            dict = doc.get_metadata()
            doc_categories = split_categories_string(dict.get('categories'))
            date = re.sub(" 0|^0", " ",
                          time.strftime("%d %b %Y, %I:%M %p",
                                        time.localtime(id_to_time(doc.id))))
            name = doc.id
            if dict:
                if dict.has_key('name'):
                    name = htmlescape(dict.get('name'))
                elif dict.has_key('title'):
                    name = htmlescape(dict.get('title'))
            fp.write('<table border=0><tr><td>')
            fp.write('<center><a href="%s"' % _doc_show_URL(doc.id))
            fp.write('><img src="/docs/%s/thumbnails/first.png" border=1><br><small>%s</small></a></center></td><td>&nbsp;</td>' % (doc.id, date))
            fp.write('<td valign=top><h3>%s</h3>' % name)
            if dict.has_key('authors'):
                fp.write('<p><small><b>&nbsp;&nbsp;&nbsp;&nbsp;%s</b></small>\n'
                         % (re.sub(' and ', ', ', dict['authors'])))
            summary = ""
            if dict.has_key('abstract'):
                summary = "<i>" + htmlescape(dict.get('abstract', '')) + '</i>'
            elif dict.has_key('summary'):
                summary = htmlescape(dict.get('summary'))
            fp.write('<P>%s' % summary)
            fp.write('</td></tr></table><br>\n')
            fp.write('<table><tr>')
            for c in categories:
                fp.write('<td><input type=checkbox label="%s" name="%s" value="%s"%s> %s</td>\n'
                         % (c, doc.id, c, ((c in doc_categories) and " checked") or "", c))
            fp.write('</tr></td></table><hr>')
        fp.write('<p><center><input type=submit value="Submit" style="padding: 10px"></center></form></body>')
        fp.close()

    elif form.has_key('specifiedcategories'):

        repo_categories = repo.categories()
        fp = response.open()
        form_categories = split_categories_string(form.get('specifiedcategories'))
        coll_id = form.get('coll')
        if form_categories:
            del form['specifiedcategories']
        if coll_id:
            del form['coll']
        fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
        ids = []
        for id in form.keys():
            if repo.valid_doc_id(id):
                ids.append(id)
                new_categories = form[id]
                if type(new_categories) == type(''):
                    new_categories = [ new_categories, ]
                doc = repo.get_document(id)
                doc_categories = split_categories_string(doc.get_metadata('categories'))
                for c in form_categories:
                    if (c in doc_categories) and not (c in new_categories):
                        doc_categories.remove(c)
                    elif (c in new_categories) and not (c in doc_categories):
                        doc_categories.append(c)
                    if not (c in repo_categories) and (c in doc_categories):
                        repo.add_category(c)
                        repo_categories = repo.categories()
                new_metadata = { 'categories': string.join(doc_categories, ',') }
                doc.update_metadata(new_metadata, false)
                fp.write('<p>Updated categories of "%s" to <b>%s</b>.\n' % (doc.get_metadata('title') or id, string.join(doc_categories, ', ')))
        # re-index all the documents in one fell swoop
        from uplib.createIndexEntry import index_folders
        newthread = uthread.start_new_thread(index_folders, (repo.docs_folder(), ids, repo.index_path()))
        note(3, "reindexing %s in %s", ids, str(newthread))
        fp.write('<center><form method=GET action="/action/basic/repo_show">\n')
        if coll_id:
            fp.write('<input type=hidden name="coll" value="%s">\n' % coll_id)
        fp.write('<input type=submit value="Return to repository"></form>\n</center>\n')
        fp.write("</body>")
        fp.close()

    else:

        response.error(HTTPCodes.BAD_REQUEST, "Badly formatted request.")

############################################################
###
###  repo_password
###
############################################################

def _repo_password (r, response, form):

    if form and form.has_key('oldpassword'):

        # new password, store it
        if (r.change_password(form["oldpassword"], form["password1"])):
            # re-direct to root
	    response.redirect("/")
        else:
	    response.error(HTTPCodes.UNAUTHORIZED, "You are not authorized to perform this operation.")
	return
        
    else:

        # send password changing form
        fp = response.open()
        fp.write("<head><title>Changing password for '%s'</title>" % r.name())
        fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
        fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
        fp.write('<script type="text/javascript" language="javascript">\n'
                 'function verify_password_match(f) {\n'
                 '  if (f.password1.value != f.password2.value) {\n'
                 '    alert("The two new passwords are not the same!  Please re-type them.");\n'
                 '    f.password1.value = "";\n'
                 '    f.password2.value = "";\n'
                 '    return false;\n'
                 '  } else {\n'
                 '    return true;\n'
                 '  };\n'
                 '}\n'
                 '</script></head>')
        fp.write("<body><h1>Changing password for '%s'</h1>\n" % r.name())
        fp.write('<FORM name="passwords" onsubmit="return verify_password_match(this)" ACTION="/action/basic/repo_password" method=POST enctype="multipart/form-data">\n')
        fp.write(r'<table width=100%>')
        fp.write('<tr><td><p>Old Password: </td><td><input type=password size=60 name=oldpassword value=""></td></tr>\n')
        fp.write('<tr><td><p>New Password: </td><td><input type=password size=60 name=password1 value=""></td></tr>\n')
        fp.write('<tr><td>New Password (again): </td><td><input type=password size=60 name=password2 value=""></td></tr>\n')
        fp.write('<tr><td colspan=2 align=center><input type=submit value="Change the password"></td></tr>\n')
        fp.write('</table></form></body>')
        fp.close()
                 

############################################################
###
###  repo_changename
###
############################################################

def _repo_changename (r, response, form):

    if form and form.has_key('newname'):

        name = form['newname']
        if (name):
            r.set_name(unicode(name, "UTF-8", "replace"))
            # re-direct to root
            response.redirect("/")
        else:
	    response.error(HTTPCodes.BAD_REQUEST, "Null new name specified.")
            return
        
    else:

        # send password changing form
        fp = response.open()
        fp.write("<head><title>Changing name of '%s'</title>" % r.name())
        fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
        fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
        fp.write("<body><h1>Changing name of '%s'</h1>\n" % r.name())
        fp.write('<FORM ACTION="/action/basic/repo_changename" method=POST enctype="multipart/form-data" accept-charset="UTF-8">\n')
        fp.write(r'<table width=100% height=100%>')
        fp.write('<tr><td>New name: </td><td><input type=text size=60 name=newname value="%s"></td></tr>' % r.name())
        fp.write('</table></form></body>')
        fp.close()
                 

############################################################
###
###  repo_collections
###
############################################################

def _repo_collections (repo, response, form):

    fp = response.open()
    colls = repo.list_collections()
    title = "Collections in '%s'" % repo.name()

    # return an HTML view of the documents in the collection

    fp.write("<head><title>%s</title>\n" % htmlescape(title))
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
    fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
    __issue_javascript_head_boilerplate(fp)
    __issue_title_styles(fp)
    fp.write('</head>\n')
    fp.write('<body bgcolor="%s" onload="javascript:pageLoad();">\n' % STANDARD_BACKGROUND_COLOR)
    __issue_menu_definition(fp)

    output_tools_block (repo, fp, "Collections in '%s'" % htmlescape(repo.name()), "Thumbnails", None, None)

    fp.write('<p>')
    if colls:
        colls.sort(_sort_collections)
        fp.write("<table width=100%>")
        bgcolor = ("white", STANDARD_BACKGROUND_COLOR)
        bgcolor_index = 0
        for name, coll in colls:
            if isinstance(coll, QueryCollection):
                content = htmlescape(coll.query)
            else:
                content = "%d items" % len(coll)
            url = "/action/basic/repo_show?coll=%s&name=%s" % (urllib.quote_plus(coll.name().encode("ASCII", "xmlcharrefreplace")),
                                                               urllib.quote_plus(name.encode("ASCII", "xmlcharrefreplace")))
            fp.write('<tr valign=center bgcolor="%s"><td align=left><a href="%s">%s</a></td><td align=left><small>%s</small></td>'
                     % (bgcolor[bgcolor_index % 2], url, htmlescape(name), content))

            if isinstance(coll, QueryCollection):
                fp.write('<td valign=center width=10% align=right><form action="/action/basic/coll_editquery" method=get>')
                fp.write('<input type=hidden name="collname" value="%s">' % htmlescape(name, true))
                fp.write('<input type=hidden name="nexturl" value="%s">' % htmlescape(response.request_path, true))
                fp.write('<input type=submit value="Edit Query"></form></td>')
            else:
                fp.write('<td width=10% align=right>&nbsp;</td>')

            fp.write('<td width=10% align=right><form action="/action/basic/coll_rename" method=get>')
            fp.write('<input type=hidden name="oldname" value="%s">' % htmlescape(name, true))
            fp.write('<input type=hidden name="nexturl" value="%s">' % htmlescape(response.request_path, true))
            fp.write('<input type=submit value="Rename"></form></td>')

            fp.write('<td width=10% align=right><form action="/action/basic/coll_delete" method=get>')
            fp.write('<input type=hidden name="coll" value="%s">' % htmlescape(coll.name(), true))
            fp.write('<input type=hidden name="nexturl" value="%s">' % htmlescape(response.request_path, true))
            fp.write('<input type=submit value="Delete"></form></td>')

            fp.write('</tr>')
            bgcolor_index = bgcolor_index + 1
        fp.write("</table>")
    else:
        fp.write("No collections defined.\n")

    output_footer(repo, fp, None, response.logged_in)
    fp.close()

############################################################
###
###  _repo_addqcoll
###
############################################################

def _repo_addqcoll (repo, response, form):
    name = form and form.get('label')
    if name:
        coll = repo.get_collection(name)
        if isinstance(coll, Collection):
            response.error(HTTPCodes.BAD_REQUEST,
			   '<P>The repository already has '
			   '<a href="repo_show?coll=%s&name=%s">a collection named "%s"</a>.'
			   % (urllib.quote_plus(coll.name().encode("ASCII", "xmlcharrefreplace")),
                              urllib.quote_plus(name.encode("ASCII", "xmlcharrefreplace")), htmlescape(name)))
            return
    query = form and form.get('query')
    if query:
        coll = repo.add_query_collection(name, query)
        if name:
            location = "repo_show?coll=%s&name=%s" % (urllib.quote_plus(coll.name().encode("ASCII", "xmlcharrefreplace")),
                                                      urllib.quote_plus(name.encode("ASCII", "xmlcharrefreplace")))
        else:
            location = "repo_show?coll=%s" % urllib.quote_plus(coll.name().encode("ASCII", "xmlcharrefreplace"))
        response.redirect(location)
    else:
        response.error(HTTPCodes.BAD_REQUEST, '<p>No query specified for new collection.')


############################################################
###
###  _repo_user_actions
###
############################################################

def _repo_user_actions (repo, response, params):

    buttons = get_buttons_sorted(FN_REPOSITORY_SCOPE)
    fp = response.open("text/plain")
    for button in buttons:
        url = button[1][4]
        if url is None:
            url = "/action/basic/repo_userbutton?uplib_userbutton_key=%s" % button[0]
        fp.write("%s, %s, %s, %s\n" % (button[0], url, button[1][3], button[1][0]))
    fp.close()

############################################################
###
###  _repo_status_json
###
############################################################

def _repo_status_json (repo, response, params):
    
    try:

        ripper_names = [x.__class__.__name__ for x in repo.rippers()]
        rlen = str(len(ripper_names))
        h = repo.history()
        j = hashlib.sha1(string.join([doc.id for doc in h[:min(len(h), 5)]], ':')).hexdigest()
        pending = repo.pending_folder()
        fp = response.open("text/plain")
        docscount = 0
        if STATS_DOCS is not None:
            docscount = STATS_DOCS
        pagescount = 0
        if STATS_PAGES is not None:
            pagescount = STATS_PAGES
        fp.write('{ history : "%s",\n  docs : %s, pages : %s,\n  rippers: [' % (j, docscount, pagescount))
        for rippername in ripper_names:
            fp.write('"' + rippername + '", ')
        fp.write('],\n  pending : [')
        first = true
        for pending in repo.list_pending(true):
            if not first:
                fp.write(",")
            first = false
            rname = pending['ripper']
            if rname in ripper_names:
                ripper_index = ripper_names.index(rname)
            else:
                if pending['status'] == "ripping":
                    note("Bad status/ripper pair for document %s:  %s/%s", pending['id'], pending['status'], rname)
                ripper_index = 0
            if pending['status'] == "error":
                error = urllib.quote(pending.get("error").encode("ASCII", "xmlcharrefreplace"))
            else:
                error = 0
            fp.write('\n  { id : "%s",\n'
                     'title : "%s",\n    '
                     'authors : "%s",\n    '
                     'pagecount : %s,\n    '
                     'status : "%s",\n    '
                     'error : "%s",\n    '
                     'ripper : %s }'
                     % (pending['id'],
                        urllib.quote(pending['title'].encode("ASCII", "xmlcharrefreplace")),
                        urllib.quote(pending['authors'].encode("ASCII", "xmlcharrefreplace")),
                        pending['page_count'],
                        pending['status'],
                        error,
                        ripper_index))
        fp.write("]\n }\n")

    except:
        note(0, "_repo_status_json exception:\n%s\n", ''.join(traceback.format_exception(*sys.exc_info())))


############################################################
###
###  coll_delete
###
############################################################

def _coll_delete (repo, response, form):
    if form and form.has_key('coll'):
        if repo.delete_collection(form['coll']):
            nexturl = form.get('nexturl')
            if not nexturl:
                response.reply('<p>Collection deleted.')
            else:
		response.redirect(nexturl)
        else:
            response.error(HTTPCodes.NOT_FOUND, '<p>No such collection.')
    else:
	response.error(HTTPCodes.BAD_REQUEST, '<p>Bad URL; no collection specified.')

############################################################
###
###  coll_delete
###
############################################################

def _coll_rename (repo, response, form):

    if not form.has_key('oldname'):
	response.error(HTTPCodes.BAD_REQUEST, "<P>No collection specified.")
        return

    oldname = form.get('oldname')

    c = repo.get_collection(oldname)
    if not isinstance(c, Collection):
        response.error(HTTPCodes.NOT_FOUND, "<P>No such collection '%s'." % htmlescape(oldname))
        return

    newname = form.get('newname')

    if newname and oldname:
        # OK, this is the re-submitted form, so change the name
        repo.rename_collection(oldname, newname)
        nexturl = form.get('nexturl')
        if nexturl:
	    response.redirect(nexturl)
        else:
	    response.reply('<P>Collection renamed to "%s".' % htmlescape(newname))
	return

    # Otherwise, we need to send the rename form

    docs = c.docs()

    fp = response.open()
    fp.write('<head><title>Collection "%s"</title>\n' % htmlescape(oldname))
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
    fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
    __issue_javascript_head_boilerplate(fp)
    fp.write('</head>\n')
    fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
    __issue_menu_definition(fp)

    fp.write('<table bgcolor="%s" width=100%%><tr>' % STANDARD_TOOLS_COLOR)

    fp.write('<td><table width=100%%><tr><td width=80%% align=left><h2>Collection "%s"</h2></td>' % htmlescape(oldname))
    fp.write('<td width=20%% align=right><font size="-1" color="white">UpLib %s</font>' % repo.get_version())
    fp.write('<font size="-2" color="%s">&nbsp;&middot;&nbsp;<a href="%s" class=parclink>%s</a></font></td></tr></table></td></tr>\n'
             % (STANDARD_BACKGROUND_COLOR, PARC_URL, htmlescape(PARCLINK_TEXT)))
    fp.write('<table bgcolor="%s" width=100%%><tr>' % STANDARD_TOOLS_COLOR)
    fp.write('<td align=left><form action="/action/basic/coll_rename" method=get>\n')
    fp.write('<input type=hidden name="oldname" value="%s">' % htmlescape(oldname))
    nexturl = form.get('nexturl')
    if nexturl:
        fp.write('<input type=hidden name="nexturl" value="%s">' % htmlescape(nexturl, true))
    fp.write('Rename collection to: <input type=text name="newname" value="" size=60>')
    fp.write('<input type=submit value="Rename"></form></td>\n')
    fp.write('</tr></table><hr><p>\n')

    if not docs:
        fp.write("Empty collection.")
    else:
        for doc in docs:
            dict = doc.get_metadata()
            title = ""
            if dict:
                # 'page-count' is the approved version, 'pagecount' is deprecated
                if dict.has_key('page-count') or dict.has_key('pagecount'):
                    pagecount = int(dict.get('page-count') or dict.get('pagecount'))
                    title = title + '(' + str(pagecount) + ' page%s)\n' % (((pagecount > 1) and "s") or "")
                if dict.has_key('title'):
                    title = title + dict['title']
                    if dict.has_key('authors'):
                        title = title + '\n' + dict['authors']
                elif dict.has_key('summary'):
                    s = re.sub(' / ', '\n', dict['summary'])
                    title = title + s[:min(len(s), 100)]
                title = htmlescape(title, true)
                iwidth, iheight = doc.icon_size()
            __output_document_icon(doc.id, title, fp, _is_sensible_browser(response.user_agent), width=iwidth, height=iheight)

    fp.write("</body>")
    fp.close()

############################################################
###
###  coll_editquery
###
############################################################

def _coll_editquery (repo, response, form):

    if not form.has_key('collname'):
	response.error(HTTPCodes.BAD_REQUEST, "<P>No collection specified.")
        return

    oldname = form.get('collname')

    c = repo.get_collection(oldname)
    if not isinstance(c, Collection):
        response.error(HTTPCodes.NOT_FOUND, "<P>No such collection '%s'." % htmlescape(oldname))
        return

    newquery = form.get('newquery')

    if newquery and oldname and form.get('changequery'):
        # OK, this is the re-submitted form, so change the query
        c.set_query(newquery)
        nexturl = form.get('nexturl')
        if nexturl:
	    response.redirect(nexturl)
        else:
	    response.reply('<P>Collection query now "%s".' % htmlescape(newquery))
	return

    # Otherwise, we need to send the edit form

    if newquery:
        docs = map(lambda x: x[1], repo.do_query(newquery))

    else:
        docs = c.docs()

    fp = response.open()
    fp.write('<head><title>Collection "%s"</title>\n' % htmlescape(oldname))
    fp.write('<meta http-equiv="Content-Script-Type" content="text/javascript">\n')
    fp.write('<link rel="shortcut icon" href="/favicon.ico">\n')
    fp.write('<link rel="icon" type="image/ico" href="/favicon.ico">\n')
    __issue_javascript_head_boilerplate(fp)
    fp.write('</head>\n')
    fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
    __issue_menu_definition(fp)

    fp.write('<table bgcolor="%s" width=100%%><tr>' % STANDARD_TOOLS_COLOR)

    fp.write('<td><table width=100%%><tr><td width=80%% align=left><h2>Collection "%s"</h2></td>' % htmlescape(oldname))
    fp.write('<td width=20%% align=right><font size="-1" color="white">UpLib %s</font>' % repo.get_version())
    fp.write('<font size="-2" color="%s">&nbsp;&middot;&nbsp;<a href="%s" class=parclink>%s</a></font></td></tr></table></td></tr>\n'
             % (STANDARD_BACKGROUND_COLOR, PARC_URL, htmlescape(PARCLINK_TEXT)))
    fp.write('<table bgcolor="%s" width=100%%><tr>' % STANDARD_TOOLS_COLOR)
    fp.write('<td align=left><form action="/action/basic/coll_editquery" method=get>\n')
    fp.write('<input type=hidden name="collname" value="%s">' % htmlescape(oldname))
    nexturl = form.get('nexturl')
    if nexturl:
        fp.write('<input type=hidden name="nexturl" value="%s">' % htmlescape(nexturl, true))
    fp.write('Change query to: <input type=text name="newquery" value="%s" size=60>' % htmlescape(newquery or c.query))
    fp.write('<input type=submit name="testquery" value="Test">\n')
    fp.write('<input type=submit name="changequery" value="Change"></form></td>\n')
    fp.write('</tr></table><hr><p>\n')

    output_query_stats (repo, fp, c, docs)

    if not docs:
        fp.write("Empty collection.")
    else:
        for doc in docs:
            dict = doc.get_metadata()
            title = ""
            if dict:
                # 'page-count' is the approved version, 'pagecount' is deprecated
                if dict.has_key('page-count') or dict.has_key('pagecount'):
                    pagecount = int(dict.get('page-count') or dict.get('pagecount'))
                    title = title + '(' + str(pagecount) + ' page%s)\n' % (((pagecount > 1) and "s") or "")
                if dict.has_key('title'):
                    title = title + dict['title']
                    if dict.has_key('authors'):
                        title = title + '\n' + dict['authors']
                elif dict.has_key('summary'):
                    s = re.sub(' / ', '\n', dict['summary'])
                    title = title + s[:min(len(s), 100)]
                title = htmlescape(title, true)
                iwidth, iheight = doc.icon_size()
            __output_document_icon(doc.id, title, fp, _is_sensible_browser(response.user_agent), width=iwidth, height=iheight)

    fp.write("</body>")
    fp.close()

############################################################
###
###  doc_get_metadata
###
############################################################

def _doc_get_metadata (repo, response, form):
    # note("_doc_get_metadata form = %s" % form)
    doc_id = form.get("doc_id")
    camefrom = form.get("camefrom") or response.request.get_header("referer")
    if doc_id and repo.valid_doc_id(doc_id):
        # request for metadata of existing document, to make changes
        metadata = repo.get_document(doc_id).get_metadata()
        metadata["doc_id"] = doc_id
        show_metadata_form (repo, response, metadata, None, camefrom)
        repo.touch_doc(doc_id)
    else:
        response.error(HTTPCodes.BAD_REQUEST, "Bad URL; no doc_id specified.")

############################################################
###
###  doc_update_metadata
###
############################################################

def _doc_update_metadata (repo, response, form):
    # note("_doc_update_metadata form = %s" % form)
    doc_id = form.get("doc_id")
    if doc_id and repo.valid_doc_id(doc_id):
        process_metadata_submission_changes(repo, doc_id, response, form)
        repo.touch_doc(doc_id)
    else:
	response.error(HTTPCodes.BAD_REQUEST, "Bad URL; no doc_id specified.")

############################################################
###
###  doc_pdf
###
############################################################

TIFF2PS = None
PS2PDF = None
TIFFTOPDF_CMD = None

NEWLINE_FLAG = 0x04
WORDENDING_FLAG = 0x02
ITALIC_FLAG = 0x10
BOLD_FLAG = 0x08
SERIF_FLAG = 0x40
FIXEDWIDTH_FLAG = 0x80
SYMBOL_FLAG = 0x20

def _make_pdf_version_from_tiff (doc, pdf_version_path):
    if not TIFF2PS:
        conf = configurator.default_configurator()
        TIFFTOPS = conf.get("tiff2ps")
        PS2PDF = conf.get("ps2pdf")
        TIFFTOPDF_CMD = conf.get("tiff-to-pdf-command")
    note(2, "creating PDF version of %s from TIFF page images", doc.id)
    versions_dir = os.path.join(doc.folder(), "versions")
    if not os.path.exists(versions_dir):
        os.mkdir(versions_dir)
        os.chmod(versions_dir, 0700)
    dpi = int(doc.get_metadata("tiff-dpi") or doc.get_metadata("images-dpi") or 300)
    width = float(doc.get_metadata("tiff-width") or doc.get_metadata("images-width") or 2550)/dpi
    height = float(doc.get_metadata("tiff-height") or doc.get_metadata("images-height") or 3300)/dpi
    note(2, "   width is %f, height is %f", width, height)
    cmd = TIFFTOPDF_CMD % (TIFFTOPS, width, height, os.path.join(doc.folder(), "document.tiff"),
                           PS2PDF, pdf_version_path)
    s, o, t = subproc(cmd)
    if s != 0:
        raise Error("tiff-to-pdf command <%s> fails with status %d.  Output is:\n%s" % (cmd, s, o))

def _make_pdf_version_from_png (doc, pdf_version_path):

    from PIL import Image
    import reportlab
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib.fonts import tt2ps

    # reportlab changed their API, so have to handle both
    import reportlab.lib.utils as reportlab_utils

    if hasattr(reportlab_utils, "ImageReader"):
        image_reader = reportlab_utils.ImageReader
    else:
        image_reader = lambda x: Image.open(x)
    INVISIBLE_MODE = 3

    note(2, "creating PDF version of %s from PNG page images", doc.id)
    versions_dir = os.path.join(doc.folder(), "versions")
    if not os.path.exists(versions_dir):
        os.mkdir(versions_dir)
        os.chmod(versions_dir, 0700)
    dpi = int(doc.get_metadata("tiff-dpi") or doc.get_metadata("images-dpi") or 300)
    width = (float(doc.get_metadata("tiff-width") or doc.get_metadata("images-width") or 2550) * inch) / dpi
    height = (float(doc.get_metadata("tiff-height") or doc.get_metadata("images-height") or 3300) * inch) / dpi

    scaling_factor = float(inch) / dpi
    note(2, "scaling page images by %s to fit into PDF file; width is %f, height is %f", scaling_factor, width, height)

    pdf = canvas.Canvas(pdf_version_path, pagesize=(width, height))

    title = doc.get_metadata("title")
    authors = doc.get_metadata("authors")
    subject = doc.get_metadata("abstract") or doc.get_metadata("email-subject")
    if title:
        pdf.setTitle(title)
    if authors:
        pdf.setAuthor(authors)
    if subject:
        pdf.setSubject(subject)

    pagesdir = os.path.join(doc.folder(), "page-images")
    pagenames = os.listdir(pagesdir)
    pagenames.sort()

    try:
        textgenerator = wordboxes_page_iterator(doc.folder())
        pagewordboxes = textgenerator.next()
    except:
        note("%s", string.join(traceback.format_exception(*sys.exc_info())))
        pagewordboxes = None

    for pagename in pagenames:
        note(3, "page %s; pagewordboxes[0] is %s", pagename, (pagewordboxes and pagewordboxes[0]))
        pdf.scale(scaling_factor, scaling_factor)
        pdf.drawImage(image_reader(os.path.join(pagesdir, pagename)), 0, 0)
        if pagewordboxes and (pagename == ('page%05d.png' % (pagewordboxes[0] + 1))):
            for box in pagewordboxes[1]:
                note(5, "    bbox \"%s\" at %s", box.text(), box.upper_left())
                textobj = pdf.beginText(box.left()/scaling_factor, (height - box.bottom())/scaling_factor)
                if box.is_fixedwidth():
                    fontfamily = "courier"
                elif box.is_serif():
                    fontfamily = "times"
                else:
                    fontfamily = "helvetica"

                fontname = tt2ps(fontfamily, box.is_bold(), box.is_italic())
                
                textobj.setFont(fontname, box.font_size()/scaling_factor)
                textobj.setTextRenderMode(INVISIBLE_MODE)
                textstring = box.text().strip().encode('latin-1', 'replace')
                if box.ends_word() and (not box.ends_line()):
                    textstring += ' '
                elif box.ends_line() and box.has_hyphen():
                    textstring += '-'
                textobj.textLines(textstring)
                pdf.drawText(textobj)
            bbox_count = len(pagewordboxes[1])
            try:
                pagewordboxes = textgenerator.next()
            except StopIteration:
                pagewordboxes = None
        else:
            bbox_count = 0
        pdf.showPage()
        note(3, "  finished page %s (%d bboxes)", pagename, bbox_count)
    pdf.save()


def _make_pdf_version (doc, pdf_version_path):
    if doc.uses_png_page_images():
        _make_pdf_version_from_png (doc, pdf_version_path)
    elif doc.uses_tiff_page_images():
        _make_pdf_version_from_tiff (doc, pdf_version_path)

def _find_and_return_pdf (repo, response, doc, ignore_original, ignore_cached):
    filepath = doc.pdf_original()
    pdf_version_path = os.path.join(doc.folder(), "versions", "document.pdf")
    ignore_original = ignore_original or doc.get_metadata("pdf-contains-no-text")
    if (not filepath or ignore_original) and (not os.path.exists(pdf_version_path) or ignore_cached):
        note(3, "making PDF version of %s", doc.id)
        _make_pdf_version (doc, pdf_version_path)
    if ((not ignore_original) and filepath) or os.path.exists(pdf_version_path):
        fname = doc.figure_file_name() + ".pdf"
        fpath = os.path.join(repo.html_folder(), "temp", fname)
        if os.path.islink(fpath) or os.path.exists(fpath): os.unlink(fpath)
        ensure_file(fpath, ((not ignore_original) and filepath) or pdf_version_path, true)
        response.redirect("/html/temp/" + fname)
        repo.touch_doc(doc.id)
        return
    else:
        response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "Can't make PDF file.")

def _doc_pdf (repo, response, form):
    doc_id = form.get("doc_id")
    ignore_original = form.has_key("ignore_original")
    ignore_cached = form.has_key("ignore_cached")
    if doc_id and repo.valid_doc_id(doc_id):
        doc = repo.get_document(doc_id)
        response.fork_request(_find_and_return_pdf, repo, response, doc, ignore_original, ignore_cached)
    else:
        if not doc_id:
            response.error(HTTPCodes.NOT_FOUND, "Bad URL; no doc_id was specified.")
        else:
            response.error(HTTPCodes.NOT_FOUND, "Specified document, %s, wasn't found in the repository." % doc_id)
    return

############################################################
###
###  doc_tiff
###
############################################################

def _doc_tiff (repo, response, form):
    doc_id = form.get("doc_id")
    filepath = None
    if doc_id and repo.valid_doc_id(doc_id):
        filepath = os.path.join(repo.doc_location(doc_id), "document.tiff")
        response.return_file("image/tiff;filename=%s.tiff" % doc_id, filepath)
        repo.touch_doc(doc_id)
    elif not doc_id:
	response.error(HTTPCodes.BAD_REQUEST, "Bad URL; no doc_id was specified.")
    else:
	response.error(HTTPCodes.NOT_FOUND, "Specified document, %s, wasn't found in the repository." % doc_id)

############################################################
###
###  _doc_pageimages
###
############################################################

def _doc_pageimages (repo, response, form):
    doc_id = form.get("doc_id")
    pageimagespath = os.path.join(repo.doc_location(doc_id), "versions", "pageimages.zip")
    if doc_id and repo.valid_doc_id(doc_id):

        # check for cached page-images zip file
        if os.path.exists(pageimagespath):
            response.return_file("image/tiff;filename=%s-page-images.zip" % doc_id, pageimagespath)
            repo.touch_doc(doc_id)
            return

        versions_dir = os.path.join(repo.doc_location(doc_id), "versions")
        if not os.path.exists(versions_dir):
            os.mkdir(versions_dir)
            os.chmod(versions_dir, 0700)

        # check for TIFF master file
        filepath = os.path.join(repo.doc_location(doc_id), "document.tiff")
        if os.path.exists(filepath):
            # do tiff part
            # first, copy the tiff file and remove compression
            tmpdir = tempfile.mktemp()
            try:
                from PIL import Image

                os.mkdir(tmpdir)
                tiffmaster = os.path.join(tmpdir, "master.tiff")

                conf = configurator.default_configurator()

                TIFFSPLIT = conf.get("tiffsplit")
                TIFFCP = conf.get("tiffcp")
                TIFF_SPLIT_CMD = conf.get("tiff-split-command")

                split_command = (TIFF_SPLIT_CMD
                                 % (TIFFCP, filepath, tiffmaster,
                                    TIFFSPLIT, tiffmaster, os.path.join(tmpdir, "x")))
                status, output, tsignal = subproc(split_command)
                if status != 0: raise Error ("'%s' signals non-zero exit status %d in %s => %s" %
                                             (split_command, dirpath, tmpdir))
                note(3, "pages are %s", str(os.listdir(tmpdir)))
                zf = zipfile.ZipFile(pageimagespath, 'w', zipfile.ZIP_STORED)
                counter = 1
                for file in os.listdir(tmpdir):
                    if file[0] == 'x':
                        note(3, "converting TIFF file %s to PNG and adding it", file)
                        Image.open(os.path.join(tmpdir, file)).save(os.path.join(tmpdir, file + ".png"), 'PNG')
                        zf.write(os.path.join(tmpdir, file + '.png'),  ('%06d' % counter) + ".png")
                        counter = counter + 1
                response.return_file("application/x-uplib-page-images;filename=%s-page-images.zip" % doc_id, pageimagespath)
                repo.touch_doc(doc_id)
            finally:
                if os.path.isdir(tmpdir): shutil.rmtree(tmpdir)
            return

        # check for PNG master file
        filepath = os.path.join(repo.doc_location(doc_id), "page-images")
        if os.path.isdir(filepath):
            # do PNG part
            zf = zipfile.ZipFile(pageimagespath, 'w', zipfile.ZIP_STORED)
            for file in os.listdir(filepath):
                if file[0] != '.':
                    zf.write(os.path.join(filepath, file), ('%06d' % int(re.findall('[0-9]+', file)[0])) + '.png')
            response.return_file("application/x-uplib-page-images;filename=%s-page-images.zip" % doc_id, pageimagespath)
            repo.touch_doc(doc_id)
            return

        response.error(HTTPCodes.NO_CONTENT, "No page images were found for this document (%s)" % doc_id)
    elif not doc_id:
	response.error(HTTPCodes.BAD_REQUEST, "Bad URL; no doc_id was specified.")
    else:
	response.error(HTTPCodes.NOT_FOUND, "Specified document, %s, wasn't found in the repository." % doc_id)

############################################################
###
###  _doc_functions
###
###  Return list of defined doc functions.
###
############################################################

def _doc_functions (repo, response, params):

    buttons = get_buttons_sorted(FN_DOCUMENT_SCOPE)
    doc_id = params.get("doc_id")
    fp = response.open("text/plain")
    if doc_id:
        fp.write("doc: %s\n" % doc_id)
    for button in buttons:
        if (not doc_id) or (not button[1][5]) or (button[1][5](repo.get_document(doc_id))):
            url = button[1][4]
            if url is None:
                url = "/action/basic/repo_userbutton?uplib_userbutton_key=%s&doc_id=%%s" % button[0]
            fp.write("%s, %s, %s, %s\n" % (button[0], url, button[1][3], button[1][0]))
    fp.close()

############################################################
###
###  _doc_ebook
###
############################################################
    
JAVAHOME = None
JARSIGNER = None
OPENSSL = None

JNLP_BOILERPLATE = """
<?xml version="1.0" encoding="utf-8"?>
<!-- JNLP File for SimpleExample Application -->
<jnlp

   codebase="%(hostport)s%(urlpath)s"
   href="%(jnlpfilename)s">

   <information>
     <title>ReadUp:  %(title)s</title>
     <vendor>UpLib</vendor>
     <description>%(description)s</description>
     <description kind="short">%(title)s</description>
     <offline-allowed/>
   </information>
   <resources>
     <j2se version="1.4+" max-heap-size="1000M" href="http://java.sun.com/products/autodl/j2se" />
     <jar href="%(jarfilename)s"/>
   </resources>
   <application-desc main-class="com.parc.uplib.readup.ebook.EBook"/>
</jnlp>
"""

def _make_ebook (doc):

    if (not JAVAHOME) or (not JARSIGNER):
        response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "JAVAHOME not initialized, can't build an ebook")
        return

    basejar = os.path.join(doc.repo.html_folder(), "ebookbase.jar")
    if not os.path.exists(basejar):
        response.error(HTTPCodes.BAD_REQUEST, "No ebookbase.jar installed in this repository.")
        return
    
    jarpath = os.path.join(JAVAHOME, "bin", "jar")
    if not os.path.exists(jarpath):
        note("Can't find \"jar\" application at %s." % jarpath)
        return None

    versions_dir = os.path.join(doc.folder(), "versions")
    if not os.path.exists(versions_dir):
        os.mkdir(versions_dir)
    tfilename = os.path.join(versions_dir, doc.figure_file_name() + ".jar")
    if os.path.exists(tfilename):
        return tfilename

    shutil.copyfile(basejar, tfilename)
    cmd = "%s ufv0 \"%s\" -C \"%s\" thumbnails -C \"%s\" metadata.txt" % (jarpath, tfilename, doc.folder(), doc.folder())
    note(3, "executing <%s>", cmd)
    status, output, tsignal = subproc(cmd)
    if status != 0:
        note("Couldn't create new ebook jar file %s: status %d, output \"%s\""
             % (tfilename, status, output))
        if os.path.exists(tfilename): os.unlink(tfilename)
        return None
    if os.path.isdir(os.path.join(doc.folder(), "links")):
        cmd = "%s ufv0 \"%s\" -C \"%s\" links" % (jarpath, tfilename, doc.folder())
        status, output, tsignal = subproc(cmd)
        if status != 0:
            note ("Couldn't add links to ebook jar file %s: status %d, output \"%s\""
                  % (tfilename, status, output))
            if os.path.exists(tfilename): os.unlink(tfilename)
            return None

    repocertfile = doc.repo.certfilename()
    if repocertfile and OPENSSL and JARSIGNER:
        # sign the jar file with the repository's certificate
        tmpcertfile = tempfile.mktemp()
        cmd = "%s pkcs12 -export -passout pass:foobar -out %s -in %s -name myrepo" % (OPENSSL, tmpcertfile, repocertfile)
        status, output, tsignal = subproc(cmd)
        if status != 0:
            note("can't sign jar file %s with certificate %s:  %s\n", tfilename, repocertfile, output)
        else:
            cmd = "%s -keystore %s -storetype pkcs12 -storepass foobar %s myrepo" % (JARSIGNER, tmpcertfile, tfilename)
            status, output, tsignal = subproc(cmd)
            if status != 0:
                note("can't sign jar file %s with certificate %s:  %s\n", tfilename, repocertfile, output)
        if os.path.exists(tmpcertfile): os.unlink(tmpcertfile)

    return tfilename

def _doc_ebook (repo, response, params):

    id = params.get("doc_id")
    if not id:
        response.error(_HTTPCodes.BAD_REQUEST, "No doc_id specified in the request parameters.")
        return

    if not repo.valid_doc_id(id):
        response.error(_HTTPCodes.BAD_REQUEST, "Invalid doc_id %s specified in the request parameters." % id)
        return

    sendjnlp = params.get("sendjnlp")

    doc = repo.get_document(id)
    ebookfile = _make_ebook(doc)
    if not ebookfile:
        response.error(_HTTPCodes.INTERNAL_SERVER_ERROR, "Can't make ebook for document %s." % id)
        return

    if not sendjnlp:
        response.return_file("application/x-java-jar-file", ebookfile)
        return

    # try to figure out the right hostname to put in the JNLP file
    option1 = get_fqdn()
    option2 = response.callers_idea_of_service
    if "." in option2 and not option2.endswith(".local"):
        hostport = option2
    else:
        hostport = "%s:%s" % (option1, repo.secure_port())

    jnlpfilename = os.path.join(doc.folder(), "versions", "document.jnlp")
    jnlpdata = JNLP_BOILERPLATE % {
        "title" : htmlescape(doc.get_metadata("title") or doc.id),
        "description" : htmlescape(doc.get_metadata("abstract") or doc.get_metadata("title") or doc.id),
        "docid" : doc.id,
        "jnlpfilename" : htmlescape(os.path.split(jnlpfilename)[1]),
        "jarfilename" : htmlescape(os.path.split(ebookfile)[1]),
        "hostport" : "https://%s" % hostport,
        "urlpath" :  htmlescape("/docs/%s/versions" % doc.id),
        }
    fp = open(jnlpfilename, "w")
    fp.write(jnlpdata.strip() + "\n")
    fp.close()

    response.return_file("application/x-java-jnlp-file", jnlpfilename)

############################################################
###
###  _doc_readup
###
############################################################
    
READUP_JNLP_BOILERPLATE = """
<?xml version="1.0" encoding="utf-8"?>
<!-- JNLP File for ReadUp Application -->
<jnlp
   spec="1.0"
   codebase="%(hostport)s">
   <information>
     <title>ReadUp:  %(title)s</title>
     <vendor>UpLib</vendor>
     <description>%(description)s</description>
     <description kind="short">%(title)s</description>
     <icon href="html/images/ReadUpJWS.gif" />
     <offline-allowed/>
   </information>
   <resources>
     <j2se version="1.5+" max-heap-size="1000M" href="http://java.sun.com/products/autodl/j2se" />
     <jar href="html/%(jarfilename)s"/>
     <!-- just in case it's a Mac, set some appropriate properties -->
     <property name="apple.awt.showGrowBox" value="false"/>
     <property name="apple.laf.useScreenMenuBar" value="true"/>
     <property name="JFileChooser.appBundleIsTraversable" value="never"/>
     <property name="com.apple.macos.useScreenMenuBar" value="true"/>
     <!-- and a session cookie for the application to use -->
     <property name="com.parc.uplib.sessionCookie" value="%(cookie)s"/>
   </resources>
   <application-desc main-class="com.parc.uplib.readup.application.UpLibShowDoc">
     <argument>--debug</argument>
     <argument>--repository=%(hostport)s</argument>
     <argument>--doc-id=%(docid)s</argument>
     <argument>--cookie=%(cookie)s</argument>
     <argument>--page=%(page)s</argument>
   </application-desc>
</jnlp>
"""

def _doc_readup (repo, response, params):

    id = params.get("doc_id")
    if not id:
        response.error(_HTTPCodes.BAD_REQUEST, "No doc_id specified in the request parameters.")
        return

    if not repo.valid_doc_id(id):
        response.error(_HTTPCodes.BAD_REQUEST, "Invalid doc_id %s specified in the request parameters." % id)
        return

    doc = repo.get_document(id)
    readupfile = os.path.join(doc.repo.html_folder(), "signedreadup.jar")
    if not os.path.exists(readupfile):
        response.error(_HTTPCodes.INTERNAL_SERVER_ERROR, "This version of UpLib doesn't support Java Web Start reading.")
        return

    page = params.get("page")
    if page: page = int(page)

    # try to figure out the right hostname to put in the JNLP file
    option1 = get_fqdn()
    option2 = response.callers_idea_of_service
    if "." in option2 and not option2.endswith(".local"):
        hostport = option2
    else:
        hostport = "%s:%s" % (option1, repo.secure_port())

    if not os.path.isdir(os.path.join(doc.folder(), "versions")):
        os.mkdir(os.path.join(doc.folder(), "versions"))
    jnlpfilename = os.path.join(doc.folder(), "versions", "readup.jnlp")
    cookie = repo.new_cookie(str(response.request.header))
    jnlpdata = READUP_JNLP_BOILERPLATE % {
        "title" : htmlescape(doc.get_metadata("title") or doc.id),
        "description" : htmlescape(doc.get_metadata("abstract") or doc.get_metadata("title") or doc.id),
        "docid" : doc.id,
        "jnlpfilename" : htmlescape(os.path.split(jnlpfilename)[1]),
        "jarfilename" : htmlescape(os.path.split(readupfile)[1]),
        "hostport" : "https://%s" % hostport,
        "urlpath" :  htmlescape("/docs/%s/versions" % doc.id),
        "cookie": "%s=%s" % (cookie.name(), cookie.value()),
        "page" : ((page is None) and -1) or page,
        }
    fp = open(jnlpfilename, "w")
    fp.write(jnlpdata.strip() + "\n")
    fp.close()

    response.return_file("application/x-java-jnlp-file", jnlpfilename)

############################################################
###
###  _doc_delete
###
############################################################

def _locate_related_docs (doc, docset=None):

    if docset is None:
        if sys.version_info < (2, 6):
            import sets
            docset = sets.Set()
        else:
            docset = set()
        docset.add(doc)

    # check for attachments to an email message
    attachment_ids = doc.get_metadata("email-attachments")
    if attachment_ids:
        for id in [x.strip() for x in attachment_ids.split(",")]:
            if doc.repo.valid_doc_id(id):
                d = doc.repo.get_document(id)
                if d not in docset:
                    docset.add(d)
                    docset.update(_locate_related_docs(d, docset))
    attachment_ids = doc.get_metadata("email-attachment-to")
    if attachment_ids:
        # find source message
        otherdocs = doc.repo.do_query("email-guid:" + attachment_ids.strip())
        for score, d in otherdocs:
            if d not in docset:
                docset.add(d)
                docset.update(_locate_related_docs(d, docset))

    return docset

def _doc_delete (repo, response, form):

    doc_id = form.get('doc_id')
    if not repo.valid_doc_id(doc_id):
        response.reply("No document with id <b>%s</b>.  It must already have been deleted." % doc_id);
        return

    referer = response.request.get_header('referer')
    confirmed = form.get('confirmed')
    action = form.get('action')
    if ((not action) or (action == 'Yes')) and doc_id and (confirmed == "yes"):
        _repo_delete_document(repo, response, form)
    elif doc_id and (action == "No"):
        response.redirect('%s' % _doc_show_URL(doc_id))
    elif doc_id:
        doc = repo.get_document(doc_id)
        attachments = _locate_related_docs(doc)
        attachments.discard(doc)

        name = htmlescape(doc.get_metadata('name') or doc.get_metadata('title') or doc.id)
        text = htmlescape(doc.get_metadata('comment') or doc.get_metadata('abstract') or doc.get_metadata('summary') or '')
        fp = response.open()
        fp.write('<html><head><title>Delete document %s?</title>\n' % name)
        fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
        show_abstract(repo, doc, fp, _is_sensible_browser(response.user_agent))
        fp.write('<hr><p bgcolor="%s"><center><form action="/action/basic/doc_delete" method=GET>\n' % STANDARD_TOOLS_COLOR)
        if attachments:
            fp.write("</center>\n")
            fp.write("<h3><i>Associated documents to delete:</i></h3><br>\n")
            for attachment in attachments:
                show_abstract(repo, attachment, fp, _is_sensible_browser(response.user_agent),
                              query="foo", showpagesearch=False)      # pass fake query to get "marked" checkbox
            fp.write("<hr><center>\n")
        fp.write('<input type=hidden name="doc_id" value="%s">' % doc_id)
        if attachments:
            fp.write('<b>Delete document and marked associated documents?</b>\n')
        else:
            fp.write('<b>Delete document?</b>\n')
        fp.write('<input type=hidden name="confirmed" value="yes">\n')
        fp.write('<input type=submit name="action" value="Yes" style="padding: 10px">\n')
        fp.write('<input type=submit name="action" value="No" style="padding: 10px">\n')
        if referer:
            fp.write('<input type=hidden name="camefrom"" value="%s">\n' % htmlescape(referer))
        fp.write('</center></form></body></html>')
        fp.close()
    else:
        response.error(BAD_REQUEST, "No doc_id specified.")

############################################################
###
###  Configuration reading
###
############################################################

def _redirect_doc_to (scope, url, repo, response, params):
    if scope == FN_REPOSITORY_SCOPE:
        pass
    elif scope == FN_DOCUMENT_SCOPE:
        url = url % params.get("doc_id")
    elif scope == FN_COLLECTION_SCOPE:
        if not ('?' in url):
            url = url + "?junkparam="
        ids = params.get("doc_id")
        if ids:
            if type(ids) in types.StringTypes:
                ids = (ids,)
            for id in ids:
                url = url + "&doc_id=" + id
        collid = params.get("coll")
        if collid:
            url = url + "&coll=" + collid
    response.redirect(url)

def read_configuration():

    global SEARCH_RESULTS_FORMAT, USING_DOCVIEWER, WANTS_DOC_ICON_MENUS, DEFAULT_QUERY_CUTOFF, DEFAULT_PAGE_QUERY_CUTOFF
    global JAVAHOME, JARSIGNER, OPENSSL, INTERACTION_CHARSET, EXTERNAL_URL, NEED_STATS_PAGES, NEED_STATS

    conf = configurator.default_configurator()
    SEARCH_RESULTS_FORMAT = conf.get('search-results-format', 'Abstract MRU')
    if not SEARCH_RESULTS_FORMAT in KNOWN_LISTING_FORMATS:
        SEARCH_RESULTS_FORMAT = 'Abstract MRU'
    USING_DOCVIEWER = conf.get_bool('use-java-docviewer', false)
    WANTS_DOC_ICON_MENUS = conf.get_bool("use-menus-on-browser-thumbnails", true)
    DEFAULT_QUERY_CUTOFF = float(conf.get("search-score-threshold") or "0.0")
    DEFAULT_PAGE_QUERY_CUTOFF = float(conf.get("page-search-score-threshold") or "0.0")
    JAVAHOME = find_JAVAHOME()
    if JAVAHOME:
        JARSIGNER = os.path.join(JAVAHOME, "bin", "jarsigner")
    OPENSSL = conf.get("openssl")
    INTERACTION_CHARSET = conf.get('interaction-charset', 'UTF-8')
    EXTERNAL_URL = conf.get('uplib-external-url', EXTERNAL_URL)
    NEED_STATS_PAGES = conf.get_bool("basic-need-page-count", False)
    NEED_STATS = conf.get_bool("basic-need-doc-count", True)

    standard_doc_buttons = string.split(conf.get('standard-doc-functions', ''), ';')
    standard_coll_buttons = string.split(conf.get('standard-collection-functions', ''), ';')
    doc_buttons = string.split(conf.get('doc-functions', ''), ';')
    user_buttons = string.split(conf.get('user-buttons', ''), ';')
    coll_buttons = string.split(conf.get('collection-functions', ''), ';')

    for button in (doc_buttons + standard_doc_buttons):
        parts = string.split(string.strip(button), ',')
        if len(parts) > 1 and len(parts) < 5:
            label = parts[0]
            url = string.strip(parts[1])
            target = ((len(parts) > 2) and string.strip(parts[2])) or None
            criterion = ((len(parts) > 3) and eval(string.strip(parts[3]))) or None
            fn = lambda repo, response, params, the_url=url, f2=_redirect_doc_to: f2(FN_DOCUMENT_SCOPE, the_url, repo, response, params)
            add_document_function (label, fn, target, url, criterion)

    for button in user_buttons:
        parts = string.split(string.strip(button), ',')
        if len(parts) > 1 and len(parts) < 5:
            label = parts[0]
            url = string.strip(parts[1])
            target = ((len(parts) > 2) and string.strip(parts[2])) or None
            criterion = ((len(parts) > 3) and eval(string.strip(parts[3]))) or None
            fn = lambda repo, response, params, the_url=url, f2=_redirect_doc_to: f2(FN_REPOSITORY_SCOPE, the_url, repo, response, params)
            add_user_button (label, fn, target, url, criterion)

    for button in (coll_buttons + standard_coll_buttons):
        parts = string.split(string.strip(button), ',')
        if len(parts) > 1 and len(parts) < 5:
            label = parts[0]
            url = string.strip(parts[1])
            target = ((len(parts) > 2) and string.strip(parts[2])) or None
            criterion = ((len(parts) > 3) and eval(string.strip(parts[3]))) or None
            fn = lambda repo, response, params, the_url=url, f2=_redirect_doc_to: f2(FN_COLLECTION_SCOPE, the_url, repo, response, params)
            add_group_operation (label, fn, target, url, criterion)

############################################################
###
###  The dictionary of basic (built-in) actions
###
############################################################

def _figure_file_name (doc, ext):
    return doc.figure_file_name() + "." + ext

############################################################
###
###  The dictionary of basic (built-in) actions
###
############################################################

_actions = {
    "repo_show"         : _repo_show,
    "repo_show_category": _repo_show_categories,
    "repo_search"       : _repo_search,
    "repo_add"          : _repo_add_document,
    "repo_delete"       : _repo_delete_document,
    "repo_password"     : _repo_password,
    "repo_changename"   : _repo_changename,
    "repo_categorize"   : _repo_categorize,
    "repo_colls"        : _repo_collections,
    "repo_addqcoll"     : _repo_addqcoll,
    "repo_userbutton"   : _repo_userbutton,
    "repo_stats"        : __show_stats,
    "repo_status_json"  : _repo_status_json,
    "repo_user_actions" : _repo_user_actions,
    "repo_multidelete"  : _repo_multidelete,

    "coll_rename"       : _coll_rename,
    "coll_delete"       : _coll_delete,
    "coll_editquery"    : _coll_editquery,

    "doc_pdf"           : _doc_pdf,
    "doc_tiff"          : _doc_tiff,
    "doc_search"        : _doc_search,
    "doc_pageimages"    : _doc_pageimages,
    "doc_ebook"         : _doc_ebook,
    "doc_meta"          : _doc_get_metadata,
    "doc_readup"        : _doc_readup,
    "doc_update"        : _doc_update_metadata,
    "doc_delete"        : _doc_delete,
    "doc_functions"     : _doc_functions,

    "login"             : _login,
    }

_initialized = false

def _initialize():
    global _initialized
    if not _initialized:
        read_configuration()
        from uplib.extensions import eview_actions
        _actions.update(eview_actions)
        from uplib.pageview import pageview_actions
        _actions.update(pageview_actions)
        from uplib.related import related_actions
        _actions.update(related_actions)
        from uplib.paragraphs import HTML, prelated
        _actions['doc_html'] = HTML
        _actions['doc_versions'] = prelated
        from uplib.categories import category_actions
        _actions.update(category_actions)
        try:
            from uplib.emailParser import show_thread as email_thread
            from uplib.emailParser import show_threads as email_threads
            from uplib.emailParser import _all_email_docs
            from uplib.emailParser import get_thread_content as get_thread_content
            from uplib.emailParser import clean_dangling_attachments
            _actions['email_thread'] = email_thread
            _actions['email_threads'] = email_threads
            _actions['email_thread_content'] = get_thread_content
            _actions['email_clean_dangling_attachments'] = clean_dangling_attachments
            # show this button if any email or attachment is in the group
            add_group_operation("E-Mail Threads", email_threads, None, None, lambda x: _all_email_docs(x, any=True))
        except ValueError, x:
            note(2, "Can't use email:  %s", x)

        _initialized = true


def lookup_action(action_name):
    # define this as a function to so that it reloads well
    _initialize()
    return _actions.get(action_name)
