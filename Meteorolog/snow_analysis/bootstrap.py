from app.database.manager import storage_manager
from app.database.models import Sensor, SensorSetting

def bootstrap_initial_data():
    """
    Veritabanı boşsa, Django paneli üzerinden yönetilecek olan
    başlangıç sensör ayarlarını ekler.
    """
    # 1. Veritabanı tablolarını oluştur
    print("--- Veritabanı tabloları oluşturuluyor... ---")
    storage_manager.init_db()

    # 2. Veritabanının boş olup olmadığını kontrol et
    with storage_manager.get_session() as session:
        if session.query(Sensor).count() > 0:
            print("✅ Veritabanı zaten veri içeriyor. Başlangıç verileri atlanıyor.")
            return

    # 3. Boşsa, başlangıç verilerini ekle
    print("--- Veritabanı boş. Başlangıç sensör verileri ekleniyor... ---")
    with storage_manager.get_session() as session:
        # Yeni Ultrasonik Yükseklik Sensörü
        ultrasonic = Sensor(name="ultrasonic_height", type="dfrobot_ultrasonic", enabled=True)
        ultrasonic.settings.extend([
            SensorSetting(key="baudrate", value="9600"),
            SensorSetting(key="fingerprint_regex", value="^\\d{3,5}$"),
            SensorSetting(key="zero_point_mm", value="3450")
        ])
        
        # Ağırlık Sensörü
        loadcell = Sensor(name="loadcell_weight", type="serial_loadcell", enabled=True)
        loadcell.settings.extend([
            SensorSetting(key="baudrate", value="9600"),
            SensorSetting(key="fingerprint_regex", value="^=\\s*(-?\\d+\\.\\d+)")
        ])
        
        # Sıcaklık ve Nem Sensörü
        sht31 = Sensor(name="sht31_temperature_humidity", type="sht3x_i2c", enabled=True)
        sht31.settings.append(SensorSetting(key="i2c_address", value="0x44"))

        session.add_all([ultrasonic, loadcell, sht31])
        print("✅ Başlangıç verileri başarıyla eklendi.")

if __name__ == "__main__":
    bootstrap_initial_data()