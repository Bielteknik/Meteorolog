import serial
import time
import glob
import re
import yaml

class SensorManager:
    """
    Sensörleri dinamik olarak keşfetmek, bağlamak ve yönetmekten sorumlu sınıf.
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
            exit() # Program yapılandırma olmadan çalışamaz.
        
        self.sensor_definitions = self.config.get('sensors', {})
        self.serial_port_pattern = self.config.get('system', {}).get('serial_port_pattern', '/dev/ttyUSB*')
        self.assigned_ports = {} # {'distance': '/dev/ttyUSB1', 'weight': '/dev/ttyUSB0'}

    def find_and_assign_sensors(self):
        """
        Sistemdeki seri portları tarar, sensörleri tanımlayıcı desenlerine göre
        keşfeder ve atamalarını yapar.
        """
        print("\nINFO: Dinamik sensör keşfi başlatıldı...")
        print(f"INFO: Taranacak port deseni: {self.serial_port_pattern}")

        available_ports = glob.glob(self.serial_port_pattern)
        if not available_ports:
            print("WARNING: Sistemde eşleşen hiçbir seri port bulunamadı.")
            return False

        print(f"INFO: Bulunan potansiyel portlar: {available_ports}")
        
        unassigned_ports = list(available_ports)
        found_sensors = {}

        for name, definition in self.sensor_definitions.items():
            if not definition.get('enabled', False) or 'identifier_pattern' not in definition:
                continue

            print(f"INFO: '{name}' sensörü aranıyor...")
            identifier_regex = re.compile(definition['identifier_pattern'])
            baudrate = definition.get('baudrate', 9600)
            sensor_found = False

            for port in list(unassigned_ports): # Kopya üzerinde iterasyon
                try:
                    with serial.Serial(port, baudrate, timeout=2) as ser:
                        # Portun kendine gelmesi için kısa bir bekleme
                        time.sleep(2) 
                        # Gelen ilk anlamlı veriyi yakalamak için birkaç satır oku
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        print(f"  -> '{port}' portundan okunan veri: '{line}'")

                        if identifier_regex.search(line):
                            print(f"SUCCESS: '{name}' sensörü '{port}' portunda bulundu!")
                            found_sensors[name] = port
                            unassigned_ports.remove(port)
                            sensor_found = True
                            break # Bu sensörü bulduk, sonraki sensöre geç
                except serial.SerialException as e:
                    print(f"  -> WARNING: '{port}' portu açılamadı veya okunamadı: {e}")
                except Exception as e:
                    print(f"  -> ERROR: '{port}' portunda beklenmedik hata: {e}")
            
            if not sensor_found:
                print(f"CRITICAL: '{name}' sensörü hiçbir portta bulunamadı!")

        self.assigned_ports = found_sensors
        
        # Sonuç kontrolü
        enabled_sensor_count = sum(1 for d in self.sensor_definitions.values() if d.get('enabled'))
        if len(self.assigned_ports) == enabled_sensor_count:
            print("\nSUCCESS: Tüm aktif sensörler başarıyla atandı.")
            return True
        else:
            print("\nERROR: Bazı sensörler bulunamadı. Lütfen bağlantıları kontrol edin.")
            return False

    def get_assigned_ports(self):
        """Atanan portları döndürür."""
        return self.assigned_ports