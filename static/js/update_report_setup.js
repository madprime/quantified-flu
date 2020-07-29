console.log($(".delete-setup-symptom"));

$(document).ready(function() { 
    console.log($(".delete-setup-symptom"));

    // Delete symptoms from setup via AJAX
    $(".delete-setup-symptom").click(function() {
        event.preventDefault();

        var symptom_item_id = this.id.split("-")[this.id.split("-").length - 1];
        var form_id = '#form-delete-setup-symptom-' + symptom_item_id;
        var li_item_id = '#li-setup-symptom-item-' + symptom_item_id;
        $(form_id).onsubmit = function(event) {
            event.preventDefault();
            return false;
        }

        var url = "/report/ajax/delete-setup-symptom/" + symptom_item_id;

        $.ajax({
            type: "POST",
            url: url,
            data: $(form_id).serialize(),
            success: function(data) {
                $(li_item_id).remove();
                if (data.delete_category) {
                    var cat_id = "#setup-symptom-category-" + data.delete_category;
                    $(cat_id).remove();
                }
            }
        });

        return false;
    });
});
