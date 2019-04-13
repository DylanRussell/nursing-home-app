$(document).ready(function(){
  $(".radio").bootstrapSwitch({
    'onText': 'MD',
    'offText': 'APRN'
  });
  $('.datepicker').datepicker({
    'endDate': '0d'
  })
  var table = $('#upcoming').DataTable({
      "aaSorting": [],
      columnDefs: [
      { orderDataType: 'dom-date', type: 'date', targets: [2] },
      { type: 'last-name', targets: [0, 1] },
      { orderDataType: 'dom-bool', type: 'boolean', targets: [3, 4, 5]}
      ]
      });
  $.fn.dataTable.ext.order['dom-date'] = function  ( settings, col )
    {
        return this.api().column( col, {order:'index'} ).nodes().map( function ( td, i ) {
            return $('input', td).val();
        });
    }
  $.fn.dataTable.ext.order['dom-bool'] = function  ( settings, col )
    {
        return this.api().column( col, {order:'index'} ).nodes().map( function ( td, i ) {
            return $('input', td).is(':checked');
        });
    }
  jQuery.extend(jQuery.fn.dataTableExt.oSort, {
    "last-name-pre": function (a) {
      if (a == null || a == "") {
        return 0;
      }
      var lastName = a.split(/\s+/)[1].toLowerCase();
      return lastName
    },
    "last-name-asc": function (a, b) {
      return ((a < b) ? -1 : ((a > b) ? 1 : 0));
    },
    "last-name-desc": function (a, b) {
      return ((a < b) ? 1 : ((a > b) ? -1 : 0));
    }
  });
  $('#submitform').click(function() {
    var data = table.$('input').serialize();
    $.ajax({url: "/prior",
            data: data,
            method: 'POST',
            success: function(result){
              if (Object.keys(result).length != 0) {
                for (var key in result){
                  $("#" + key).parent().append("<p class='help-block' style='color:#a94442'>" + result[key] + "</p>");
                }
              } else {
                location.reload();
              }
            }
          });
        });
});