import serial
import time
from typing import Optional
import logging

from app.config import settings
from app.models.schemas import SensorReading
from app.sensors.manager import SensorManager
from app.sensors.parsers import parse_height, parse_weight, parse_sht3x

logger = logging.getLogger(__name__)

class DataCollector:
    """
    SensorManager'ı kullanarak sensörlerden veri okur ve
    bunları bir SensorReading modelinde birleştirir.
    """
    def __init__(self, sensor_manager: SensorManager):
        self.manager = sensor_manager

    def collect_single_reading(self) -> SensorReading:
        """Tüm bağlı sensörlerden tek bir okuma döngüsü gerçekleştirir."""
        height, weight, temp, hum = None, None, None, None

        # Mesafe sensörü okuması
        if self.manager.is_height_connected and self.manager.height_ser:
            try:
                if self.manager.height_ser.in_waiting > 0:
                    data = self.manager.height_ser.read(self.manager.height_ser.in_waiting)
                    height = parse_height(data)
            except serial.SerialException as e:
                logger.error(f"Failed to read from height sensor: {e}")
                self.manager.is_height_connected = False # Bağlantı koptu

        # Ağırlık sensörü okuması
        if self.manager.is_weight_connected and self.manager.weight_ser:
            try:
                if self.manager.weight_ser.in_waiting > 0:
                    line = self.manager.weight_ser.readline()
                    weight = parse_weight(line)
            except serial.SerialException as e:
                logger.error(f"Failed to read from weight sensor: {e}")
                self.manager.is_weight_connected = False # Bağlantı koptu

        # Sıcaklık ve Nem sensörü okuması
        if self.manager.is_temp_hum_connected and self.manager.i2c_bus:
            try:
                # SHT3x'e ölçüm komutunu gönder
                self.manager.i2c_bus.write_i2c_block_data(
                    settings.I2C_SHT3X_ADDRESS, 0x2C, [0x06]
                )
                time.sleep(0.1) # Ölçüm için kısa bir bekleme
                # Veriyi oku
                data = self.manager.i2c_bus.read_i2c_block_data(
                    settings.I2C_SHT3X_ADDRESS, 0x00, 6
                )
                temp, hum = parse_sht3x(data)
            except OSError as e:
                logger.error(f"Failed to read from I2C sensor: {e}")
                self.manager.is_temp_hum_connected = False # Bağlantı koptu

        return SensorReading(
            height_mm=height,
            weight_g=weight,
            temperature_c=temp,
            humidity_perc=hum
        )