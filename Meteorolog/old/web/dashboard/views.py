from django.shortcuts import render
from .models import Reading, AnomalyLog, SystemHealthLog

def get_common_context():
    """Tüm sayfalarda ortak olan context verilerini döndürür."""
    return {
        'latest_health_log': SystemHealthLog.objects.first(),
    }

def dashboard_view(request):
    context = get_common_context()
    context.update({
        'active_page': 'dashboard',
        'latest_reading': Reading.objects.first(),
        'recent_readings': Reading.objects.all()[:5],
    })
    return render(request, 'dashboard/dashboard.html', context)

def anomalies_view(request):
    context = get_common_context()
    context.update({
        'active_page': 'anomalies',
        'anomaly_logs': AnomalyLog.objects.all()[:50] # Örnek olarak son 50 anomali
    })
    return render(request, 'dashboard/anomalies.html', context)

def reports_view(request):
    # Bu kısımda normalde dosya sisteminden raporları listeleme mantığı olur.
    # Şimdilik statik veri ile gösteriyoruz.
    dummy_reports = [
        {'name': 'Z_Report_2025-07-15.md', 'date': '15.07.2025 23:55', 'size': '15 KB'},
        {'name': 'Z_Report_2025-07-14.md', 'date': '14.07.2025 23:55', 'size': '12 KB'},
        {'name': 'Z_Report_2025-07-13.md', 'date': '13.07.2025 23:55', 'size': '14 KB'},
    ]
    context = get_common_context()
    context.update({
        'active_page': 'reports',
        'reports': dummy_reports
    })
    return render(request, 'dashboard/reports.html', context)

def settings_view(request):
    # Bu kısım ileride bir ayar modeli veya Django formu ile yönetilebilir.
    context = get_common_context()
    context.update({
        'active_page': 'settings'
    })
    return render(request, 'dashboard/settings.html', context)