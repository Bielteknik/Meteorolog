from rich.console import Console
from rich.table import Table
from rich.panel import Panel
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
        if not data:
            self.console.print("[bold red]❌ Sensörlerden veri alınamadı.[/bold red]")
            return

        ts = datetime.now().strftime('%H:%M:%S')
        dist = f"{data.get('distance_mm', 'N/A')} mm"
        weight = f"{data.get('weight_g', 'N/A')} g"
        temp = f"{data.get('temperature_c', 'N/A')}°C"
        hum = f"{data.get('humidity_percent', 'N/A')}%"
        
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
            status_text = Text("BAĞLI", style="green") if status.get('connected') else Text("BAĞLI DEĞİL", style="red")
            table.add_row(f"-> {name.capitalize()} Sensörü", status_text, status.get('detail', ''))

        table.add_section()
        
        # Görev Durumları
        last_collection = system_status.get('last_collection', {})
        table.add_row("🔄 Son Veri Toplama", Text(last_collection.get('status', 'Çalışmadı'), style="green" if last_collection.get('status') == 'Success' else "default"), f"Zaman: {last_collection.get('time', 'N/A')}")
        
        # API satırı bilinçli olarak çıkarıldı.
        
        table.add_section()
        
        next_job = system_status.get('next_job', {})
        table.add_row("⏳ Sonraki Görev", Text(next_job.get('time', 'N/A'), style="bold"), next_job.get('name', 'Bilinmiyor'))

        self.console.print(table)