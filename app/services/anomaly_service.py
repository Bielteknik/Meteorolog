# app/services/anomaly_service.py
import logging
from typing import Dict, Optional, Tuple

from app.config import settings
from app.models.schemas import ProcessedReading

logger = logging.getLogger(__name__)

# Anomali eşik değerleri. Bu değerler ayarlanabilir.
# Bir döngüde sıcaklığın 10 dereceden fazla değişmesi bir sıçramadır.
ANOMALY_THRESHOLDS = {
    "temperature_c": 10.0,
    "humidity_perc": 30.0,
    "snow_height_mm": 50.0, # 30dk içinde 5cm'den fazla ani değişim
}
# Bir sensör 5 döngü boyunca aynı değeri verirse "donmuş" kabul edilir.
STALL_DETECTION_COUNT = 5


class AnomalyService:
    """
    Gelen verilerdeki ani sıçramaları (spike) ve donmaları (stall) tespit eder.
    """
    def __init__(self):
        self.last_valid_reading: Optional[ProcessedReading] = None
        self.stall_counters: Dict[str, int] = {
            "temperature_c": 0,
            "humidity_perc": 0,
            "height_mm": 0,
            "weight_g": 0
        }
        self.last_stall_values: Dict[str, Optional[float]] = {k: None for k in self.stall_counters}

        logger.info("Anomaly detection service initialized.")

    def check_for_anomalies(self, current_reading: ProcessedReading) -> Tuple[Dict[str, str], list[str]]:
        """
        Mevcut okumayı bir öncekiyle karşılaştırır ve anomali durumlarını döndürür.
        Döndürülenler: (anomali_durumları, tetiklenen_uyarı_mesajları)
        """
        statuses = {}
        alerts = []

        if self.last_valid_reading is None:
            logger.debug("First reading received, skipping anomaly checks.")
            self.update_state(current_reading)
            return statuses, alerts

        # --- 1. Sıçrama (Spike) Kontrolü ---
        for metric, threshold in ANOMALY_THRESHOLDS.items():
            current_value = getattr(current_reading, metric, None)
            last_value = getattr(self.last_valid_reading, metric, None)

            if current_value is not None and last_value is not None:
                if abs(current_value - last_value) > threshold:
                    status_key = f"{metric.split('_')[0]}_status"
                    statuses[status_key] = "ANOMALY_SPIKE"
                    alert_msg = (
                        f"ANOMALY DETECTED (SPIKE) in '{metric}': "
                        f"Value jumped from {last_value:.2f} to {current_value:.2f}."
                    )
                    logger.warning(alert_msg)
                    alerts.append(alert_msg)

        # --- 2. Donma (Stall) Kontrolü ---
        for metric in self.stall_counters.keys():
            current_value = getattr(current_reading, metric, None)

            if current_value is not None and self.last_stall_values[metric] is not None:
                # Değerler neredeyse aynı mı? (float karşılaştırması için)
                if abs(current_value - self.last_stall_values[metric]) < 1e-6:
                    self.stall_counters[metric] += 1
                else:
                    # Değer değişti, sayacı sıfırla
                    self.stall_counters[metric] = 0
            else:
                 self.stall_counters[metric] = 0
            
            self.last_stall_values[metric] = current_value

            if self.stall_counters[metric] >= STALL_DETECTION_COUNT:
                status_key = f"{metric.split('_')[0]}_status"
                statuses[status_key] = "ANOMALY_STALL"
                alert_msg = (
                    f"ANOMALY DETECTED (STALL) in '{metric}': "
                    f"Sensor has been reporting the same value ({current_value}) for {STALL_DETECTION_COUNT} cycles."
                )
                logger.warning(alert_msg)
                alerts.append(alert_msg)
                # Uyarı tekrar tetiklenmesin diye sayacı sıfırlayalım
                self.stall_counters[metric] = 0

        self.update_state(current_reading)
        return statuses, alerts

    def update_state(self, reading: ProcessedReading):
        """Servisin durumunu son geçerli okuma ile günceller."""
        # Sadece geçerli (None olmayan) değerlere sahip okumaları hafızada tut
        if any(v is not None for k, v in reading.model_dump().items() if 'mm' in k or 'g' in k or 'c' in k or 'perc' in k):
            self.last_valid_reading = reading