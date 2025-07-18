# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AnomalyLogs(models.Model):
    timestamp = models.DateTimeField(blank=True, null=True)
    sensor = models.CharField()
    anomaly_type = models.CharField()
    value = models.CharField(blank=True, null=True)
    details = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'anomaly_logs'


class ApiQueue(models.Model):
    timestamp = models.DateTimeField(blank=True, null=True)
    payload = models.CharField()
    attempts = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'api_queue'


class EmailLogs(models.Model):
    timestamp = models.DateTimeField(blank=True, null=True)
    recipient = models.CharField()
    subject = models.CharField()

    class Meta:
        managed = False
        db_table = 'email_logs'


class Readings(models.Model):
    timestamp = models.DateTimeField(blank=True, null=True)
    distance_mm = models.TextField(blank=True, null=True)  # This field type is a guess.
    snow_weight_kg = models.TextField(blank=True, null=True)  # This field type is a guess.
    snow_height_mm = models.TextField(blank=True, null=True)  # This field type is a guess.
    snow_density_kg_m3 = models.TextField(blank=True, null=True)  # This field type is a guess.
    swe_mm = models.TextField(blank=True, null=True)  # This field type is a guess.
    temperature_c = models.TextField(blank=True, null=True)  # This field type is a guess.
    humidity_percent = models.TextField(blank=True, null=True)  # This field type is a guess.
    data_source = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'readings'


class SystemHealthLogs(models.Model):
    timestamp = models.DateTimeField(blank=True, null=True)
    cpu_temp_c = models.TextField(blank=True, null=True)  # This field type is a guess.
    cpu_usage_percent = models.TextField(blank=True, null=True)  # This field type is a guess.
    memory_usage_percent = models.TextField(blank=True, null=True)  # This field type is a guess.
    disk_usage_percent = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'system_health_logs'
