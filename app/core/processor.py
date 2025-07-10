import logging
from typing import List, Tuple, Dict
import pandas as pd
from app.config import settings
from app.models.schemas import RawSensorData, ProcessedReading
from app.sensors.parsers import (
    parse_height_from_raw, parse_weight_from_raw, parse_temp_hum_from_raw
)
from app.services.anomaly_service import AnomalyService

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.anomaly_service = AnomalyService()

    def _validate_value(self, value: float | None, metric_name: str) -> Tuple[float | None, str]:
        # ... Bu metodda değişiklik yok ...
        if value is None: return None, "NO_DATA"
        min_val, max_val = settings.VALIDATION_RANGES.get(metric_name, (None, None))
        if min_val is not None and max_val is not None and not (min_val <= value <= max_val):
            logger.warning(f"Validation failed for {metric_name}: value {value} is out of range ({min_val}, {max_val}).")
            return None, "OUT_OF_RANGE"
        return value, "OK"

    def process_single_reading(self, raw_data: RawSensorData) -> Tuple[ProcessedReading, Dict[str, str]]:
        """
        Tek bir ham okumayı işler ve işlenmiş okuma ile birlikte anomali detaylarını döndürür.
        """
        height = parse_height_from_raw(raw_data.height_raw)
        weight = parse_weight_from_raw(raw_data.weight_raw)
        temp, hum, source = None, None, "local"
        if raw_data.temp_hum_raw:
            temp, hum = parse_temp_hum_from_raw(raw_data.temp_hum_raw)
        elif raw_data.temp_hum_api:
            temp, hum = raw_data.temp_hum_api
            source = "api"
        
        valid_height, height_status = self._validate_value(height, "height_mm")
        valid_weight, weight_status = self._validate_value(weight, "weight_g")
        valid_temp, temp_status = self._validate_value(temp, "temperature_c")
        valid_hum, hum_status = self._validate_value(hum, "humidity_perc")

        snow_height = self._calculate_snow_height(valid_height)
        density = self._calculate_density(valid_weight, snow_height)

        processed_reading = ProcessedReading(
            timestamp=raw_data.timestamp,
            height_mm=valid_height, weight_g=valid_weight, temperature_c=valid_temp, humidity_perc=valid_hum,
            snow_height_mm=snow_height, density_kg_m3=density,
            height_status=height_status, weight_status=weight_status, temperature_status=temp_status, humidity_status=hum_status,
            temp_hum_source=source
        )
        
        anomaly_statuses, anomaly_details = self.anomaly_service.check_for_anomalies(processed_reading)
        
        if anomaly_statuses:
            for status_key, status_value in anomaly_statuses.items():
                setattr(processed_reading, status_key, status_value)
        
        return processed_reading, anomaly_details

    def analyze_burst_readings(self, readings: List[ProcessedReading]) -> ProcessedReading:
        # ... Bu metodda değişiklik yok ...
        if not readings: return ProcessedReading()
        df = pd.DataFrame([r.model_dump() for r in readings])
        summary = ProcessedReading()
        summary.timestamp = pd.to_datetime(df['timestamp']).max().to_pydatetime()
        numeric_cols = ["height_mm", "weight_g", "temperature_c", "humidity_perc", "snow_height_mm", "density_kg_m3"]
        for col in numeric_cols:
            if col in df and not df[col].isnull().all():
                setattr(summary, col, df[col].mean(skipna=True))
        status_cols = ["height_status", "weight_status", "temperature_status", "humidity_status", "temp_hum_source"]
        for col in status_cols:
             if col in df and not df[col].empty:
                setattr(summary, col, df[col].mode()[0])
        return summary

    def _calculate_snow_height(self, height_mm: float | None) -> float | None:
        if height_mm is None: return None
        return max(0.0, settings.SENSOR_ZERO_DISTANCE_MM - height_mm)

    def _calculate_density(self, weight_g: float | None, snow_height_mm: float | None) -> float | None:
        if weight_g is None or snow_height_mm is None or snow_height_mm <= 0: return None
        try:
            mass_kg = weight_g / 1000.0; snow_height_m = snow_height_mm / 1000.0
            volume_m3 = settings.MEASUREMENT_AREA_M2 * snow_height_m
            return round(mass_kg / volume_m3, 2)
        except ZeroDivisionError: return None