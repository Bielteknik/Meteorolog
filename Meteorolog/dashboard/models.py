from django.db import models

class Setting(models.Model):
    """Sistem ayarlarını veritabanında saklamak için model."""
    key = models.CharField(max_length=50, primary_key=True, help_text="Ayarın anahtarı (örn: RTSP_USER). Değiştirilemez.")
    value = models.CharField(max_length=255, help_text="Ayarın değeri.")

    def __str__(self):
        return self.key
    
    class Meta:
        verbose_name = "Sistem Ayarı"
        verbose_name_plural = "Sistem Ayarları"

class Reading(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    distance_mm = models.FloatField(blank=True, null=True)
    snow_weight_kg = models.FloatField(blank=True, null=True)
    snow_height_mm = models.FloatField(blank=True, null=True)
    snow_density_kg_m3 = models.FloatField(blank=True, null=True)
    swe_mm = models.FloatField(blank=True, null=True)
    temperature_c = models.FloatField(blank=True, null=True)
    humidity_percent = models.FloatField(blank=True, null=True)
    data_source = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

class ApiQueue(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    payload = models.TextField()
    attempts = models.IntegerField(default=0)
    is_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

class EmailLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_sent = models.BooleanField(default=True)

    class Meta:
        ordering = ['-timestamp']

class AnomalyLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    anomaly_type = models.CharField(max_length=50)
    details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

class SystemHealthLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    cpu_temp_c = models.FloatField(blank=True, null=True)
    cpu_usage_percent = models.FloatField(blank=True, null=True)
    memory_usage_percent = models.FloatField(blank=True, null=True)
    disk_usage_percent = models.FloatField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']