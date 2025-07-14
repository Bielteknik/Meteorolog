# app/sensor_manager.py ("Sıfır Hafıza" Stratejisi)
import time
import re
from typing import Dict, Optional, Tuple, Union

import serial
import serial.tools.list_ports
from smbus2 import SMBus, i2c_msg

class SensorManager:
    """
    Tüm fiziksel sensörlerin bağlantısını, durumunu ve veri okumasını yönetir.
    Strateji: Her okuma döngüsünde tüm sensörleri sıfırdan tarar, okur ve kapatır.
    """
    def __init__(self):
        # Bu sınıf artık başlangıçta neredeyse hiçbir şey yapmıyor.
        # Sadece I2C adresini saklıyor.
        self.sht3x_addr = 0x44
        print("✅ Sensör Yöneticisi 'Sıfır Hafıza' modunda başlatıldı.")

    def read_all_sensors(self) -> Dict[str, Optional[Union[str, Tuple[float, float]]]]:
        """
        Tüm sensörleri sıfırdan tarar, bulur, okur ve bağlantıları kapatır.
        """
        raw_data = {"height_raw": None, "weight_raw": None, "temp_hum_raw": None}

        # --- Adım 1: Seri Portları Tara ve Oku ---
        available_ports = serial.tools.list_ports.comports()
        
        for port in available_ports:
            if "ttyS" in port.device: continue

            ser = None
            try:
                # Her port için bağlan, oku, tanı ve kapat
                ser = serial.Serial(port.device, 9600, timeout=2)
                # Sensörlerin "uyanması" için bu bekleme kritik olabilir
                time.sleep(2) 
                
                # Tek seferde bolca veri oku
                buffer = ser.read(100).decode('utf-8', errors='ignore')

                # Yükseklik sensörü mü?
                if 'R' in buffer:
                    lines = buffer.strip().split('\n')
                    for line in reversed(lines):
                        if line.startswith('R'):
                            raw_data["height_raw"] = line.strip()
                            print(f"  ✅ Yükseklik verisi okundu: {port.device}")
                            break
                
                # Ağırlık sensörü mü?
                elif '=' in buffer:
                    lines = buffer.strip().split('\n')
                    for line in reversed(lines):
                        match = re.search(r'=\s*(-?\d+\.\d+)', line)
                        if match:
                            raw_data["weight_raw"] = f"={match.group(1)}"
                            print(f"  ✅ Ağırlık verisi okundu: {port.device}")
                            break
            except Exception as e:
                print(f"  ❌ {port.device} portu işlenirken hata: {e}")
            finally:
                if ser and ser.is_open:
                    ser.close()

        # --- Adım 2: I2C Sensörünü Tara ve Oku ---
        i2c_bus = None
        try:
            i2c_bus = SMBus(1)
            # Ölçüm komutunu ve okuma komutunu bir arada gönder
            write = i2c_msg.write(self.sht3x_addr, [0x2C, 0x06])
            read = i2c_msg.read(self.sht3x_addr, 6)
            i2c_bus.i2c_rdwr(write) 
            time.sleep(0.5) # Ölçüm için bekle
            i2c_bus.i2c_rdwr(read)

            data = list(read)
            temp = -45 + (175 * (data[0] * 256 + data[1])) / 65535.0
            humidity = 100 * (data[3] * 256 + data[4]) / 65535.0
            raw_data["temp_hum_raw"] = (temp, humidity)
            print("  ✅ Sıcaklık/Nem verisi okundu.")
        except Exception as e:
            print(f"  ❌ Sıcaklık/Nem sensöründen okuma hatası: {e}")
        finally:
            if i2c_bus:
                i2c_bus.close()
                
        return raw_data

    def close_all(self):
        """Bu stratejide bu fonksiyonun bir işlevi kalmadı."""
        print("🔌 Bağlantılar her döngüde kapatıldığı için ek işlem gerekmiyor.")