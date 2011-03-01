//
// This file is part of the "UpLib 1.7.11" release.
// Copyright (C) 2003-2011  Palo Alto Research Center, Inc.
// 
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License along
// with this program; if not, write to the Free Software Foundation, Inc.,
// 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
//

var swirlimg = '<table width=100% height=100%><tr height=100%><td width=100% valign=center align=center>' +
               '<img width=24 height=24 src="/html/images/swirl.gif"></td></tr></table>';

//
// getPageSize()
// Returns array with page width, height and window width, height
// Core code from - quirksmode.com
// Edit for Firefox by pHaez
//
function getPageSize(){
    
    var xScroll, yScroll;
    
    if (window.innerHeight && window.scrollMaxY) {  
        xScroll = window.innerWidth + window.scrollMaxX;
        yScroll = window.innerHeight + window.scrollMaxY;
    } else if (document.body.scrollHeight > document.body.offsetHeight){ // all but Explorer Mac
        xScroll = document.body.scrollWidth;
        yScroll = document.body.scrollHeight;
    } else { // Explorer Mac...would also work in Explorer 6 Strict, Mozilla and Safari
        xScroll = document.body.offsetWidth;
        yScroll = document.body.offsetHeight;
    }
    
    var windowWidth, windowHeight;
    
    if (self.innerHeight) { // all except Explorer
        if(document.documentElement.clientWidth){
            windowWidth = document.documentElement.clientWidth; 
        } else {
            windowWidth = self.innerWidth;
        }
        windowHeight = self.innerHeight;
    } else if (document.documentElement && document.documentElement.clientHeight) { // Explorer 6 Strict Mode
        windowWidth = document.documentElement.clientWidth;
        windowHeight = document.documentElement.clientHeight;
    } else if (document.body) { // other Explorers
        windowWidth = document.body.clientWidth;
        windowHeight = document.body.clientHeight;
    }   
    
    // for small pages with total height less then height of the viewport
    if(yScroll < windowHeight){
        pageHeight = windowHeight;
    } else { 
        pageHeight = yScroll;
    }

    // for small pages with total width less then width of the viewport
    if(xScroll < windowWidth){  
        pageWidth = xScroll;        
    } else {
        pageWidth = windowWidth;
    }

    arrayPageSize = new Array(pageWidth,pageHeight,windowWidth,windowHeight) 
    return arrayPageSize;
}

function remove_alias (person_id, alias_name, reload_on_success) {
    // alert("removing alias " + alias_name + " for " + person_id);
    new Ajax.Request('/action/Person/remove_alias?person=' + person_id + '&alias=' + encodeURIComponent(alias_name), {
        method: 'get',
        onSuccess: function(response) {
            // alert("succeeded in removing '" + alias_name + "' as alias for " + person_id);
            if (reload_on_success) {
                document.location.reload();
            }
        },
        onFailure: function(response) {
            alert("failed to remove '" + alias_name + "' as alias for " + person_id);
        },
     })
}

function use_alias_as_name (person_id, alias_name, reload_on_success) {
    new Ajax.Request('/action/Person/use_alias_as_name?person=' + person_id + '&alias=' + encodeURIComponent(alias_name), {
        method: 'get',
        onSuccess: function(response) {
            // alert("succeeded in removing '" + alias_name + "' as alias for " + person_id);
            if (reload_on_success) {
                window.location=reload_on_success;
            }
        },
        onFailure: function(response) {
            alert("failed to set '" + alias_name + "' as name for " + person_id);
        },
     })
}

function add_alias (person_id, input_widget, evt, reload_on_success) {
    // alert("add_alias(" + person_id + ", " + input_widget + ", " + evt.charCode + ", " + evt.keyCode + ")");
    // in general, RETURN shows up as charCode 0 and keyCode 13
    if (evt && (evt.keyCode == 13)) {
        // alert("submitting alias " + input_widget.value + " to repository as alias for " + person_id);
        new Ajax.Request('/action/Person/add_alias?person=' + person_id + '&alias=' + encodeURIComponent(input_widget.value), {
            method: 'get',
            onSuccess: function(response) {
                    // alert("succeeded in adding '" + input_widget.value + "' as alias for " + person_id);
                    if (reload_on_success) {
                        document.location.reload();
                    }
                },
            onFailure: function(response) {
                    alert("failed to add '" + input_widget.value + "' as alias for " + person_id);
                },
            })
    }
}

