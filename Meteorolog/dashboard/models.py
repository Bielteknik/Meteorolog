from django.db import models

class Setting(models.Model):
    key = models.CharField(max_length=50, primary_key=True, help_text="Ayarın anahtarı. Değiştirilemez.")
    value = models.CharField(max_length=255, help_text="Ayarın değeri.")
    def __str__(self): return self.key
    class Meta:
        verbose_name = "Sistem Ayarı"
        verbose_name_plural = "Sistem Ayarları"

class Reading(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField()
    distance_mm = models.FloatField(blank=True, null=True)
    snow_weight_kg = models.FloatField(blank=True, null=True)
    snow_height_mm = models.FloatField(blank=True, null=True)
    snow_density_kg_m3 = models.FloatField(blank=True, null=True)
    swe_mm = models.FloatField(blank=True, null=True)
    temperature_c = models.FloatField(blank=True, null=True)
    humidity_percent = models.FloatField(blank=True, null=True)
    data_source = models.TextField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'readings'
        ordering = ['-timestamp']

class ApiQueue(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField()
    payload = models.TextField()
    attempts = models.IntegerField()
    # is_sent = models.BooleanField(default=False) # HATA: Bu alan modelde yok, kaldırıldı.
    class Meta:
        managed = False
        db_table = 'api_queue'
        ordering = ['-timestamp']

class EmailLog(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField()
    recipient = models.TextField()
    subject = models.TextField()
    # is_sent = models.BooleanField(default=True) # HATA: Bu alan modelde yok, kaldırıldı.
    class Meta:
        managed = False
        db_table = 'email_logs'
        ordering = ['-timestamp']

class AnomalyLog(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField()
    sensor = models.TextField()
    anomaly_type = models.TextField()
    value = models.TextField(blank=True, null=True)
    details = models.TextField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'anomaly_logs'
        ordering = ['-timestamp']

class SystemHealthLog(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField()
    cpu_temp_c = models.FloatField(blank=True, null=True)
    cpu_usage_percent = models.FloatField(blank=True, null=True)
    memory_usage_percent = models.FloatField(blank=True, null=True)
    disk_usage_percent = models.FloatField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = 'system_health_logs'
        ordering = ['-timestamp']