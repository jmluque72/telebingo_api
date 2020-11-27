$(document).ready(function() {
    function update(select){
        var type = select.val();
        var text = select.closest(".row").find('input[data-prize=text]');
        var value = select.closest(".row").find('input[data-prize=value]');

        $(value).removeAttr('required');
        $(text).removeAttr('required');
        if (type == 0) {
            value.show();
            $(value).attr('required', 'requred');
            text.hide();
        } else if (type == 1) {
            text.hide();
            value.hide();
        } else {
            text.show();
            $(text).attr('required', 'requred');
            value.hide();
        }
    }

    $('select[data-prize=type]').each(function(){
        $(this).selectpicker().on('changed.bs.select', function (e) {
            update($(this));
        });
        update($(this));
    });
});
