import json
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

class ApiClient:
    """Uzak sunucu API'sine veri göndermek için kullanılır."""
    
    def send_hourly_summary(self, summary_data: dict) -> bool:
        """
        Saatlik özet verisini alır ve ana API'ye gönderir.
        Başarılı olursa True, başarısız olursa False döndürür.
        """
        url = settings.api.base_url
        headers = {'Content-Type': 'application/json'}
        
        # Veriyi JSON formatına çevir
        try:
            payload = json.dumps(summary_data)
        except Exception as e:
            print(f"  ❌ API verisi JSON'a çevrilirken hata: {e}")
            return False

        print(f"  🛰️  API'ye gönderiliyor: {url}")
        print(f"  [dim]Payload: {payload}[/dim]")

        try:
            response = requests.post(url, data=payload, headers=headers, timeout=15)
            # 2xx ile başlayan başarılı durum kodlarını kontrol et
            if 200 <= response.status_code < 300:
                print(f"  ✅ API'ye veri başarıyla gönderildi. Status: {response.status_code}")
                return True
            else:
                print(f"  ❌ API gönderimi başarısız. Status: {response.status_code}, Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"  ❌ API bağlantı hatası: {e}")
            return False