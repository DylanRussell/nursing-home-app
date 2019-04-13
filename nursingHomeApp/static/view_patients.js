$(document).ready(function(){
    var table = $('#patients').DataTable({
        "aaSorting": [],
        columnDefs: [
        { type: 'last-name', targets: [4] }
        ]
        });
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
    $("#floornum").change((function() {
      table.column(2).search($("#floornum option:selected").val(), true, false).draw();
    }));
});