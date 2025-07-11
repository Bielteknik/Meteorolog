import requests
import json
from datetime import datetime

class CommunicationManager:
    """
    Uzak API sunucusu ile iletişimi yönetir.
    """
    def __init__(self, config):
        self.config = config.get('api', {})
        self.api_url = self.config.get('url')
        self.api_timeout = self.config.get('timeout_seconds', 30)
        
        if not self.api_url:
            print("WARNING: API URL'si yapılandırmada bulunamadı. İletişim modülü pasif kalacak.")
        
        print("INFO: CommunicationManager başlatıldı.")

    def format_data_for_api(self, data_from_db):
        """
        Veritabanından gelen veriyi API'nin beklediği formata dönüştürür.
        """
        if not data_from_db:
            return None
        
        # API'nin beklediği anahtarlarla eşleştirme yap
        # API tam sayı bekliyor, bu yüzden 'or 0' ile None değerlerini 0'a çevirip int() yapıyoruz.
        api_data = {
            "tarih": data_from_db.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            "sicaklik": int(data_from_db.get('temperature_c') or 0),
            "nem": int(data_from_db.get('humidity_percent') or 0),
            "mesafe": int(data_from_db.get('distance_mm') or 0),
            "agirlik": int(data_from_db.get('weight_g') or 0)
        }
        return api_data

    def send_data(self, data_payload):
        """
        Hazırlanmış veri paketini API'ye gönderir.
        """
        if not self.api_url:
            print("ERROR: API URL'si ayarlanmamış. Veri gönderilemiyor.")
            return False
            
        if not data_payload:
            print("WARNING: Gönderilecek veri yok.")
            return False

        headers = {'Content-Type': 'application/json'}
        
        try:
            print(f"INFO: API'ye veri gönderiliyor -> {self.api_url}")
            print(f"  -> Payload: {json.dumps(data_payload)}")
            
            response = requests.post(self.api_url, headers=headers, json=data_payload, timeout=self.api_timeout)
            
            # Sunucudan gelen yanıtı kontrol et
            if 200 <= response.status_code < 300:
                print(f"SUCCESS: Veri başarıyla gönderildi. Status: {response.status_code}")
                return True
            else:
                print(f"ERROR: API'ye veri gönderilemedi. Status: {response.status_code}, Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"CRITICAL: API bağlantı hatası: {e}")
            return False