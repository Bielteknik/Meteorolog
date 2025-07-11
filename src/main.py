from modules.sensor_manager import SensorManager

CONFIG_PATH = '../config/config.yaml'

def initialize_system():
    """
    Sistemi başlatır, sensörleri keşfeder ve durumu raporlar.
    """
    print("=============================================")
    print("=  Sistem Başlatma Prosedürü                =")
    print("=============================================")
    
    # 1. Adım: Sensör Yöneticisini Başlat ve Sensörleri Keşfet
    manager = SensorManager(config_path=CONFIG_PATH)
    is_successful = manager.find_and_assign_sensors()
    
    print("\n--- Keşif Sonucu ---")
    if is_successful:
        print("Durum: Başarılı")
        assigned = manager.get_assigned_ports()
        for sensor_name, port_name in assigned.items():
            print(f"  - {sensor_name.capitalize()} Sensörü: {port_name}")
    else:
        print("Durum: Başarısız. Aktif sensörlerden bazıları bulunamadı.")
        
    print("=============================================")
    print("=  Başlatma Prosedürü Tamamlandı           =")
    print("=============================================")

if __name__ == "__main__":
    initialize_system()