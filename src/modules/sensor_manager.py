import serial
import time
import glob
import re
import yaml

class SensorManager:
    """
    Sensörleri dinamik olarak keşfetmek, bağlamak ve yönetmekten sorumlu sınıf.
    Bu sürüm, portları tek tek analiz ederek daha güvenilir bir keşif yapar.
    """
    def __init__(self, config_path):
        """
        Args:
            config_path (str): Yapılandırma dosyasının yolu.
        """
        print("INFO: SensorManager başlatılıyor...")
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            print("INFO: Yapılandırma dosyası başarıyla yüklendi.")
        except FileNotFoundError:
            print(f"CRITICAL: Yapılandırma dosyası bulunamadı: {config_path}")
            # Yapılandırma olmadan devam etmek imkansız.
            raise SystemExit("Yapılandırma dosyası eksik, sistem durduruluyor.")
        
        self.sensor_definitions = self.config.get('sensors', {})
        self.serial_port_pattern = self.config.get('system', {}).get('serial_port_pattern', '/dev/ttyUSB*')
        self.assigned_ports = {} # {'distance': '/dev/ttyUSB1', 'weight': '/dev/ttyUSB0'}

    def find_and_assign_sensors(self):
        """
        Sistemdeki seri portları tarar, HER BİR PORTU BİR KEZ OKUR ve hangi sensöre
        ait olduğunu belirleyerek atama yapar.
        """
        print("\nINFO: Dinamik sensör keşfi başlatıldı...")
        print(f"INFO: Taranacak port deseni: {self.serial_port_pattern}")

        available_ports = glob.glob(self.serial_port_pattern)
        if not available_ports:
            print("WARNING: Sistemde '{self.serial_port_pattern}' deseniyle eşleşen hiçbir seri port bulunamadı.")
            # Devam etmeden önce eksik sensörleri kontrol et
        
        print(f"INFO: Bulunan potansiyel portlar: {available_ports}")

        # Sensör adı ve regex desenini içeren bir sözlük oluşturalım
        # Sadece 'enabled: true' olan ve seri port kullanan sensörleri dahil et
        regex_map = {
            name: re.compile(definition['identifier_pattern'])
            for name, definition in self.sensor_definitions.items()
            if definition.get('enabled', False) and 'identifier_pattern' in definition
        }

        # Her bir portu tek tek ele alalım
        for port in available_ports:
            print(f"\nINFO: '{port}' portu analiz ediliyor...")
            # Şimdilik baudrate sabit, gelecekte config'den alınabilir.
            baudrate = 9600
            
            try:
                with serial.Serial(port, baudrate, timeout=2) as ser:
                    # Sensörün veri göndermeye başlaması için kritik bekleme
                    time.sleep(2) 
                    # Olası başlangıç gürültüsünü temizlemek için buffer'ı oku
                    ser.reset_input_buffer()
                    # Taze veri okumak için tekrar kısa bir bekleme
                    time.sleep(0.5)
                    
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    print(f"  -> Okunan veri: '{line}'")

                    if not line:
                        print(f"  -> WARNING: '{port}' portundan boş veri okundu. Atlanıyor.")
                        continue

                    # Okunan veri hangi sensörün deseniyle eşleşiyor?
                    found_match = False
                    for name, regex in regex_map.items():
                        if regex.search(line):
                            if name in self.assigned_ports:
                                print(f"  -> CRITICAL: Çakışma! '{name}' sensörü zaten '{self.assigned_ports[name]}' portuna atanmış. '{port}' portu da aynı sensör verisini gönderiyor.")
                            else:
                                print(f"  -> SUCCESS: Bu veri '{name}' sensörüne ait. Atama yapılıyor.")
                                self.assigned_ports[name] = port
                                found_match = True
                                # Eşleşme bulundu, bu port için başka desene bakmaya gerek yok.
                                break 
                    
                    if not found_match:
                        print(f"  -> WARNING: Okunan veri, tanımlı hiçbir sensör deseniyle eşleşmedi.")

            except serial.SerialException as e:
                print(f"  -> ERROR: '{port}' portu açılamadı veya okunamadı: {e}")
            except Exception as e:
                print(f"  -> ERROR: '{port}' portunda beklenmedik hata: {e}")

        # ----- Sonuç Kontrolü -----
        # Config'de aktif olan sensörlerin isimlerini al
        enabled_sensor_names = {name for name, d in self.sensor_definitions.items() if d.get('enabled')}
        
        # Bulunan (atanan) sensörlerin isimlerini al
        found_sensor_names = set(self.assigned_ports.keys())

        # I2C gibi seri port kullanmayanları şimdilik hesaptan çıkaralım
        serial_enabled_names = {name for name, d in self.sensor_definitions.items() if d.get('enabled') and 'identifier_pattern' in d}
        
        if serial_enabled_names.issubset(found_sensor_names):
            print("\nSUCCESS: Tüm aktif seri port sensörleri başarıyla atandı.")
            return True
        else:
            missing_sensors = serial_enabled_names - found_sensor_names
            if missing_sensors:
                print(f"\nERROR: Şu sensörler bulunamadı: {', '.join(missing_sensors)}. Lütfen bağlantıları kontrol edin.")
            return False

    def get_assigned_ports(self):
        """Atanan portları döndürür."""
        return self.assigned_ports