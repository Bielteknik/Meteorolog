from typing import Dict, Any, Optional
from .config import settings
from .storage_manager import storage_manager, Reading, AnomalyLog

class AnomalyDetector:
    """Sensör verilerindeki anormallikleri tespit eder."""

    def __init__(self):
        self.last_reading: Optional[Reading] = self._get_last_reading_from_db()
        print(f"🕵️  Anomali Dedektörü başlatıldı. Son okunan veri: {'Var' if self.last_reading else 'Yok'}")

    def _get_last_reading_from_db(self) -> Optional[Reading]:
        """Veritabanından en son kaydedilen okumayı çeker."""
        session = storage_manager.get_session()
        try:
            last_reading = session.query(Reading).order_by(Reading.id.desc()).first()
            return last_reading
        finally:
            session.close()

    def check(self, current_data: Dict[str, Any]):
        """Mevcut veriyi alır, anormallikleri kontrol eder ve loglar."""
        anomalies_found = []

        if not self.last_reading:
            print("  ℹ️  Karşılaştırılacak önceki veri yok, anomali kontrolü atlanıyor.")
            db_compatible_data = {k: v for k, v in current_data.items() if hasattr(Reading, k)}
            self.last_reading = Reading(**db_compatible_data)
            return

        # --- Kontrol 1: Ani Sıcaklık Sıçraması ---
        if current_data.get('temperature_c') is not None and self.last_reading.temperature_c is not None:
            temp_change = abs(current_data['temperature_c'] - self.last_reading.temperature_c)
            if temp_change > settings.anomaly_rules.max_temp_change_per_cycle:
                details = f"Sıcaklık {temp_change:.1f}°C değişti (Limit: {settings.anomaly_rules.max_temp_change_per_cycle}°C)"
                self._log_anomaly('temperature', 'rate_of_change', str(current_data.get('temperature_c')), details)
                anomalies_found.append(details)
            
        # --- YENİ KONTROL: Ani Kar Yüksekliği Sıçraması ---
        if current_data.get('snow_height_mm') is not None and self.last_reading.snow_height_mm is not None:
            height_change_cm = abs(current_data['snow_height_mm'] - self.last_reading.snow_height_mm) / 10.0
            limit_cm = settings.anomaly_rules.max_snow_height_change_per_cycle_cm
            if height_change_cm > limit_cm:
                details = f"Kar yüksekliği {height_change_cm:.1f} cm değişti (Limit: {limit_cm} cm)"
                self._log_anomaly('snow_height', 'rate_of_change', str(current_data.get('snow_height_mm')), details)
                anomalies_found.append(details)

        # --- Kontrol 3: Donmuş Sensör ---
        if (current_data.get('temperature_c') == self.last_reading.temperature_c and
            current_data.get('humidity_percent') == self.last_reading.humidity_percent and
            current_data.get('snow_height_mm') == self.last_reading.snow_height_mm):
            details = "Tüm sensör değerleri bir önceki döngüyle aynı."
            self._log_anomaly('system', 'frozen_sensor', 'N/A', details)
            anomalies_found.append(details)

        if anomalies_found:
            print(f"  🚨 ANOMALİ TESPİT EDİLDİ: {', '.join(anomalies_found)}")
        
        db_compatible_data = {k: v for k, v in current_data.items() if hasattr(Reading, k)}
        self.last_reading = Reading(**db_compatible_data)

    def _log_anomaly(self, sensor: str, anomaly_type: str, value: str, details: str):
        """Tespit edilen bir anomaliyi veritabanına kaydeder."""
        session = storage_manager.get_session()
        try:
            new_log = AnomalyLog(sensor=sensor, anomaly_type=anomaly_type, value=value, details=details)
            session.add(new_log)
            session.commit()
        except Exception as e:
            print(f"  ❌ Anomali loglama hatası: {e}")
            session.rollback()
        finally:
            session.close()