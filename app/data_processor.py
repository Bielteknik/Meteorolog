import re
from typing import Dict, Any, Optional, Tuple

from .config import settings
from .weather_api import WeatherAPI

class DataProcessor:
    """
    Ham sensör verilerini işler, metrikleri hesaplar ve anlamlı hale getirir.
    """
    def __init__(self):
        self.weather_api = WeatherAPI()

    def _parse_height(self, raw_height: Optional[str]) -> Optional[float]:
        """'R3650' formatındaki veriyi float'a çevirir."""
        if raw_height and raw_height.startswith('R'):
            try:
                # 'R' harfinden sonrasını al ve sayıya çevir
                return float(raw_height[1:])
            except (ValueError, TypeError):
                return None
        return None

    def _parse_weight(self, raw_weight: Optional[str]) -> Optional[float]:
        """'=12.34' formatındaki veriyi kg'a çevirir (185.56 -> 185.56 kg)."""
        if raw_weight and raw_weight.startswith('='):
            try:
                # '=' karakterinden sonrasını al ve sayıya çevir
                return float(raw_weight[1:])
            except (ValueError, TypeError):
                return None
        return None

    def process(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ham veri sözlüğünü alır ve işlenmiş, zenginleştirilmiş bir sözlük döndürür.
        """
        processed_data = {
            "temperature_c": None,
            "humidity_percent": None,
            "snow_height_mm": None,
            "snow_weight_kg": None,
            "snow_density_kg_m3": None,
            "swe_mm": None,
            "data_source": "sensor"
        }

        # Adım 1: Sıcaklık ve Nem verisini işle veya yedekten al
        if raw_data.get("temp_hum_raw"):
            processed_data["temperature_c"] = raw_data["temp_hum_raw"][0]
            processed_data["humidity_percent"] = raw_data["temp_hum_raw"][1]
        else:
            # Fiziksel sensörden veri gelmediyse, API'den yedek veri çek
            print("  ⚠️ Fiziksel sıcaklık sensörü verisi yok. Yedek API'ye başvuruluyor...")
            backup_data = self.weather_api.get_backup_data()
            if backup_data:
                processed_data["temperature_c"] = backup_data[0]
                processed_data["humidity_percent"] = backup_data[1]
                processed_data["data_source"] = "api_backup"

        # Adım 2: Ham mesafe ve ağırlığı parse et
        distance_mm = self._parse_height(raw_data.get("height_raw"))
        weight_kg = self._parse_weight(raw_data.get("weight_raw"))

        # Adım 3: Ana metrikleri hesapla
        if distance_mm is not None:
            # Kar Yüksekliği (mm) = Referans Yükseklik - Ölçülen Mesafe
            snow_height = settings.sensors.height_sensor_zero_mm - distance_mm
            processed_data["snow_height_mm"] = max(0, snow_height) # Negatif olamaz

        if weight_kg is not None:
            processed_data["snow_weight_kg"] = weight_kg

        # Adım 4: Yoğunluk ve SWE'yi hesapla (eğer yeterli veri varsa)
        snow_height_m = processed_data.get("snow_height_mm")
        if snow_height_m is not None and snow_height_m > 0 and weight_kg is not None:
            snow_height_m /= 1000 # mm'yi metreye çevir
            
            # Hacim (m³) = Ölçüm Alanı (m²) * Kar Yüksekliği (m)
            volume_m3 = settings.station.measurement_area_m2 * snow_height_m
            
            # Yoğunluk (kg/m³) = Kütle (kg) / Hacim (m³)
            if volume_m3 > 0:
                density = weight_kg / volume_m3
                processed_data["snow_density_kg_m3"] = density
                
                # SWE (mm) = Kar Yüksekliği (mm) * (Kar Yoğunluğu / Su Yoğunluğu)
                # Su Yoğunluğu ~ 1000 kg/m³
                swe = processed_data["snow_height_mm"] * (density / 1000.0)
                processed_data["swe_mm"] = swe

        return processed_data