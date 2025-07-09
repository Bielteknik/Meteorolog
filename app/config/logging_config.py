import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path

def setup_logging():
    """Uygulama genelinde kullanılacak loglama sistemini kurar."""
    
    # Proje kök dizininde bir 'logs' klasörü oluştur
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "meteo_station.log"

    # Log formatını belirle
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 1. Dosya Handler'ı (File Handler) - Tüm logları dosyaya yazar
    # Dosya boyutu 5MB olunca eski logları 'meteo_station.log.1' gibi yedekler.
    # En fazla 5 yedek dosya tutar.
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO) # INFO ve üzerindeki her şeyi dosyaya yaz
    file_handler.setFormatter(log_format)

    # 2. Konsol Handler'ı (Stream Handler) - Sadece UYARI ve HATALARI konsola yazar
    # Bu, normal çalışma sırasında konsolun temiz kalmasını sağlar.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING) # Sadece WARNING ve ERROR'ları konsola yaz
    console_handler.setFormatter(log_format)

    # Kök logger'ı al ve yapılandır
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # En düşük log seviyesini ayarla
    
    # Eğer daha önce handler eklenmişse temizle (tekrar tekrar çalışmayı önler)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Handler'ları kök logger'a ekle
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info("Loglama sistemi başarıyla kuruldu.")