function validate_data(d) {
    if (d.length == 0)
        return null;
    i = d.indexOf(':');
    if (i < 1)
        return null;
    name = d.substring(0, i);
    if ((i + 1) >= d.length)
        return null;
    return new Array(d.substring(0, i).strip(), d.substring(i+1, d.length).strip());
}

function add_metadata (person_id, name, value, reload_on_success) {
    new Ajax.Request('/action/Person/add_metadata?person=' + person_id
                     + '&name=' + encodeURIComponent(name)
                     + '&value=' + value, {
        method: 'get',
        onSuccess: function(response) {
                // alert("succeeded in adding '" + name + ": " + value + "' as metadata for " + person_id);
                if (reload_on_success) {
                    document.location.reload();
                }
            },
        onFailure: function(response) {
                alert("failed to add '" + name + ": " + value + "' as metadata for " + person_id);
            },
        })
}

function add_metadata_from_widget (person_id, input_widget, evt, reload_on_success) {
    // alert("add_metadata(" + person_id + ", " + input_widget + ", " + evt.charCode + ", " + evt.keyCode + ")");
    // in general, RETURN shows up as charCode 0 and keyCode 13
    if (evt && (evt.keyCode == 13)) {
        data = validate_data(input_widget.value);
        if (data != null) {
            add_metadata(person_id, data[0], encodeURIComponent(data[1]), reload_on_success);
        } else {
            alert("format of metadata values must be NAME : VALUE");
        }
    }
}

function remove_metadata (person_id, name, value, reload_on_success) {
    new Ajax.Request('/action/Person/remove_metadata?person=' + person_id
                     + '&name=' + encodeURIComponent(name)
                     + '&value=' + encodeURIComponent(value), {
        method: 'get',
        onSuccess: function(response) {
            if (reload_on_success) {
                document.location.reload();
            }
        },
        onFailure: function(response) {
            alert("failed to remove '" + name + ": " + value + "' as metadata for " + person_id);
        },
    });
}

function add_note (person_id, input_widget_name, reload_on_success) {
    // in general, RETURN shows up as charCode 0 and keyCode 13
    input_widget = $(input_widget_name);
    new Ajax.Request('/action/Person/add_note?person=' + person_id
                     + '&note=' + encodeURIComponent(input_widget.value), {
        method: 'get',
        onSuccess: function(response) {
                // alert("succeeded in adding '" + input_widget.value + "' as note for " + person_id);
                if (reload_on_success) {
                    document.location.reload();
                }
            },
        onFailure: function(response) {
                alert("failed to add '" + input_widget.value + "' as note for " + person_id + ":\n" + response.responseText);
            },
     });
}

function add_alias_string (person_id, alias_name, reload_on_success) {
    // alert("submitting alias " + alias_name + " to repository as alias for " + person_id);
    new Ajax.Request('/action/Person/add_alias?person=' + person_id + '&alias=' + encodeURIComponent(alias_name), {
        method: 'get',
        onSuccess: function(response) {
            // alert("succeeded in adding '" + input_widget.value + "' as alias for " + person_id);
            if (reload_on_success) {
                document.location.reload();
                }
            },
        onFailure: function(response) {
            alert("failed to add '" + alias_name + "' as alias for " + person_id);
        },
    })
}

function add_email_address (person_id, address, reload_on_success) {
    // alert("submitting alias " + alias_name + " to repository as alias for " + person_id);
    new Ajax.Request('/action/Person/add_email_address?person=' + person_id + '&address=' + encodeURIComponent(address), {
        method: 'get',
        onSuccess: function(response) {
            // alert("succeeded in adding '" + address + "' as email address for " + person_id);
            if (reload_on_success) {
                document.location.reload();
                }
            },
        onFailure: function(response) {
            alert("failed to add '" + address + "' as email address for " + person_id);
        },
    })
}

