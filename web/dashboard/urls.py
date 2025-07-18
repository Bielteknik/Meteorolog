from django.urls import path
from . views import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
]

