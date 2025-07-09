# app/sensors/parsers.py - NİHAİ VERSİYON

from typing import Optional, Tuple

def parse_height(data: bytes) -> Optional[float]:
    """
    Mesafe sensöründen gelen 'Rxxxx' formatındaki veriyi parse eder.
    Eski projeden alınan test edilmiş mantık kullanılmıştır.
    """
    try:
        # Gelen byte dizisinde birden fazla mesaj olabilir, 'R' harfini sondan aramak
        # en güncel veriyi alma olasılığını artırır.
        str_data = data.decode('ascii', errors='ignore')
        if 'R' in str_data:
            # En son 'R' harfinin konumunu bul
            start_idx = str_data.rfind('R') + 1
            # 'R'den sonra en az 4 karakter olup olmadığını kontrol et
            if len(str_data) >= start_idx + 4:
                # Sonraki 4 karakteri al
                distance_str = str_data[start_idx : start_idx + 4]
                # Sadece rakamlardan oluşuyorsa çevir
                if distance_str.isdigit():
                    return float(distance_str)
    except (ValueError, UnicodeDecodeError):
        pass  # Hata durumunda None dönecek
    return None

def parse_weight(data: bytes) -> Optional[float]:
    """
    Ağırlık sensöründen gelen '=   15.65B0' formatındaki veriyi parse eder.
    Eski projeden alınan ve minicom'da teyit edilen mantık kullanılmıştır.
    """
    try:
        str_data = data.decode('ascii', errors='ignore').strip()
        
        # Formatın '=' ile başladığını ve içinde '.' olduğunu kontrol edelim
        if str_data.startswith("=") and "." in str_data:
            # Eşittir işaretini ve baştaki/sondaki boşlukları at
            cleaned_str = str_data.lstrip('=').strip()
            
            # Değerin sayısal kısmını ve birim/checksum kısmını ayır
            # Genellikle sayısal olmayan ilk karakterde ayrım yapılır.
            numeric_part = ""
            for char in cleaned_str:
                if char.isdigit() or char == '.':
                    numeric_part += char
                else:
                    # Sayısal olmayan bir karaktere gelindiğinde döngüden çık
                    break
            
            if numeric_part:
                value_kg = float(numeric_part)
                # Değeri kg kabul edip grama çeviriyoruz
                return value_kg * 1000
    except (ValueError, UnicodeDecodeError, IndexError):
        pass  # Hata durumunda None dönecek
    return None

def parse_sht3x(data: list) -> Tuple[Optional[float], Optional[float]]:
    """SHT3x sensöründen gelen 6 byte'lık veriyi sıcaklık ve neme çevirir."""
    try:
        if not data or len(data) < 6:
            return None, None
            
        # Sıcaklık hesaplama
        temp_raw = (data[0] << 8) | data[1]
        temperature = -45 + (175 * temp_raw / 65535.0)
        
        # Nem hesaplama
        hum_raw = (data[3] << 8) | data[4]
        humidity = 100 * hum_raw / 65535.0
        
        return round(temperature, 2), round(humidity, 2)
    except (IndexError, TypeError):
        return None, None