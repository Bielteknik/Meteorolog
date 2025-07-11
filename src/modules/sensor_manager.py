import serial
import time
import glob
import re
import yaml

class SensorManager:
    """
    Sensörleri dinamik olarak keşfetmek, bağlamak ve yönetmekten sorumlu sınıf.
    Bu sürüm, zamanlama sorunlarını çözmek için daha sabırlı bir okuma mantığı içerir.
    """
    def __init__(self, config_path):
        print("INFO: SensorManager başlatılıyor...")
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            print("INFO: Yapılandırma dosyası başarıyla yüklendi.")
        except FileNotFoundError:
            print(f"CRITICAL: Yapılandırma dosyası bulunamadı: {config_path}")
            raise SystemExit("Yapılandırma dosyası eksik, sistem durduruluyor.")
        
        self.sensor_definitions = self.config.get('sensors', {})
        self.serial_port_pattern = self.config.get('system', {}).get('serial_port_pattern', '/dev/ttyUSB*')
        self.assigned_ports = {}

    def find_and_assign_sensors(self):
        """
        Sistemdeki seri portları tarar. Her bir portu, anlamlı bir veri gelene kadar
        belirli bir süre dinler ve sonra kimliğini belirler.
        """
        print("\nINFO: Dinamik sensör keşfi başlatıldı...")
        print(f"INFO: Taranacak port deseni: {self.serial_port_pattern}")

        available_ports = glob.glob(self.serial_port_pattern)
        if not available_ports:
            print(f"WARNING: Sistemde '{self.serial_port_pattern}' deseniyle eşleşen hiçbir seri port bulunamadı.")

        print(f"INFO: Bulunan potansiyel portlar: {available_ports}")

        regex_map = {
            name: re.compile(definition['identifier_pattern'])
            for name, definition in self.sensor_definitions.items()
            if definition.get('enabled', False) and 'identifier_pattern' in definition
        }

        for port in available_ports:
            print(f"\nINFO: '{port}' portu analiz ediliyor...")
            baudrate = 9600
            
            try:
                with serial.Serial(port, baudrate, timeout=1) as ser: # Timeout'u 1 saniye yapalım
                    # Sensörün kendine gelmesi için ilk bekleme
                    time.sleep(2)
                    ser.reset_input_buffer()

                    print("  -> Anlamlı veri bekleniyor (en fazla 5 saniye)...")
                    start_time = time.time()
                    line = ""
                    # Anlamlı bir veri gelene kadar veya 5 saniye dolana kadar bekle
                    while time.time() - start_time < 5:
                        try:
                            # readline() bloke edici olduğu için timeout'a kadar bekler
                            raw_line = ser.readline()
                            if raw_line:
                                line = raw_line.decode('utf-8', errors='ignore').strip()
                                if line: # Eğer satır boş değilse döngüden çık
                                    break
                        except serial.SerialException:
                            # Bu genellikle cihaz çıkarıldığında olur, döngüyü kır
                            break
                    
                    print(f"  -> Okunan veri: '{line}'")

                    if not line:
                        print(f"  -> WARNING: '{port}' portundan zaman aşımı süresince veri okunamadı. Atlanıyor.")
                        continue

                    found_match = False
                    for name, regex in regex_map.items():
                        if regex.search(line):
                            if name in self.assigned_ports:
                                print(f"  -> CRITICAL: Çakışma! '{name}' sensörü zaten atanmış.")
                            else:
                                print(f"  -> SUCCESS: Bu veri '{name}' sensörüne ait. Atama yapılıyor.")
                                self.assigned_ports[name] = port
                                found_match = True
                                break 
                    
                    if not found_match:
                        print(f"  -> WARNING: Okunan veri, tanımlı hiçbir sensör deseniyle eşleşmedi.")

            except serial.SerialException as e:
                print(f"  -> ERROR: '{port}' portu açılamadı veya okunamadı: {e}")
            except Exception as e:
                print(f"  -> ERROR: '{port}' portunda beklenmedik hata: {e}")

        # ----- Sonuç Kontrolü -----
        serial_enabled_names = {name for name, d in self.sensor_definitions.items() if d.get('enabled') and 'identifier_pattern' in d}
        found_sensor_names = set(self.assigned_ports.keys())
        
        if serial_enabled_names.issubset(found_sensor_names):
            print("\nSUCCESS: Tüm aktif seri port sensörleri başarıyla atandı.")
            return True
        else:
            missing_sensors = serial_enabled_names - found_sensor_names
            if missing_sensors:
                print(f"\nERROR: Şu sensörler bulunamadı: {', '.join(missing_sensors)}. Lütfen bağlantıları kontrol edin.")
            return False

    def get_assigned_ports(self):
        return self.assigned_ports