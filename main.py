import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- HATAYI ÇÖZEN KISIM SONU ---

import logging
from app.logging_config import setup_logging
from app.scheduler import JobScheduler

if __name__ == "__main__":
    # Konsolu temiz tutacak olan GELİŞMİŞ loglama sistemini kuruyoruz.
    setup_logging()
    
    try:
        scheduler = JobScheduler()
        scheduler.run_forever()
    except Exception as e:
        # Bu kritik hata, ayarlandığı gibi hem dosyaya hem de konsola yazılacaktır.
        logging.critical("Uygulama başlatılamadı veya beklenmedik bir şekilde sonlandı.", exc_info=True)