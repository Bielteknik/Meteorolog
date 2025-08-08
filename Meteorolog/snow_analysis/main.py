import time
from rich.console import Console

# Veritabanı ve yönetici modüllerini import et
from app.database.manager import storage_manager
from app.database.models import Sensor, SensorSetting

# Ana uygulama yöneticisini import et
from app.managers.sensor_manager import SensorManager

console = Console()

def initialize_system():
    """
    Uygulamanın çalışması için gereken temel kontrolleri ve kurulumları yapar.
    1. Veritabanı tablolarının var olduğundan emin olur, yoksa oluşturur.
    2. Sensör tanımları boşsa, başlangıç verilerini ekler.
    """
    console.print("[bold cyan]--- 🔧 Sistem Başlatılıyor: Veritabanı kontrol ediliyor... ---[/bold cyan]")
    
    # 1. Adım: Tabloları oluştur (SQLAlchemy, tablolar zaten varsa tekrar oluşturmaz)
    storage_manager.init_db()

    # 2. Adım: Veritabanında sensör tanımı olup olmadığını kontrol et
    with storage_manager.get_session() as session:
        if session.query(Sensor).count() == 0:
            console.print("[yellow]ℹ️ Veritabanı boş. Başlangıç sensör verileri ekleniyor...[/yellow]")
            
            # Yeni Ultrasonik Yükseklik Sensörü
            ultrasonic = Sensor(name="ultrasonic_height", type="dfrobot_ultrasonic", enabled=True)
            ultrasonic.settings.extend([
                SensorSetting(key="baudrate", value="9600"),
                SensorSetting(key="fingerprint_regex", value="^\\d{3,5}$"),
                SensorSetting(key="zero_point_mm", value="3450")
            ])
            
            # Ağırlık Sensörü
            loadcell = Sensor(name="loadcell_weight", type="serial_loadcell", enabled=True)
            loadcell.settings.extend([
                SensorSetting(key="baudrate", value="9600"),
                SensorSetting(key="fingerprint_regex", value="^=\\s*(-?\\d+\\.\\d+)")
            ])
            
            # Sıcaklık ve Nem Sensörü
            sht31 = Sensor(name="sht31_temperature_humidity", type="sht3x_i2c", enabled=True)
            sht31.settings.append(SensorSetting(key="i2c_address", value="0x44"))

            session.add_all([ultrasonic, loadcell, sht31])
            console.print("[green]✅ Başlangıç verileri başarıyla eklendi.[/green]")
        else:
            console.print("[green]✅ Veritabanı hazır.[/green]")


def main():
    """
    Uygulamanın ana giriş noktası.
    """
    console.print("\n[bold]❄️ Akıllı Kar İstasyonu Başlatılıyor ❄️[/bold]")
    
    # Her şeyden önce, veritabanının hazır olduğundan emin ol.
    initialize_system()
    
    # Sensör yöneticisini başlat.
    sensor_manager = SensorManager(storage_manager)
    
    try:
        # Sensörleri bul ve bağlan.
        sensor_manager.discover_and_connect_sensors()

        # Eğer en az bir sensör bulunduysa, test için birkaç okuma yap.
        if sensor_manager.active_plugins:
            console.print("\n[bold cyan]--- 🔄 Test Okuma Döngüsü Başlatıldı (Çıkmak için Ctrl+C) ---[/bold cyan]")
            count = 0
            while True:
                count += 1
                console.print(f"\n[bold]--- Okuma #{count} ---[/bold]")
                sensor_data = sensor_manager.read_all_connected_sensors()
                # Gelecekte bu veri 'data_processor'a gönderilecek.
                console.print(f"--> İşlenecek Veri Paketi: {sensor_data}")
                time.sleep(10)
        else:
            console.print("\n[bold red]Hiçbir sensör bulunamadığı için okuma yapılamıyor.[/bold red]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Kullanıcı tarafından işlem durduruldu.[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Beklenmedik bir hata oluştu: {e}[/bold red]")
        # Hatanın detayını görmek için traceback'i yazdırabiliriz (geliştirme için)
        console.print_exception(show_locals=True)
    finally:
        # Uygulama kapanırken tüm bağlantıları temizle.
        sensor_manager.disconnect_all()
        console.print("\n[bold]--- 👋 Program Sonlandırıldı ---[/bold]")


if __name__ == "__main__":
    main()