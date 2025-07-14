import os
import requests
from dotenv import load_dotenv

class WeatherApiManager:
    def __init__(self, config):
        self.config = config.get('openweathermap', {})
        if not self.config.get('enabled'):
            self.api_key = None
            return
        load_dotenv()
        api_key_var = self.config.get('api_key_env_var')
        self.api_key = os.getenv(api_key_var)
        if not self.api_key:
            print(f"WARNING: OpenWeatherMap API anahtarı '{api_key_var}' bulunamadı. Yedekleme pasif.")
            return
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.params = {'appid': self.api_key, 'units': self.config.get('units', 'metric')}
        if 'lat' in self.config and 'lon' in self.config:
            self.params.update({'lat': self.config['lat'], 'lon': self.config['lon']})
        elif 'city_id' in self.config:
            self.params['id'] = self.config['city_id']
        self.cached_data = {}
        print("INFO: WeatherApiManager başlatıldı.")

    def get_weather_data(self):
        if not self.api_key: return None
        try:
            print("INFO: OpenWeatherMap API'sine bağlanılıyor...")
            response = requests.get(self.base_url, params=self.params, timeout=15)
            response.raise_for_status()
            data = response.json()
            self.cached_data = {'temperature_c': data['main']['temp'], 'humidity_percent': data['main']['humidity']}
            print(f"SUCCESS: OpenWeatherMap verisi alındı: Temp={self.cached_data['temperature_c']}°C, Hum={self.cached_data['humidity_percent']}%")
            return self.cached_data
        except Exception as e:
            print(f"ERROR: OpenWeatherMap API hatası: {e}")
            return None

    def get_cached_data(self): return self.cached_data
    def shutdown(self): pass