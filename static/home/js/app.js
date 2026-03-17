function removeItem(that){
  var r=confirm("Are you sure?");
  if(r){
    that.parentNode.parentNode.removeChild(that.parentNode);
  }
}

function removeItemHTML(){
  return "<label class='rm_item' onClick='removeItem(this)'>X</label>";
}

function generalSelect(name,items,label,slcted_item,other_options){

	var slct="<select name='"+name+"' "+other_options+">";
	slct+="<option selected value=''>"+label+"</option>";
	for(var i in items){
		if(i==slcted_item){
			slct+="<option selected value='"+i+"'>"+items[i]+"</option>";
		}else{
			slct+="<option value='"+i+"'>"+items[i]+"</option>";
		}
	}
	return slct+"</select>";
}


function setLikeRadio(item,clss){
  if(item.checked){
    items=document.querySelectorAll(clss);
    for(var i in items){
      if(items[i]!=item){
        items[i].checked=false;
        }
    }
  }
}


function windPop(link) {
  window.open(link,"zzz","width=1100,height=1000,menubar=no,resizable=yes,scrollbars=yes");
}

function pad(str, len, pad, dir) {
  var STR_PAD_LEFT = 1;
  var STR_PAD_RIGHT = 2;
  var STR_PAD_BOTH = 3;

    if (typeof(len) == "undefined") { var len = 0; }
    if (typeof(pad) == "undefined") { var pad = ' '; }
    if (typeof(dir) == "undefined") { var dir = STR_PAD_RIGHT; }

    if (len + 1 >= str.length) {

        switch (dir){

            case STR_PAD_LEFT:
                str = Array(len + 1 - str.length).join(pad) + str;
            break;

            case STR_PAD_BOTH:
                var right = Math.ceil((padlen = len - str.length) / 2);
                var left = padlen - right;
                str = Array(left+1).join(pad) + str + Array(right+1).join(pad);
            break;

            default:
                str = str + Array(len + 1 - str.length).join(pad);
            break;

        } // switch

    }

    return str;

}

function future_date(string_date){
  var now = new Date();
  var string_s = strtotime(string_date);
  var now_s = now.getTime();
  return string_s>now_s;
}

function strtotime(string_date){
  var date_obj = new Date(string_date+" 00:00:00");
  return date_obj.getTime();
}