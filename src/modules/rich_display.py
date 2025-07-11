from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text
from datetime import datetime

class RichDisplay:
    """Zengin konsol çıktılarını yöneten sınıf."""
    def __init__(self):
        self.console = Console()

    def print_startup_banner(self):
        banner_text = Text("Kar Gözlem ve Çığ Tahmin İstasyonu v0.3", style="bold magenta", justify="center")
        self.console.print(Panel(banner_text, title="[bold green]SİSTEM BAŞLATILIYOR[/bold green]", border_style="green"))

    def print_collection_header(self):
        self.console.print("\n[bold magenta]🔥 Veri Toplanıyor...[/bold magenta]")

    def print_collection_result(self, data):
        """Tek satırlık okuma sonucunu yazdırır."""
        # Veri yoksa veya boşsa, hata mesajı göster
        if not data:
            self.console.print("[bold red]❌ Sensörlerden veri alınamadı.[/bold red]")
            return

        ts = datetime.now().strftime('%H:%M:%S')
        
        # Değerleri al veya 'N/A' olarak ayarla
        dist = f"{data.get('distance_mm', 'N/A')} mm" if 'distance_mm' in data else "N/A"
        weight = f"{data.get('weight_g', 'N/A')} g" if 'weight_g' in data else "N/A"
        temp = f"{data.get('temperature_c', 'N/A')}°C" if 'temperature_c' in data else "N/A"
        hum = f"{data.get('humidity_percent', 'N/A')}%" if 'humidity_percent' in data else "N/A"
        
        output = f"[{ts}] ✅ | 📏 {dist:<10} | ⚖️ {weight:<10} | 🌡️ {temp:<10} | 💧 {hum:<10}"
        self.console.print(output)
        self.console.print("[dim]Sensörler bir sonraki döngüye kadar kapatıldı.[/dim]")


    def print_status_dashboard(self, system_status):
        """Sistemin genel durumunu gösteren bir tablo yazdırır."""
        
        table = Table(title=f"📊 Sistem Durum Kontrolü ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) 📊",
                      show_header=True, header_style="bold cyan")
        table.add_column("Öğe", style="dim", width=22)
        table.add_column("Durum", width=21)
        table.add_column("Detay", width=30)

        # Sensör Durumları
        for name, status in system_status.get('sensors', {}).items():
            status_text = Text("BAĞLI", style="green") if status['connected'] else Text("BAĞLI DEĞİL", style="red")
            table.add_row(f"📏 {name.capitalize()} Sensörü", status_text, status['detail'])
        
        # I2C Durumu (Örnek)
        i2c_status = system_status.get('i2c_sensor', {})
        i2c_conn = Text("BAĞLI", style="green") if i2c_status.get('connected') else Text("HATA/YEDEK MOD", style="yellow")
        table.add_row("🌡️/💧 Sıcaklık/Nem", i2c_conn, i2c_status.get('detail', 'Bilinmiyor'))
        
        table.add_section()

        # Görev Durumları
        last_collection = system_status.get('last_collection', {})
        table.add_row("🔄 Son Veri Toplama", Text(last_collection.get('status', 'Not run yet'), style="green" if last_collection.get('status') == 'Success' else "default"), f"Zaman: {last_collection.get('time', 'N/A')}")
        
        last_api = system_status.get('last_api_send', {})
        table.add_row("🛰️ Son API Gönderimi", Text(last_api.get('status', 'Not run yet'), style="green" if last_api.get('status') == 'Success' else "default"), f"Zaman: {last_api.get('time', 'N/A')}")
        
        table.add_section()
        
        # Sonraki Görev
        next_job = system_status.get('next_job', {})
        table.add_row("⏳ Sonraki Görev", Text(next_job.get('time', 'N/A'), style="bold"), next_job.get('name', 'Bilinmiyor'))

        self.console.print(table)