function remove_author (doc_id, person_id, reload_on_success) {
    // alert("removing author " + person_id + " for document " + doc_id);
    new Ajax.Request('/action/Person/remove_author?person=' + person_id + '&doc_id=' + doc_id, {
        method: 'get',
        onSuccess: function(response) {
            // alert("succeeded in removing '" + person_id + "' as author of " + doc_id);
            if (reload_on_success) {
                document.location.reload();
            }
        },
        onFailure: function(response) {
            alert("failed to remove '" + person_id + "' as author of " + doc_id);
        },
     })
}

function remove_photo (pic_id, person_id, reload_on_success) {
    // alert("removing photo " + pic_id + " for person " + person_id);
    new Ajax.Request('/action/Person/remove_photo?person=' + person_id + '&doc_id=' + pic_id, {
        method: 'get',
        onSuccess: function(response) {
            // alert("succeeded in removing '" + pic_id + "' as picture of " + person_id);
            if (reload_on_success) {
                document.location.reload();
            }
        },
        onFailure: function(response) {
            alert("failed to remove '" + pic_id + "' as picture of " + person_id);
        },
     })
}

function show_excluded (person_id, etype) {
    // alert("removing photo for person " + person_id);
    new Ajax.Request('/action/Person/show_excluded?person=' + person_id + "&etype=" + etype, {
        method: 'get',
        onSuccess: function(response) {
            document.location.reload();
        },
        onFailure: function(response) {
            alert("failed to show excluded " + etype + " for " + person_id);
        },
     })
}

function remove_canonical_photo (person_id, reload_on_success) {
    // alert("removing photo for person " + person_id);
    new Ajax.Request('/action/Person/remove_canonical_photo?person=' + person_id, {
        method: 'get',
        onSuccess: function(response) {
            // alert("succeeded in removing the photo of " + person_id);
            if (reload_on_success) {
                document.location.reload();
            }
        },
        onFailure: function(response) {
            alert("failed to remove the photo of " + person_id);
        },
     })
}

function make_canonical_photo (pic_id, person_id, reload_on_success) {
    // alert("making photo " + pic_id + " the canonical picture for person " + person_id);
    new Ajax.Request('/action/Person/make_canonical_photo?person=' + person_id + '&doc_id=' + pic_id, {
        method: 'get',
        onSuccess: function(response) {
            // alert("succeeded in making '" + pic_id + "' the photo for " + person_id);
            if (reload_on_success) {
                document.location.reload();
            }
        },
        onFailure: function(response) {
            alert("failed to make '" + pic_id + "' the photo for " + person_id);
        },
     })
}

var reload_on_picture_hide = false;

function hide_picture_search_panel () {
    var p = $("PicturesSearchPanel");
    p.style.visibility = "hidden";
    p.innerHTML = '';
    if (reload_on_picture_hide) {
        document.location.reload();
    }
}

function reveal_picture_search_panel (person_id) {
    var p = $("PicturesSearchPanel");
    var t = $("topleveltable");
    var sizes = getPageSize();

    // show the panel
    p.innerHTML = swirlimg;
    p.style.left = t.offsetLeft;
    p.style.top = t.offsetTop;
    p.style.width = t.offsetWidth;
    p.style.height = sizes[1];
    p.style.visibility = "visible";
    reload_on_picture_hide = false;

    // start the search going
    new Ajax.Request('/action/Person/look_for_pictures?headless=true&person=' + person_id, {
        method: 'get',
        onSuccess: function(response) {
            p.innerHTML = '<table width=100%><tr><td align=right><input type=button value="Hide picture search" ' +
                          'onclick="javascript:hide_picture_search_panel();"></td></tr><tr><td>' +
                          response.responseText + '</td></tr></table>';
        },
        onFailure: function(response) {
            alert("Couldn't do Yahoo! search for pictures");
            hide_picture_search_panel()
        },
     })
}

