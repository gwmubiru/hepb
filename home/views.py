from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login

# Create your views here.
@login_required
def home(request):
	return render(request, 'home/index.html')


def login_page(request):
	return render(request, 'home/login.html')

def login_attempt(request):
	error_message = "incorrect username or password"
	username = request.POST['username']
	password = request.POST['password']
	user = authenticate(username=username, password=password)
	if user is not None:
		if user.is_active:
			login(request, user)
			return redirect('/')
		else:
			return render(request, 'home/login.html', {'error_message': error_message, })
	else:
		return render(request, 'home/login.html', {'error_message': error_message, })
		# Return an 'invalid login' error message.