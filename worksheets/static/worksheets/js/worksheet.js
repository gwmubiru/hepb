
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

	$http.get("/worksheets/pending_envelopes?sample_type="+st).success(function(data){
		$scope.pending_envelopes = data;
	});

	/*$http.get("/worksheets/pending_samples/").success(function(data){
		$scope.samples = data;
	});

	*/
	$http.get("/worksheets/pending_samples?repeat=1").success(function(data){
		$scope.repeat_samples = data;
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
			var append = (type=='sample')?"sample_search="+$scope.sample_search:"envelope_number="+$scope.envelope_number;
			$http.get("/worksheets/pending_samples?"+append).success(function(data){
				$scope.samples = data;
			});
		}
		
	}

	$scope.setSample = function($event, i){
		var keyCode = $event.which || $event.keyCode;
		if((keyCode == 13 && $scope.machine_type=='C') || $scope.machine_type!='C'){
			//$scope.selected_samples.push($scope.samples[i]);
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
			var next_index = Number(rack_index)+1;
			$("#racks"+next_index).focus();
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
				if($scope.selected_samples.indexOf(sample)==-1){
					$scope.selected_samples.push(sample);
					sample_obj.prop('checked', true);
				}
			}

			
		}

	}


}

app.controller(ctrller);