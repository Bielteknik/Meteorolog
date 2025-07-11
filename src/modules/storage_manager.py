import sqlite3
from datetime import datetime
import os

class StorageManager:
    """
    İşlenmiş verileri SQLite veritabanına kaydeder.
    """
    def __init__(self, db_path):
        """
        Args:
            db_path (str): SQLite veritabanı dosyasının yolu.
        """
        # Veritabanı dosyasının klasörünün var olduğundan emin ol
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            print(f"INFO: Veritabanı klasörü oluşturuldu: {db_dir}")

        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            print(f"INFO: Veritabanı bağlantısı başarılı: {self.db_path}")
            self._create_table()
        except sqlite3.Error as e:
            print(f"CRITICAL: Veritabanı hatası: {e}")
            raise

    def _create_table(self):
        """
        'readings' tablosu yoksa oluşturur.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                distance_mm INTEGER,
                weight_g INTEGER,
                temperature_c REAL,
                humidity_percent REAL,
                snow_height_mm INTEGER,
                density_kg_m3 REAL,
                swe_mm REAL
            )
            """)
            self.conn.commit()
            print("INFO: 'readings' tablosu hazır.")
        except sqlite3.Error as e:
            print(f"ERROR: Tablo oluşturma hatası: {e}")

    def save_reading(self, data):
        """
        Bir okuma setini veritabanına kaydeder.
        
        Args:
            data (dict): Kaydedilecek verileri içeren sözlük.
        """
        sql = ''' INSERT INTO readings(timestamp, distance_mm, weight_g, temperature_c, 
                                     humidity_percent, snow_height_mm, density_kg_m3, swe_mm)
                  VALUES(?,?,?,?,?,?,?,?) '''
        
        # Veri sözlüğünde olmayan anahtarlar için None değeri ata
        record = (
            data.get('timestamp'),
            data.get('distance_mm'),
            data.get('weight_g'),
            data.get('temperature_c'),
            data.get('humidity_percent'),
            data.get('snow_height_mm'),
            data.get('density_kg_m3'),
            data.get('swe_mm')
        )
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, record)
            self.conn.commit()
            print(f"INFO: Yeni kayıt veritabanına eklendi (ID: {cursor.lastrowid})")
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"ERROR: Veritabanına kayıt eklenemedi: {e}")
            return None

    def __del__(self):
        """Nesne yok edildiğinde veritabanı bağlantısını kapatır."""
        if self.conn:
            self.conn.close()