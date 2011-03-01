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

import string, sys, os, hashlib, re, tempfile, shutil, httplib

try:
    from plibUtil import note, HTTPCodes, configurator, update_metadata, zipup, https_post_multipart, parse_URL, get_fqdn
    from basicPlugins import STANDARD_BACKGROUND_COLOR, STANDARD_LEGEND_COLOR, _doc_show_URL
    import newFolder
except ImportError:
    from uplib.plibUtil import note, configurator, update_metadata, zipup, get_fqdn
    from uplib.webutils import HTTPCodes, https_post_multipart, parse_URL
    from uplib.basicPlugins import STANDARD_BACKGROUND_COLOR, STANDARD_LEGEND_COLOR, _doc_show_URL
    import uplib.newFolder as newFolder 


def _push_doc (doc, remote_repo_url, remote_password):

    note(3, "pushing %s  (%s)...", doc.id, doc.get_metadata("title"))
    tdir = tempfile.mktemp()
    os.mkdir(tdir)
    try:
        if os.path.isdir(os.path.join(doc.folder(), "page-images")):
            shutil.copytree(os.path.join(doc.folder(), "page-images"), os.path.join(tdir, "page-images"))
        else:
            shutil.copyfile(os.path.join(doc.folder(), "document.tiff"), os.path.join(tdir, "document.tiff"))
        if os.path.exists(doc.text_path()):
            shutil.copyfile(os.path.join(doc.folder(), "contents.txt"), os.path.join(tdir, "contents.txt"))
        if os.path.exists(os.path.join(doc.folder(), "paragraphs.txt")):
            shutil.copyfile(os.path.join(doc.folder(), "paragraphs.txt"), os.path.join(tdir, "paragraphs.txt"))
        if os.path.exists(os.path.join(doc.folder(), "wordbboxes")):
            shutil.copyfile(os.path.join(doc.folder(), "wordbboxes"), os.path.join(tdir, "wordbboxes"))
        if os.path.exists(os.path.join(doc.folder(), "images")):
            shutil.copytree(os.path.join(doc.folder(), "images"), os.path.join(tdir, "images"))
        if os.path.exists(os.path.join(doc.folder(), "originals")):
            shutil.copytree(os.path.join(doc.folder(), "originals"), os.path.join(tdir, "originals"))
        if os.path.exists(os.path.join(doc.folder(), "links")):
            shutil.copytree(os.path.join(doc.folder(), "links"), os.path.join(tdir, "links"))

        # filter the metadata
        conf = configurator()
        md = doc.get_metadata()
        newmd = {}
        properties = string.split(conf.get('synchronizing-properties') or
                                  conf.get('metadata-sharing-properties') or
                                  conf.get('metadata-sharing-default-properties'), ':')

        for property in ["title", "date", "authors", "citation"]:
            if not property in properties:
                properties.append(property)

        for prop in properties:
            if md.has_key(prop):
                newmd[prop] = md[prop]
        update_metadata(os.path.join(tdir, "metadata.txt"), newmd)

        host, port, path = parse_URL(remote_repo_url)

        # create zipfile of the folder
        tmpfilename = zipup(tdir)
        try:
            # send it to the repository
            errcode, errmsg, headers, text = https_post_multipart(host, port, remote_password,
                                                                  "/action/basic/repo_add",
                                                                  (("password", remote_password,),
                                                                   ("filetype", "zipped-folder",)),
                                                                  (("newfile", tmpfilename),))
            if errcode != 200:
                raise ValueError("Posting of data to repository %s resulted in error %d (%s).\nReturned text was:\n%s" % (remote_repo_url, errcode, errmsg, text))
            note(3, "text from remote repository was\n%s.\n", text)
            note(3, "%s successfully posted to %s.", tdir, remote_repo_url)

        finally:
            if os.path.exists(tmpfilename):
                os.unlink(tmpfilename)

        return text.strip()

    finally:
        if os.path.exists(tdir):
            shutil.rmtree(tdir)


