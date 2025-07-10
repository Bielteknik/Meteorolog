import logging
from typing import Dict, Optional, Tuple, List

from app.config import settings
from app.models.schemas import ProcessedReading

logger = logging.getLogger(__name__)

ANOMALY_THRESHOLDS = {
    "temperature_c": 10.0,
    "humidity_perc": 30.0,
    "snow_height_mm": 50.0,
}
STALL_DETECTION_COUNT = 5
WEIGHT_STALL_IGNORE_THRESHOLD_G = 50.0 # 50 gramın altındaki ağırlık donmalarını önemseme

class AnomalyService:
    def __init__(self):
        self.last_valid_reading: Optional[ProcessedReading] = None
        self.stall_counters: Dict[str, int] = {
            "temperature_c": 0, "humidity_perc": 0, "height_mm": 0, "weight_g": 0
        }
        self.last_stall_values: Dict[str, Optional[float]] = {k: None for k in self.stall_counters}
        logger.info("Anomaly detection service initialized.")

    def check_for_anomalies(self, current_reading: ProcessedReading) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Mevcut okumayı analiz eder ve tespit edilen anomalileri döndürür.
        Dönenler: (anomali_durumları, anomali_detayları)
        """
        statuses: Dict[str, str] = {}
        details: Dict[str, str] = {}

        if self.last_valid_reading is None:
            self.update_state(current_reading)
            return statuses, details

        # 1. Sıçrama (Spike) Kontrolü
        for metric, threshold in ANOMALY_THRESHOLDS.items():
            current_value = getattr(current_reading, metric, None)
            last_value = getattr(self.last_valid_reading, metric, None)
            if current_value is not None and last_value is not None:
                if abs(current_value - last_value) > threshold:
                    status_key = f"{metric.split('_')[0]}_status"
                    statuses[status_key] = "ANOMALY_SPIKE"
                    details[metric] = f"SPIKE (Sıçrama) | Değer {last_value:.2f} -> {current_value:.2f} olarak sıçradı."

        # 2. Donma (Stall) Kontrolü
        for metric in self.stall_counters.keys():
            current_value = getattr(current_reading, metric, None)
            if current_value is not None and self.last_stall_values[metric] is not None:
                if abs(current_value - self.last_stall_values[metric]) < 1e-6:
                    self.stall_counters[metric] += 1
                else:
                    self.stall_counters[metric] = 0
            else:
                 self.stall_counters[metric] = 0
            self.last_stall_values[metric] = current_value

            if self.stall_counters[metric] >= STALL_DETECTION_COUNT:
                # Akıllı Ağırlık Kontrolü: Ağırlık çok düşükse bu bir anomali değildir.
                if metric == "weight_g" and current_value is not None and current_value < WEIGHT_STALL_IGNORE_THRESHOLD_G:
                    self.stall_counters[metric] = 0 # Sayacı sıfırla ve devam et
                    continue

                status_key = f"{metric.split('_')[0]}_status"
                statuses[status_key] = "ANOMALY_STALL"
                details[metric] = f"STALL (Donma) | Sensör {self.stall_counters[metric]} defa aynı değeri raporladı: {current_value}"
                self.stall_counters[metric] = 0

        self.update_state(current_reading)
        return statuses, details

    def update_state(self, reading: ProcessedReading):
        if any(v is not None for k, v in reading.model_dump().items() if 'mm' in k or 'g' in k or 'c' in k or 'perc' in k):
            self.last_valid_reading = reading