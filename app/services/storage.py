import logging
from pathlib import Path
from typing import List

import pandas as pd
from app.config import settings
from app.models.schemas import ProcessedReading

logger = logging.getLogger(__name__)

class CsvStorageService:
    """Verileri günlük CSV dosyalarına kaydeder."""
    def __init__(self):
        self.folder_path = Path(settings.CSV_FOLDER)
        self._ensure_csv_directory()

    def _ensure_csv_directory(self):
        """CSV dosyalarının bulunacağı 'data/csv_exports' dizininin var olduğundan emin olur."""
        self.folder_path.mkdir(parents=True, exist_ok=True)

    def save_readings_to_csv(self, readings: List[ProcessedReading]):
        """
        Verilen okuma listesini, günün tarihine göre adlandırılmış 
        bir CSV dosyasına ekler ve sayısal değerleri formatlar.
        """
        if not readings:
            return

        try:
            # Dosya adında 'log' kelimesi gereksiz, kaldıralım.
            today_str = readings[0].timestamp.strftime('%Y%m%d')
            file_path = self.folder_path / f"sensor_data_{today_str}.csv"

            # Okuma listesini bir pandas DataFrame'e dönüştür
            df_new = pd.DataFrame([r.model_dump() for r in readings])
            
            # Timestamp sütununu daha okunabilir bir formata getir
            df_new['timestamp'] = pd.to_datetime(df_new['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

            # YENİ: Ondalıklı sayıları formatla
            # Yuvarlanacak sütunları ve basamak sayılarını belirle
            float_format_map = {
                "height_mm": "%.2f",
                "weight_g": "%.2f",
                "temperature_c": "%.2f",
                "humidity_perc": "%.2f",
                "snow_height_mm": "%.2f",
                "density_kg_m3": "%.2f"
            }
            
            # to_csv fonksiyonu float_format parametresini doğrudan destekler
            header = not file_path.exists()
            df_new.to_csv(
                file_path, 
                mode='a', 
                header=header, 
                index=False, 
                encoding='utf-8',
                float_format='%.2f' # Tüm float'ları 2 basamağa yuvarla
            )
            
            logger.debug(f"{len(readings)} reading(s) saved to '{file_path.name}'.")

        except Exception as e:
            logger.error(f"Failed to save readings to CSV file: {e}")