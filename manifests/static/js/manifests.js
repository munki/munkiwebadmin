/* Javascript for manifests/index template */

$(document).ajaxSend(function(event, xhr, settings) {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    var cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))){
        // Only send the token to relative URLs i.e. locally.
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});

$(document).ready(function(){
    $('#manifest_list_table').dataTable({
        "sDom": "<'row'<'span6'l><'span6'f>r>t<'row'<'span6'i><'span6'p>>",
        "bPaginate": false,
        "sScrollY": "480px",
        "bScrollCollapse": true,
        "bInfo": false,
        "bFilter": false,
        "bStateSave": true,
        "aaSorting": [[0,'asc']]
    });
    $('a.manifest').click(function(){
        var manifest_name = $(this).attr('id');
        getManifestDetail(manifest_name);
    });
});

function deleteManifest() {
  var manifest_name = $('.manifest_name').attr('id');
  location.href='/manifest/delete/' + manifest_name.replace(/\//g, ':');
}

function cleanDetailPane() {
  // unbind any existing event handlers for the detail pane
    $('.editable').off('dblclick');
    $('.lineitem_delete').off('click');

    // destroy sortability for existing elements
    //$('.catalogs_section').sortable('destroy');
    //$('.included_manifests_section').sortable('destroy');
    //$('.section').sortable('destroy');
    
    // clear detail pane
    // $('#detail').html('<div></div>')
}

function getManifestDetail(manifest_name) {
    if (inEditMode) {
        if (! confirm('Discard current changes?')) {
            event.preventDefault();
            return;
        }
        inEditMode = false;
        $(window).unbind("beforeunload");
    }
    if (!manifest_name) {
        var manifest_name = $('.manifest_name').attr('id');
    };
    $("#imgProgress").show();
    cleanDetailPane();
    // get new detail for the pane
    var manifestURL = '/manifest/detail/' + manifest_name.replace(/\//g, ':');
    $.get(manifestURL, function(data) {
        $('#detail').html(data);
        $('.edit').click(function(){
            makeEditableItems(manifest_name);
        });
        $("#imgProgress").hide();
    });
    $('.manifest[id="' + manifest_name + '"]').addClass('selected');
    $('.manifest[id!="' + manifest_name + '"]').removeClass('selected');
    $('#delete_manifest').removeClass('disabled');
    //$('.lineitem_delete').on('click', function() {    
    //      var r = confirm("Really delete " + manifest_name + "?");
    //});
    
    //location.hash = "/" + manifest_name;
    event.preventDefault();
}

var autocomplete_data = {};
var inEditMode = false;
function makeEditableItems(manifest_name) {
    $("#imgProgress").show();
    // get data for use in autocomplete
    var source_url = "/manifest/json/autocomplete/"
                     + manifest_name.replace(/\//g, ':');
    $.getJSON(source_url, function(data) {
        autocomplete_data = data;
        $("#imgProgress").hide();
    });
    // make sections sortable and drag/droppable
    $('.catalogs_section').sortable();
    $('.included_manifests_section').sortable();
    $('.section').sortable({
        connectWith: '.section'
    });
    //replace <a> links with 'editable' divs
    $('.lineitem').children($('a')).each(function(){
        var item = "<div class='editable'>" + $(this).parent().attr('id') + "</div>";
        $(this).replaceWith(item);
    });
    $('.lineitem').append("<a href='#' class='btn btn-danger btn-mini lineitem_delete'><i class='icon-minus icon-white'></i><a>");
    $('.editable').on('dblclick', function() {
        makeEditableItem(manifest_name, $(this));
    });
    $('.lineitem_delete').on('click', function() {
      if ($(this).parent().attr('id')) {    
        var r = confirm("Really delete " + $(this).parent().attr('id') + " from " + $(this).parent().parent().attr('id') + "?");
        if (r == true){ $(this).parent().remove(); };
      } else {
          $(this).parent().remove();
      }
    });
    $('.section_label').append("<a class='btn btn-success btn-mini add_item' href='#'><i class='icon-plus icon-white'></i></a>");
    $('.add_item').click(function() {
        var list_item = $("<li class='lineitem'><div class='editable'></div><a href='#' class='btn btn-danger btn-mini lineitem_delete'><i class='icon-minus icon-white'></i><a></li>");
        $(this).parent().siblings($('ul')).append(list_item);
        makeEditableItem(manifest_name, list_item.children(".editable"));
    });
    $('.edit').val('Save').unbind('click').click(function() {
        getManifestDetailFromDOMAndSave();
    });
    $('#save_and_cancel').append("<input type='button' class='cancel btn' value='Cancel' onClick='cancelEdit()'></input>");
    $(window).bind('beforeunload', function(){
        return "Changes will be lost!";
    });
    inEditMode = true;
}

function updateLineItem(item) {
    var text_value = item.val();
    if (text_value.length) {
        item.parent().attr('id', text_value);
        var new_div = $("<div class='editable'>" + text_value + "</div>")
        item.replaceWith(new_div);
    } else {
        item.parent().remove();
    }
}

function makeEditableItem(manifest_name, editable_div) {
    // commit any existing active lineiteminput
    $('.lineiteminput').each(function(){updateLineItem($(this))});

    var text_value = editable_div.text();
    var input_box = $("<input type='text' id='" + text_value + "' class='lineiteminput' value='" + text_value + "' />");
    var grandparent_id = editable_div.parent().parent().attr('id');
    var kind = 'items';
    if (grandparent_id == 'catalogs') {
      kind = 'catalogs';
    } else if (grandparent_id == 'included_manifests') {
      kind = 'manifests';
    }
    editable_div.replaceWith(input_box);
    input_box.autocomplete({
        source: autocomplete_data[kind],
        minLength: 1,
        delay: 0,
    })
    input_box.focus();
    input_box.bind('keyup', function(event) {
        if (event.which == '13' || event.which == '9') {
            event.preventDefault();
            updateLineItem($(this));
        } else if (event.which == '27') {
            event.preventDefault();
            $(this).val($(this).attr('id'));
            updateLineItem($(this));
        }
    });
}

function cancelEdit() {
    inEditMode = false;
    $(window).unbind("beforeunload");
    getManifestDetail();
}

function getManifestSectionArray(section_name) {
    // gets array elements from manifest section
    // returns an array
    // section_name is the JQuery class descriptor
    the_array = [];
    $(section_name).children($('li')).each(function(){
        var item = $(this).attr('id');
        if (item) { the_array.push(item); };
    });
    return the_array;
}

function getManifestDetailFromDOMAndSave() {
    // reads elements from the DOM to build up a JSON object
    // describing the manifest post-edit
    // then POSTs to server
    
    //
    $("#imgProgress").show();
    
    //unbind beforeunload
    inEditMode = false;
    $(window).unbind("beforeunload");
    
    // commit any existing active lineiteminput
    $('.lineiteminput').each(function(){updateLineItem($(this))});
    
    var manifest = {};
    var manifest_name = $('.manifest_name').attr('id');
    $('#manifest_detail').children($('manifest_section')).children($('ul')).each(function() {
        section_name = $(this).attr('id');
        if (section_name) {
          manifest[section_name] = getManifestSectionArray('#' + section_name);
        }
    });
    var postdata = JSON.stringify(manifest)
    var postURL = '/manifest/detail/' + manifest_name.replace(/\//g, ':');
    //alert(postdata);
    //console.log(postdata);
    $.ajax({
      type: 'POST',
      url: postURL,
      data: postdata,
      success: function(data) {
        //alert("SUCCESS: " + data);
        getManifestDetail();
        //$("#imgProgress").hide();
      },
      error: function(jqXHR, textStatus, errorThrown) {
        $("#imgProgress").hide();
        alert("ERROR: " + textStatus + "\n" + errorThrown);
      },
      dataType: 'json'
    });
}
