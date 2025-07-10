from typing import Optional, Tuple

def parse_height_from_raw(data: bytes) -> Optional[float]:
    """
    Mesafe sensöründen gelen 'Rxxxx' formatındaki ham byte verisini parse eder.
    """
    if not data:
        return None
    try:
        str_data = data.decode('ascii', errors='ignore')
        if 'R' in str_data:
            # En son 'R'yi bul, çünkü buffer'da birden fazla okuma olabilir
            start_idx = str_data.rfind('R') + 1
            if len(str_data) >= start_idx + 4:
                distance_str = str_data[start_idx : start_idx + 4]
                if distance_str.isdigit():
                    return float(distance_str)
    except (ValueError, UnicodeDecodeError):
        pass
    return None

def parse_weight_from_raw(data: bytes) -> Optional[float]:
    """
    Ağırlık sensöründen gelen '=   15.65B0' formatındaki ham byte verisini parse eder.
    """
    if not data:
        return None
    try:
        str_data = data.decode('ascii', errors='ignore').strip()
        if str_data.startswith("=") and "." in str_data:
            cleaned_str = str_data.lstrip('=').strip()
            numeric_part = ""
            for char in cleaned_str:
                if char.isdigit() or char == '.':
                    numeric_part += char
                else:
                    break
            if numeric_part:
                value_kg = float(numeric_part)
                return value_kg * 1000  # kg'dan grama çevir
    except (ValueError, UnicodeDecodeError, IndexError):
        pass
    return None

def parse_temp_hum_from_raw(data: list) -> Tuple[Optional[float], Optional[float]]:
    """SHT3x sensöründen gelen 6 byte'lık ham veriyi sıcaklık ve neme çevirir."""
    if not data or len(data) < 6:
        return None, None
    try:
        temp_raw = (data[0] << 8) | data[1]
        temperature = -45 + (175 * temp_raw / 65535.0)
        
        hum_raw = (data[3] << 8) | data[4]
        humidity = 100 * hum_raw / 65535.0
        
        return round(temperature, 2), round(humidity, 2)
    except (IndexError, TypeError):
        return None, None