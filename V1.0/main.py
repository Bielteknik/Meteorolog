import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# rich kütüphanesini içe aktarıyoruz
from rich.logging import RichHandler
from app.scheduler import JobScheduler

def setup_logging():
    """
    Uygulama genelinde kullanılacak, KONSOLU TEMİZ TUTAN 
    loglama sistemini kurar.
    """
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "meteo_station.log"

    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 1. Dosya Handler'ı - Tüm detaylı logları dosyaya yazar (INFO seviyesinden)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    # 2. Konsol Handler'ı - Sadece KRİTİK HATALARI konsola yazar (ERROR ve üstü)
    console_handler = RichHandler(
        level="ERROR", 
        show_time=True, 
        show_path=False,
        rich_tracebacks=True
    )

    # Kök logger'ı yapılandır
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info("Merkezi loglama sistemi main.py üzerinden kuruldu. Konsol log seviyesi: ERROR.")


if __name__ == "__main__":
    # Loglama sistemini ilk iş olarak kuruyoruz.
    setup_logging()
    
    try:
        scheduler = JobScheduler()
        scheduler.run_forever()
    except Exception as e:
        # Bu kritik hata, ayarlandığı gibi hem dosyaya hem de konsola yazılacaktır.
        logging.critical("Uygulama başlatılamadı veya beklenmedik bir şekilde sonlandı.", exc_info=True)