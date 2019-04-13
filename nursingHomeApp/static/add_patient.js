$(document).ready(function(){
    $('#priorVisit, #lastVisit, #admittance').datepicker();
    $('#skilledVisits').prop('disabled', true);
    $('#status').change(function(){
    if ($('#status').val() == '2') {
        $('#skilledVisits').prop('disabled', false);
    } else {
        $('#skilledVisits').prop('disabled', true);
    }
    });
    $('form').submit(function(e) {
      $(':disabled').each(function(e) {
          $(this).removeAttr('disabled');
      });
    });
});