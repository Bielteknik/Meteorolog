import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path

from rich.logging import RichHandler

def setup_logging():
    """Uygulama genelinde kullanılacak loglama sistemini kurar."""
    
    log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "meteo_station.log"

    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 1. Dosya Handler'ı - Tüm logları dosyaya yazar (INFO ve üstü)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)

    # 2. Konsol Handler'ı - Sadece KRİTİK HATALARI konsola yazar (ERROR ve üstü)
    # Bu, normal çalışma sırasında konsolun tamamen temiz kalmasını sağlar.
    console_handler = RichHandler(
        level="ERROR", 
        show_time=True, 
        show_path=False,
        rich_tracebacks=True
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) 
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info("Loglama sistemi kuruldu. Konsol log seviyesi: ERROR.")