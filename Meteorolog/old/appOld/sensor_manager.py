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

    def _parse_dfrobot_ultrasonic(self, buffer: bytes) -> Optional[int]:
        """
        DFRobot A02YYUW ultrasonik sensörünün veri paketini ayrıştırır.
        Paket Formatı: 0xFF (Header) + DATA_H (Yüksek byte) + DATA_L (Düşük byte) + SUM (Sağlama)
        Referans: DFRobot_ult.py
        """
        # Buffer içinde en sondan başlayarak 0xFF header'ını ara
        last_header_index = buffer.rfind(b'\xff')

        # Header bulunduysa ve paketin tamamı buffer içindeyse
        if last_header_index != -1 and len(buffer) >= last_header_index + 4:
            packet = buffer[last_header_index : last_header_index + 4]
            header, data_h, data_l, received_sum = packet

            # Sağlama toplamını hesapla
            # (Header + DATA_H + DATA_L) & 0xFF
            calculated_sum = (header + data_h + data_l) & 0xFF

            if calculated_sum == received_sum:
                distance_mm = (data_h << 8) | data_l
                return distance_mm
            else:
                # Checksum hatası
                print(f"  ⚠️ DFRobot sensör checksum hatası! Gelen: {received_sum}, Hesaplanan: {calculated_sum}")
                return None
        return None

    def read_all_sensors(self) -> Dict[str, Optional[Union[str, Tuple[float, float], int]]]:
        """
        Tüm sensörleri sıfırdan tarar, bulur, okur ve bağlantıları kapatır.
        """
        raw_data = {"height_raw": None, "weight_raw": None, "temp_hum_raw": None}

        # --- Adım 1: Seri Portları Tara ve Oku ---
        available_ports = serial.tools.list_ports.comports()
        
        for port in available_ports:
            # Raspberry Pi'deki dahili seri portları atla
            if "ttyS" in port.device or "ttyAMA" in port.device: continue

            ser = None
            try:
                # Her port için bağlan, oku, tanı ve kapat
                ser = serial.Serial(port.device, 9600, timeout=2)
                # Sensörlerin "uyanması" için bu bekleme kritik olabilir
                time.sleep(2) 
                
                # Tek seferde bolca veri oku (byte olarak)
                buffer_bytes = ser.read(100)

                # --- YENİ SENSÖR: DFRobot Ultrasonik Yükseklik Sensörü ---
                # DFRobot sensörü 0xFF ile başlayan bir byte paketi gönderir.
                ultrasonic_distance = self._parse_dfrobot_ultrasonic(buffer_bytes)
                if ultrasonic_distance is not None:
                    raw_data["height_raw"] = ultrasonic_distance
                    print(f"  ✅ DFRobot Yükseklik verisi okundu: {ultrasonic_distance} mm ({port.device})")
                
                # Ağırlık sensörü metin tabanlı olduğu için ayrıca decode edip kontrol et
                buffer_str = buffer_bytes.decode('utf-8', errors='ignore')
                if '=' in buffer_str:
                    lines = buffer_str.strip().split('\n')
                    for line in reversed(lines):
                        match = re.search(r'=\s*(-?\d+\.\d+)', line)
                        if match:
                            raw_data["weight_raw"] = f"={match.group(1)}"
                            print(f"  ✅ Ağırlık verisi okundu: {port.device}")
                            break
            except serial.SerialException as e:
                print(f"  ❌ {port.device} portu açılamadı: {e}")
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
        except FileNotFoundError:
             print("  ⚠️ I2C bus (1) bulunamadı. Sıcaklık/Nem sensörü atlanıyor.")
        except Exception as e:
            print(f"  ❌ Sıcaklık/Nem sensöründen okuma hatası: {e}")
        finally:
            if i2c_bus:
                i2c_bus.close()                
        return raw_data

    def close_all(self):
        """Bu stratejide bu fonksiyonun bir işlevi kalmadı."""
        print("🔌 Bağlantılar her döngüde kapatıldığı için ek işlem gerekmiyor.")