import schedule
import time
import logging
import sys
import traceback
from datetime import datetime, timedelta
from typing import List, Optional
from tqdm import tqdm
from rich.console import Console
from rich.table import Table

from app.config import settings
from app.models.schemas import ProcessedReading
from app.sensors.manager import SensorManager
from app.core.collector import DataCollector
from app.core.processor import DataProcessor
from app.services.database import DatabaseService
from app.services.storage import CsvStorageService
from app.services.notification import NotificationService
from app.services.remote_api_service import RemoteApiService

logger = logging.getLogger(__name__)

class JobScheduler:
    def __init__(self):
        self.console = Console()
        self.sensor_manager = SensorManager()
        self.db_service = DatabaseService()
        self.processor = DataProcessor(self.db_service)
        self.collector = DataCollector(self.sensor_manager)
        self.csv_service = CsvStorageService()
        self.notification_service = NotificationService()
        self.remote_api = RemoteApiService()

        self.last_collection_time: Optional[datetime] = None
        self.last_collection_status: str = "Not run yet"
        self.last_api_post_time: Optional[datetime] = None
        self.last_api_post_status: str = "Not run yet"
        self.last_daily_report_time: Optional[datetime] = None

    def setup_schedule(self):
        interval = settings.DATA_COLLECTION_INTERVAL_MINUTES
        schedule.every(interval).minutes.do(self.run_collection_cycle)
        logger.info(f"Ana görev {interval} dakikada bir çalışacak şekilde ayarlandı.")

        schedule.every().hour.at(":01").do(self.run_remote_post_job)
        logger.info("Uzak API'ye veri gönderme görevi her saatin 1. dakikasında çalışacak şekilde ayarlandı.")
        
        schedule.every().day.at("00:05").do(self.run_daily_report_job)
        logger.info("Günlük anomali raporu görevi her gün 00:05'te çalışacak şekilde ayarlandı.")

    def run_daily_report_job(self):
        logger.info("Günlük anomali raporu oluşturuluyor...")
        self.last_daily_report_time = datetime.now()
        try:
            start_of_report_period = self.last_daily_report_time - timedelta(days=1)
            total_anomalies = self.db_service.count_anomalies_since(start_of_report_period)
            report_title = "Günlük Sistem Sağlık ve Anomali Raporu"
            report_details = (
                f"Rapor Dönemi: {start_of_report_period.strftime('%Y-%m-%d %H:%M')} - {self.last_daily_report_time.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"Bu dönemde tespit edilen toplam anomali sayısı: {total_anomalies}"
            )
            logger.info(f"--- {report_title} ---\n{report_details}\n--- RAPOR SONU ---")
            self.notification_service.send_error_notification(report_title, report_details)
        except Exception as e:
            logger.error(f"Günlük rapor oluşturma görevinde hata: {e}", exc_info=True)

    def run_remote_post_job(self):
        logger.info("Uzak API'ye veri gönderme görevi başlatılıyor...")
        self.last_api_post_time = datetime.now()
        try:
            latest_reading = self.db_service.get_latest_reading()
            if latest_reading:
                success = self.remote_api.post_reading(latest_reading)
                self.last_api_post_status = "Success" if success else "Failed"
            else:
                logger.warning("Uzak API'ye göndermek için veritabanında hiç kayıt bulunamadı.")
                self.last_api_post_status = "No data to send"
        except Exception as e:
            logger.error(f"Uzak API'ye veri gönderme görevinde beklenmedik bir hata oluştu: {e}", exc_info=True)
            self.last_api_post_status = "Crashed"
            self.notification_service.send_error_notification("Uzak API'ye Veri Gönderme Hatası", traceback.format_exc())

    def run_collection_cycle(self):
        logger.info("Veri toplama döngüsü başlatılıyor...")
        self.last_collection_time = datetime.now()
        try:
            self.sensor_manager.discover_and_connect()
            self.sensor_manager.prepare_for_reading()
            if not self.sensor_manager.is_temp_hum_connected:
                 if not self.collector.owm_service.is_fallback_active:
                    logger.warning("I2C sensor not found. Activating OWM fallback for this cycle.")
                    self.collector.owm_service.is_fallback_active = True
                    self.collector.owm_service.update_cache(force_update=True)
            else:
                 if self.collector.owm_service.is_fallback_active:
                    logger.info("I2C sensor is back online. Disabling OWM fallback.")
                    self.collector.owm_service.is_fallback_active = False
            collected_readings: List[ProcessedReading] = []
            burst_duration = timedelta(minutes=settings.DATA_BURST_DURATION_MINUTES)
            sample_interval = timedelta(seconds=settings.DATA_BURST_SAMPLE_INTERVAL_SECONDS)
            end_time = datetime.now() + burst_duration
            with tqdm(total=int(burst_duration.total_seconds()), desc="[bold magenta]🔥 Veri Toplanıyor[/bold magenta]", bar_format="{l_bar}{bar}|", file=sys.stdout, leave=True) as pbar:
                while datetime.now() < end_time:
                    start_loop_time = time.time()
                    raw_data = self.collector.collect_raw_data()
                    processed_data = self.processor.process_raw_data(raw_data)
                    collected_readings.append(processed_data)
                    loop_duration = time.time() - start_loop_time
                    sleep_time = max(0, sample_interval.total_seconds() - loop_duration)
                    time.sleep(sleep_time)
                    pbar.update(int(sample_interval.total_seconds()))
            print()
            if not collected_readings:
                logger.warning("Veri toplama patlaması sonucunda hiç veri elde edilemedi.")
                self._print_summary(ProcessedReading(), status_icon="⚠️")
                self.last_collection_status = "Failed (No Data)"
                return
            summary_reading = self.processor.analyze_burst_readings(collected_readings)
            self.db_service.save_reading(summary_reading)
            self.csv_service.save_readings_to_csv([summary_reading])
            self._print_summary(summary_reading, status_icon="✅")
            logger.info("Döngü başarıyla tamamlandı.")
            self.last_collection_status = "Success"
        except Exception:
            self.last_collection_status = "Crashed"
            logger.critical("Veri toplama döngüsünde kritik bir hata oluştu!", exc_info=True)
            self.notification_service.send_error_notification("Kritik Döngü Hatası", traceback.format_exc())
            print()
            self._print_summary(ProcessedReading(), status_icon="❌")
        finally:
            self.sensor_manager.disconnect_all()
            self.console.print("[dim]Sensörler bir sonraki döngüye kadar kapatıldı.[/dim]")
    
    def print_system_status(self):
        table = Table(title=f"📊 Sistem Durum Kontrolü ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) 📊", style="cyan", title_style="bold magenta")
        table.add_column("Öğe", style="bold green", no_wrap=True)
        table.add_column("Durum", style="bold")
        table.add_column("Detay", style="cyan")
        h_status = "[bold green]BAĞLI[/]" if self.sensor_manager.is_height_connected else "[bold yellow]BAĞLI DEĞİL[/]"
        h_detail = self.sensor_manager.height_port or "Port bulunamadı."
        table.add_row("📏 Yükseklik Sensörü", h_status, h_detail)
        w_status = "[bold green]BAĞLI[/]" if self.sensor_manager.is_weight_connected else "[bold yellow]BAĞLI DEĞİL[/]"
        w_detail = self.sensor_manager.weight_port or "Port bulunamadı."
        table.add_row("⚖️ Ağırlık Sensörü", w_status, w_detail)
        if self.sensor_manager.is_temp_hum_connected:
            t_status = "[bold green]BAĞLI[/]"; t_detail = f"I2C Bus {settings.I2C_BUS} aktif."
        else:
            t_status = "[bold red]YEDEK MOD[/]"; t_detail = "OpenWeatherMap kullanılıyor."
        table.add_row("🔌/📡 Sıcaklık/Nem", t_status, t_detail)
        table.add_section()
        status_color = {"Success": "green", "Crashed": "red", "Failed": "red", "Failed (No Data)": "yellow"}.get(self.last_collection_status, "white")
        status_text = f"[{status_color}]{self.last_collection_status}[/]"
        time_text = self.last_collection_time.strftime('%H:%M:%S') if self.last_collection_time else "N/A"
        table.add_row("🔄 Son Veri Toplama", status_text, f"Zaman: {time_text}")
        status_color = {"Success": "green", "Crashed": "red", "Failed": "red"}.get(self.last_api_post_status, "white")
        status_text = f"[{status_color}]{self.last_api_post_status}[/]"
        time_text = self.last_api_post_time.strftime('%H:%M:%S') if self.last_api_post_time else "N/A"
        table.add_row("🛰️ Son API Gönderimi", status_text, f"Zaman: {time_text}")
        report_time_str = self.last_daily_report_time.strftime('%Y-%m-%d %H:%M') if self.last_daily_report_time else "Henüz oluşturulmadı"
        table.add_row("📜 Son Günlük Rapor", report_time_str, "")
        table.add_section()
        
        # --- BU BÖLÜM TAMAMEN YENİDEN YAZILDI ---
        next_run_str = "N/A"
        job_details_str = "Hiç görev planlanmamış."
        if schedule.jobs:
            # En yakın çalışacak görevi bul
            next_job = min(schedule.jobs, key=lambda j: j.next_run)
            # Bu görevin çalışma zamanını al
            next_run_time_obj = next_job.next_run
            if next_run_time_obj:
                next_run_str = next_run_time_obj.strftime('%H:%M:%S')

            # O zamanda çalışacak tüm görevlerin isimlerini topla
            upcoming_jobs = [
                getattr(j.job_func, '__name__', 'Bilinmeyen Görev')
                for j in schedule.jobs if j.next_run == next_run_time_obj
            ]
            job_details_str = ", ".join(sorted(list(set(upcoming_jobs))))

        table.add_row("⏳ Sonraki Görev", next_run_str, job_details_str)
        self.console.print(table)
        
    def log_system_status(self):
        # Bu metodda değişiklik yok, aynı kalıyor
        pass

    def _print_summary(self, summary: ProcessedReading, status_icon: str):
        now = datetime.now()
        next_run_time = now + timedelta(minutes=settings.DATA_COLLECTION_INTERVAL_MINUTES)
        h_str = f"{summary.snow_height_mm:.1f} mm" if summary.snow_height_mm is not None else "N/A"
        w_str = f"{summary.weight_g:.0f} g" if summary.weight_g is not None else "N/A"
        source_icon = "📡" if summary.temp_hum_source == "api" else "🔌"
        t_str = f"{summary.temperature_c:.1f}°C" if summary.temperature_c is not None else "N/A"
        hu_str = f"{summary.humidity_perc:.1f}%" if summary.humidity_perc is not None else "N/A"
        summary_line = (
            f"[white on black][{now.strftime('%H:%M:%S')}][/white on black] {status_icon} | "
            f"📏 [bold cyan]{h_str.ljust(9)}[/bold cyan] | "
            f"⚖️  [bold green]{w_str.ljust(8)}[/bold green] | "
            f"{source_icon}🌡️ [bold yellow]{t_str.ljust(7)}[/bold yellow] | "
            f"💧 [bold blue]{hu_str.ljust(6)}[/bold blue] | "
            f"⏳ [dim]{next_run_time.strftime('%H:%M')}[/dim]"
        )
        self.console.print(summary_line)

    def run_forever(self):
        logger.info("Meteoroloji İstasyonu Servisi Başlatılıyor...")
        self.setup_schedule()
        self.notification_service.send_startup_notification()
        self.console.print("\n[bold green]✨ Sistem aktif. İlk döngü hemen başlatılıyor...[/bold green]")
        self.run_collection_cycle()
        self.console.print("\n[bold]📊 Döngü Sonrası Durum Kontrolü 📊[/bold]")
        self.print_system_status()
        self.console.print(f"\n[bold green]✨ Normal zamanlama döngüsü bekleniyor...[/bold green]")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.console.print("\n[bold red]🛑 Program kullanıcı tarafından durduruldu.[/bold red]")
            logger.info("Program kullanıcı tarafından durduruldu.")
        finally:
            logger.info("👋 Hoşçakalın!")
            self.console.print("[bold blue]👋 Program sonlandırıldı.[/bold blue]")