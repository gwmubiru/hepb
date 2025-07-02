
var app=angular.module('worksheet_samples', [], function($interpolateProvider) {
        $interpolateProvider.startSymbol('<%');
        $interpolateProvider.endSymbol('%>');
    });

ctrller={};
ctrller.worksheetSamplesController = function($scope,$http){
	$scope.Math = window.Math;
	$scope.selected_samples = [];
	$scope.pending_envelopes = [];
	$scope.current_env = '';
	$scope.instrument_ids = [];
	$scope.scanned_racks = [];
	$scope.repeat_samples_count = "";
	$scope.pending_samples_count = "";
	$scope.still_loading = true;

	$http.get("/worksheets/pending_envelopes?sample_type="+st).success(function(data){
		$scope.pending_envelopes = data;
	});

	/*$http.get("/worksheets/pending_samples/").success(function(data){
		$scope.samples = data;
	});

	*/
	$http.get("/worksheets/pending_samples?repeat=1&sample_type="+st).success(function(data){
		$scope.repeat_samples = data;
	});

	$http.get("/worksheets/pending_samples?stats=1&sample_type="+st).success(function(data){
		$scope.repeat_samples_count = "("+data.repeat_samples_count+")";
		$scope.pending_samples_count = "("+data.pending_samples_count+")";
		$scope.still_loading = false;
	});

	$scope.getEnvSamples = function(pk){		
		$scope.current_env = pk;
		$scope.envelope_number = "";
		$http.get("/worksheets/pending_samples?env_pk="+pk).success(function(data){
			$scope.samples = data;
		});
		$(".env_list").removeClass("active");
		$('#env'+pk).addClass('active');
	}



	$scope.getSamples = function($event,type){
		var keyCode = $event.which || $event.keyCode;
		if(keyCode == 13){
			var append = (type=='sample'||type=='repeat_sample')?"sample_search="+$scope.sample_search:"envelope_number="+$scope.envelope_number;
			if(type=='repeat_sample'){
				append = "repeat_sample_search="+$scope.repeat_sample_search
			}
			$http.get("/worksheets/pending_samples?"+append).success(function(data){
				if (type=='repeat_sample'){
					$scope.repeat_samples = data;
				}else{
					$scope.samples = data;
				}
			});
		}
		
	}

	$scope.setSample = function($event, i){
		var keyCode = $event.which || $event.keyCode;
		if((keyCode == 13 && $scope.machine_type=='C') || $scope.machine_type!='C'){
			//$scope.selected_samples.push($scope.samples[i]);
			if($scope.machine_type=='C'){
				st = setInstrumentID($("#sss"+i));
				if(st==false){ return false;}
			}
			selectSample($scope.samples[i], $("#sss"+i));
			var next_index = Number(i)+1;
			$("#sss"+next_index).focus();
		}		
	}

	$scope.setRepeatSample = function($event, i){
		//console.log("in in in");
		var keyCode = $event.which || $event.keyCode;
		if((keyCode == 13 && $scope.machine_type=='C') || $scope.machine_type!='C'){
			//console.log($scope.repeat_samples[i]);
			if($scope.machine_type=='C'){
				st = setInstrumentID($("#rrr"+i));
				if(st==false){ return false;}
			}
			selectSample($scope.repeat_samples[i], $("#rrr"+i), true);
			//$scope.selected_samples.push($scope.repeat_samples[i]);
			var next_index = Number(i)+1;
			$("#rrr"+next_index).focus();
		}		
	}

	$scope.setAll = function(){
		if($("#check_all").prop('checked')==true){
			for(var i in $scope.samples){ 
				selectSample($scope.samples[i], $("#sss"+i));
			}
		}
		
	}

	$scope.removeSelectedSample = function(sample){
		//console.log("gonna delete"+i);
		index = $scope.selected_samples.indexOf(sample);
		if(index!=-1){
			$scope.selected_samples.splice(index, 1);
		}
	}

	$scope.nextRack = function($event, rack_index){
		var keyCode = $event.which || $event.keyCode;
		if(keyCode == 13){
			var rack_now = $("#racks"+rack_index);
			if($scope.scanned_racks.indexOf(rack_now.val())==-1){
				$scope.scanned_racks.push(rack_now.val());
				var next_index = Number(rack_index)+1;
				$("#racks"+next_index).focus();
			}else{
				alert("Rack "+rack_now.val()+" already scanned");
				rack_now.val('');
				return false;
			}
			
		}		

	}

	selectSample = function(sample, sample_obj, repeat=false){
		if((sample.in_worksheet!=true || repeat==true) && sample.sample_type==$scope.w_sample_type){
			//console.log("re"+$scope.sample_limit+" kde"+$scope.selected_samples.length);
			if($scope.selected_samples.length==$scope.sample_limit){
				alert("required number reached");
				sample_obj.prop('checked', false);
				return false;
			}else{
				if(sampleExists(sample)==false){
					$scope.selected_samples.push(sample);
					sample_obj.prop('checked', true);
				}
			}

			
		}

	}

	setInstrumentID = function(sample){
		var exists = 0;
		$.ajax({
			'async': false,
			'type': "GET",
			'global': false,
			'url': "/worksheets/get_instrument_id/?instrument_id="+sample.val(),
			'success': function (data) { exists = data; }
		});

		if(exists==1){
			alert(sample.val()+" exists in the database");
			sample.val("");
			ret = false;
		}else if($scope.instrument_ids.indexOf(sample.val()) != -1){
			alert(sample.val()+" already scanned");
			sample.val("");
			ret =false;
		}else{
			$scope.instrument_ids.push(sample.val());
			ret = true;
		}

		return ret;		
	}

	sampleExists = function(sample){
		ret = false;
		for(var i in $scope.selected_samples){ 
			var s = $scope.selected_samples[i];
			if (sample.form_number==s.form_number){
				ret = true;
				break;
			}
		}
		return ret;

	}


}

app.controller(ctrller);