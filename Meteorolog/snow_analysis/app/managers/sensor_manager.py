import time
import serial
import serial.tools.list_ports
from rich.console import Console

from app.database.manager import StorageManager
from app.sensors.base_sensor import BaseSensor
from app.sensors.dfrobot_ultrasonic import DFRobotUltrasonic
from app.sensors.serial_loadcell import SerialLoadcell
from app.sensors.sht3x_i2c import SHT3xI2C

console = Console()

# --- YENİ ---
# Denenecek yaygın baud hızları listesi
COMMON_BAUDRATES = [9600, 115200, 57600, 38400, 19200]
# ------------

class SensorManager:
    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.sensor_configs = []
        self.active_plugins: dict[str, BaseSensor] = {}

        self.PLUGIN_MAP = {
            "dfrobot_ultrasonic": DFRobotUltrasonic,
            "serial_loadcell": SerialLoadcell,
            "sht3x_i2c": SHT3xI2C,
        }

    def discover_and_connect_sensors(self, timeout_seconds: int = 180):
        console.print(f"[bold yellow]🔄 Sensör Keşfi Başlatıldı... (Maksimum Süre: {timeout_seconds} saniye)[/bold yellow]")
        
        self.sensor_configs = self.storage_manager.get_enabled_sensor_configs()
        if not self.sensor_configs:
            console.print("[bold red]❌ Veritabanında aktif sensör tanımı bulunamadı. İşlem durduruldu.[/bold red]")
            return

        serial_sensors_to_find = [s for s in self.sensor_configs if 'i2c' not in s.get('type', '')]
        i2c_sensors_to_find = [s for s in self.sensor_configs if 'i2c' in s.get('type', '')]

        start_time = time.time()
        found_sensors = []

        if i2c_sensors_to_find:
            found_i2c = self._discover_i2c_sensors(i2c_sensors_to_find)
            found_sensors.extend(found_i2c)

        while time.time() - start_time < timeout_seconds:
            unfound_serial_sensors = [s for s in serial_sensors_to_find if s['name'] not in [f['name'] for f in found_sensors]]
            if not unfound_serial_sensors:
                console.print("[green]✅ Tüm seri sensörler daha önceki turlarda bulundu.[/green]")
                break

            console.print(f"\n[cyan]ℹ️ Kalan seri sensörler için portlar taranıyor... ({len(unfound_serial_sensors)} sensör kaldı)[/cyan]")
            found_now = self._discover_serial_sensors(unfound_serial_sensors)
            if found_now:
                found_sensors.extend(found_now)
            
            if len(unfound_serial_sensors) == len(found_now):
                break
                
            time.sleep(10)

        console.print("\n[bold green]--- Keşif Tamamlandı ---[/bold green]")
        if len(found_sensors) == len(self.sensor_configs):
            console.print("[bold green]✅ Tüm aktif sensörler başarıyla bulundu ve bağlandı.[/bold green]")
        else:
            unfound_names = [s['name'] for s in self.sensor_configs if s['name'] not in [f['name'] for f in found_sensors]]
            console.print(f"[bold red]❌ KRİTİK: Şu sensörler bulunamadı: {', '.join(unfound_names)}[/bold red]")
            console.print("[bold yellow]Lütfen sensör bağlantılarını, güç durumunu ve baud hızlarını kontrol edin.[/bold yellow]")

    def _discover_i2c_sensors(self, i2c_sensors: list[dict]) -> list[dict]:
        # Bu fonksiyon aynı, değişiklik yok.
        found_list = []
        for config in i2c_sensors:
            plugin_class = self.PLUGIN_MAP.get(config['type'])
            if not plugin_class: continue
            plugin_instance = plugin_class(config)
            if plugin_instance.connect(port="1"):
                self.active_plugins[config['name']] = plugin_instance
                self.storage_manager.update_sensor_status(config['id'], port=f"i2c-1 @ {config.get('i2c_address')}")
                found_list.append(config)
        return found_list

    def _discover_serial_sensors(self, serial_sensors: list[dict]) -> list[dict]:
        found_list = []
        
        assigned_ports = [p.port for p in self.active_plugins.values() if p.port]
        available_ports = [p.device for p in serial.tools.list_ports.comports() if p.device not in assigned_ports and 'ttyS' not in p.device]

        console.print(f"   [dim]Bulunan Kullanılabilir USB Portlar: {available_ports if available_ports else 'YOK'}[/dim]")

        if not available_ports:
            return found_list

        for port in available_ports:
            if port in [p.port for p in self.active_plugins.values()]: continue

            for config in serial_sensors:
                plugin_class = self.PLUGIN_MAP.get(config['type'])
                if not plugin_class: continue

                console.print(f"  [dim]➡️ {port} portu üzerinde '{config['name']}' sensörü test ediliyor...[/dim]")
                
                # --- GÜNCELLENEN BÖLÜM: BAUD HIZI TARAMASI ---
                found_match_for_sensor = False
                for baudrate in COMMON_BAUDRATES:
                    console.print(f"     [grey50]Baudrate denemesi:[/grey50] [bright_black]{baudrate}[/bright_black]")
                    try:
                        test_conn = serial.Serial(port, baudrate, timeout=2)
                        time.sleep(2)
                        data_sample = test_conn.read(200).decode('utf-8', errors='ignore')
                        test_conn.close()

                        if data_sample and plugin_class.check_fingerprint(data_sample, config):
                            escaped_data = data_sample.encode('unicode_escape').decode('utf-8')
                            console.print(f"     [bold green]✔️ ANLAMLI VERİ BULUNDU![/bold green] RAW: [bright_black]{escaped_data}[/bright_black]")
                            console.print(f"[bold green]✔️ EŞLEŞME: '{config['name']}' sensörü {port} portunda, {baudrate} baud ile bulundu![/bold green]")
                            
                            # Eşleşme bulundu, kalıcı bağlantı kur
                            # Baudrate'i config'de geçici olarak güncelle
                            config['baudrate'] = baudrate 
                            plugin_instance = plugin_class(config)
                            if plugin_instance.connect(port):
                                self.active_plugins[config['name']] = plugin_instance
                                self.storage_manager.update_sensor_status(config['id'], port)
                                found_list.append(config)
                                found_match_for_sensor = True
                                break # Baudrate döngüsünü kır
                    except serial.SerialException:
                        continue # Bu baudrate ile port açılamadı, sonrakini dene.
                
                if found_match_for_sensor:
                    break # Sensör bu portta bulundu, bir sonraki porta geç.
                # ----------------------------------------------------
        return found_list

    # read_all_connected_sensors ve disconnect_all metodları aynı kalabilir, değişiklik gerekmiyor.
    def read_all_connected_sensors(self) -> dict:
        sensor_data = {}
        console.print("[bold]Sensör Verileri Okunuyor...[/bold]")
        for name, plugin in self.active_plugins.items():
            data = plugin.read()
            sensor_data[name] = data
            if data is not None:
                console.print(f"  [green]Okunan Veri[/green] -> {name}: {data}")
            else:
                console.print(f"  [red]Okuma Hatası[/red] -> {name}: Veri alınamadı")
        return sensor_data

    def disconnect_all(self):
        console.print("\n[bold yellow]🔌 Tüm sensör bağlantıları kapatılıyor...[/bold yellow]")
        for plugin in self.active_plugins.values():
            plugin.disconnect()
        console.print("[bold green]✅ Bağlantılar kapatıldı.[/bold green]")