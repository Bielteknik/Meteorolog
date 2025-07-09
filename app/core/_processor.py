from app.config import _settings
from app.models.schemas import SensorReading, ProcessedReading

class DataProcessor:
    """
    Sensör verilerini işler, ek hesaplamalar yapar (kar yüksekliği, yoğunluk vb.).
    """
    def process(self, reading: SensorReading) -> ProcessedReading:
        """
        Bir SensorReading nesnesini alır ve hesaplanmış değerlerle birlikte
        bir ProcessedReading nesnesi döndürür.
        """
        snow_height = self._calculate_snow_height(reading.height_mm)
        density = self._calculate_density(
            weight_g=reading.weight_g,
            snow_height_mm=snow_height
        )

        # ProcessedReading nesnesini oluştururken,
        # temel okuma verilerini ve yeni hesaplanan verileri birleştiriyoruz.
        return ProcessedReading(
            **reading.model_dump(),  # SensorReading'den gelen tüm verileri kopyala
            snow_height_mm=snow_height,
            density_kg_m3=density
        )

    def _calculate_snow_height(self, height_mm: float | None) -> float | None:
        """Mesafe okumasından kar yüksekliğini hesaplar."""
        if height_mm is None:
            return None
        # Kar yüksekliği, sensörün sıfır noktası ile ölçülen mesafe arasındaki farktır.
        # Sonucun negatif olmaması için max(0, ...) kullanılır.
        return max(0.0, _settings.SENSOR_ZERO_DISTANCE_MM - height_mm)

    def _calculate_density(self, weight_g: float | None, snow_height_mm: float | None) -> float | None:
        """Ağırlık ve kar yüksekliğinden yoğunluğu (kg/m³) hesaplar."""
        if weight_g is None or snow_height_mm is None or snow_height_mm <= 0:
            return None

        try:
            # Hacim (m³) = Alan (m²) * Kar Yüksekliği (m)
            # Yoğunluk (kg/m³) = Kütle (kg) / Hacim (m³)
            mass_kg = weight_g / 1000.0
            snow_height_m = snow_height_mm / 1000.0
            volume_m3 = _settings.MEASUREMENT_AREA_M2 * snow_height_m
            
            density = mass_kg / volume_m3
            return round(density, 2)
        except ZeroDivisionError:
            return None