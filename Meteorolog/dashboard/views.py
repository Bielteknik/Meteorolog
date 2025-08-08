from django.shortcuts import render
from django.http import StreamingHttpResponse, JsonResponse
from .models import Reading, SystemHealthLog, Setting
import cv2
import numpy as np
import json
import threading
import time
import os
from django.conf import settings
from datetime import datetime

KALIBRASYON_DOSYASI = "kalibrasyon.json"
lock = threading.Lock()

def get_rtsp_url():
    """Veritabanından kamera ayarlarını alıp RTSP URL'sini oluşturur."""
    try:
        user = Setting.objects.get(key='RTSP_USER').value
        password = Setting.objects.get(key='RTSP_PASSWORD').value
        ip = Setting.objects.get(key='RTSP_IP').value
        port = Setting.objects.get(key='RTSP_PORT').value
        channel = Setting.objects.get(key='RTSP_CHANNEL').value
        return f"rtsp://{user}:{password}@{ip}:{port}/Streaming/Channels/{channel}"
    except Setting.DoesNotExist:
        return None

def dashboard_view(request):
    # HATA DÜZELTİLDİ: Olmayan 'get_common_context' fonksiyonu çağrısı kaldırıldı.
    # Context sözlüğü doğrudan burada oluşturuluyor.
    context = {
        'latest_reading': Reading.objects.first(),
        'recent_readings': Reading.objects.all()[:5],
    }
    return render(request, 'dashboard/dashboard.html', context)

def kalibrasyon_verisi_yukle():
    try:
        with open(KALIBRASYON_DOSYASI, 'r') as f: return json.load(f)
    except: return None

def kar_seviyesini_bul_ve_ciz(frame, kalibrasyon):
    if not kalibrasyon:
        cv2.putText(frame, "Kalibrasyon Gerekli!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame, 0.0
    alt_nokta, ust_nokta = tuple(kalibrasyon['alt_nokta']), tuple(kalibrasyon['ust_nokta'])
    x_orta = int(alt_nokta[0])
    roi_y1, roi_y2 = int(ust_nokta[1]), int(alt_nokta[1])
    if roi_y1 >= roi_y2: return frame, 0.0
    cetvel_bolgesi = frame[roi_y1:roi_y2, max(0, x_orta - 10):min(frame.shape[1], x_orta + 10)]
    blurred_roi = cv2.GaussianBlur(cv2.cvtColor(cetvel_bolgesi, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    
    # Gradient tabanlı kenar tespiti (daha sağlam bir yöntem)
    y_roi = np.argmax(np.mean(np.gradient(blurred_roi.astype(float), axis=0), axis=1))
    
    kar_seviyesi_y = roi_y1 + y_roi
    kar_yuksekligi_pixel = max(0, alt_nokta[1] - kar_seviyesi_y)
    kar_yuksekligi_cm = kar_yuksekligi_pixel * kalibrasyon['cm_per_pixel']
    cv2.line(frame, alt_nokta, ust_nokta, (255, 0, 0), 2)
    cv2.line(frame, (x_orta - 25, kar_seviyesi_y), (x_orta + 25, kar_seviyesi_y), (0, 255, 255), 2)
    cv2.putText(frame, f"Yukseklik: {kar_yuksekligi_cm:.1f} cm", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
    return frame, kar_yuksekligi_cm

def stream_camera():
    RTSP_URL = get_rtsp_url()
    kalibrasyon = kalibrasyon_verisi_yukle()
    if not RTSP_URL:
        hata_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(hata_frame, "Kamera Ayarlari Eksik!", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, buffer = cv2.imencode('.jpg', hata_frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        return

    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        hata_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(hata_frame, "Kamera Baglantisi Yok", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, buffer = cv2.imencode('.jpg', hata_frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        cap.release()
        return

    while True:
        with lock: ret, frame = cap.read()
        if not ret: time.sleep(1); continue
        processed_frame, _ = kar_seviyesini_bul_ve_ciz(frame, kalibrasyon)
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        if not ret: continue
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    cap.release()

def video_feed_view(request):
    return StreamingHttpResponse(stream_camera(), content_type='multipart/x-mixed-replace; boundary=frame')

def snapshot_view(request):
    RTSP_URL = get_rtsp_url()
    if not RTSP_URL: return JsonResponse({'status': 'error', 'message': 'Kamera ayarları bulunamadı.'}, status=500)
    
    cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
    if not cap.isOpened(): return JsonResponse({'status': 'error', 'message': 'Kameraya bağlanılamadı.'}, status=500)
    with lock: ret, frame = cap.read()
    cap.release()
    if not ret: return JsonResponse({'status': 'error', 'message': 'Kameradan görüntü alınamadı.'}, status=500)

    kalibrasyon = kalibrasyon_verisi_yukle()
    processed_frame, kar_yuksekligi = kar_seviyesini_bul_ve_ciz(frame, kalibrasyon)
    
    filename = f"snapshot_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
    save_path_dir = os.path.join(settings.MEDIA_ROOT, 'snapshots')
    os.makedirs(save_path_dir, exist_ok=True)
    cv2.imwrite(os.path.join(save_path_dir, filename), processed_frame)
    file_url = os.path.join(settings.MEDIA_URL, 'snapshots', filename).replace("\\", "/")

    return JsonResponse({'status': 'ok', 'message': f'Görüntü kaydedildi: {filename}', 'url': file_url, 'height': f'{kar_yuksekligi:.1f} cm'})