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
        except: return None
    def process_reading_data(self, raw):
        p = {f"{k}_mm" if k == 'distance' else f"{k}_g": self._parse(k, v) for k, v in raw.items() if k in ['distance', 'weight']}
        p.update({k: round(v, 1) if v is not None else None for k, v in raw.items() if k in ['temperature_c', 'humidity_percent']})
        if p.get('distance_mm') is not None:
            p['snow_height_mm'] = max(0, self.config['sensors']['distance']['mount_height_mm'] - p['distance_mm'])
        if p.get('snow_height_mm', 0) > 0 and p.get('weight_g', 0) > 0:
            h, area, w = p['snow_height_mm']/1000.0, self.config['sensors']['weight']['measurement_area_m2'], p['weight_g']/1000.0
            if (vol := h * area) > 0:
                p['density_kg_m3'] = round((density := w / vol), 2)
                p['swe_mm'] = round(p['snow_height_mm'] * (density / 1000), 2)
        return p
    def shutdown(self): pass