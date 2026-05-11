from django.urls import path
from ContactBook import views
 
urlpatterns = [
    path('', views.index, name='home'),
]
