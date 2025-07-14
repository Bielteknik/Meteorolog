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
    snow_density_kg_m3 = Column(Float, nullable=True)
    swe_mm = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)
    data_source = Column(String, default='sensor') # 'sensor' veya 'api'

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

# Ana veritabanı yöneticisi nesnesini oluştur
storage_manager = StorageManager(engine)