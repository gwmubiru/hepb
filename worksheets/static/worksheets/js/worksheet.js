
var app=angular.module('worksheet_samples', [], function($interpolateProvider) {
        $interpolateProvider.startSymbol('<%');
        $interpolateProvider.endSymbol('%>');
    });

ctrller={};
ctrller.worksheetSamplesController = function($scope,$http){
	$scope.selected_samples = [];

	$http.get("/worksheets/pending_samples/").success(function(data){
		$scope.samples = data;
	});

	$http.get("/worksheets/pending_samples?repeat=1").success(function(data){
		$scope.repeat_samples = data;
	});

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

}

app.controller(ctrller);