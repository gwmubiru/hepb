from typing import no_type_check
from django.http import request
from django.http.request import HttpHeaders
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from urllib.parse import urlencode
from django.http import JsonResponse, HttpResponse
import json
import requests
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User, auth
from backend.models import UserProfile
# Create your views here.

def redirect(request):

    baseurl = "http://10.200.254.40/oauth/authorize?client_id=8&redirect_url=http%3A%2F%2F10.200.254.78%3A9999%2Foauth%2Fcallback&response_type=code"

    return HttpResponseRedirect(baseurl)

def callback(request):

    url = 'http://10.200.254.40/oauth/token'
    payload = {'grant_type':'authorization_code','client_id':'8','client_secret':'kmQjYl13Gu4bvXubskegAJJaG1gBvfKVsrWVGR3s',
                    'redirect_url':'http://10.200.254.74:8080/oauth/callback','code':request.GET['code']}
    headers = {}
    response = requests.request("POST", url, headers=headers, data=payload)

    results =  json.loads(response.text)

    userid = results['user_id']

    profile = UserProfile.objects.filter(idp_key = userid).get()
    print(profile.user)
    print(profile.user.username)

    if profile is not None:
        user = User.objects.filter(id=profile.user.id).get()
        user = authenticate(id=profile.user.id)
        print(user)
        login(request, profile.user)
        #phone = profile.user.username
        return HttpResponseRedirect("http://10.200.254.74:8080/")
    else:
        print(profile)
    return HttpResponse(profile)
  
    # response = request.POST.get(url, form_params=form_params)
    # return JsonResponse(response['user_id'])
  
  
