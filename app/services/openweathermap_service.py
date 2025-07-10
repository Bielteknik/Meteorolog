# app/services/openweathermap_service.py
import logging, requests
from typing import Optional, Tuple
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)

class OpenWeatherMapService:
    def __init__(self):
        self.api_key = settings.OWM_API_KEY; self.lat = settings.OWM_LATITUDE; self.lon = settings.OWM_LONGITUDE
        self.api_url = f"https://api.openweathermap.org/data/2.5/weather?lat={self.lat}&lon={self.lon}&appid={self.api_key}&units=metric"
        self.enabled = bool(self.api_key and self.lat and self.lon)
        self.cached_data: Optional[Tuple[float, float]] = None
        self.last_update_time: Optional[datetime] = None
        self.is_fallback_active: bool = False
        if not self.enabled: logger.warning("OWM service is disabled due to missing API key or location.")

    def _fetch_from_api(self) -> Optional[Tuple[float, float]]:
        if not self.enabled: return None
        # Bu log kaldırıldı.
        # logger.info("Attempting to fetch fresh data from OpenWeatherMap API...")
        try:
            response = requests.get(self.api_url, timeout=10); response.raise_for_status()
            data = response.json()
            temp = data.get("main", {}).get("temp"); humidity = data.get("main", {}).get("humidity")
            if temp is not None and humidity is not None:
                # Bu log kaldırıldı.
                # logger.info(f"Successfully fetched data from OWM: Temp={temp}°C, Hum={humidity}%")
                return float(temp), float(humidity)
        except requests.exceptions.RequestException as e: logger.error(f"Failed to get data from OWM API: {e}")
        except (KeyError, ValueError) as e: logger.error(f"Error parsing OWM API response: {e}")
        return None

    def update_cache(self, force_update: bool = False):
        now = datetime.now()
        if not force_update and self.last_update_time and self.last_update_time.hour == now.hour:
            return
        new_data = self._fetch_from_api()
        if new_data:
            self.cached_data = new_data; self.last_update_time = now
            # Bu log kaldırıldı.
            # logger.info("OpenWeatherMap cache has been updated.")
        else: logger.error("Failed to update OpenWeatherMap cache.")

    def get_fallback_data(self) -> Optional[Tuple[float, float]]:
        if not self.is_fallback_active or not self.enabled: return None
        if self.cached_data is None or (self.last_update_time and self.last_update_time.hour != datetime.now().hour):
             self.update_cache()
        return self.cached_data