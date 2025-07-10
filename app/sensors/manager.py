import time
import logging
from typing import Dict

# Gerçek kütüphaneler ve projemizin parser'ları
from app.config import settings
from app.sensors.parsers import parse_height_from_raw, parse_weight_from_raw

# --- Platforma Özel Kütüphaneleri Koşullu Olarak Yükleme ---
if not settings.DEV_MODE:
    try:
        import serial
        import serial.tools.list_ports
        from smbus2 import SMBus
    except ImportError:
        logging.critical("Linux modunda gerekli 'pyserial' veya 'smbus2' kütüphaneleri bulunamadı.")
        raise
else:
    # Windows'ta geliştirme yaparken bu blok çalışır ve donanımı simüle eder.
    logging.warning("DEV_MODE is active. Using dummy sensor classes.")
    
    class serial:
        class Serial:
            def __init__(self, port=None, baudrate=None, timeout=None):
                self.port = port
                self.is_open = True
                self._dummy_data_type = "none"
                if port and "H" in port: self._dummy_data_type = "height"
                if port and "W" in port: self._dummy_data_type = "weight"
                logging.info(f"[DEV_MODE] Dummy Serial connection created for port: {port}")
            def close(self): self.is_open = False; logging.info(f"[DEV_MODE] Dummy Serial connection closed for port: {self.port}")
            def read(self, size=1): 
                if self._dummy_data_type == "height": return b'R1234'
                return b''
            def readline(self):
                if self._dummy_data_type == "weight": return b'=   12.34B0\n'
                return b''
            def reset_input_buffer(self): pass
            @property
            def in_waiting(self): return 10
        
        class SerialException(Exception): pass

        # DEV_MODE için sahte bir list_ports fonksiyonu
        @staticmethod
        def list_ports():
            class DummyPort: device = "DUMMY_H"
            class DummyPort2: device = "DUMMY_W"
            return [DummyPort(), DummyPort2()]
        tools = type("tools", (), {"list_ports": list_ports})()

    class SMBus:
        def __init__(self, bus=None):
            logging.info(f"[DEV_MODE] Dummy SMBus created for bus: {bus}")
        def write_i2c_block_data(self, addr, cmd, data): pass
        def read_i2c_block_data(self, addr, cmd, length): return [0] * length
        def write_byte(self, addr, val): pass
        def close(self): logging.info("[DEV_MODE] Dummy SMBus connection closed.")

logger = logging.getLogger(__name__)

