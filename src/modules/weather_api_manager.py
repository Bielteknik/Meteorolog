# Dosya: Meteorolog/src/modules/weather_api_manager.py
import os
import requests
from dotenv import load_dotenv

class WeatherApiManager:
    """
    OpenWeatherMap API'sinden veri alır ve yönetir.
    """
    def __init__(self, config):
        self.config = config.get('openweathermap', {})
        if not self.config.get('enabled'):
            self.api_key = None
            print("INFO: OpenWeatherMap modülü pasif.")
            return

        # .env dosyasını veya sistem çevre değişkenlerini yükle
        load_dotenv()
        # API anahtarını çevre değişkeninden oku
        api_key_var = self.config.get('api_key_env_var')
        self.api_key = os.getenv(api_key_var)

        if not self.api_key:
            print(f"CRITICAL: OpenWeatherMap API anahtarı '{api_key_var}' çevre değişkeninde bulunamadı!")
            return

        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.lat = self.config.get('lat')
        self.lon = self.config.get('lon')
        self.city_id = self.config.get('city_id')
        self.units = self.config.get('units', 'metric')
        
        # En son başarılı okumayı saklamak için önbellek
        self.cached_data = {}
        print("INFO: WeatherApiManager başlatıldı.")

    def get_weather_data(self):
        """API'den güncel hava durumu verisini çeker."""
        if not self.api_key:
            return None

        params = {
            'appid': self.api_key,
            'units': self.units,
        }
        if self.lat and self.lon:
            params['lat'] = self.lat
            params['lon'] = self.lon
        elif self.city_id:
            params['id'] = self.city_id
        else:
            print("ERROR: Konum bilgisi (lat/lon veya city_id) yapılandırmada eksik.")
            return None
            
        try:
            print("INFO: OpenWeatherMap API'sine bağlanılıyor...")
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status() # Hatalı durum kodları için (4xx, 5xx) exception fırlat
            
            data = response.json()
            temp = data['main']['temp']
            humidity = data['main']['humidity']
            
            print(f"SUCCESS: OpenWeatherMap verisi alındı: Temp={temp}°C, Hum={humidity}%")
            
            # Önbelleği güncelle
            self.cached_data = {'temperature_c': temp, 'humidity_percent': humidity}
            return self.cached_data
            
        except requests.exceptions.RequestException as e:
            print(f"ERROR: OpenWeatherMap API bağlantı hatası: {e}")
            return None
        except KeyError:
            print("ERROR: OpenWeatherMap'ten gelen yanıtta beklenen veri bulunamadı.")
            return None

    def get_cached_data(self):
        """Önbellekteki son başarılı veriyi döndürür."""
        return self.cached_data