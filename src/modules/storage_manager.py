import os
import sqlite3

class StorageManager:
    def __init__(self, db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        print(f"INFO: Veritabanı bağlantısı başarılı: {db_path}")
        self._create_table()
    def _create_table(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY, timestamp TEXT, distance_mm INTEGER, weight_g INTEGER,
            temperature_c REAL, humidity_percent REAL, snow_height_mm INTEGER,
            density_kg_m3 REAL, swe_mm REAL)""")
        self.conn.commit()
    def save_reading(self, data):
        sql = """INSERT INTO readings(timestamp, distance_mm, weight_g, temperature_c, 
            humidity_percent, snow_height_mm, density_kg_m3, swe_mm) VALUES(?,?,?,?,?,?,?,?)"""
        record = tuple(data.get(k) for k in ['timestamp', 'distance_mm', 'weight_g', 'temperature_c', 'humidity_percent', 'snow_height_mm', 'density_kg_m3', 'swe_mm'])
        cursor = self.conn.cursor(); cursor.execute(sql, record); self.conn.commit()
        print(f"INFO: Yeni kayıt veritabanına eklendi (ID: {cursor.lastrowid})")
    def shutdown(self):
        if self.conn: self.conn.close(); print("INFO: Veritabanı bağlantısı kapatıldı.")