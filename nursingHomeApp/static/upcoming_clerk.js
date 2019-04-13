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
      { type: 'date-uk', targets: [2, 3, 5, 6] }, //specify your date column number,starting from 0
      { type: 'last-name', targets: [0, 4] }
      ]
      });
  jQuery.extend(jQuery.fn.dataTableExt.oSort, {
    "date-uk-pre": function (a) {
      if (a == null || a == "") {
        return 0;
      }
    var ukDatea = a.split(' ')[0].split('/');
      return (ukDatea[2] + ukDatea[0] + ukDatea[1]) * 1;
    },
    "date-uk-asc": function (a, b) {
      return ((a < b) ? -1 : ((a > b) ? 1 : 0));
    },
    "date-uk-desc": function (a, b) {
      return ((a < b) ? 1 : ((a > b) ? -1 : 0));
    },

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
    $.ajax({url: "/submit/upcoming",
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
  })
  $("#floornum").change((function() {
    table.column(1).search($("#floornum option:selected").val(), true, false).draw();
  }));
  $("#clinicians").change((function() {
    table.search($("#clinicians option:selected").val()).draw();
  }));
});