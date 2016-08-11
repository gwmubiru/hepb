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