# app/report_generator.py
import os
from datetime import datetime, timedelta
import numpy as np
from rich.console import Console

# Modelleri ve yöneticiyi import et
from .storage_manager import storage_manager, Reading, AnomalyLog, SystemHealthLog

console = Console()

class ReportGenerator:
    """Günlük özet raporları oluşturur."""

    def generate_daily_z_report(self):
        """
        Son 24 saatin verilerini özetleyen bir Markdown raporu oluşturur.
        """
        console.print("  📄 Günlük Z Raporu oluşturuluyor...")
        
        report_content = f"# Günlük Z Raporu - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        session = storage_manager.get_session()
        try:
            one_day_ago = datetime.now() - timedelta(hours=24)
            
            # --- 1. Veri Özeti ---
            report_content += "## 1. Veri Özeti (Son 24 Saat)\n\n"
            readings = session.query(Reading).filter(Reading.timestamp >= one_day_ago).all()
            if not readings:
                report_content += "Raporlanacak ölçüm verisi bulunamadı.\n\n"
            else:
                temps = [r.temperature_c for r in readings if r.temperature_c is not None]
                heights = [r.snow_height_mm for r in readings if r.snow_height_mm is not None]
                
                report_content += f"- Toplam Ölçüm Sayısı: {len(readings)}\n"
                if temps:
                    report_content += f"- Ortalama Sıcaklık: {np.mean(temps):.1f}°C\n"
                    report_content += f"- En Düşük Sıcaklık: {np.min(temps):.1f}°C\n"
                    report_content += f"- En Yüksek Sıcaklık: {np.max(temps):.1f}°C\n"
                if heights:
                    report_content += f"- Maksimum Kar Yüksekliği: {np.max(heights):.1f} mm\n\n"
            
            # --- 2. Anomali Özeti ---
            report_content += "## 2. Tespit Edilen Anomaliler\n\n"
            anomalies = session.query(AnomalyLog).filter(AnomalyLog.timestamp >= one_day_ago).all()
            if not anomalies:
                report_content += "Anomali tespit edilmedi.\n"
            else:
                report_content += "| Zaman | Sensör | Tip | Detay |\n"
                report_content += "|---|---|---|---|\n"
                for anom in anomalies:
                    ts = anom.timestamp.strftime('%H:%M:%S')
                    report_content += f"| {ts} | {anom.sensor} | {anom.anomaly_type} | {anom.details} |\n"
            
            # --- 3. Sistem Sağlığı Özeti ---
            report_content += "\n## 3. Sistem Sağlığı Özeti\n\n"
            health_logs = session.query(SystemHealthLog).filter(SystemHealthLog.timestamp >= one_day_ago).all()
            if not health_logs:
                report_content += "Sistem sağlığı verisi bulunamadı.\n"
            else:
                cpu_temps = [h.cpu_temp_c for h in health_logs if h.cpu_temp_c is not None]
                disk_usages = [h.disk_usage_percent for h in health_logs if h.disk_usage_percent is not None]
                
                if cpu_temps:
                    report_content += f"- Ortalama CPU Sıcaklığı: {np.mean(cpu_temps):.1f}°C\n"
                    report_content += f"- Maksimum CPU Sıcaklığı: {np.max(cpu_temps):.1f}°C\n"
                if disk_usages:
                    report_content += f"- Son Disk Kullanımı: {disk_usages[-1]:.1f}%\n"

            # Raporu dosyaya yaz
            report_dir = "reports"
            os.makedirs(report_dir, exist_ok=True)
            report_filename = os.path.join(report_dir, f"Z_Report_{datetime.now().strftime('%Y-%m-%d')}.md")
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            console.print(f"  ✅ Rapor başarıyla '{report_filename}' dosyasına kaydedildi.")

        except Exception as e:
            console.print(f"  [red]❌ Rapor oluşturma hatası: {e}[/red]")
        finally:
            session.close()