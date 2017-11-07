
var app=angular.module('verify', [], function($interpolateProvider) {
        $interpolateProvider.startSymbol('<%');
        $interpolateProvider.endSymbol('%>');
    });

ctrller={};
ctrller.VerifyController = function($scope,$http){
	
	$scope.vdata = {};
	$scope.sample = {};

	$http.get("/samples/verify_envelope/"+envelope_id).success(function(data){
		console.log("we got this"+JSON.stringify(data));
		$scope.vdata=data;
		// $scope.sample=data[0];
		// $scope.nxt_sample=1;
		$scope.selectSample(sample_id)
		$('#gender').val($scope.sample.gender);
		$('#locator_category').val($scope.sample.locator_category);
		$('#facility_id').val($scope.sample.facility_id);
	});



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
	}


	$scope.selectSample = function(sample_id){
		for(var i in $scope.vdata){
			if(sample_id == $scope.vdata[i].sample_id ){
				$scope.sample = $scope.vdata[i];
				$scope.nxt_sample = parseInt(i)+1;
				break;
			}
		}
	}

}

app.controller(ctrller);