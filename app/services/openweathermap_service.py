import logging
import requests
from typing import Optional, Tuple
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

class OpenWeatherMapService:
    """
    OpenWeatherMap API'sinden hava durumu verilerini almak için durum bilgisi tutan (stateful) bir servis.
    Veriyi önbelleğe alır ve sadece saat başlarında günceller.
    """
    def __init__(self):
        self.api_key = settings.OWM_API_KEY
        self.lat = settings.OWM_LATITUDE
        self.lon = settings.OWM_LONGITUDE
        self.api_url = f"https://api.openweathermap.org/data/2.5/weather?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"
        self.enabled = bool(self.api_key and self.lat and self.lon)

        # Önbellek ve durum yönetimi için değişkenler
        self.cached_data: Optional[Tuple[float, float]] = None
        self.last_update_time: Optional[datetime] = None
        self.is_fallback_active: bool = False # I2C'nin genel olarak arızalı olup olmadığını belirtir

        if not self.enabled:
            logger.warning("OpenWeatherMap service is disabled due to missing API key or location settings.")

    def _fetch_from_api(self) -> Optional[Tuple[float, float]]:
        """API'den veri çekme işlemini gerçekleştiren özel (private) metod."""
        if not self.enabled:
            return None
        logger.info("Attempting to fetch fresh data from OpenWeatherMap API...")
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            temp = data.get("main", {}).get("temp")
            humidity = data.get("main", {}).get("humidity")
            if temp is not None and humidity is not None:
                logger.info(f"Successfully fetched data from OpenWeatherMap: Temp={temp}°C, Hum={humidity}%")
                return float(temp), float(humidity)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get data from OpenWeatherMap API: {e}")
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing OpenWeatherMap API response: {e}")
        return None

    def update_cache(self, force_update: bool = False):
        """
        Önbelleği API'den gelen yeni verilerle günceller.
        'force_update=True' bayrağı, zaman kontrolü yapmadan güncelleme yapar.
        """
        now = datetime.now()
        # Eğer zorunlu güncelleme istenmiyorsa, zaman kontrolü yap
        if not force_update:
            # Henüz hiç güncelleme yapılmadıysa veya son güncelleme farklı bir saatteyse, güncelle
            if self.last_update_time and self.last_update_time.hour == now.hour:
                logger.debug("OWM cache is up-to-date for the current hour. Skipping API call.")
                return

        new_data = self._fetch_from_api()
        if new_data:
            self.cached_data = new_data
            self.last_update_time = now
            logger.info("OpenWeatherMap cache has been updated.")
        else:
            logger.error("Failed to update OpenWeatherMap cache.")

    def get_fallback_data(self) -> Optional[Tuple[float, float]]:
        """
        Yedek mod aktif olduğunda çağrılır. Gerekirse önbelleği günceller
        ve ardından önbellekteki veriyi döndürür.
        """
        if not self.is_fallback_active or not self.enabled:
            return None

        # Eğer önbellek boşsa (ilk hata) veya saat başıysa, güncelle.
        if self.cached_data is None or (self.last_update_time and self.last_update_time.hour != datetime.now().hour):
             self.update_cache()

        return self.cached_data