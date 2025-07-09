import pandas as pd
import pathlib
from datetime import datetime
from typing import List

from app.config import _settings
from app.models.schemas import ProcessedReading

class CsvStorageService:
    """Verileri günlük CSV dosyalarına kaydeder."""
    def __init__(self, folder_path: str = _settings.CSV_FOLDER):
        self.folder_path = pathlib.Path(folder_path)
        self._ensure_csv_directory()
    
    def _ensure_csv_directory(self):
        """CSV dosyalarının bulunacağı dizinin var olduğundan emin olur."""
        self.folder_path.mkdir(parents=True, exist_ok=True)

    def save_readings_to_csv(self, readings: List[ProcessedReading]):
        """
        Verilen okuma listesini, günün tarihine göre adlandırılmış 
        bir CSV dosyasına ekler.
        """
        if not readings:
            return

        today_str = datetime.now().strftime('%Y%m%d')
        file_path = self.folder_path / f"{_settings.LOG_FILE_PREFIX}_{today_str}.csv"

        # Okuma listesini bir pandas DataFrame'e dönüştür
        df_new = pd.DataFrame([r.model_dump() for r in readings])
        
        # Timestamp sütununu daha okunabilir bir formata getir
        df_new['timestamp'] = pd.to_datetime(df_new['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

        # Dosya zaten varsa, başlık olmadan ekle. Yoksa, başlıkla oluştur.
        header = not file_path.exists()
        df_new.to_csv(file_path, mode='a', header=header, index=False)
        print(f"💾 {len(readings)} okuma '{file_path.name}' dosyasına kaydedildi.")