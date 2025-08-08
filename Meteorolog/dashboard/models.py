from django.db import models

class Reading(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True) # Otomatik zaman damgası
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