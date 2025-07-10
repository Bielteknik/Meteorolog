# app/sensors/manager.py
import time, logging
from typing import Dict
from app.config import settings
from app.sensors.parsers import parse_height_from_raw, parse_weight_from_raw

# --- Platforma Özel Kütüphaneler (Bu kısım aynı kalıyor) ---
if not settings.DEV_MODE:
    try:
        import serial, serial.tools.list_ports
        from smbus2 import SMBus
    except ImportError:
        logging.critical("Linux modunda gerekli 'pyserial' veya 'smbus2' kütüphaneleri bulunamadı."); raise
else:
    # Bu uyarı, geliştirme yaparken yararlı olduğu için kalabilir.
    logging.warning("DEV_MODE is active. Using dummy sensor classes.")
    # ... (Geri kalan DEV_MODE kodu aynı)
    class serial:
        class Serial:
            def __init__(self, p=None, b=None, t=None): self.port=p; self.is_open=True; self._t="h" if p and "H" in p else "w"
            def close(self): self.is_open=False
            def read(self, s=1): return b'R1234' if self._t=="h" else b'= 1.2B\r\n'
            def readline(self): return self.read(10)
            def reset_input_buffer(self): pass
            @property
            def in_waiting(self): return 10
        class SerialException(Exception): pass
        @staticmethod
        def list_ports():
            class DP: device="DUMMY_H"
            class DP2: device="DUMMY_W"
            return [DP(), DP2()]
        tools = type("tools", (), {"list_ports": list_ports})()
    class SMBus:
        def __init__(self, bus=None): pass
        def write_i2c_block_data(self, a, c, d): pass
        def read_i2c_block_data(self, a, c, l): return [0]*l
        def write_byte(self, a, v): pass
        def close(self): pass

logger = logging.getLogger(__name__)

class SensorManager:
    # ... (__init__ metodu aynı kalıyor) ...
    def __init__(self):
        self.height_ser: "serial.Serial" | None = None; self.weight_ser: "serial.Serial" | None = None
        self.i2c_bus: "SMBus" | None = None; self.is_height_connected: bool = False
        self.is_weight_connected: bool = False; self.is_temp_hum_connected: bool = False
        self.height_port: str | None = None; self.weight_port: str | None = None

    def _sniff_ports(self, duration_seconds: int = 15) -> Dict[str, str]:
        if settings.DEV_MODE: return {"DUMMY_H": "height", "DUMMY_W": "weight"}
        potential_ports = [p.device for p in serial.tools.list_ports.comports() if 'ttyUSB' in p.device or 'ttyACM' in p.device]
        if not potential_ports: return {}
        open_ports: Dict[str, serial.Serial] = {}
        sensor_map: Dict[str, str] = {}
        for port_name in potential_ports:
            try: open_ports[port_name] = serial.Serial(port_name, settings.SERIAL_BAUD_RATE, timeout=0.1)
            except serial.SerialException as e: logger.error(f"Could not open port {port_name} for sniffing: {e}")
        if not open_ports: return {}
        end_time = time.time() + duration_seconds
        while time.time() < end_time and len(sensor_map) < len(open_ports):
            for port_name, ser_conn in open_ports.items():
                if port_name in sensor_map: continue
                try:
                    if ser_conn.in_waiting > 0:
                        chunk = ser_conn.read(64)
                        if parse_weight_from_raw(chunk) is not None:
                            sensor_map[port_name] = "weight"; continue
                        if parse_height_from_raw(chunk) is not None:
                            sensor_map[port_name] = "height"; continue
                except serial.SerialException as e: logger.error(f"Error reading from {port_name} during sniffing: {e}")
            if len(sensor_map) >= len(potential_ports): break
            time.sleep(0.5)
        for ser_conn in open_ports.values(): ser_conn.close()
        return sensor_map

    def discover_and_connect(self):
        sensor_map = self._sniff_ports()
        for port, sensor_type in sensor_map.items():
            if sensor_type == "height": self.height_port = port
            elif sensor_type == "weight": self.weight_port = port
        self._connect_all()

    def _connect_all(self):
        if self.height_port and not self.is_height_connected:
            try:
                self.height_ser = serial.Serial(self.height_port, settings.SERIAL_BAUD_RATE, timeout=1.0)
                self.is_height_connected = True
            except (serial.SerialException, FileNotFoundError) as e: logger.error(f"Failed to connect to height sensor on {self.height_port}: {e}")
        if self.weight_port and not self.is_weight_connected:
            try:
                self.weight_ser = serial.Serial(self.weight_port, settings.SERIAL_BAUD_RATE, timeout=1.0)
                self.is_weight_connected = True
            except (serial.SerialException, FileNotFoundError) as e: logger.error(f"Failed to connect to weight sensor on {self.weight_port}: {e}")
        if not self.is_temp_hum_connected:
            try:
                self.i2c_bus = SMBus(settings.I2C_BUS)
                if not settings.DEV_MODE: self.i2c_bus.write_i2c_block_data(settings.I2C_SHT3X_ADDRESS, 0x2C, [0x06])
                self.is_temp_hum_connected = True
            except (FileNotFoundError, PermissionError, OSError) as e:
                # Önemli bir hata olduğu için bu log kalmalı.
                logger.error(f"Failed to connect to Temp/Humidity sensor (I2C): {e}")

    def disconnect_all(self):
        if self.height_ser and self.height_ser.is_open: self.height_ser.close()
        if self.weight_ser and self.weight_ser.is_open: self.weight_ser.close()
        if self.i2c_bus: self.i2c_bus.close()
        self.is_height_connected = self.is_weight_connected = self.is_temp_hum_connected = False
        self.height_port = self.weight_port = None