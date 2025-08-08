from django.urls import path
from . import views
from . import api

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('video_feed/', views.video_feed_view, name='video_feed'),
    path('snapshot/', views.snapshot_view, name='snapshot'),
    path('api/readings/', api.ReadingCreateAPIView.as_view(), name='api-reading-create'),
]