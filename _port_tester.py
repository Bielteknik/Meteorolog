import serial
import time
import glob
import threading

# Test edilecek baud hızı
BAUD_RATE = 9600

def read_from_port(port_name):
    """Belirtilen seri portu sürekli olarak okur ve ekrana basar."""
    print(f"Dinlemeye başlanıyor: {port_name}")
    try:
        with serial.Serial(port_name, BAUD_RATE, timeout=1) as ser:
            while True:
                try:
                    # readline() satır sonu karakteri (\n) bekler.
                    # Sensörleriniz bu karakteri gönderiyorsa en iyi yöntem budur.
                    if ser.in_waiting > 0:
                        line = ser.readline()
                        if line:
                            # Gelen veriyi hem ham byte olarak hem de 
                            # okunabilir metin olarak yazdıralım.
                            # repr() fonksiyonu \r, \n gibi özel karakterleri gösterir.
                            print(f"[{port_name}] -> {repr(line)}")
                    time.sleep(0.1)
                except serial.SerialException as e:
                    print(f"HATA: {port_name} portunda okuma hatası: {e}")
                    break
                except KeyboardInterrupt:
                    break
    except serial.SerialException as e:
        print(f"HATA: {port_name} portu açılamadı: {e}")
    
    print(f"Dinleme durduruldu: {port_name}")

def main():
    """Sistemdeki tüm ttyUSB portlarını bulur ve her biri için bir okuma süreci başlatır."""
    # /dev/ttyUSB0, /dev/ttyUSB1 vb. portları bul
    usb_ports = glob.glob("/dev/ttyUSB*")

    if not usb_ports:
        print("Hiçbir /dev/ttyUSB* portu bulunamadı.")
        print("Lütfen sensörlerin bağlı ve tanınmış olduğundan emin olun.")
        return

    print(f"Bulunan portlar: {', '.join(usb_ports)}")
    print("-" * 30)

    threads = []
    for port in usb_ports:
        # Her port için ayrı bir thread (iş parçacığı) başlatıyoruz
        # Bu sayede tüm portları aynı anda dinleyebiliriz.
        thread = threading.Thread(target=read_from_port, args=(port,))
        threads.append(thread)
        thread.start()

    print("Tüm portlar dinleniyor. Çıkmak için Ctrl+C tuşuna basın.")
    
    try:
        # Ana thread'in, diğer thread'ler çalışırken beklemesini sağla
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\nProgram kullanıcı tarafından durduruluyor...")

if __name__ == "__main__":
    main()