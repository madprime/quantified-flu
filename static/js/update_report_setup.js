function deleteSymptom() {
    event.preventDefault();

    var symptom_item_id = this.id.split("-")[this.id.split("-").length - 1];
    var form_id = '#form-delete-setup-symptom-' + symptom_item_id;
    var li_item_id = '#tr-setup-symptom-item-' + symptom_item_id;
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

            // delete symptom item row
            $(li_item_id).remove();

            // delete category if now empty
            if (data.delete_category) {
                var cat_id = "#setup-symptom-category-" + data.delete_category;
                $(cat_id).remove();
                $("#form-row-category-ordering").replaceWith('<div class="alert alert-warning">Please reload form to edit category ordering.</div>')
            }

            // insert alphabetically into available symptom additions
            var options = $("#form-create-setup-symptom select option");
            var new_option_text = data.symptom_verbose + ' (' + data.category_name + ')';
            var new_option = '<option id="option-add-setup-symptom-' +
                data.symptom_id + '" value="' + data.symptom_id + '">' + new_option_text + '</option>';
            for (var i = 0; i < options.length; i++) {
                curr_text = options.eq(i).html();
                if (curr_text > new_option_text) {
                    options.eq(i).before(new_option);
                    break;
                } else if (i == options.length - 1) {
                    options.eq(i).after(new_option);
                }
            }
        }
    });

    return false;
};


function addSymptom() {
    event.preventDefault();

    var cat_name = this.id.split("-")[this.id.split("-").length - 1];
    var form_id = "#form-create-setup-symptom";
    $(form_id).onsubmit = function(event) {
        event.preventDefault();
        return false;
    }

    var url = "/report/ajax/create-setup-symptom";
    $.ajax({
        type: "POST",
        url: url,
        data: $(form_id).serialize(),
        success: function(data) {
            var div_id = "setup-symptom-category-" + data.symptom_item_category;

            var td_id = "td-delete-setup-symptom-" + data.symptom_item_id;
            var new_tr = '<tr id="tr-setup-symptom-item-' + data.symptom_item_id +
                '"><td>' + data.symptom_item_verbose +
                '</td><td id="' + td_id + '"></td></tr>';

            // add as new category section, if this is new.
            if (data.new_category) {
                $("#edit-symptom-categories").append('<div id="' + div_id + '"></div>');
                $("#" + div_id).append('<h4><span class="text-muted">Category: </span>' + data.symptom_item_category + '</h4>')
                $("#" + div_id).append('<table class="table table-sm table-hover" id="symptom-items-' +
                    data.symptom_item_category + '"><tbody></tbody></table>');
                $("#" + div_id + " table tbody").append(new_tr);
                $("#form-row-category-ordering").replaceWith('<div class="alert alert-warning">Categories have changed due to editing symptoms. Please save and reload this form to edit category ordering.</div>')
            } else {
                // insert alphabetically to existing category
                var cat_rows = $("#" + div_id + " table tbody").children();
                for (var i = 0; i < cat_rows.length; i++) {
                    var curr_text = cat_rows.eq(i).children().eq(0).html();
                    if (curr_text > data.symptom_item_verbose) {
                        cat_rows.eq(i).before(new_tr);
                        break;
                    } else if (i == cat_rows.length - 1) {
                        // new last item
                        cat_rows.eq(i).after(new_tr);
                    }
                }
            }

            var form_id = "form-delete-setup-symptom-" + data.symptom_item_id;
            $(".form-delete-symptom-item").first().clone()
                .appendTo("#" + td_id).attr('id', form_id)
                .attr('action', '/report/delete-setup-symptom/' + data.symptom_item_id);
            $("#" + form_id + " .delete-setup-symptom")
                .attr('id', 'btn-delete-setup-symptom-item-' + data.symptom_item_id)
                .click(deleteSymptom);

            // remove item from symptom addition dropdown
            var option_id = "option-add-setup-symptom-" + data.symptom_id;
            $("#" + option_id).remove();
        }
    });

    return false;
};


$(document).ready(function() {

    // Delete symptoms from setup via AJAX
    $(".delete-setup-symptom").click(deleteSymptom);

    // Add symptoms via AJAX
    $(".create-setup-symptom").click(addSymptom);

});
