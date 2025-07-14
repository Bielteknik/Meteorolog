# main.py
from rich import print
from config import settings

def main():
    """
    Ana program başlangıç noktası.
    """
    print("[bold green]✅ Yapılandırma başarıyla yüklendi![/bold green]")
    print("\n[bold cyan]Aktif Yapılandırma Detayları:[/bold cyan]")
    
    # rich kütüphanesi Pydantic modellerini otomatik olarak güzel basar
    print(settings)

if __name__ == "__main__":
    main()