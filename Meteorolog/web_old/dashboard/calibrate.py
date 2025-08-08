import cv2
import numpy as np
import json
import sys

# --- AYARLAR ---
# Çalışan RTSP URL'niz
RTSP_URL = "rtsp://admin:Ejder.25@192.168.1.50:554/Streaming/Channels/101"

# Kalibrasyon için kullandığınız referans cetvelinin gerçek yüksekliği (cm)
# Örneğin, cetvelin altındaki "0" işareti ile üstündeki "15" işareti arasını seçiyorsanız, bu değer 15.0 olmalı.
# Tüm cetveli (örneğin 250cm) referans alıyorsanız, daha hassas olur.
CETVEL_GERCEK_YUKSEKLIK_CM = 250.0 

# Kalibrasyon verilerinin kaydedileceği dosya
KALIBRASYON_DOSYASI = "kalibrasyon.json"

# --- DEĞİŞKENLER ---
kalibrasyon_noktalari = []

# --- FONKSİYON ---
def fare_tiklamasi(event, x, y, flags, param):
    """Fare tıklamalarını yakalamak için callback fonksiyonu."""
    global kalibrasyon_noktalari
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(kalibrasyon_noktalari) < 2:
            print(f"Nokta eklendi: ({x}, {y})")
            kalibrasyon_noktalari.append((x, y))

# --- ANA KOD ---
print("--- KAMERA KALİBRASYON ARACI ---")
print("Bu script, Django uygulamasının kullanacağı kalibrasyon dosyasını oluşturur.")
print("Lütfen açılacak pencerede SADECE CETVEL üzerinde iki noktaya tıklayın:")
print(f"1. TIKLAMA: Cetvelin alt referans noktası (Örn: 0 cm çizgisi)")
print(f"2. TIKLAMA: Cetvelin üst referans noktası (Örn: {CETVEL_GERCEK_YUKSEKLIK_CM} cm çizgisi)")

cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
if not cap.isOpened():
    print(f"HATA: Kamera akışına bağlanılamadı. RTSP URL'sini kontrol edin: {RTSP_URL}")
    sys.exit()

cv2.namedWindow('Kalibrasyon')
cv2.setMouseCallback('Kalibrasyon', fare_tiklamasi)

while len(kalibrasyon_noktalari) < 2:
    ret, frame = cap.read()
    if not ret:
        print("Hata: Kameradan kare okunamadı.")
        break
    
    # Kullanıcıya yardımcı olmak için talimatları ekrana yaz
    talimat1 = "1. Cetvelin ALT noktasina tikla"
    talimat2 = f"2. Cetvelin UST ({CETVEL_GERCEK_YUKSEKLIK_CM}cm) noktasina tikla"
    cv2.putText(frame, talimat1, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.putText(frame, talimat2, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Tıklanan noktaları göster
    for nokta in kalibrasyon_noktalari:
        cv2.circle(frame, nokta, 5, (0, 255, 0), -1)

    cv2.imshow('Kalibrasyon', frame)
    if cv2.waitKey(20) & 0xFF == ord('q'):
        cap.release()
        cv2.destroyAllWindows()
        print("İşlem iptal edildi.")
        sys.exit()

# Kalibrasyon tamamlandı, verileri hesapla ve kaydet
alt_nokta = kalibrasyon_noktalari[0]
ust_nokta = kalibrasyon_noktalari[1]

cetvel_piksel_yuksekligi = abs(alt_nokta[1] - ust_nokta[1])

if cetvel_piksel_yuksekligi == 0:
    print("HATA: Cetvel yüksekliği 0 piksel olamaz. Lütfen dikey olarak farklı noktalara tıklayın.")
    sys.exit()

# Bir pikselin kaç cm'ye denk geldiğini hesapla
cm_per_pixel = CETVEL_GERCEK_YUKSEKLIK_CM / cetvel_piksel_yuksekligi

kalibrasyon_verisi = {
    'alt_nokta': alt_nokta,
    'ust_nokta': ust_nokta,
    'cm_per_pixel': cm_per_pixel
}

with open(KALIBRASYON_DOSYASI, 'w') as f:
    json.dump(kalibrasyon_verisi, f, indent=4)
    
print("\nBAŞARILI!")
print(f"Kalibrasyon tamamlandı ve '{KALIBRASYON_DOSYASI}' dosyasına kaydedildi.")
print("Artık Django sunucusunu çalıştırabilirsiniz.")

cap.release()
cv2.destroyAllWindows()