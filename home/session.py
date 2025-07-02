from django.shortcuts import render
from django.contrib.auth import logout


def login(request):
	return render(request, 'home/login.html')


def logoutnow(request):
	logout(request)
	return render(request, 'home/login.html')