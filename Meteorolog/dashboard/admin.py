from django.contrib import admin
from .models import Reading, ApiQueue, EmailLog, AnomalyLog, SystemHealthLog, Setting

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    # Yeni ayar eklemeyi engelle, sadece mevcutları düzenle
    def has_add_permission(self, request):
        return False
    # Ayarları silmeyi engelle
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'temperature_c', 'snow_height_mm', 'data_source')
    list_filter = ('timestamp', 'data_source')

@admin.register(ApiQueue)
class ApiQueueAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'is_sent', 'attempts')
    list_filter = ('is_sent', 'timestamp')

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'recipient', 'subject', 'is_sent')
    list_filter = ('is_sent', 'timestamp')

@admin.register(AnomalyLog)
class AnomalyLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'anomaly_type')
    list_filter = ('anomaly_type', 'timestamp')

@admin.register(SystemHealthLog)
class SystemHealthLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'cpu_temp_c', 'cpu_usage_percent', 'memory_usage_percent')