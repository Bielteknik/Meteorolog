import cv2
import numpy as np
import json

# --- AYARLAR ---
# Bir önceki koddan aldığınız çalışan RTSP URL'niz
RTSP_URL = "rtsp://admin:Ejder.25@192.168.1.50:554/Streaming/Channels/101"

# Eşel cetvelinin gerçek yüksekliği (cm)
CETVEL_GERCEK_YUKSEKLIK_CM = 15.0

# Kalibrasyon verilerinin kaydedileceği dosya
KALIBRASYON_DOSYASI = "kalibrasyon.json"

# --- DEĞİŞKENLER ---
kalibrasyon_noktalari = []
kalibrasyon_verisi = None

# --- FONKSİYONLAR ---

def fare_tiklamasi(event, x, y, flags, param):
    """Fare tıklamalarını yakalamak için callback fonksiyonu."""
    global kalibrasyon_noktalari
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(kalibrasyon_noktalari) < 2:
            print(f"Nokta eklendi: ({x}, {y})")
            kalibrasyon_noktalari.append((x, y))

def kalibrasyon_verisi_yukle():
    """Kaydedilmiş kalibrasyon verisini dosyadan yükler."""
    try:
        with open(KALIBRASYON_DOSYASI, 'r') as f:
            data = json.load(f)
            # JSON'dan gelen listeleri NumPy dizisine çevir
            data['alt_nokta'] = np.array(data['alt_nokta'])
            data['ust_nokta'] = np.array(data['ust_nokta'])
            print("Kalibrasyon verisi başarıyla yüklendi.")
            return data
    except FileNotFoundError:
        print("Kalibrasyon dosyası bulunamadı. Lütfen kalibrasyon yapın.")
        return None
    except Exception as e:
        print(f"Kalibrasyon verisi yüklenirken hata oluştu: {e}")
        return None

def kar_seviyesini_bul(frame, kalibrasyon):
    """Görüntüde kar seviyesini tespit eder."""
    alt_nokta = kalibrasyon['alt_nokta']
    ust_nokta = kalibrasyon['ust_nokta']

    # Sadece cetvelin olduğu dikey alanı (ROI - Region of Interest) alalım
    # Genişliği 10 piksel olarak alalım (cetvelin x koordinatı etrafında)
    x_orta = int(alt_nokta[0])
    roi_x1 = max(0, x_orta - 5)
    roi_x2 = min(frame.shape[1], x_orta + 5)
    
    # y koordinatları, cetvelin altından üstüne doğru olmalı
    roi_y1 = int(ust_nokta[1])
    roi_y2 = int(alt_nokta[1])

    cetvel_bolgesi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
    
    # Gri tonlamaya çevir ve bulanıklaştır (gürültüyü azaltmak için)
    gray_roi = cv2.cvtColor(cetvel_bolgesi, cv2.COLOR_BGR2GRAY)
    blurred_roi = cv2.GaussianBlur(gray_roi, (5, 5), 0)

    # Kar genellikle parlak, cetvel ise daha koyu renktedir.
    # Aşağıdan yukarıya doğru tarayarak parlaklıktaki ani düşüşü arayalım.
    # Eşik değeri (threshold) aydınlatma koşullarına göre ayarlamanız gerekebilir.
    parlaklik_esigi = 100  # 0-255 arası bir değer. Ortamınıza göre ayarlayın.
    
    kar_seviyesi_y = roi_y2 # Başlangıçta kar yok, en altta varsayalım

    # Cetvel bölgesini aşağıdan yukarıya (görüntüde y değeri büyükten küçüğe) tara
    for y in range(blurred_roi.shape[0] - 1, -1, -1):
        # O satırdaki piksellerin ortalama parlaklığı
        ortalama_parlaklik = np.mean(blurred_roi[y, :])
        if ortalama_parlaklik < parlaklik_esigi:
            # Parlaklık eşiğin altına düştü, burası muhtemelen karın bittiği yer.
            # ROI koordinatını ana görüntü koordinatına çevir
            kar_seviyesi_y = roi_y1 + y
            break
            
    return kar_seviyesi_y

# --- ANA KOD ---

# Önce kaydedilmiş bir kalibrasyon var mı diye kontrol et
kalibrasyon_verisi = kalibrasyon_verisi_yukle()

cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
if not cap.isOpened():
    print("Hata: Kamera akışına bağlanılamadı.")
    exit()

cv2.namedWindow('Kar Yuksekligi Olcumu')

