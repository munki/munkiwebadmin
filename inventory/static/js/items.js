/*
    This script is used on the inventory/items route to handle loading the
    table data via json. It also formats the columns so each value as clickable
    original version by Joe Wollard; this version by Greg Neagle
*/

$(document).ready(function()
{
    // Perform the json call and format the results so that DataTables will
    // understand it.
    var process_json = function( sSource, aoData, fnCallback )
    {
        $.getJSON( sSource, function(json, status, jqXHR)
        {
            // update the count info badge
            $("#item-count-badge").text(json.length);

            // let datatables do its thing.
            fnCallback( {'aaData': json} );
        });
    }


    var version_count_template = function(name, version, count)
    {
        return "<a href='?name=" + encodeURIComponent(name) 
            + "&version=" + encodeURIComponent(version) + "'>" + version 
            + "<span class='badge badge-info pull-right'>" + count + "</span>"
            + "</a><br />";
    }


    var format_versions_column = function(data, type, rowObject)
    {
        out = ''
        for(var i = 0; i < data.length; i++)
        {
            var version = data[i]['version'],
                count = data[i]['count'];
            out += version_count_template(
                rowObject.name,
                version,
                count
            );
        }
        return out;
    }


    var format_name_column = function(data, type, rowObject)
    {
        return '<a href="?name=' + encodeURIComponent(data)
            + '">' + data + "</a>";
    }


    $("#inventory-items-table").dataTable({
        "sAjaxSource": window.location.href + ".json",
        "fnServerData": process_json,
        "iDisplayLength": 20,
        "sPaginationType": "bootstrap",
        "aLengthMenu": [[20, 50, -1], [20, 50, "All"]],
        "bStateSave": true,
        "bDeferRender": true,
        "aaSorting": [[4,'desc']],
        "aoColumns": [
            {'mData': 'name',
             'mRender': format_name_column
             },
            {'mData': 'versions',
             'mRender': format_versions_column
            }
        ]
    });
});