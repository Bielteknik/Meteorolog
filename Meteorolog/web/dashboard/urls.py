from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('anomalies/', views.anomalies_view, name='anomalies'),
    path('reports/', views.reports_view, name='reports'),
    path('settings/', views.settings_view, name='settings'),

    # Kamera entegrasyonu için yeni URL'ler
    path('video_feed/', views.video_feed_view, name='video_feed'),
    path('snapshot/', views.snapshot_view, name='snapshot'),
]