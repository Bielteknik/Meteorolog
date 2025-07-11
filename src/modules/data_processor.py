import re

class DataProcessor:
    """
    Ham sensör verilerini alır, parse eder, doğrular ve anlamlı
    bilgilere dönüştürür.
    """
    def __init__(self, config):
        """
        Args:
            config (dict): Sistem yapılandırma sözlüğü.
        """
        self.config = config
        print("INFO: DataProcessor başlatıldı.")

    def parse_raw_data(self, sensor_name, raw_data):
        """
        Belirli bir sensörden gelen ham veriyi parse eder.

        Args:
            sensor_name (str): 'distance' veya 'weight' gibi sensör adı.
            raw_data (str): Sensörden okunan ham metin.

        Returns:
            int veya float: Parse edilmiş sayısal değer veya None.
        """
        if sensor_name == 'distance':
            return self._parse_distance(raw_data)
        elif sensor_name == 'weight':
            return self._parse_weight(raw_data)
        # Gelecekte eklenecek diğer sensörler için buraya 'elif' eklenebilir.
        return None

    def _parse_distance(self, data):
        """Mesafe sensöründen gelen veriyi parse eder (Rxxxx -> mm)."""
        try:
            # Sadece 4 rakamı bul ve al
            match = re.search(r'\d{4}', data)
            if match:
                distance_mm = int(match.group(0))
                # Temel doğrulama (örneğin 0'dan büyük olmalı)
                if distance_mm > 0:
                    return distance_mm
        except (ValueError, TypeError):
            pass # Hatalı formatı görmezden gel
        return None

    def _parse_weight(self, data):
        """Ağırlık sensöründen gelen veriyi parse eder (= 183.25B0 -> gram)."""
        try:
            # Eşittir işaretinden sonraki ondalıklı sayıyı bul
            match = re.search(r'=\s*([\d\.]+)', data)
            if match:
                value_str = match.group(1)
                value_float = float(value_str)
                # Onaylanan formül: 183.25 -> 183 kg 25 gr -> 183025 gr
                kg_part = int(value_float)
                gr_part = int(round((value_float % 1) * 100))
                total_grams = (kg_part * 1000) + gr_part
                return total_grams
        except (ValueError, TypeError):
            pass
        return None
        
    def calculate_derived_values(self, processed_data):
        """
        İşlenmiş verilerden yeni değerler (Kar Yüksekliği, Yoğunluk, SWE) hesaplar.
        
        Args:
            processed_data (dict): {'distance_mm': 2800, 'weight_g': 10500} gibi.
            
        Returns:
            dict: Hesaplanmış değerlerin eklendiği sözlük.
        """
        # Kar Yüksekliği
        if 'distance_mm' in processed_data and processed_data['distance_mm'] is not None:
            mount_height = self.config['sensors']['distance']['mount_height_mm']
            snow_height_mm = mount_height - processed_data['distance_mm']
            # Kar yüksekliği negatif olamaz
            processed_data['snow_height_mm'] = max(0, snow_height_mm)

        # Kar Yoğunluğu ve SWE (Kar Su Eşdeğeri)
        if 'snow_height_mm' in processed_data and processed_data['snow_height_mm'] > 0 and \
           'weight_g' in processed_data and processed_data['weight_g'] is not None:
            
            snow_height_m = processed_data['snow_height_mm'] / 1000.0
            measurement_area_m2 = self.config['sensors']['weight']['measurement_area_m2']
            snow_volume_m3 = snow_height_m * measurement_area_m2
            
            snow_weight_kg = processed_data['weight_g'] / 1000.0
            
            # Yoğunluk (kg/m^3)
            if snow_volume_m3 > 0:
                density_kg_m3 = snow_weight_kg / snow_volume_m3
                processed_data['density_kg_m3'] = round(density_kg_m3, 2)

                # SWE (mm)
                # SWE = Yükseklik(mm) * (Kar Yoğunluğu / Su Yoğunluğu)
                water_density = 1000 # kg/m^3
                swe_mm = processed_data['snow_height_mm'] * (density_kg_m3 / water_density)
                processed_data['swe_mm'] = round(swe_mm, 2)
                
        return processed_data