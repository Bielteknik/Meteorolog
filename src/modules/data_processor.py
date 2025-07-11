import re

class DataProcessor:
    def __init__(self, config):
        self.config = config
        print("INFO: DataProcessor başlatıldı.")

    def _parse_distance(self, data):
        try:
            match = re.search(r'\d{4}', data)
            if match:
                return int(match.group(0))
        except (ValueError, TypeError): pass
        return None

    def _parse_weight(self, data):
        try:
            match = re.search(r'=\s*([\d\.]+)', data)
            if match:
                value_float = float(match.group(1))
                kg_part = int(value_float)
                gr_part = int(round((value_float % 1) * 100))
                return (kg_part * 1000) + gr_part
        except (ValueError, TypeError): pass
        return None

    def _calculate_derived_values(self, processed_data):
        if 'distance_mm' in processed_data and processed_data['distance_mm'] is not None:
            mount_height = self.config['sensors']['distance']['mount_height_mm']
            snow_height_mm = mount_height - processed_data['distance_mm']
            processed_data['snow_height_mm'] = max(0, snow_height_mm)

        if processed_data.get('snow_height_mm', 0) > 0 and processed_data.get('weight_g', 0) > 0:
            snow_height_m = processed_data['snow_height_mm'] / 1000.0
            area = self.config['sensors']['weight']['measurement_area_m2']
            volume = snow_height_m * area
            weight_kg = processed_data['weight_g'] / 1000.0
            if volume > 0:
                density = weight_kg / volume
                processed_data['density_kg_m3'] = round(density, 2)
                swe_mm = processed_data['snow_height_mm'] * (density / 1000)
                processed_data['swe_mm'] = round(swe_mm, 2)
        return processed_data

    def process_reading_data(self, raw_data):
        """Ham veri sözlüğünü işler, parse eder ve türetilmiş değerleri hesaplar."""
        processed = {}
        for key, value in raw_data.items():
            if key == 'distance':
                processed['distance_mm'] = self._parse_distance(value)
            elif key == 'weight':
                processed['weight_g'] = self._parse_weight(value)
            elif key == 'temperature_c':
                processed['temperature_c'] = round(value, 1) if value is not None else None
            elif key == 'humidity_percent':
                processed['humidity_percent'] = round(value, 1) if value is not None else None
        
        return self._calculate_derived_values(processed)