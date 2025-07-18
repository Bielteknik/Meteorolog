from django.shortcuts import render
from .models import Reading, AnomalyLog, SystemHealthLog

def dashboard_view(request):
    # 1. En son ölçümü al (ordering sayesinde ilk kayıt en sonuncudur)
    latest_reading = Reading.objects.first()

    # 2. Son 5 ölçüm kaydını al
    recent_readings = Reading.objects.all()[:5]

    # 3. En son sistem sağlığı logunu al
    latest_health_log = SystemHealthLog.objects.first()

    # 4. Şablona gönderilecek verileri bir sözlükte topla
    context = {
        'latest_reading': latest_reading,
        'recent_readings': recent_readings,
        'latest_health_log': latest_health_log,
    }

    # 5. Verileri 'dashboard/dashboard.html' şablonuna gönder ve sayfayı oluştur
    return render(request, 'dashboard/dashboard.html', context)