def _get_doc_to_file (local_repo, host, port, password, path):
    h = httplib.HTTPS(host, port)
    h.putrequest('GET', path)
    if password:
        h.putheader('Password', password)
    h.endheaders()
    errcode, errmsg, headers = h.getreply()
    if errcode == 200:
        bits = h.file.read()
        return newFolder.create(local_repo, bits, "zipped-folder", {})
    elif errcode == 302:
        # moved temporarily
        newpath = headers.get("Location")
        if newpath:
            return _get_doc_to_file(local_repo, host, port, password, newpath)
        else:
            raise ValueError('Temporary redirect (302) without a Location header while fetching ' + path)
    elif errcode == 401:
        raise ValueError("bad reply code 401 (not authorized) from remote repository")
    else:
        raise ValueError('bad status %d (%s) received while fetching %s' % (errcode, errmsg, path))

def _pull_doc (local_repo, doc_id, remote_repo_url, remote_password):
    host, port, path = parse_URL(remote_repo_url)
    return _get_doc_to_file(local_repo, host, port, remote_password, '/action/externalAPI/fetch_folder?doc_id=%s' % doc_id)

def _calculate_doc_hash (doc):

    doc_path = doc.pdf_original()
    if not doc_path or not os.path.exists(doc_path):
        doc_path = os.path.join(doc.folder(), "document.tiff")
        if not os.path.exists(doc_path):
            prefix = os.path.join(doc.folder(), "page-images")
            if os.path.isdir(prefix):
                files = os.listdir(prefix)
                files.sort()
            else:
                return 0
        else:
            prefix = doc.folder()
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


def _check_hashes (hashes, remote_repo, remote_password):

    host, port, path = parse_URL(remote_repo)

    hashtext = string.join(hashes, "\n")

    # create zipfile of the folder
    errcode, errmsg, headers, text = https_post_multipart(host, port, remote_password,
                                                          "/action/SynchronizeRepositories/check_hashes",
                                                          [("hashes", hashtext),],
                                                          ())
    if errcode != 200:
        note("Errcode %s received.  Error text from repository was\n%s.\n", errcode, errmsg)
        return None

    else:
        results = []
        resultsA = text.split("\n")
        for result in resultsA:
            rr = string.strip(result)
            if rr:
                results.append(string.split(rr))
        return results


def _build_hash_dict (repo):
    # build a list of document fingerprints
    docs = repo.generate_docs()
    hash_dict = {}
    for doc in docs:
        if hasattr(doc, "sha_hash"):
            hashvalue = doc.sha_hash()
        else:
            hashvalue = _calculate_doc_hash(doc)
        hash_dict[hashvalue] = doc
    return hash_dict


def check_hashes (repo, response, params):

    """Return values are one of
    <hash> L
    <hash> R <docid> <title>
    """

    remote_hashes = params.get("hashes")
    note("checking hashes...")
    if not remote_hashes:
        response.error(HTTPCodes.BAD_REQUEST, "<p>No hashes specified.")
        note("no hashes")
        return
    note("hashes are %s", remote_hashes)
    hash_dict = _build_hash_dict(repo)
    remote_hash_list = string.split(remote_hashes, "\n")
    retval = ""
    for hash in remote_hash_list:
        note("checking remote hash %s", hash)
        if hash_dict.has_key(hash):
            # document present in both places
            # retval = retval + "%s B" % hash + "\n"
            del hash_dict[hash]
        else:
            # document present only in caller
            retval = retval + "%s L" % hash + "\n"

    for key in hash_dict.keys():
        # document present only on callee
        title = hash_dict[key].get_metadata("title") or ""
        title = re.sub("\s", "`", title)
        retval = retval + "%s R" % key + " " + hash_dict[key].id + " " + title + "\n"

    note(3, "return values are %s", retval)

    fp = response.open("text/plain")
    fp.write(retval)
    fp.close()
    return


def sync (repo, response, params):

    # check the parameters
    remote_repo = params.get('repository')
    if not remote_repo:
        response.error(HTTPCodes.BAD_REQUEST, "<p>No remote repository specified.")
        return

    remote_password = params.get('password', "")

    # build a list of document fingerprints
    hash_dict = _build_hash_dict(repo)

    note("hash dict is %s", hash_dict)

    # check each fingerprint with remote repository
    remote_matches = _check_hashes (hash_dict.keys(), remote_repo, remote_password)

    note("remote matches are %s", remote_matches)

    fp = response.open()
    if not remote_matches:
        fp.write("<P>Both repositories match.<br>\n")
    else:
        # push across all matches that aren't on the remote side
        for match in remote_matches:
            note("hash is %s, match_code is %s", match[0], match[1])
            if match[1] == 'L':
                _push_doc (hash_dict[match[0]], remote_repo, remote_password)
                doc = hash_dict[match[0]]
                note("doc is %s", doc)
                fp.write("pushed doc %s (%s)...<br>" % (doc.id, doc.get_metadata("title")))
            elif match[1] == 'R':
                _pull_doc (repo, match[2], remote_repo, remote_password)
                note("remote doc ID is %s", match[2])
                title = ((len(match) > 3) and re.sub("`", " ", match[3])) or ""
                fp.write("pulled doc %s (%s)...<br>" % (match[2], title))
    fp.close()

