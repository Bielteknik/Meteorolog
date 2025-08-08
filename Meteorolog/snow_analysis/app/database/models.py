from sqlalchemy import (Column, Integer, String, Float, DateTime, Boolean, 
                        ForeignKey, Text)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Sensor(Base):
    """
    Sisteme tanımlı her bir sensörü temsil eder. Ayarları Django dashboard'u
    üzerinden yönetilecektir.
    """
    __tablename__ = 'sensors'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False, comment="Sensöre verilen benzersiz isim (örn: 'ultrasonic_height')")
    type = Column(String(100), nullable=False, comment="Sensör plugin'inin tipini belirtir (örn: 'dfrobot_ultrasonic')")
    enabled = Column(Boolean, default=True, nullable=False, comment="Bu sensörün veri toplama döngüsüne dahil edilip edilmeyeceği")
    
    # Sensör script'i tarafından güncellenecek durum bilgileri
    last_known_port = Column(String(255), nullable=True, comment="Keşfedilen son seri port veya I2C adresi")
    last_seen = Column(DateTime, nullable=True, comment="Sensörün son görüldüğü zaman")

    settings = relationship("SensorSetting", back_populates="sensor", cascade="all, delete-orphan")
    measurements = relationship("Measurement", back_populates="sensor")

    def __repr__(self):
        return f"<Sensor(id={self.id}, name='{self.name}', enabled={self.enabled})>"

class SensorSetting(Base):
    """
    Bir sensöre ait ayarları (baudrate, regex, vb.) key-value şeklinde tutar.
    Bu yapı, farklı sensörlerin farklı ayarlara sahip olabilmesini sağlar.
    """
    __tablename__ = 'sensor_settings'
    id = Column(Integer, primary_key=True)
    key = Column(String(100), nullable=False, comment="Ayarın adı (örn: 'baudrate')")
    value = Column(String(255), nullable=False, comment="Ayarın değeri (örn: '9600')")
    sensor_id = Column(Integer, ForeignKey('sensors.id'), nullable=False)

    sensor = relationship("Sensor", back_populates="settings")

    def __repr__(self):
        return f"<SensorSetting(sensor='{self.sensor.name}', key='{self.key}', value='{self.value}')>"

class Measurement(Base):
    """
    Her bir sensörden gelen ham ve işlenmiş ölçümleri tekil olarak saklar.
    """
    __tablename__ = 'measurements'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    sensor_id = Column(Integer, ForeignKey('sensors.id'), nullable=False)
    
    # Ölçülen değerler
    value_type = Column(String(50), comment="Ölçümün tipi (örn: 'temperature_c', 'snow_height_mm')")
    value_numeric = Column(Float, nullable=True)
    value_text = Column(String, nullable=True)

    sensor = relationship("Sensor", back_populates="measurements")

class AnomalyLog(Base):
    """Tespit edilen tüm anormallikleri kaydeder."""
    __tablename__ = 'anomaly_logs'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    sensor_name = Column(String, nullable=False)
    anomaly_type = Column(String, nullable=False)
    details = Column(Text, nullable=True)