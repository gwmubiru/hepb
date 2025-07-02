from django.urls import path

from . import views

urlpatterns = [
    path("redirect", views.redirect, name="redirect"),
    path("callback", views.callback, name="callback"),
]