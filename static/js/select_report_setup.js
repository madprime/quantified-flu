$(document).ready(function() { 

  console.log("hey");
  // Display setup for customization based on selection.
  $("#select-customize-report-setup").change(function () {
    $("#select-customize-report-setup option:selected" ).each(function() {
      var setup_id = this.value;
      var info_div_id = "#info-customize-report-setup-" + setup_id;
      $(".info-customize-report-setup:not(.d-none)").addClass("d-none");
      $(info_div_id).removeClass("d-none");
    });
  }).change();
})