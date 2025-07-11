import sqlite3
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from app.config import settings
from app.models.schemas import ProcessedReading

logger = logging.getLogger(__name__)

class DatabaseService:
    """SQLite veritabanı işlemlerini yönetir."""
    def __init__(self):
        self.db_path = settings.DATABASE_FILE_PATH
        self._ensure_db_directory()
        self._create_tables_if_not_exists()

    def _ensure_db_directory(self):
        """Veritabanı dosyasının bulunacağı 'data' dizininin var olduğundan emin olur."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Veritabanına bir bağlantı nesnesi döndürür."""
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.Error as e:
            logger.critical(f"FATAL: Could not connect to database at {self.db_path}: {e}")
            raise

    def _create_tables_if_not_exists(self):
        """Gerekli tüm tabloları (readings, anomalies) oluşturur."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Okumalar Tablosu
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                height_mm REAL,
                weight_g REAL,
                temperature_c REAL,
                humidity_perc REAL,
                snow_height_mm REAL,
                density_kg_m3 REAL,
                height_status TEXT,
                weight_status TEXT,
                temperature_status TEXT,
                humidity_status TEXT,
                temp_hum_source TEXT 
            )
            ''')
            
            # Yeni Anomali Tablosu
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                metric TEXT NOT NULL,
                anomaly_type TEXT NOT NULL,
                details TEXT
            )
            ''')

            conn.commit()
            conn.close()
            logger.info(f"Database tables are ready at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to create tables: {e}")

    def save_reading(self, reading: ProcessedReading):
        """Tek bir işlenmiş okumayı (ProcessedReading) veritabanına kaydeder."""
        sql = '''
        INSERT INTO readings (
            timestamp, height_mm, weight_g, temperature_c, humidity_perc, 
            snow_height_mm, density_kg_m3, height_status, weight_status,
            temperature_status, humidity_status, temp_hum_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        data_tuple = (
            reading.timestamp.isoformat(),
            reading.height_mm,
            reading.weight_g,
            reading.temperature_c,
            reading.humidity_perc,
            reading.snow_height_mm,
            reading.density_kg_m3,
            reading.height_status,
            reading.weight_status,
            reading.temperature_status,
            reading.humidity_status,
            reading.temp_hum_source,
        )

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, data_tuple)
            conn.commit()
            conn.close()
            logger.debug(f"Successfully saved a reading to the database with timestamp {reading.timestamp}.")
        except sqlite3.Error as e:
            logger.error(f"Failed to save reading to database: {e}")

    def save_anomaly(self, metric: str, anomaly_type: str, details: str):
        """Tespit edilen bir anomaliyi veritabanına kaydeder."""
        sql = "INSERT INTO anomalies (timestamp, metric, anomaly_type, details) VALUES (?, ?, ?, ?)"
        data_tuple = (datetime.now().isoformat(), metric, anomaly_type, details)
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, data_tuple)
            conn.commit()
            conn.close()
            logger.warning(f"Anomaly saved to DB: {metric} - {anomaly_type}")
        except sqlite3.Error as e:
            logger.error(f"Failed to save anomaly to database: {e}")

    def count_anomalies_since(self, start_time: datetime) -> int:
        """Belirtilen zamandan bu yana kaydedilen anomali sayısını döndürür."""
        sql = "SELECT COUNT(*) FROM anomalies WHERE timestamp >= ?"
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, (start_time.isoformat(),))
            count_result = cursor.fetchone()
            conn.close()
            return count_result[0] if count_result else 0
        except sqlite3.Error as e:
            logger.error(f"Failed to count anomalies: {e}")
            return -1

    def get_latest_reading(self) -> Optional[ProcessedReading]:
        """Veritabanındaki en son kaydı bir ProcessedReading nesnesi olarak döndürür."""
        sql = "SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1"
        try:
            conn = self._get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql)
            row = cursor.fetchone()
            conn.close()

            if row:
                return ProcessedReading(
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    height_mm=row['height_mm'],
                    weight_g=row['weight_g'],
                    temperature_c=row['temperature_c'],
                    humidity_perc=row['humidity_perc'],
                    snow_height_mm=row['snow_height_mm'],
                    density_kg_m3=row['density_kg_m3'],
                    height_status=row['height_status'],
                    weight_status=row['weight_status'],
                    temperature_status=row['temperature_status'],
                    humidity_status=row['humidity_status'],
                    temp_hum_source=row['temp_hum_source']
                )
            return None
        except sqlite3.Error as e:
            logger.error(f"Failed to get the latest reading from database: {e}")
            return None