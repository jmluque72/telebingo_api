$(document).ready(function() {
    var idmenu = $('#selected_menu').text().trim();
    if(idmenu.length != 0) {
        $(idmenu).addClass('active');
    }

    var idtab = $('#selected_tab').text().trim();
    if(idtab.length != 0) {
        $(idtab).removeClass('tab-inactiva');
        $(idtab).addClass('tab-activa');
    }

    setTimeout(function(){ $(".messages").remove(); }, 3000);

    var selects = $('select');
        selects.selectpicker({
    });
    selects.on('change', function(evt){
        $('select').selectpicker('refresh');
    });

    $('.dotted').on('input', function () {
        var value = $(this).val().split('.').join("");
       $(this).val(addThousandSeparator(value));
    });
});

$.fn.scrollBottom = function() {
  return $(document).height() - this.scrollTop() - this.height();
};

function isNumber(n) {
    return !isNaN(parseFloat(n)) && isFinite(n);
}

function addThousandSeparator(nStr)
{
	nStr += '';
	x = nStr.split(',');
	x1 = x[0];
	x2 = x.length > 1 ? ',' + x[1] : '';
	var rgx = /(\d+)(\d{3})/;
	while (rgx.test(x1)) {
		x1 = x1.replace(rgx, '$1' + '.' + '$2');
	}
	return x1 + x2;
}

$.fn.selectRange = function(start, end) {
    if(end === undefined) {
        end = start;
    }
    return this.each(function() {
        if('selectionStart' in this) {
            this.selectionStart = start;
            this.selectionEnd = end;
        } else if(this.setSelectionRange) {
            this.setSelectionRange(start, end);
        } else if(this.createTextRange) {
            var range = this.createTextRange();
            range.collapse(true);
            range.moveEnd('character', end);
            range.moveStart('character', start);
            range.select();
        }
    });
};