
var app=angular.module('authorize', [], function($interpolateProvider) {
        $interpolateProvider.startSymbol('<%');
        $interpolateProvider.endSymbol('%>');
    });

ctrller={};
ctrller.authorizeController = function($scope,$http){
	$scope.selected_samples = [];

	$http.get("/worksheets/pending_samples/").success(function(data){
		$scope.samples = data;
	});

	$http.get("/worksheets/pending_samples?repeat=1").success(function(data){
		$scope.repeat_samples = data;
	});

	$scope.getSamples = function($event){
		var keyCode = $event.which || $event.keyCode;
		if(keyCode == 13){
			$http.get("/worksheets/pending_samples?envelope_number="+$scope.envelope_number+"").success(function(data){
				$scope.samples = data;
			});
		}
		
	}

	$scope.setSample = function($event, i){
		var keyCode = $event.which || $event.keyCode;
		if(keyCode == 13){
			$scope.selected_samples.push($scope.samples[i]);
			var next_index = Number(i)+1;
			$("#sss"+next_index).focus();
		}		
	}

	$scope.setRepeatSample = function($event, i){
		var keyCode = $event.which || $event.keyCode;
		if(keyCode == 13){
			$scope.selected_samples.push($scope.repeat_samples[i]);
			var next_index = Number(i)+1;
			$("#rrr"+next_index).focus();
		}		
	}

/*
	$scope.saveVerification= function(){
		//console.log(JSON.stringify($scope.sample));
		//$http.get("/samples/save_verify?"+$scope.sample)

		 $http({method:'GET',url:"/samples/save_verify",params:$scope.sample}).success(function(response) {
			//console.log(response);
			if(response=="saved"){
				//alert("Saved successfully");
				if($scope.nxt_sample>=$scope.vdata.length){
					$("#completed").css("display","block");
				}else{
					$scope.sample = $scope.vdata[$scope.nxt_sample];
					$scope.nxt_sample += 1;
					$("#success").css("display","block");

					setTimeout(function(){
						$("#success").slideUp( "slow");
					},400);
				}				
			}else{
				alert("verifying failed");
				$scope.sample = $scope.vdata[($scope.nxt_sample-1)]
			}

					});
		return false;
	}*/

}

app.controller(ctrller);