
var app=angular.module('verify', [], function($interpolateProvider) {
        $interpolateProvider.startSymbol('<%');
        $interpolateProvider.endSymbol('%>');
    });

ctrller={};
ctrller.VerifyController = function($scope,$http){
	
	$scope.vdata = {};
	$scope.sample = {};
	$scope.current_index =0;
	
	$http.get("/samples/verify_envelope/"+envelope_id).success(function(data){
		$scope.vdata=data;
		$scope.selectSample(sample_id);
		$scope.patHist();		
	});



	$scope.saveVerification= function(){
		if($scope.sample.accepted=='0'){
			$scope.sample.rejection_reason_id = $('#rejection_reason_id').val();
		}

		 $http({method:'GET',url:"/samples/save_verify",params:$scope.sample}).success(function(response) {
			if(response=="saved"){
				$scope.sample = $scope.vdata[$scope.nxt_sample];
				$scope.move();
				$("#success").css("display","block");
				setTimeout(function(){
					$("#success").slideUp( "slow");
				},1000);		
			}else{
				alert("verifying failed, reason:"+response);
				$scope.sample = $scope.vdata[$scope.current_index];
			}
		});
	}

	$scope.skip = function(){
		$scope.sample = $scope.vdata[$scope.nxt_sample];
		$scope.move();
	}

	$scope.move = function(){
		if($scope.nxt_sample==0){
			//$('#myModal').modal('show');
			 window.location.href = "/samples/search/?search_val="+$scope.sample.envelope_number+"&approvals=1&env_complete=1"
		}
		$scope.vdata[$scope.current_index].current = '';
		$scope.vdata[$scope.nxt_sample].current = 'active';
		$scope.current_index = $scope.nxt_sample;
		$scope.nxt_sample += 1;
		$scope.nxt_sample = $scope.nxt_sample==$scope.vdata.length?0:$scope.nxt_sample;
		$scope.patHist();

		//console.log("next sample:"+$scope.nxt_sample)
	}


	$scope.selectSample = function(sample_id){
		$scope.vdata[$scope.current_index].current = '';
		for(var i in $scope.vdata){
			if(sample_id == $scope.vdata[i].sample_id ){
				$scope.vdata[i].current = 'active'; 
				$scope.sample = $scope.vdata[i];
				$scope.current_index = i;
				$scope.nxt_sample = parseInt(i)+1;
				$scope.nxt_sample = $scope.nxt_sample==$scope.vdata.length?0:$scope.nxt_sample;
				//console.log("next index:-"+$scope.nxt_sample);
				break;
			}
		}
		$scope.patHist();
	}

	$scope.patHist = function(){
		$scope.patient_history=[];
		$http.get("/samples/patient_history/"+$scope.sample.facility_id+"/?art_number="+$scope.sample.art_number).success(function(data){
			$scope.patient_history = data;
		});		
	}

}

app.controller(ctrller);