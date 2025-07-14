# app/sensor_manager.py (Bağlantı Yenileme Stratejisi)
import time
import re
from typing import Dict, Optional, Tuple, Union

import serial
import serial.tools.list_ports
from smbus2 import SMBus, i2c_msg

class SensorManager:
    """
    Tüm fiziksel sensörlerin bağlantısını, durumunu ve veri okumasını yönetir.
    Strateji: Her okuma döngüsünde seri port bağlantılarını yeniden kurar.
    """
    def __init__(self):
        # Port ve adres bilgileri
        self.height_port: Optional[str] = None
        self.weight_port: Optional[str] = None
        self.sht3x_addr = 0x44
        
        # I2C bus'ını kalıcı olarak açık tutabiliriz, daha stabildir.
        self.i2c_bus: Optional[SMBus] = None

        # Sensörlerin bulunup bulunmadığını gösteren bayraklar
        self.height_found: bool = False
        self.weight_found: bool = False
        self.temp_found: bool = False
        
        print("🔍 Sensör Yöneticisi başlatıldı. İlk sensör taraması yapılıyor...")
        self.find_all_sensors()
        self.report_status()

    def find_all_sensors(self):
        """Tüm sensör portlarını ve adreslerini tarar, ancak bağlantıyı açık bırakmaz."""
        # --- Seri Sensörleri Bul ---
        available_ports = serial.tools.list_ports.comports()
        if not available_ports:
            print("  ⚠️ Hiçbir seri port bulunamadı.")
        else:
            print(f"  ℹ️ Bulunan seri portlar: {[port.device for port in available_ports]}")

        for port in available_ports:
            if "ttyS" in port.device: continue

            ser = None
            try:
                ser = serial.Serial(port.device, 9600, timeout=1)
                time.sleep(2)
                buffer = ser.read(100).decode('utf-8', errors='ignore')
                
                if 'R' in buffer and not self.height_port:
                    self.height_port = port.device
                    self.height_found = True
                    print(f"  ✅ Yükseklik sensörü portu bulundu: {self.height_port}")
                elif '=' in buffer and not self.weight_port:
                    self.weight_port = port.device
                    self.weight_found = True
                    print(f"  ✅ Ağırlık sensörü portu bulundu: {self.weight_port}")
            except Exception as e:
                print(f"  ❌ {port.device} portu taranırken hata: {e}")
            finally:
                if ser and ser.is_open:
                    ser.close()
        
        # --- I2C Sensörünü Bul ---
        try:
            bus_number = 1
            self.i2c_bus = SMBus(bus_number)
            self.i2c_bus.write_byte(self.sht3x_addr, 0x00) # Varlığını kontrol et
            self.temp_found = True
            print(f"  ✅ Sıcaklık/Nem (SHT3x) sensörü I2C-{bus_number} adresinde ({hex(self.sht3x_addr)}) bulundu.")
        except Exception:
            print(f"  ⚠️ Sıcaklık/Nem sensörü I2C adresinde ({hex(self.sht3x_addr)}) bulunamadı.")
            self.temp_found = False
            if self.i2c_bus:
                self.i2c_bus.close()
                self.i2c_bus = None

    def read_all_sensors(self) -> Dict[str, Optional[Union[str, Tuple[float, float]]]]:
        """
        Tüm sensörlerden veri okur. Seri portları bu fonksiyon içinde açar ve kapatır.
        """
        raw_data = {"height_raw": None, "weight_raw": None, "temp_hum_raw": None}
        
        # Yükseklik oku
        if self.height_found and self.height_port:
            ser = None
            try:
                ser = serial.Serial(self.height_port, 9600, timeout=2)
                buffer = ser.read_until(expected=b'\n', size=20).decode('utf-8', errors='ignore')
                lines = buffer.strip().split('\n')
                for line in reversed(lines):
                    if line.startswith('R'):
                        raw_data["height_raw"] = line.strip()
                        break
            except Exception as e:
                print(f"  ❌ Yükseklik sensöründen okuma hatası: {e}")
                self.height_found = False # Bir sonraki denemeye kadar devre dışı bırak
            finally:
                if ser and ser.is_open:
                    ser.close()

        # Ağırlık oku
        if self.weight_found and self.weight_port:
            ser = None
            try:
                ser = serial.Serial(self.weight_port, 9600, timeout=2)
                buffer = ser.read_until(expected=b'\n', size=50).decode('utf-8', errors='ignore')
                lines = buffer.strip().split('\n')
                for line in reversed(lines):
                    match = re.search(r'=\s*(-?\d+\.\d+)', line)
                    if match:
                        raw_data["weight_raw"] = f"={match.group(1)}"
                        break
            except Exception as e:
                print(f"  ❌ Ağırlık sensöründen okuma hatası: {e}")
                self.weight_found = False # Bir sonraki denemeye kadar devre dışı bırak
            finally:
                if ser and ser.is_open:
                    ser.close()

        # Sıcaklık/Nem oku
        if self.temp_found and self.i2c_bus:
            try:
                write = i2c_msg.write(self.sht3x_addr, [0x2C, 0x06])
                read = i2c_msg.read(self.sht3x_addr, 6)
                self.i2c_bus.i2c_rdwr(write, read)
                data = list(read)
                temp = -45 + (175 * (data[0] * 256 + data[1])) / 65535.0
                humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
                raw_data["temp_hum_raw"] = (temp, humidity)
            except Exception as e:
                print(f"  ❌ Sıcaklık/Nem sensöründen okuma hatası: {e}")
                self.temp_found = False

        return raw_data

    def report_status(self):
        """Sensörlerin bulunup bulunmadığını raporlar."""
        print("--- Sensör Durum Raporu ---")
        print(f"📏 Yükseklik: {'BULUNDU' if self.height_found else 'BULUNAMADI'} ({self.height_port or 'N/A'})")
        print(f"⚖️ Ağırlık:   {'BULUNDU' if self.weight_found else 'BULUNAMADI'} ({self.weight_port or 'N/A'})")
        print(f"🌡️ Sıcaklık:  {'BULUNDU' if self.temp_found else 'BULUNAMADI'} (I2C)")
        print("---------------------------")
        
    def close_all(self):
        """Kalıcı bağlantıları (sadece I2C) kapatır."""
        if self.i2c_bus:
            self.i2c_bus.close()
            print("🔌 I2C bağlantısı kapatıldı.")