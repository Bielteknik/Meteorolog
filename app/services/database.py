import sqlite3
import logging
from pathlib import Path
from typing import List

from app.config import settings
from app.models.schemas import ProcessedReading

logger = logging.getLogger(__name__)

class DatabaseService:
    """SQLite veritabanı işlemlerini yönetir."""
    def __init__(self):
        self.db_path = settings.DATABASE_FILE_PATH
        self._ensure_db_directory()
        self._create_table_if_not_exists()

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

    def _create_table_if_not_exists(self):
        """'readings' tablosunu, eğer mevcut değilse, oluşturur."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
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
                humidity_status TEXT
            )
            ''')
            conn.commit()
            conn.close()
            logger.info(f"Database table 'readings' is ready at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to create 'readings' table: {e}")


    def save_reading(self, reading: ProcessedReading):
        """Tek bir işlenmiş okumayı (ProcessedReading) veritabanına kaydeder."""
        sql = '''
        INSERT INTO readings (
            timestamp, height_mm, weight_g, temperature_c, humidity_perc, 
            snow_height_mm, density_kg_m3, height_status, weight_status,
            temperature_status, humidity_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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