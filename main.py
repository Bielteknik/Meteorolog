import logging
from app.scheduler import JobScheduler

def setup_logging():
    """Uygulama için temel loglama yapılandırmasını kurar."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("meteo_station.log", encoding='utf-8'),
            logging.StreamHandler() # Logları hem dosyaya hem konsola yazar
        ]
    )
    logging.info("Logging configured.")

if __name__ == "__main__":
    setup_logging()
    
    try:
        scheduler = JobScheduler()
        scheduler.run_forever()
    except Exception as e:
        logging.critical("Uygulama başlatılamadı veya beklenmedik bir şekilde sonlandı.", exc_info=True)