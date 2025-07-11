import logging
import time

from app.config import settings
from app.models.schemas import RawSensorData
from app.sensors.manager import SensorManager
from app.services.openweathermap_service import OpenWeatherMapService

logger = logging.getLogger(__name__)

class DataCollector:
    """
    SensorManager'ı kullanarak sensörlerden ham veri okur.
    I2C sensörü başarısız olursa OpenWeatherMap API'sini akıllı yedek olarak kullanır.
    """
    def __init__(self, sensor_manager: SensorManager):
        self.manager = sensor_manager
        self.owm_service = OpenWeatherMapService()

    def collect_raw_data(self) -> RawSensorData:
        """Tüm bağlı sensörlerden veya API'lerden ham veriyi okur."""
        raw_data = RawSensorData()

        # Seri port sensörleri
        if self.manager.is_height_connected and self.manager.height_ser:
            try:
                if self.manager.height_ser.in_waiting > 0:
                    raw_data.height_raw = self.manager.height_ser.read(self.manager.height_ser.in_waiting)
            except Exception as e:
                logger.error(f"Error reading from height sensor: {e}")

        if self.manager.is_weight_connected and self.manager.weight_ser:
            try:
                if self.manager.weight_ser.in_waiting > 0:
                    raw_data.weight_raw = self.manager.weight_ser.readline()
            except Exception as e:
                logger.error(f"Error reading from weight sensor: {e}")

        # Sıcaklık ve Nem sensörü (AKILLI YEDEKLEME MANTIĞI)
        i2c_read_success = False
        if self.manager.is_temp_hum_connected and self.manager.i2c_bus:
            try:
                self.manager.i2c_bus.write_i2c_block_data(settings.I2C_SHT3X_ADDRESS, 0x2C, [0x06])
                time.sleep(0.1)
                temp_hum_bytes = self.manager.i2c_bus.read_i2c_block_data(settings.I2C_SHT3X_ADDRESS, 0x00, 6)
                if any(temp_hum_bytes):
                    raw_data.temp_hum_raw = temp_hum_bytes
                    i2c_read_success = True
                else:
                    logger.warning("I2C sensor returned all zeros, considering it a read failure.")
            except Exception as e:
                logger.error(f"Error reading from I2C sensor: {e}. Switching to OWM fallback mode if not already active.")

        # Durum değerlendirmesi ve veri kaynağı seçimi
        if i2c_read_success:
            if self.owm_service.is_fallback_active:
                logger.info("Local I2C sensor is back online. Disabling OWM fallback mode.")
                self.owm_service.is_fallback_active = False
        else:
            if not self.owm_service.is_fallback_active:
                logger.warning("Local I2C sensor has failed. Activating OWM fallback mode.")
                self.owm_service.is_fallback_active = True
            
            raw_data.temp_hum_api = self.owm_service.get_fallback_data()
        
        return raw_data