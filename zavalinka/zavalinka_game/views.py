from http.client import HTTPResponse
from django.shortcuts import render

from django.http import HttpResponse

# Create your views here.


def home_page_view(request):
    return render(request, "zavalinka_game/home_page.html")