def syncdocs (repo, response, params):

    # check the parameters
    remote_repo = params.get('repository')
    if not remote_repo:
        response.error(HTTPCodes.BAD_REQUEST, "<p>No remote repository specified.")
        return

    remote_password = params.get('password', "")

    doc_ids = params.get('doc_id')
    if not doc_ids:
        response.error(HTTPCodes.BAD_REQUEST, "<p>No doc_id's specified.")
        return
    if (type(doc_ids) == type('')):
        doc_ids = [doc_ids,]

    pushing = params.has_key('both') or params.has_key('push')
    pulling = params.has_key('both') or params.has_key('pull')

    fp = response.open()

    for doc_id in doc_ids:
        if doc_id[0] == 'R' and pulling:
            id = _pull_doc (repo, doc_id[1:], remote_repo, remote_password)
            fp.write("<p>Pulled %s from remote repository, local ID is %s\n" % (doc_id[1:], id))
        if doc_id[0] == 'L' and pushing:
            doc = repo.get_document(doc_id[1:])
            id = _push_doc (doc, remote_repo, remote_password)
            title = doc.get_metadata("title")
            title = (title and (" (" + title + ")")) or ""
            fp.write("<p>Pushed %s%s to remote repository; remote ID is %s\n" % (doc_id[1:], title, id))
    fp.close()

def push (repo, response, params):

    # check the parameters
    remote_repo = params.get('repository')
    if not remote_repo:
        response.error(HTTPCodes.BAD_REQUEST, "<p>No remote repository specified.")
        return

    remote_password = params.get('password', "")

    # build a list of document fingerprints
    hash_dict = _build_hash_dict(repo)

    note("hash dict is %s", hash_dict)

    # check each fingerprint with remote repository
    remote_matches = _check_hashes (hash_dict.keys(), remote_repo, remote_password)

    note("remote matches are %s", remote_matches)

    fp = response.open()
    if not remote_matches:
        fp.write("<P>Both repositories match.<br>\n")
    else:
        # push across all matches that aren't on the remote side
        for match in remote_matches:
            note("hash is %s, match_code is %s", match[0], match[1])
            if match[1] == 'L':
                _push_doc (hash_dict[match[0]], remote_repo, remote_password)
                doc = hash_dict[match[0]]
                note("doc is %s", doc)
                fp.write("pushed doc %s (%s)...<br>" % (doc.id, doc.get_metadata("title")))
    fp.close()

def pull (repo, response, params):

    # check the parameters
    remote_repo = params.get('repository')
    if not remote_repo:
        response.error(HTTPCodes.BAD_REQUEST, "<p>No remote repository specified.")
        return

    remote_password = params.get('password', "")

    # build a list of document fingerprints
    hash_dict = _build_hash_dict(repo)

    note("hash dict is %s", hash_dict)

    # check each fingerprint with remote repository
    remote_matches = _check_hashes (hash_dict.keys(), remote_repo, remote_password)

    note("remote matches are %s", remote_matches)

    fp = response.open()
    if not remote_matches:
        fp.write("<P>Both repositories match.<br>\n")
    else:
        # push across all matches that aren't on the remote side
        for match in remote_matches:
            note("hash is %s, match_code is %s", match[0], match[1])
            if match[1] == 'R':
                _pull_doc (repo, match[2], remote_repo, remote_password)
                note("remote doc ID is %s", match[2])
                fp.write("pulled doc %s...<br>" % match[2])
    fp.close()


