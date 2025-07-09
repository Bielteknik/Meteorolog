from typing import Optional, Tuple

def parse_height(data: bytes) -> Optional[float]:
    """Mesafe sensöründen gelen 'Rxxxx' formatındaki veriyi parse eder."""
    try:
        str_data = data.decode('ascii', errors='ignore')
        if 'R' in str_data:
            # 'R' harfinden sonraki 4 karakteri bul ve sayıya çevir
            start_idx = str_data.rfind('R') + 1
            if start_idx < len(str_data):
                num_str = str_data[start_idx : start_idx + 4]
                if num_str.isdigit():
                    return float(num_str)
    except (ValueError, UnicodeDecodeError):
        pass  # Hata durumunda None dönecek
    return None

def parse_weight(data: bytes) -> Optional[float]:
    """Ağırlık sensöründen gelen 'kg' içeren veriyi parse edip grama çevirir."""
    try:
        str_data = data.decode('ascii', errors='ignore').strip()
        if "kg" in str_data:
            # Sadece sayısal kısmı ve noktayı al
            numeric_part = "".join(c for c in str_data if c.isdigit() or c == '.')
            if numeric_part:
                kg_value = float(numeric_part)
                return kg_value * 1000  # Grama çevir
    except (ValueError, UnicodeDecodeError):
        pass  # Hata durumunda None dönecek
    return None

def parse_sht3x(data: list) -> Tuple[Optional[float], Optional[float]]:
    """SHT3x sensöründen gelen 6 byte'lık veriyi sıcaklık ve neme çevirir."""
    try:
        # Sıcaklık hesaplama
        temp_raw = (data[0] << 8) | data[1]
        temperature = -45 + (175 * temp_raw / 65535.0)
        # Nem hesaplama
        hum_raw = (data[3] << 8) | data[4]
        humidity = 100 * hum_raw / 65535.0
        return round(temperature, 2), round(humidity, 2)
    except (IndexError, TypeError):
        return None, None