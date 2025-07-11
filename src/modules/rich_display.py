from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime

class RichDisplay:
    def __init__(self):
        self.console = Console()

    def print_startup_banner(self):
        banner_text = Text("Kar Gözlem ve Çığ Tahmin İstasyonu v1.1 (Modüler)", style="bold magenta", justify="center")
        self.console.print(Panel(banner_text, title="[bold green]SİSTEM BAŞLATILIYOR[/bold green]", border_style="green"))

    def print_collection_header(self):
        self.console.print("\n[bold magenta]🔥 Veri Toplanıyor...[/bold magenta]")

    def print_collection_result(self, data):
        if not data:
            self.console.print("[bold red]❌ Sensörlerden anlamlı veri alınamadı.[/bold red]")
            return
        ts = datetime.now().strftime('%H:%M:%S')
        dist = f"{data.get('distance_mm', 'N/A')} mm"
        weight = f"{data.get('weight_g', 'N/A')} g"
        temp = f"{data.get('temperature_c', 'N/A')}°C"
        hum = f"{data.get('humidity_percent', 'N/A')}%"
        output = f"[{ts}] ✅ | 📏 {dist:<10} | ⚖️ {weight:<10} | 🌡️ {temp:<10} | 💧 {hum:<10}"
        self.console.print(output)

    def print_status_dashboard(self, system_status):
        table = Table(title=f"📊 Sistem Durum Kontrolü ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) 📊", show_header=True, header_style="bold cyan")
        table.add_column("Öğe", style="dim", width=28)
        table.add_column("Durum", width=15)
        table.add_column("Detay", width=32)
        sensor_map = {"temperature_humidity": "🌡️/💧 Sıcaklık/Nem", "distance": "📏 Mesafe", "weight": "⚖️ Ağırlık"}
        for name in sensor_map.keys():
            status = system_status.get('sensors', {}).get(name, {})
            pretty_name = sensor_map.get(name, name.capitalize())
            is_connected = status.get('connected', False)
            status_text = Text("BAĞLI", style="green") if is_connected else Text("BAĞLI DEĞİL", style="red")
            if "YEDEK" in status.get('detail', ''): status_text = Text("YEDEK MOD", style="yellow")
            table.add_row(pretty_name, status_text, status.get('detail', ''))
        table.add_section()
        last_collection = system_status.get('last_collection', {})
        table.add_row("🔄 Son Veri Toplama", Text(last_collection.get('status', 'Çalışmadı'), style="green" if last_collection.get('status') == 'Success' else "default"), f"Zaman: {last_collection.get('time', 'N/A')}")
        table.add_section()
        next_job = system_status.get('next_job', {})
        table.add_row("⏳ Sonraki Görev", Text(next_job.get('time', 'Bilinmiyor'), style="bold"), next_job.get('name', 'Veri Toplama'))
        self.console.print(table)