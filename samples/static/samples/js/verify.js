
var app=angular.module('verify', [], function($interpolateProvider) {
        $interpolateProvider.startSymbol('<%');
        $interpolateProvider.endSymbol('%>');
    });

ctrller={};
ctrller.VerifyController = function($scope,$http){
	
	$scope.vdata = {};
	$scope.sample = {};

	$http.get("/samples/verify_envelope/"+envelope_id).success(function(data){
		//console.log("we got this"+JSON.stringify(data));
		$scope.vdata=data;
		$scope.sample=data[0];
		$scope.nxt_sample=1;

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
				$scope.sample = $scope.vdata[$scope.nxt_sample];
				$scope.nxt_sample += 1;
			}else{
				alert("verifying failed");
				$scope.sample = $scope.vdata[($scope.nxt_sample-1)]
			}

			$("#success").css("display","block");

			setTimeout(function(){
				$("#success").slideUp( "slow");
			},1000);
		});
		return false;
	}

}

app.controller(ctrller);