/*
    Warranty scripts by Adam Reed <adam.reed@anu.edu.au>
*/

function get_warranty_status(serial) {
       $.ajaxSetup({
         beforeSend: function() {
           $('#warranty_status_checking').show();
           $('#warranty_status').hide();
         },
         complete: function(){
               $('#warranty_status_checking').hide();
               $('#warranty_status').show();
         },
         success: function() {}
       });

  $.ajax({
      url: '/report/warranty/' + serial,
      type: 'GET',
      dataType: 'html',
      success: function(data, textStatus, xhr) {
                $('#warranty_status').html(data)
      },
      error: function(xhr, textStatus, errorThrown) {
                $('#warranty_status').html('Problem retrieving warranty status')
      }
  });
}

function postwith (to,params) {
  var hiddenForm = document.createElement("form");
  hiddenForm.method="post";
  hiddenForm.action = to;
  hiddenForm.target = "_blank";
  for (var key in params) {
    if(params.hasOwnProperty(key)) {
      var hiddenField = document.createElement("input");
      hiddenField.setAttribute("type", "hidden");
      hiddenField.setAttribute("name", key);
      hiddenField.setAttribute("value", params[key]);
      hiddenForm.appendChild(hiddenField);
    }
  }
  document.body.appendChild(hiddenForm);
  hiddenForm.submit();
  document.body.removeChild(hiddenForm);
}