$(document).ready(function() {

    $('.cooliframe').each(function(idx, elem){
        var $elem = $(elem);
        var srcRef = $elem.data("src");
        var resize = $elem.data("resize");
        var iframeDef = "<iframe width='100%' height='100%' src='" + srcRef + "'/>";
        $elem.append(iframeDef);
        $elem.css("overflow", "hidden");
        if(!!resize){
            $elem.css("resize", resize);
        }
    });

});
