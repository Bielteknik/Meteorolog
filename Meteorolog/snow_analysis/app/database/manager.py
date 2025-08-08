# app/database/manager.py (Güncellenmiş ve Tam Hali)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime  # <--- HATA GİDERİLDİ: Eksik olan import satırı eklendi.
from contextlib import contextmanager

from app.database.models import Base, Sensor, SensorSetting

class StorageManager:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self._SessionFactory = sessionmaker(bind=self.engine)
        print("✅ Veritabanı Yöneticisi başlatıldı.")

    def init_db(self):
        """Veritabanı ve tabloları oluşturur."""
        try:
            Base.metadata.create_all(self.engine)
            print("✅ Veritabanı ve tablolar başarıyla kontrol edildi/oluşturuldu.")
        except Exception as e:
            print(f"❌ Veritabanı oluşturulurken bir hata oluştu: {e}")
            raise

    @contextmanager
    def get_session(self):
        """İşlemler için bir veritabanı oturumu sağlar ve otomatik kapatır."""
        session = self._SessionFactory()
        try:
            yield session
            session.commit()
        except Exception as e:
            print(f"❌ Veritabanı işlemi sırasında hata: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def get_enabled_sensor_configs(self) -> list[dict]:
        """
        Veritabanından aktif olan tüm sensörlerin yapılandırmasını,
        SensorManager'ın anlayacağı formatta okur.
        """
        with self.get_session() as session:
            active_sensors_db = session.query(Sensor).filter_by(enabled=True).all()
            
            sensor_configs = []
            for sensor_db in active_sensors_db:
                config = {
                    "id": sensor_db.id,
                    "name": sensor_db.name,
                    "type": sensor_db.type,
                }
                settings_dict = {setting.key: setting.value for setting in sensor_db.settings}
                config.update(settings_dict)
                sensor_configs.append(config)
            return sensor_configs
            
    def update_sensor_status(self, sensor_id: int, port: str):
        """Sensör keşfedildikten sonra, bulunduğu portu ve görülme zamanını günceller."""
        with self.get_session() as session:
            # .one() metodu, sonuç bulunamazsa veya birden fazla sonuç dönerse hata verir.
            # Bu durumda bu beklenen bir davranıştır.
            sensor_to_update = session.query(Sensor).filter_by(id=sensor_id).one()
            sensor_to_update.last_known_port = port
            sensor_to_update.last_seen = datetime.now() # Artık 'datetime' tanınıyor.
            print(f"ℹ️ Veritabanı güncellendi: '{sensor_to_update.name}' portu -> {port}")

# Global bir storage_manager nesnesi oluşturalım.
# db_url'yi merkezi konfigürasyondan alacak şekilde ayarlayacağız.
# Şimdilik geçici olarak burada tanımlayalım.
db_url = "sqlite:///station_data.db"
storage_manager = StorageManager(db_url)