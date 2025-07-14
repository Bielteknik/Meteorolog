import time
import re
from typing import Dict, Optional, Tuple

import serial
import serial.tools.list_ports
from smbus2 import SMBus, i2c_msg

class SensorManager:
    """
    Tüm fiziksel sensörlerin bağlantısını, durumunu ve veri okumasını yönetir.
    """
    def __init__(self):
        # Seri port nesneleri
        self.height_ser: Optional[serial.Serial] = None
        self.weight_ser: Optional[serial.Serial] = None
        
        # I2C nesnesi
        self.i2c_bus: Optional[SMBus] = None
        self.sht3x_addr = 0x44  # SHT3x sensörünün varsayılan I2C adresi

        # Sensör durumları
        self.is_height_ok: bool = False
        self.is_weight_ok: bool = False
        self.is_temp_ok: bool = False
        
        # Bulunan portların adları
        self.height_port: Optional[str] = None
        self.weight_port: Optional[str] = None
        
        print("🔍 Sensör Yöneticisi başlatıldı. Sensörler aranıyor...")
        self.find_and_connect_all()

    def find_and_connect_all(self):
        """Tüm sensörleri bulur ve bağlantılarını kurar."""
        self._find_serial_sensors()
        self._find_i2c_sensors()
        self.report_status()

    def _find_serial_sensors(self):
        """USB'ye bağlı seri sensörleri (Yükseklik, Ağırlık) arar ve bağlanır."""
        available_ports = serial.tools.list_ports.comports()
        if not available_ports:
            print("  ⚠️ Hiçbir seri port bulunamadı.")
            return

        print(f"  ℹ️ Bulunan seri portlar: {[port.device for port in available_ports]}")

        for port in available_ports:
            # Eğer bu port zaten başka bir sensöre atanmışsa atla
            if port.device in [self.height_port, self.weight_port]:
                continue
            
            # /dev/ttyS0 gibi dahili portları genellikle atlamak daha iyidir.
            if "ttyS" in port.device:
                print(f"  ⏭️  Dahili port {port.device} atlanıyor.")
                continue

            ser = None # Hata durumunda kapatabilmek için döngü dışında tanımla
            try:
                # Porta bağlanmayı dene
                ser = serial.Serial(port.device, 9600, timeout=1) # Timeout'u 1 saniye yapalım
                time.sleep(2) # Portun açılması için kritik bekleme

                # Belirli bir süre (örn. 2 saniye) boyunca gelen veriyi topla
                buffer = b''
                start_time = time.time()
                while time.time() - start_time < 2.0:
                    if ser.in_waiting > 0:
                        buffer += ser.read(ser.in_waiting)
                
                # Toplanan veriyi string'e çevir
                decoded_buffer = buffer.decode('utf-8', errors='ignore')
                
                # Yükseklik sensörü mü? ('R' içerir)
                if 'R' in decoded_buffer and not self.height_ser:
                    self.height_ser = ser
                    self.height_port = port.device
                    self.is_height_ok = True
                    print(f"  ✅ Yükseklik sensörü bağlandı: {self.height_port}")
                    continue # Diğer porta geç
                
                # Ağırlık sensörü mü? ('=' içerir)
                elif '=' in decoded_buffer and not self.weight_ser:
                    self.weight_ser = ser
                    self.weight_port = port.device
                    self.is_weight_ok = True
                    print(f"  ✅ Ağırlık sensörü bağlandı: {self.weight_port}")
                    continue
                
                # Sensör tanınmadıysa portu kapat
                print(f"  ⚠️ {port.device} portundaki veri tanınamadı. Veri: '{decoded_buffer[:50]}...'")
                ser.close()

            except (serial.SerialException, OSError) as e:
                print(f"  ❌ {port.device} portuna bağlanırken hata: {e}")
                if ser and ser.is_open:
                    ser.close()

    def _find_i2c_sensors(self):
        """I2C bus'ını tarar ve SHT3x sensörünü arar."""
        try:
            # Raspberry Pi'da genellikle I2C bus 1 kullanılır
            bus_number = 1
            self.i2c_bus = SMBus(bus_number)
            # Adrese basit bir yazma işlemi yaparak varlığını kontrol et
            self.i2c_bus.write_byte(self.sht3x_addr, 0x00)
            self.is_temp_ok = True
            print(f"  ✅ Sıcaklık/Nem (SHT3x) sensörü I2C-{bus_number} adresinde ({hex(self.sht3x_addr)}) bulundu.")
        except FileNotFoundError:
            print("  ⚠️ I2C bus'ı bulunamadı. I2C arayüzü etkin mi?")
            self.is_temp_ok = False
        except Exception as e:
            # Adres bulunamazsa genellikle OSError: [Errno 121] Remote I/O error hatası verir
            print(f"  ⚠️ Sıcaklık/Nem sensörü I2C adresinde ({hex(self.sht3x_addr)}) bulunamadı.")
            self.is_temp_ok = False
            if self.i2c_bus:
                self.i2c_bus.close()
            self.i2c_bus = None

    def read_all_sensors(self) -> Dict[str, Optional[str]]:
        """
        Bağlı olan tüm sensörlerden ham veri okur.
        Döndürdüğü veri: {'height_raw': 'R3650', 'weight_raw': '=12.34', 'temp_hum_raw': (21.5, 45.8)}
        """
        raw_data = {
            "height_raw": None,
            "weight_raw": None,
            "temp_hum_raw": None # (sıcaklık, nem) tuple'ı
        }

        # Yükseklik oku
        if self.is_height_ok and self.height_ser:
            try:
                # Buffer'ı temizle ve taze veri bekle
                self.height_ser.reset_input_buffer()
                line = self.height_ser.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith('R'):
                    raw_data["height_raw"] = line
            except Exception as e:
                print(f"  ❌ Yükseklik sensörü okuma hatası: {e}")
                self.is_height_ok = False # Sorun varsa durumu güncelle

        # Ağırlık oku
        if self.is_weight_ok and self.weight_ser:
            try:
                self.weight_ser.reset_input_buffer()
                line = self.weight_ser.readline().decode('utf-8', errors='ignore').strip()
                # Ağırlık verisi formatı: "=    0.00C0". Regex ile sayıyı alalım.
                match = re.search(r'=\s*(-?\d+\.\d+)', line)
                if match:
                    # Sadece "=12.34" formatında saklayalım
                    raw_data["weight_raw"] = f"={match.group(1)}"
            except Exception as e:
                print(f"  ❌ Ağırlık sensörü okuma hatası: {e}")
                self.is_weight_ok = False

        # Sıcaklık/Nem oku
        if self.is_temp_ok and self.i2c_bus:
            try:
                # SHT3x'e tek seferlik ölçüm komutu gönder (0x2C, 0x06)
                write = i2c_msg.write(self.sht3x_addr, [0x2C, 0x06])
                self.i2c_bus.i2c_rdwr(write)
                time.sleep(0.5) # Sensörün ölçüm yapması için bekle

                # 6 byte veri oku (Sıcaklık MSB, LSB, CRC, Nem MSB, LSB, CRC)
                read = i2c_msg.read(self.sht3x_addr, 6)
                self.i2c_bus.i2c_rdwr(read)
                data = list(read)
                
                # Ham veriyi sıcaklık ve neme dönüştür
                temp = -45 + (175 * (data[0] * 256 + data[1])) / (2**16 - 1)
                humidity = (100 * (data[3] * 256 + data[4])) / (2**16 - 1)
                raw_data["temp_hum_raw"] = (temp, humidity)
            except Exception as e:
                print(f"  ❌ Sıcaklık/Nem sensörü okuma hatası: {e}")
                self.is_temp_ok = False

        return raw_data

    def report_status(self):
        """Sensörlerin mevcut durumunu konsola basar."""
        print("--- Sensör Durum Raporu ---")
        print(f"📏 Yükseklik: {'BAĞLI' if self.is_height_ok else 'BAĞLI DEĞİL'} ({self.height_port or 'N/A'})")
        print(f"⚖️ Ağırlık:   {'BAĞLI' if self.is_weight_ok else 'BAĞLI DEĞİL'} ({self.weight_port or 'N/A'})")
        print(f"🌡️ Sıcaklık:  {'BAĞLI' if self.is_temp_ok else 'BAĞLI DEĞİL'} (I2C)")
        print("---------------------------")
        
    def close_all(self):
        """Tüm açık bağlantıları güvenli bir şekilde kapatır."""
        if self.height_ser and self.height_ser.is_open:
            self.height_ser.close()
        if self.weight_ser and self.weight_ser.is_open:
            self.weight_ser.close()
        if self.i2c_bus:
            self.i2c_bus.close()
        print("🔌 Tüm sensör bağlantıları kapatıldı.")