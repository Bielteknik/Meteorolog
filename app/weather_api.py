from typing import Optional, Tuple
import requests
from .config import settings

class WeatherAPI:
    """OpenWeatherMap API'sinden veri almak için kullanılır."""
    
    def get_backup_data(self) -> Optional[Tuple[float, float]]:
        """
        OpenWeatherMap'ten yedek sıcaklık ve nem verisi çeker.
        """
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            'lat': settings.api.latitude,
            'lon': settings.api.longitude,
            'appid': settings.secrets.openweathermap_key,
            'units': 'metric' # Sıcaklığı Santigrat olarak almak için
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # HTTP 4xx veya 5xx hatası varsa exception fırlat
            data = response.json()
            
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            print(f"  🌦️  Yedek API'den veri alındı: {temp}°C, {humidity}%")
            return (temp, humidity)
        except requests.exceptions.RequestException as e:
            print(f"  ❌ OpenWeatherMap API hatası: {e}")
            return None