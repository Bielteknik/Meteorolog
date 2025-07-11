# app/services/remote_api_service.py
import logging
import requests
from typing import Optional
from datetime import datetime

from app.config import settings
from app.models.schemas import ProcessedReading

logger = logging.getLogger(__name__)

class RemoteApiService:
    """
    İşlenmiş verileri belirtilen bir JSON API uç noktasına gönderir.
    """
    def __init__(self):
        self.api_url = settings.REMOTE_API_ENDPOINT
        self.enabled = bool(self.api_url)

    def post_reading(self, reading: ProcessedReading) -> bool:
        """
        Verilen ProcessedReading nesnesini JSON formatında API'ye gönderir.
        """
        if not self.enabled:
            logger.debug("Remote API posting is disabled. No API endpoint set in settings.")
            return False

        if not reading:
            logger.warning("post_reading called with no reading data. Aborting.")
            return False

        try:
            # API'nin beklediği JSON formatında verileri hazırlayalım
            # None gelen değerler için "0" gibi varsayılan bir değer atayalım
            payload = {
                "tarih": reading.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "sicaklik": int(round(reading.temperature_c, 0)) if reading.temperature_c is not None else 0,
                "nem": int(round(reading.humidity_perc, 0)) if reading.humidity_perc is not None else 0,
                "mesafe": int(round(reading.height_mm, 0)) if reading.height_mm is not None else 0,
                "agirlik": int(round(reading.weight_g, 0)) if reading.weight_g is not None else 0,
                "karyuksekligi": int(round(reading.snow_height_mm, 0)) if reading.snow_height_mm is not None else 0,
            }

            logger.info(f"Posting JSON data to {self.api_url}: {payload}")
            
            # Form verisi yerine JSON gönderiyoruz, bu yüzden `json=` parametresini kullanıyoruz.
            # Bu, Content-Type başlığını otomatik olarak 'application/json' olarak ayarlar.
            response = requests.post(self.api_url, json=payload, timeout=20)
            
            response.raise_for_status() # 2xx dışındaki durum kodları için bir hata fırlatır.

            logger.info(f"Successfully posted data to API. Status: {response.status_code}")
            return True

        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to post data. HTTP Error: {e.response.status_code}. Response: {e.response.text[:200]}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while trying to post data to API: {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error in post_reading: {e}", exc_info=True)
            return False