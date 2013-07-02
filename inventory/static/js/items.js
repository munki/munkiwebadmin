/*
    This script is used on the inventory/items route to handle loading the
    table data via json. It also formats the columns so each value as clickable
    original version by Joe Wollard; this version by Greg Neagle
*/

$(document).ready(function()
{
    var version_count_template = function(name, version, count)
    {
        return "<a href='?name="
            + encodeURIComponent(name) 
            + "&version=" + encodeURIComponent(version)
            + "'>" + version + "<span class='badge badge-info pull-right'>"
            + count + "</span></a><br />";
    }

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


    var format_name_column = function(rowObject)
    {
        var name = rowObject.aData['name'];
        return '<a href="?name=' + encodeURIComponent(name)
            + '">' + name + "</a>";
    }


    var format_versions_column = function(rowObject)
    {
        var v = rowObject.aData['versions'],
        out = ''
        for(var i = 0; i < v.length; i++)
        {
            var version = v[i]['version'],
                count = v[i]['count'];
            out += version_count_template(
                rowObject.aData['name'],
                version,
                count
            );
        }
        return out;
    }


    $("#inventory-items-table").dataTable({
        "sAjaxSource": window.location.href + ".json",
        "fnServerData": process_json,
        "iDisplayLength": 20,
        "sPaginationType": "bootstrap",
        "aLengthMenu": [[20, 50, -1], [20, 50, "All"]],
        "bStateSave": true,
        "aaSorting": [[4,'desc']],
        "aoColumns": [
            {'mData': 'name'},
            {'mData': 'versions'}
        ],
        "aoColumnDefs": [
            {
                'fnRender': format_name_column,
                'aTargets': [0]
            },
            {
                'fnRender': format_versions_column,
                'aTargets': [1]
            }
        ]
    });
});