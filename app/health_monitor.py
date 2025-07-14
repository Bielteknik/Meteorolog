import psutil
from .storage_manager import storage_manager, SystemHealthLog # Düzeltme: SystemHealthLog import edildi

class HealthMonitor:
    """Sistemin sağlık durumunu (CPU, RAM, Disk) izler."""

    def get_health_metrics(self) -> dict:
        """Sistem sağlık metriklerini bir sözlük olarak döndürür."""
        return {
            "cpu_temp_c": self._get_cpu_temperature(),
            "cpu_usage_percent": psutil.cpu_percent(interval=1),
            "memory_usage_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent
        }

    def _get_cpu_temperature(self) -> float | None:
        """Raspberry Pi'nin CPU sıcaklığını okur."""
        try:
            # Python 3.9 ve altı için: Optional[float]
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = int(f.read().strip()) / 1000.0
            return temp
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"  ❌ CPU sıcaklığı okunamadı: {e}")
            return None

    def log_health_metrics(self):
        """Sağlık metriklerini okur ve veritabanına kaydeder."""
        metrics = self.get_health_metrics()
        session = storage_manager.get_session()
        try:
            # Hatanın olduğu satır artık doğru çalışacak
            new_log = SystemHealthLog(**metrics)
            session.add(new_log)
            session.commit()
        except Exception as e:
            print(f"  ❌ Sistem sağlığı loglama hatası: {e}")
            session.rollback()
        finally:
            session.close()