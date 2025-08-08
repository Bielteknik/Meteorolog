import cv2

# Kendi RTSP URL'nizi buraya yapıştırın
# Yüksek çözünürlük için ana akışı (101) veya
# daha düşük çözünürlük/daha akıcı görüntü için alt akışı (102) kullanabilirsiniz.
rtsp_url = "rtsp://admin:Ejder.25@192.168.1.64:554/Streaming/Channels/102"

# Video yakalama nesnesini oluştur
# cv2.CAP_FFMPEG parametresi bazı durumlarda bağlantı kararlılığını artırabilir.
cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)

# Bağlantının başarılı olup olmadığını kontrol et
if not cap.isOpened():
    print("Hata: Kamera akışına bağlanılamadı.")
    print("Lütfen RTSP URL'sini, kullanıcı adı/şifreyi ve IP adresini kontrol edin.")
    exit()

print("Kamera akışına başarıyla bağlanıldı. Çıkmak için 'q' tuşuna basın.")

# Görüntüyü kare kare oku ve göster
while True:
    # Bir sonraki kareyi oku
    ret, frame = cap.read()

    # Eğer kare başarıyla okunamazsa (akış sonlandıysa), döngüden çık
    if not ret:
        print("Akıştan kare okunamadı. Bağlantı kopmuş olabilir.")
        break

    # Kareyi ekranda göster
    cv2.imshow('Hikvision Kamera Goruntusu', frame)

    # 'q' tuşuna basıldığında döngüden çık ve pencereyi kapat
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Her şey bittiğinde, yakalama nesnesini serbest bırak ve pencereleri kapat
cap.release()
cv2.destroyAllWindows()