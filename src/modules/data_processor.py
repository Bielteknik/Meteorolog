import re

class DataProcessor:
    def __init__(self, config):
        self.config = config
        print("INFO: DataProcessor başlatıldı.")

    def _parse(self, name, data):
        try:
            if name == 'distance': return int(re.search(r'\d{4}', data).group(0))
            if name == 'weight':
                val = float(re.search(r'=\s*([\d\.]+)', data).group(1))
                return (int(val) * 1000) + int(round((val % 1) * 100))
        except (AttributeError, ValueError, TypeError): return None

    def process_reading_data(self, raw_data):
        processed = {}
        for key, value in raw_data.items():
            if key in ['distance', 'weight']:
                parsed_val = self._parse(key, value)
                processed[f'{key}_mm' if key == 'distance' else f'{key}_g'] = parsed_val
            elif key in ['temperature_c', 'humidity_percent']:
                processed[key] = round(value, 1) if value is not None else None
        
        if 'distance_mm' in processed and processed['distance_mm'] is not None:
            mount_h = self.config['sensors']['distance']['mount_height_mm']
            processed['snow_height_mm'] = max(0, mount_h - processed['distance_mm'])
        
        if processed.get('snow_height_mm', 0) > 0 and processed.get('weight_g', 0) > 0:
            h_m, area, w_kg = processed['snow_height_mm']/1000.0, self.config['sensors']['weight']['measurement_area_m2'], processed['weight_g']/1000.0
            if (vol := h_m * area) > 0:
                density = w_kg / vol
                processed['density_kg_m3'] = round(density, 2)
                processed['swe_mm'] = round(processed['snow_height_mm'] * (density / 1000), 2)
        return processed