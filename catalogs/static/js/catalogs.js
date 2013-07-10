// Javascript for catalogs views

$(document).ready(function() {
   $('#catalog_items').dataTable({
        "sDom": "<'row'<'span6'l><'span6'f>r>t<'row'<'span6'i><'span6'p>>",
        "bPaginate": false,
        "sScrollY": "480px",
        "bScrollCollapse": true,
        "bInfo": false,
        "bFilter": false,
        "bStateSave": true,
        "aaSorting": [[0,'asc']]
    });
} );

function getCatalogItem(catalog_name, catalog_index, item_name, item_version)     {
    var catalogItemURL = '/catalog/' + catalog_name + '/' + catalog_index + '/';
    $.get(catalogItemURL, function(data) {
        $('#catalog_item_detail').html(data);
    });
    $('.catalog_item[name="' + item_name + '"]').addClass('selected');
    $('.catalog_item[name!="' + item_name + '"]').removeClass('selected');
}