if not kalibrasyon_verisi:
    # KALİBRASYON MODU
    print("\n--- KALİBRASYON MODU ---")
    print("Lütfen önce cetvelin EN ALT (0 cm) noktasına, sonra EN ÜST (250 cm) noktasına tıklayın.")
    cv2.setMouseCallback('Kar Yuksekligi Olcumu', fare_tiklamasi)
    
    while len(kalibrasyon_noktalari) < 2:
        ret, frame = cap.read()
        if not ret:
            print("Kare okunamadı.")
            break
        
        # Kullanıcıya yardımcı olmak için talimatları ekrana yaz
        talimat_metni = "1- Cetvelin en ALTINA tikla. 2- Cetvelin en USTUNE tikla."
        cv2.putText(frame, talimat_metni, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Tıklanan noktaları göster
        for nokta in kalibrasyon_noktalari:
            cv2.circle(frame, nokta, 5, (0, 255, 0), -1)

        cv2.imshow('Kar Yuksekligi Olcumu', frame)
        if cv2.waitKey(20) & 0xFF == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            exit()
            
    # Kalibrasyon tamamlandı, verileri hesapla ve kaydet
    alt_nokta = kalibrasyon_noktalari[0]
    ust_nokta = kalibrasyon_noktalari[1]
    
    # y eksenindeki piksel farkı
    cetvel_piksel_yuksekligi = abs(alt_nokta[1] - ust_nokta[1])
    
    if cetvel_piksel_yuksekligi == 0:
        print("Hata: Cetvel yüksekliği 0 piksel olamaz. Lütfen tekrar deneyin.")
        exit()

    cm_per_pixel = CETVEL_GERCEK_YUKSEKLIK_CM / cetvel_piksel_yuksekligi

    kalibrasyon_verisi = {
        'alt_nokta': alt_nokta,
        'ust_nokta': ust_nokta,
        'cm_per_pixel': cm_per_pixel
    }

    with open(KALIBRASYON_DOSYASI, 'w') as f:
        # NumPy dizilerini listeye çevirerek JSON'a kaydedilebilir hale getir
        data_to_save = kalibrasyon_verisi.copy()
        data_to_save['alt_nokta'] = list(data_to_save['alt_nokta'])
        data_to_save['ust_nokta'] = list(data_to_save['ust_nokta'])
        json.dump(data_to_save, f)
        
    print("Kalibrasyon tamamlandı ve 'kalibrasyon.json' dosyasına kaydedildi.")
    cv2.setMouseCallback('Kar Yuksekligi Olcumu', lambda *args : None) # Callback'i devre dışı bırak


# ÖLÇÜM MODU
print("\n--- ÖLÇÜM MODU ---")
print("Çıkmak için 'q' tuşuna basın.")
while True:
    ret, frame = cap.read()
    if not ret:
        print("Akıştan kare okunamadı.")
        break

    # Kar seviyesini bul
    kar_seviyesi_y = kar_seviyesini_bul(frame, kalibrasyon_verisi)

    # Kar yüksekliğini hesapla
    alt_nokta_y = kalibrasyon_verisi['alt_nokta'][1]
    kar_yuksekligi_pixel = alt_nokta_y - kar_seviyesi_y
    
    # Negatif değerleri engelle
    kar_yuksekligi_pixel = max(0, kar_yuksekligi_pixel) 
    
    kar_yuksekligi_cm = kar_yuksekligi_pixel * kalibrasyon_verisi['cm_per_pixel']

    # --- Görselleştirme ---
    # Kalibrasyon noktalarını ve cetvel çizgisini çiz
    alt_p = tuple(kalibrasyon_verisi['alt_nokta'])
    ust_p = tuple(kalibrasyon_verisi['ust_nokta'])
    cv2.line(frame, alt_p, ust_p, (255, 0, 0), 2)
    cv2.circle(frame, alt_p, 5, (0, 255, 0), -1)
    cv2.circle(frame, ust_p, 5, (0, 255, 0), -1)

    # Kar seviyesi çizgisini çiz
    kar_seviyesi_x = alt_p[0]
    cv2.line(frame, (kar_seviyesi_x - 20, kar_seviyesi_y), (kar_seviyesi_x + 20, kar_seviyesi_y), (0, 255, 255), 2)

    # Sonucu ekrana yazdır
    sonuc_metni = f"Kar Yuksekligi: {kar_yuksekligi_cm:.1f} cm"
    cv2.putText(frame, sonuc_metni, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
    
    cv2.imshow('Kar Yuksekligi Olcumu', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()