function add_as_picture(person_id, pic_title, photo_url, backup_photo_url, category, button_id, make_canonical) {

    if (category && (category.length > 0))
        category_tag = "&md-categories=" + encodeURIComponent(category);
    else
        category_tag = "";
    $(button_id).innerHTML = 'Saving...';
    new Ajax.Request('/action/UploadDocument/add?wait=true&no-redirect=true'
                     + '&URL='  + encodeURIComponent(photo_url) + category_tag
                     + '&md-title=' + encodeURIComponent(pic_title), {
        method: 'get',
        onSuccess: function(response) {
            $(button_id).innerHTML = 'Saved.';
            doc_id = response.responseText;
            if (make_canonical) {
                make_canonical_photo(doc_id, person_id, true);
            } else {
                reload_on_picture_hide = true;
            }
        },
        onFailure: function(response) {
            $(button_id).innerHTML = "<font color=orange>Couldn't add picture " + photo_url + " to repository</font>;"
                + " trying Yahoo! thumnail instead...";
            new Ajax.Request('/action/UploadDocument/add?wait=true&no-redirect=true'
                             + '&URL='  + encodeURIComponent(backup_photo_url) + category_tag
                             + '&md-title=' + encodeURIComponent(pic_title), {
                method: 'get',
                onSuccess: function(response) {
                    $(button_id).innerHTML = 'Saved.';
                    doc_id = response.responseText;
                    if (make_canonical) {
                        make_canonical_photo(doc_id, person_id, true);
                    } else {
                        reload_on_picture_hide = true;
                    }
                },
                onFailure: function(response) {
                    $(button_id).innerHTML = "<font color=red>Couldn't add picture to repository: "
                       + response.responseText + "</font>";
                },
             })

            $(button_id).innerHTML = "<font color=red>Couldn't add picture " + photo_url + " to repository</font>";
        },
     })
}

function email_addresses (doc_id, person_id, action) {
    sectionname = doc_id + "-authoredemailaddresses";
    emailbutton = doc_id + "-emailbutton";
    if (action == 'show') {
        // alert("finding email addresses in " + doc_id + " for person " + person_id);
        new Ajax.Request('/action/Person/look_for_email_address?person=' + person_id + '&doc_id=' + doc_id, {
            method: 'get',
            onSuccess: function(response) {
                // alert("length of responseText is " + response.responseText.length);
                if (response.responseText.length > 0) {
                    lines = response.responseText.split(/\r?\n/);
                    //alert("lines for " + sectionname + " are " + lines);
                    if (lines.length > 0) {
                        newhtml = "<ul>\n";
                        for (addr in Iterator(lines)) {
                            newhtml += "<li>";
                            newhtml = newhtml + "<tt>" + addr[1] + "</tt>";
                            newhtml = (newhtml +
                                       ' <input type=button value="Add this email address" ' + 
                                       'onclick="javascript:add_email_address(\'' +
                                       person_id +
                                       "', '" +
                                       addr[1] +
                                       "', true);" +
                                       '"></li>');
                        }
                        newhtml = newhtml + "</ul>\n";
                        // alert("newhtml for " + sectionname + " is " + newhtml);
                    } else {
                        newhtml = '<i>No email addresses found.</i>';
                    }
                    $(sectionname).innerHTML = newhtml;
                    $(emailbutton).innerHTML = '<input type=button value="Hide email addresses" ' + 
                    'onclick="javascript:email_addresses(\'' + doc_id + "', '" + person_id + "', 'hide');" + '">';
                } else {
                    $(sectionname).innerHTML = '<small>(no email addresses found)</small>';
                    $(emailbutton).innerHTML = '';
                }
            },
            onFailure: function(response) {
                alert("failed to find email addresses in '" + doc_id + "' for " + person_id + ":\n" + response.responseText);
            },
         })
    } else {
         $(sectionname).innerHTML = '';
         $(emailbutton).innerHTML = '<input type=button value="Look for email address" ' + 
         'onclick="javascript:email_addresses(\'' + doc_id + "', '" + person_id + "', 'show');" + '">';
    }
}
