from sqlalchemy import (create_engine, Column, Integer, String, Float, 
                        DateTime, MetaData, Table, inspect)
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import os

# Veritabanı dosyasının adı
DATABASE_FILE = "station_data.db"
# Veritabanı motorunu oluştur. `check_same_thread=False` APScheduler ile uyumluluk için önemlidir.
engine = create_engine(f"sqlite:///{DATABASE_FILE}", connect_args={"check_same_thread": False})

# SQLAlchemy için temel sınıflar
Base = declarative_base()
metadata = MetaData()

# --- Tablo Modellerini Tanımla ---
# Base sınıfından miras alarak tablolarımızı Python sınıfları olarak tanımlıyoruz.
class Reading(Base):
    __tablename__ = 'readings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    snow_height_mm = Column(Float, nullable=True)
    snow_weight_kg = Column(Float, nullable=True)  # <-- YENİ SÜTUN
    snow_density_kg_m3 = Column(Float, nullable=True)
    swe_mm = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    data_source = Column(String, default='sensor')

class ApiQueue(Base):
    __tablename__ = 'api_queue'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    payload = Column(String, nullable=False) # Gönderilecek JSON verisi
    attempts = Column(Integer, default=0)

class AnomalyLog(Base):
    __tablename__ = 'anomaly_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    sensor = Column(String, nullable=False)
    anomaly_type = Column(String, nullable=False)
    value = Column(String, nullable=True)
    details = Column(String, nullable=True)

class EmailLog(Base):
    __tablename__ = 'email_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)

class SystemHealthLog(Base):
    __tablename__ = 'system_health_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    cpu_temp_c = Column(Float, nullable=True)
    cpu_usage_percent = Column(Float, nullable=True)
    memory_usage_percent = Column(Float, nullable=True)
    disk_usage_percent = Column(Float, nullable=True)

# --- Veritabanı Yönetici Sınıfı ---
class StorageManager:
    def __init__(self, engine):
        self.engine = engine
        self._Session = sessionmaker(bind=self.engine)
        self.init_db()

    def init_db(self):
        """
        Veritabanını ve tanımlı tabloları oluşturur (eğer mevcut değillerse).
        """
        try:
            # Base.metadata.create_all, Base'den türeyen tüm tabloları oluşturur.
            Base.metadata.create_all(self.engine)
            print("✅ Veritabanı ve tablolar başarıyla kontrol edildi/oluşturuldu.")
        except Exception as e:
            print(f"❌ Veritabanı oluşturulurken bir hata oluştu: {e}")
            exit(1)

    def get_session(self):
        """
        Yeni bir veritabanı oturumu (session) döndürür.
        """
        return self._Session()

    def save_reading(self, processed_data: dict):
        """
        İşlenmiş veri sözlüğünü alır ve 'readings' tablosuna kaydeder.
        """
        session = self.get_session()
        try:
            # Sözlükteki verileri Reading modelinin alanlarıyla eşleştir
            new_reading = Reading(
                timestamp=datetime.now(),
                snow_height_mm=processed_data.get("snow_height_mm"),
                snow_weight_kg=processed_data.get("snow_weight_kg"), # <-- YENİ SATIR                
                snow_density_kg_m3=processed_data.get("snow_density_kg_m3"),
                swe_mm=processed_data.get("swe_mm"),
                temperature_c=processed_data.get("temperature_c"),
                humidity_percent=processed_data.get("humidity_percent"),
                data_source=processed_data.get("data_source", "unknown")
            )
            session.add(new_reading)
            session.commit()
            print("   [bold]💾 Veri başarıyla veritabanına kaydedildi.[/bold]")
        except Exception as e:
            print(f"   ❌ Veritabanına kaydetme hatası: {e}")
            session.rollback() # Hata durumunda işlemi geri al
        finally:
            session.close() # Oturumu her zaman kapat

    def get_readings_for_last_hour(self):
        """Son 1 saat içindeki tüm okumaları veritabanından çeker."""
        session = self.get_session()
        try:
            one_hour_ago = datetime.now() - timedelta(hours=1)
            results = session.query(Reading).filter(Reading.timestamp >= one_hour_ago).all()
            return results
        except Exception as e:
            print(f"  ❌ Son 1 saatlik verileri okuma hatası: {e}")
            return []
        finally:
            session.close()

    def add_to_api_queue(self, payload_json: str):
        """Gönderilemeyen bir veri paketini API kuyruğuna ekler."""
        session = self.get_session()
        try:
            new_item = ApiQueue(payload=payload_json, attempts=1)
            session.add(new_item)
            session.commit()
            print("  ⚠️ Veri API kuyruğuna eklendi.")
        except Exception as e:
            print(f"  ❌ API kuyruğuna ekleme hatası: {e}")
            session.rollback()
        finally:
            session.close()

    def get_oldest_from_api_queue(self):
        """Kuyruktaki en eski öğeyi alır ve deneme sayısını artırır."""
        session = self.get_session()
        try:
            # En eski öğeyi (en düşük id) bul
            item = session.query(ApiQueue).order_by(ApiQueue.id.asc()).first()
            if item:
                item.attempts += 1
                session.commit()
            return item
        except Exception as e:
            print(f"  ❌ API kuyruğundan veri alma hatası: {e}")
            return None
        finally:
            session.close()

    def remove_from_api_queue(self, item_id: int):
        """Başarıyla gönderilen bir öğeyi ID'sine göre kuyruktan siler."""
        session = self.get_session()
        try:
            item_to_delete = session.query(ApiQueue).filter(ApiQueue.id == item_id).one()
            session.delete(item_to_delete)
            session.commit()
        except Exception as e:
            print(f"  ❌ API kuyruğundan silme hatası: {e}")
            session.rollback()
        finally:
            session.close()

# Ana veritabanı yöneticisi nesnesini oluştur
storage_manager = StorageManager(engine)