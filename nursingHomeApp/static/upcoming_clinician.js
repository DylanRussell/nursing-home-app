$(document).ready(function(){
  var table = $('#upcoming').DataTable({
      "aaSorting": [],
      columnDefs: [
      { type: 'date-uk', targets: [2, 3, 4, 5] },
      { type: 'last-name', targets: [0] } //specify your date column number,starting from 0
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
});