def synchronize (repo, response, params):

    def test_boolean_param (param):
        return ((param.lower() == "true") or
                (param.lower() == "on") or
                (param.lower() == "yes"))

    def _prompt_for_target(response, target="https://"):
        fp = response.open()
        fp.write('<html><head><title>Synchronize Two UpLib Repositories</title></head>\n')
        fp.write('<body bgcolor="%s">' % STANDARD_BACKGROUND_COLOR +
                 '<form action="/action/SynchronizeRepositories/synchronize" method=POST>'
                 '<p>URL of repository to synchronize with:<br>')
        fp.write('<input type=text name=repository value="%s" size=80>\n' % target)
        fp.write('<p>Password for remote repository:<br>')
        fp.write('<input type=password size=80 name=password value="">')
        fp.write('<p><input type=checkbox name=localchecked value=true checked>Push Local Docs to Remote Repository, by default')
        fp.write('<p><input type=checkbox name=remotechecked value=true>Pull Remote Docs to Local Repository, by default')
        fp.write('<p><input type=submit value="Show Differences" style="padding: 10px">')
        fp.write('</form></body></html>')
        fp.close()
        return

    repository_url = params.get('repository')
    if not repository_url:
        _prompt_for_target(response)
        return

    note("params are %s", params.items())

    local_checked = test_boolean_param(params.get("localchecked", "false"))
    remote_checked = test_boolean_param(params.get("remotechecked", "false"))

    # build a list of document fingerprints
    hash_dict = _build_hash_dict(repo)

    note("hash dict is %s", hash_dict)

    # check each fingerprint with remote repository
    remote_password = params.get("password", "")
    remote_matches = _check_hashes (hash_dict.keys(), repository_url, remote_password)
    note("remote_matches are %s", remote_matches)

    if remote_matches is None:
        response.error(HTTPCodes.INTERNAL_SERVER_ERROR, "Remote repository can't reply.")
        return

    fp = response.open()
    fp.write('<html><head><title>Differences:  %s and https://%s:%d/</title></head>\n' % (repository_url,
                                                                                          get_fqdn(), repo.port() - 1))
    if len(remote_matches) == 0:
        fp.write("<body>No differences.  The repositories are synchronized.</body>\n")
        fp.close()
        return

    remote_only = [item for item in remote_matches if item[1] == 'R']
    local_only = [item for item in remote_matches if item[1] == 'L']
    note("local_only is %s, remote_only is %s", local_only, remote_only)

    nrows = max(len(remote_only), len(local_only)) + 2
    fp.write('<body bgcolor="%s">\n' % STANDARD_BACKGROUND_COLOR)
    fp.write('<p><font size=+1><center><b>Differences between %s and %s</b></center><br><hr><p>\n' %
             (repository_url, "https://%s:%d/" % (get_fqdn(), repo.port() - 1)))
             
    fp.write('<form action="/action/SynchronizeRepositories/syncdocs" method=POST>\n' +
             '<input type=hidden name=repository value="%s">\n' % repository_url +
             '<input type=hidden name=password value="%s">\n' % remote_password)
    fp.write('<table width=100% border=0>\n' +
             '<tr><td><center><i>Remote only</i></center><br><hr>\n</td>' +
             '<td><center><i>Local only</i></center><br><hr>\n</td></tr>\n')

    fp.write("<tr><td>")
    for match in remote_only:
        title = ((len(match) > 3) and match[3]) or match[2]
        title = re.sub('`', ' ', title)
        fp.write('<input type=checkbox name=doc_id value="R%s" %s>%s ' % (match[2], (remote_checked and "checked") or "", title))
        fp.write('<a href="%s%s" target="_blank">(see)</a><br>\n' % (repository_url, _doc_show_URL(match[2])))
    fp.write('<p><center><input type=submit name="pull" value="Pull These Docs" style="padding: 10px">'
             '</center></td>\n')

    fp.write("<td>\n")
    for match in local_only:
        doc = hash_dict[match[0]]
        title = doc.get_metadata("title") or doc.id
        fp.write('<input type=checkbox name=doc_id value="L%s" %s>%s ' % (doc.id, (local_checked and "checked") or "", title))
        fp.write('<a href="%s" target="_blank">(see)</a><br>\n' % (_doc_show_URL(doc.id),))
    fp.write('<p><center><input type=submit name="push" value="Push These Docs" style="padding: 10px">'
             '</center></td>\n')
    fp.write("</tr></table><hr>"+
             '<center><input type=submit name="both" value="Synchronize both repositories" style="padding: 10px">'
             '</center></form>\n</body></html>\n')
    fp.close()
    return
