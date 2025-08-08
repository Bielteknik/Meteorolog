from django.core.management.base import BaseCommand
from dashboard.models import Setting

class Command(BaseCommand):
    help = 'Veritabanındaki sistem ayarlarını başlatır veya günceller.'

    def handle(self, *args, **options):
        # Admin panelinden yönetilecek ayarların listesi
        # Anahtar : Varsayılan Değer
        SETTINGS = {
            'RTSP_USER': 'admin',
            'RTSP_PASSWORD': 'Ejder.25',
            'RTSP_IP': '192.168.1.50',
            'RTSP_PORT': '554',
            'RTSP_CHANNEL': '101',
        }

        self.stdout.write("Sistem ayarları kontrol ediliyor...")
        
        for key, value in SETTINGS.items():
            # Ayar zaten varsa güncelle, yoksa oluştur (update_or_create)
            obj, created = Setting.objects.update_or_create(
                key=key,
                defaults={'value': value}
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"'{key}' ayarı oluşturuldu: {value}"))
            else:
                self.stdout.write(f"'{key}' ayarı zaten mevcuttu, varsayılan değere güncellendi.")
        
        self.stdout.write(self.style.SUCCESS("Tüm ayarlar başarıyla kontrol edildi/oluşturuldu."))