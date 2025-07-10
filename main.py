import logging
# Kendi basit loglama sistemimizi kurmuyoruz.
# Bunun yerine, projenin merkezi ve akıllı loglama sistemini içe aktarıyoruz.
from app.logging_config import setup_logging
from app.scheduler import JobScheduler

if __name__ == "__main__":
    # Konsolu temiz tutacak olan GELİŞMİŞ loglama sistemini kuruyoruz.
    # Bu fonksiyon, app/logging_config.py dosyasından geliyor ve
    # konsola sadece ERROR ve CRITICAL seviyesindeki hataları yazacak şekilde ayarlandı.
    setup_logging()
    
    try:
        scheduler = JobScheduler()
        scheduler.run_forever()
    except Exception as e:
        # Bu kritik hata, ayarlandığı gibi hem dosyaya hem de konsola yazılacaktır.
        logging.critical("Uygulama başlatılamadı veya beklenmedik bir şekilde sonlandı.", exc_info=True)