from django.urls import path
from . import views


urlpatterns = [
    path('', views.home_page_view, name='home_page'),
    path('friends_list/', views.friends_list, name='friends_list')
]