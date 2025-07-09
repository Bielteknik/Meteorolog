import sqlite3
import pathlib
from typing import List

from app.config import _settings
from app.models.schemas import ProcessedReading

class DatabaseService:
    """Veritabanı işlemlerini (oluşturma, kaydetme) yönetir."""
    def __init__(self, db_path: str = _settings.DATABASE_FILE_PATH):
        self.db_path = db_path
        self._ensure_db_directory()
        self._create_table()

    def _ensure_db_directory(self):
        """Veritabanı dosyasının bulunacağı dizinin var olduğundan emin olur."""
        pathlib.Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        """Gerekli tabloyu oluşturur."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            height_mm REAL,
            weight_g REAL,
            temperature_c REAL,
            humidity_perc REAL,
            snow_height_mm REAL,
            density_kg_m3 REAL
        )
        ''')
        conn.commit()
        conn.close()

    def save_reading(self, reading: ProcessedReading):
        """Tek bir işlenmiş okumayı veritabanına kaydeder."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO readings (
            timestamp, height_mm, weight_g, temperature_c, humidity_perc, 
            snow_height_mm, density_kg_m3
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            reading.timestamp.isoformat(), reading.height_mm, reading.weight_g,
            reading.temperature_c, reading.humidity_perc,
            reading.snow_height_mm, reading.density_kg_m3
        ))
        conn.commit()
        conn.close()
        
    def save_bulk_readings(self, readings: List[ProcessedReading]):
        """Birden fazla okumayı tek seferde veritabanına kaydeder."""
        conn = self._get_connection()
        cursor = conn.cursor()
        data_to_insert = [
            (
                r.timestamp.isoformat(), r.height_mm, r.weight_g,
                r.temperature_c, r.humidity_perc,
                r.snow_height_mm, r.density_kg_m3
            ) for r in readings
        ]
        cursor.executemany('''
        INSERT INTO readings (
            timestamp, height_mm, weight_g, temperature_c, humidity_perc, 
            snow_height_mm, density_kg_m3
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', data_to_insert)
        conn.commit()
        conn.close()