class SensorManager:
    """
    Seri portları dinamik olarak tarar, gelen veriyi "koklayarak"
    hangi portun hangi sensöre ait olduğunu belirler ve bağlantıları yönetir.
    """
    def __init__(self):
        self.height_ser: "serial.Serial" | None = None
        self.weight_ser: "serial.Serial" | None = None
        self.i2c_bus: "SMBus" | None = None

        self.is_height_connected: bool = False
        self.is_weight_connected: bool = False
        self.is_temp_hum_connected: bool = False

        self.height_port: str | None = None
        self.weight_port: str | None = None

    def _sniff_ports(self, duration_seconds: int = 30) -> Dict[str, str]:
        """
        Seri portları tarar, belirli bir süre dinler ve veri formatına göre
        sensör tipini (height, weight) belirler.
        """
        if settings.DEV_MODE:
            logger.info("[DEV_MODE] Skipping real port sniffing. Assigning dummy ports.")
            return {"DUMMY_H": "height", "DUMMY_W": "weight"}

        potential_ports = [port.device for port in serial.tools.list_ports.comports() if 'ttyUSB' in port.device or 'ttyACM' in port.device]
        if not potential_ports:
            logger.warning("No potential serial ports (ttyUSB*, ttyACM*) found.")
            return {}

        logger.info(f"Sniffing on ports: {potential_ports} for up to {duration_seconds} seconds...")
        
        open_ports: Dict[str, serial.Serial] = {}
        sensor_map: Dict[str, str] = {}

        for port_name in potential_ports:
            try:
                open_ports[port_name] = serial.Serial(port_name, settings.SERIAL_BAUD_RATE, timeout=0.1)
            except serial.SerialException as e:
                logger.error(f"Could not open port {port_name} for sniffing: {e}")

        if not open_ports:
            logger.error("Could not open any serial ports for sniffing.")
            return {}

        end_time = time.time() + duration_seconds
        while time.time() < end_time and len(sensor_map) < len(open_ports):
            ports_to_remove = []
            for port_name, ser_conn in open_ports.items():
                if port_name in sensor_map: continue
                try:
                    if ser_conn.in_waiting > 0:
                        line_data = ser_conn.readline()
                        if parse_weight_from_raw(line_data) is not None:
                            logger.info(f"✅ Found WEIGHT sensor on port {port_name}!")
                            sensor_map[port_name] = "weight"
                            continue

                        raw_data = line_data + ser_conn.read(ser_conn.in_waiting)
                        if parse_height_from_raw(raw_data) is not None:
                            logger.info(f"✅ Found HEIGHT sensor on port {port_name}!")
                            sensor_map[port_name] = "height"
                            continue
                except serial.SerialException as e:
                    logger.error(f"Error reading from {port_name} during sniffing: {e}")
                    ports_to_remove.append(port_name)

            for port_name in set(ports_to_remove):
                if port_name in open_ports:
                    open_ports[port_name].close()
            
            if len(sensor_map) >= 2: break
            time.sleep(0.5)

        for ser_conn in open_ports.values():
            ser_conn.close()

        logger.info(f"Sniffing complete. Sensor map: {sensor_map}")
        return sensor_map

    def discover_and_connect(self):
        """Portları koklayarak sensörleri keşfeder ve bulduğu sensörlere bağlanır."""
        logger.info("--- Starting Sensor Discovery (Sniffing Mode) ---")
        sensor_map = self._sniff_ports()

        for port, sensor_type in sensor_map.items():
            if sensor_type == "height": self.height_port = port
            elif sensor_type == "weight": self.weight_port = port
        
        self._connect_all()
        logger.info("--- Sensor Discovery Finished ---")

    def _connect_all(self):
        """Tespit edilen portlara ve I2C cihazına kalıcı olarak bağlanır."""
        logger.info("Attempting to establish final connections to sensors...")

        if self.height_port and not self.is_height_connected:
            try:
                self.height_ser = serial.Serial(self.height_port, settings.SERIAL_BAUD_RATE, timeout=1.0)
                self.is_height_connected = True
                logger.info(f"Final connection to HEIGHT sensor established on {self.height_port}.")
            except (serial.SerialException, FileNotFoundError) as e:
                logger.error(f"Failed to connect to height sensor on {self.height_port}: {e}")

        if self.weight_port and not self.is_weight_connected:
            try:
                self.weight_ser = serial.Serial(self.weight_port, settings.SERIAL_BAUD_RATE, timeout=1.0)
                self.is_weight_connected = True
                logger.info(f"Final connection to WEIGHT sensor established on {self.weight_port}.")
            except (serial.SerialException, FileNotFoundError) as e:
                logger.error(f"Failed to connect to weight sensor on {self.weight_port}: {e}")

        if not self.is_temp_hum_connected:
            try:
                self.i2c_bus = SMBus(settings.I2C_BUS)
                if not settings.DEV_MODE:
                    self.i2c_bus.write_i2c_block_data(settings.I2C_SHT3X_ADDRESS, 0x2C, [0x06])
                self.is_temp_hum_connected = True
                logger.info(f"Temp/Humidity sensor connected successfully on I2C bus {settings.I2C_BUS}.")
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.error(f"Failed to connect to Temp/Humidity sensor (I2C): {e}")

    def disconnect_all(self):
        """Tüm aktif bağlantıları güvenli bir şekilde kapatır."""
        logger.info("Disconnecting all sensors...")
        if self.height_ser and self.height_ser.is_open: self.height_ser.close()
        if self.weight_ser and self.weight_ser.is_open: self.weight_ser.close()
        if self.i2c_bus: self.i2c_bus.close()
        
        self.is_height_connected = False
        self.is_weight_connected = False
        self.is_temp_hum_connected = False
        self.height_port = None
        self.weight_port = None
        
        logger.info("All sensor connections have been closed.")