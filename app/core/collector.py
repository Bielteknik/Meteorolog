import logging
import time

from app.config import settings
from app.models.schemas import RawSensorData
from app.sensors.manager import SensorManager

logger = logging.getLogger(__name__)

class DataCollector:
    """SensorManager'ı kullanarak sensörlerden ham veri okur."""
    def __init__(self, sensor_manager: SensorManager):
        self.manager = sensor_manager

    def collect_raw_data(self) -> RawSensorData:
        """Tüm bağlı sensörlerden ham veriyi okur ve bir RawSensorData modelinde birleştirir."""
        raw_data = RawSensorData()

        if self.manager.is_height_connected and self.manager.height_ser:
            try:
                if self.manager.height_ser.in_waiting > 0:
                    raw_data.height_raw = self.manager.height_ser.read(self.manager.height_ser.in_waiting)
            except Exception as e:
                logger.error(f"Error reading from height sensor: {e}")
                self.manager.is_height_connected = False

        if self.manager.is_weight_connected and self.manager.weight_ser:
            try:
                if self.manager.weight_ser.in_waiting > 0:
                    raw_data.weight_raw = self.manager.weight_ser.readline()
            except Exception as e:
                logger.error(f"Error reading from weight sensor: {e}")
                self.manager.is_weight_connected = False

        if self.manager.is_temp_hum_connected and self.manager.i2c_bus:
            try:
                # Ölçüm komutunu gönder ve bekle
                self.manager.i2c_bus.write_i2c_block_data(settings.I2C_SHT3X_ADDRESS, 0x2C, [0x06])
                time.sleep(0.1)
                # Veriyi oku
                raw_data.temp_hum_raw = self.manager.i2c_bus.read_i2c_block_data(settings.I2C_SHT3X_ADDRESS, 0x00, 6)
            except Exception as e:
                logger.error(f"Error reading from I2C sensor: {e}")
                self.manager.is_temp_hum_connected = False
        
        return raw_data