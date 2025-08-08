from django.urls import path
from . import views
from . import api

urlpatterns = [
    # Web arayüzü URL'leri
    path('', views.dashboard_view, name='dashboard'),
    path('anomalies/', views.anomalies_view, name='anomalies'),
    path('reports/', views.reports_view, name='reports'),
    path('settings/', views.settings_view, name='settings'),
    
    # Kamera URL'leri
    path('video_feed/', views.video_feed_view, name='video_feed'),
    path('snapshot/', views.snapshot_view, name='snapshot'),
    
    # API URL'i
    path('api/readings/', api.ReadingCreateAPIView.as_view(), name='api-reading-create'),
]