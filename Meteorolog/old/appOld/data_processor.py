import re
from typing import Dict, Any, Optional, Tuple

from .config import settings
from .weather_api import WeatherAPI
from rich.console import Console

console = Console()

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
                return float(raw_height[1:])
            except (ValueError, TypeError):
                return None
        return None

    def _parse_weight(self, raw_weight: Optional[str]) -> Optional[float]:
        """'=12.34' formatındaki veriyi kg'a çevirir."""
        if raw_weight and raw_weight.startswith('='):
            try:
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
            "distance_mm": None,
            "snow_weight_kg": 0.0,
            "snow_height_mm": 0.0,
            "snow_density_kg_m3": 0.0,
            "swe_mm": 0.0,
            "data_source": "sensor"
        }

        if raw_data.get("temp_hum_raw"):
            processed_data["temperature_c"] = raw_data["temp_hum_raw"][0]
            processed_data["humidity_percent"] = raw_data["temp_hum_raw"][1]
        else:
            console.print("  [yellow]⚠️ Fiziksel sıcaklık sensörü verisi yok. Yedek API'ye başvuruluyor...[/yellow]")
            backup_data = self.weather_api.get_backup_data()
            if backup_data:
                processed_data["temperature_c"] = backup_data[0]
                processed_data["humidity_percent"] = backup_data[1]
                processed_data["data_source"] = "api_backup"

        distance_mm = self._parse_height(raw_data.get("height_raw"))
        weight_kg = self._parse_weight(raw_data.get("weight_raw"))
        
        processed_data["distance_mm"] = distance_mm
        processed_data["snow_weight_kg"] = weight_kg if weight_kg is not None else 0.0
        
        if distance_mm is not None:
            snow_height = settings.sensors.height_sensor_zero_mm - distance_mm
            processed_data["snow_height_mm"] = max(0.0, snow_height)

        snow_height_mm = processed_data.get("snow_height_mm")
        current_weight_kg = processed_data.get("snow_weight_kg")
        
        if snow_height_mm and snow_height_mm > 0 and current_weight_kg is not None:
            snow_height_m = snow_height_mm / 1000.0
            volume_m3 = settings.station.measurement_area_m2 * snow_height_m
            
            if volume_m3 > 0:
                density = current_weight_kg / volume_m3
                processed_data["snow_density_kg_m3"] = density
                swe = snow_height_mm * (density / 1000.0)
                processed_data["swe_mm"] = swe

        return processed_data