from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
from .models import Reading, AnomalyLog, SystemHealthLog
from django.forms.models import model_to_dict
import cv2
import numpy as np
import json
import threading
import time
import os
from django.conf import settings
from datetime import datetime

# --- GÖRÜNTÜ İŞLEME AYARLARI ---
RTSP_URL = "rtsp://admin:Ejder.25@192.168.1.50:554/Streaming/Channels/101"
KALIBRASYON_DOSYASI = "kalibrasyon.json"
lock = threading.Lock() # Kamera kaynağına aynı anda erişimi engellemek için

def dashboard_view(request):
    context = {
        'latest_reading': Reading.objects.first(),
        'recent_readings': Reading.objects.all()[:5],
    }
    return render(request, 'dashboard/dashboard.html', context)

def get_common_context():
    """Tüm sayfalarda ortak olan context verilerini döndürür."""
    return {
        'latest_health_log': SystemHealthLog.objects.first(),
    }

def kalibrasyon_verisi_yukle():
    """Kaydedilmiş kalibrasyon verisini dosyadan yükler."""
    try:
        with open(KALIBRASYON_DOSYASI, 'r') as f:
            data = json.load(f)
            data['alt_nokta'] = tuple(data['alt_nokta'])
            data['ust_nokta'] = tuple(data['ust_nokta'])
            return data
    except FileNotFoundError:
        return None
    except Exception:
        return None

def kar_seviyesini_bul_ve_ciz(frame, kalibrasyon):
    """Görüntüde kar seviyesini bulur, hesaplar ve görseli frame üzerine çizer."""
    if not kalibrasyon:
        cv2.putText(frame, "Kalibrasyon Gerekli!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame, 0.0

    alt_nokta = kalibrasyon['alt_nokta']
    ust_nokta = kalibrasyon['ust_nokta']
    
    # ROI (Region of Interest - İlgili Alan)
    x_orta = int(alt_nokta[0])
    roi_x1 = max(0, x_orta - 10)
    roi_x2 = min(frame.shape[1], x_orta + 10)
    roi_y1 = int(ust_nokta[1])
    roi_y2 = int(alt_nokta[1])

    if roi_y1 >= roi_y2 or roi_x1 >= roi_x2:
        cv2.putText(frame, "Gecersiz ROI", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame, 0.0
        
    cetvel_bolgesi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
    gray_roi = cv2.cvtColor(cetvel_bolgesi, cv2.COLOR_BGR2GRAY)
    blurred_roi = cv2.GaussianBlur(gray_roi, (5, 5), 0)

    parlaklik_esigi = 120
    kar_seviyesi_y_roi = blurred_roi.shape[0] -1
    for y in range(blurred_roi.shape[0] - 1, -1, -1):
        if np.mean(blurred_roi[y, :]) < parlaklik_esigi:
            kar_seviyesi_y_roi = y
            break
            
    kar_seviyesi_y = roi_y1 + kar_seviyesi_y_roi
    
    kar_yuksekligi_pixel = max(0, alt_nokta[1] - kar_seviyesi_y)
    kar_yuksekligi_cm = kar_yuksekligi_pixel * kalibrasyon['cm_per_pixel']

    # Görselleştirme
    cv2.line(frame, alt_nokta, ust_nokta, (255, 0, 0), 2)
    cv2.circle(frame, alt_nokta, 5, (0, 255, 0), -1)
    cv2.circle(frame, ust_nokta, 5, (0, 255, 0), -1)
    cv2.line(frame, (x_orta - 25, kar_seviyesi_y), (x_orta + 25, kar_seviyesi_y), (0, 255, 255), 2)
    sonuc_metni = f"Kar Yuksekligi: {kar_yuksekligi_cm:.1f} cm"
    cv2.putText(frame, sonuc_metni, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
    
    return frame, kar_yuksekligi_cm

def stream_camera():
    """Kamera akışını MJPEG formatında yield eden bir generator."""
    kalibrasyon = kalibrasyon_verisi_yukle()
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        # Kamera yoksa hata görseli oluştur
        hata_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(hata_frame, "Kamera Baglantisi Yok", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        ret, buffer = cv2.imencode('.jpg', hata_frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        return

    while True:
        with lock:
            ret, frame = cap.read()
        if not ret:
            time.sleep(1) # Tekrar denemeden önce bekle
            continue

        processed_frame, _ = kar_seviyesini_bul_ve_ciz(frame, kalibrasyon)
        
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        if not ret:
            continue
            
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    cap.release()

def video_feed_view(request):
    """Video akışını sunan view."""
    return StreamingHttpResponse(stream_camera(), content_type='multipart/x-mixed-replace; boundary=frame')

def snapshot_view(request):
    """Kameradan anlık bir görüntü alıp kaydeden view."""
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        return JsonResponse({'status': 'error', 'message': 'Kameraya bağlanılamadı.'}, status=500)
    
    with lock:
        ret, frame = cap.read()
    cap.release()

    if not ret:
        return JsonResponse({'status': 'error', 'message': 'Kameradan görüntü alınamadı.'}, status=500)

    kalibrasyon = kalibrasyon_verisi_yukle()
    processed_frame, kar_yuksekligi = kar_seviyesini_bul_ve_ciz(frame, kalibrasyon)
    
    # Dosyayı kaydet
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"snapshot_{timestamp}.jpg"
    
    # media/snapshots klasörünü oluştur (yoksa)
    save_path_dir = os.path.join(settings.MEDIA_ROOT, 'snapshots')
    os.makedirs(save_path_dir, exist_ok=True)
    
    save_path = os.path.join(save_path_dir, filename)
    cv2.imwrite(save_path, processed_frame)
    
    # URL'yi oluştur
    file_url = os.path.join(settings.MEDIA_URL, 'snapshots', filename).replace("\\", "/")

    return JsonResponse({
        'status': 'ok', 
        'message': f'Görüntü kaydedildi: {filename}',
        'url': file_url,
        'height': f'{kar_yuksekligi:.1f} cm'
    })


# --- Eski View Fonksiyonları (Aynı kalıyor) ---

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
        'anomaly_logs': AnomalyLog.objects.all()[:50]
    })
    return render(request, 'dashboard/anomalies.html', context)

def reports_view(request):
    dummy_reports = [
        {'name': 'Z_Report_2025-07-15.md', 'date': '15.07.2025 23:55', 'size': '15 KB'},
        {'name': 'Z_Report_2025-07-14.md', 'date': '14.07.2025 23:55', 'size': '12 KB'},
    ]
    context = get_common_context()
    context.update({
        'active_page': 'reports',
        'reports': dummy_reports
    })
    return render(request, 'dashboard/reports.html', context)

def settings_view(request):
    context = get_common_context()
    context.update({
        'active_page': 'settings'
    })
    return render(request, 'dashboard/settings.html', context)