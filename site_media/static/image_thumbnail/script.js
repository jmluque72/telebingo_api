$(document).ready(function() {
    function readURL(input) {
        // Actualizar la imagen cuando el usuario cambia el archivo

        if (input.files && input.files[0]) {
            var reader = new FileReader();
            var img = $(input).parents('.thumbnail-group').find('img')[0];
            var width = $(input).data('width');
            var height = $(input).data('height');

            var span = $('<span class="close">&times;</span>');
            span.on('click', function() {
                $(img).attr('src', 'http://www.placehold.it/'+parseInt(width)+'x'+parseInt(height));
                $(img).attr('width', '').attr('height', '');
                $(img).val('');
                $(this).remove();
            });

            reader.onload = function (e) {
                $(img).attr('src', e.target.result);
                $(img).attr('width', width);
                $(img).attr('height', height);
                span.insertBefore(img);
            };

            reader.readAsDataURL(input.files[0]);
        }
    }

    $('.image_thumbnail').change(function(){
        readURL(this);
    });

});
