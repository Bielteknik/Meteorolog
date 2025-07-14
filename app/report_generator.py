import os
from datetime import datetime, timedelta
from .storage_manager import storage_manager, Reading, AnomalyLog
import numpy as np

class ReportGenerator:
    """Günlük özet raporları oluşturur."""

    def generate_daily_z_report(self):
        """
        Son 24 saatin verilerini özetleyen bir Markdown raporu oluşturur.
        """
        print("  📄 Günlük Z Raporu oluşturuluyor...")
        
        report_content = f"# Günlük Z Raporu - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        session = storage_manager.get_session()
        try:
            one_day_ago = datetime.now() - timedelta(hours=24)
            
            # --- Veri Özeti ---
            readings = session.query(Reading).filter(Reading.timestamp >= one_day_ago).all()
            report_content += "## 1. Veri Özeti (Son 24 Saat)\n\n"
            if not readings:
                report_content += "Raporlanacak veri bulunamadı.\n\n"
            else:
                temps = [r.temperature_c for r in readings if r.temperature_c is not None]
                heights = [r.snow_height_mm for r in readings if r.snow_height_mm is not None]
                
                report_content += f"- Toplam Ölçüm Sayısı: {len(readings)}\n"
                report_content += f"- Ortalama Sıcaklık: {np.mean(temps):.1f}°C\n"
                report_content += f"- En Düşük Sıcaklık: {np.min(temps):.1f}°C\n"
                report_content += f"- En Yüksek Sıcaklık: {np.max(temps):.1f}°C\n"
                report_content += f"- Maksimum Kar Yüksekliği: {np.max(heights):.1f} mm\n\n"
            
            # --- Anomali Özeti ---
            anomalies = session.query(AnomalyLog).filter(AnomalyLog.timestamp >= one_day_ago).all()
            report_content += "## 2. Tespit Edilen Anomaliler\n\n"
            if not anomalies:
                report_content += "Anomali tespit edilmedi.\n"
            else:
                report_content += "| Zaman | Sensör | Tip | Detay |\n"
                report_content += "|---|---|---|---|\n"
                for anom in anomalies:
                    ts = anom.timestamp.strftime('%H:%M:%S')
                    report_content += f"| {ts} | {anom.sensor} | {anom.anomaly_type} | {anom.details} |\n"
            
            # Raporu dosyaya yaz
            report_dir = "reports"
            os.makedirs(report_dir, exist_ok=True)
            report_filename = os.path.join(report_dir, f"Z_Report_{datetime.now().strftime('%Y-%m-%d')}.md")
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            print(f"  ✅ Rapor başarıyla '{report_filename}' dosyasına kaydedildi.")

        except Exception as e:
            print(f"  ❌ Rapor oluşturma hatası: {e}")
        finally:
            session.close()