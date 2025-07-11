import logging
from typing import Dict, Optional

from app.models.schemas import ProcessedReading

logger = logging.getLogger(__name__)

ANOMALY_THRESHOLDS = {
    "temperature_c": 10.0,
    "humidity_perc": 30.0,
    "snow_height_mm": 50.0,
}
STALL_DETECTION_COUNT = 5

class AnomalyService:
    """
    Gelen verilerdeki ani sıçramaları (spike) ve donmaları (stall) tespit eder
    ve veritabanına kaydeder.
    """
    def __init__(self, db_service):
        self.db_service = db_service
        self.last_valid_reading: Optional[ProcessedReading] = None
        self.stall_counters: Dict[str, int] = {
            "temperature_c": 0,
            "humidity_perc": 0,
            "height_mm": 0,
            "weight_g": 0
        }
        self.last_stall_values: Dict[str, Optional[float]] = {k: None for k in self.stall_counters}
        logger.info("Anomaly detection service initialized.")

    def check_for_anomalies(self, current_reading: ProcessedReading):
        """
        Mevcut okumayı bir öncekiyle karşılaştırır ve anomali varsa veritabanına kaydeder.
        """
        if self.last_valid_reading is None:
            logger.debug("First reading received, skipping anomaly checks.")
            self.update_state(current_reading)
            return

        # Sıçrama (Spike) Kontrolü
        for metric, threshold in ANOMALY_THRESHOLDS.items():
            current_value = getattr(current_reading, metric, None)
            last_value = getattr(self.last_valid_reading, metric, None)
            if current_value is not None and last_value is not None:
                if abs(current_value - last_value) > threshold:
                    details = f"Value jumped from {last_value:.2f} to {current_value:.2f}."
                    self.db_service.save_anomaly(metric, "SPIKE", details)

        # Donma (Stall) Kontrolü
        for metric in self.stall_counters.keys():
            current_value = getattr(current_reading, metric, None)
            if current_value is not None and self.last_stall_values.get(metric) is not None:
                if abs(current_value - self.last_stall_values[metric]) < 1e-6:
                    self.stall_counters[metric] += 1
                else:
                    self.stall_counters[metric] = 0
            else:
                 self.stall_counters[metric] = 0
            
            self.last_stall_values[metric] = current_value

            if self.stall_counters[metric] >= STALL_DETECTION_COUNT:
                details = f"Sensor has been reporting the same value ({current_value}) for {STALL_DETECTION_COUNT} cycles."
                self.db_service.save_anomaly(metric, "STALL", details)
                self.stall_counters[metric] = 0

        self.update_state(current_reading)

    def update_state(self, reading: ProcessedReading):
        """Servisin durumunu son geçerli okuma ile günceller."""
        if any(v is not None for k, v in reading.model_dump().items() if 'mm' in k or 'g' in k or 'c' in k or 'perc' in k):
            self.last_valid_reading = reading