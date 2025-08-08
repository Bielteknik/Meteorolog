from django.contrib import admin
from .models import Reading, ApiQueue, EmailLog, AnomalyLog, SystemHealthLog, Setting

@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Reading)
class ReadingAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'temperature_c', 'snow_height_mm', 'data_source')
    list_filter = ('timestamp', 'data_source')

@admin.register(ApiQueue)
class ApiQueueAdmin(admin.ModelAdmin):
    # 'is_sent' alanı list_display ve list_filter'dan kaldırıldı.
    list_display = ('timestamp', 'attempts', 'payload')
    list_filter = ('timestamp',)

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    # 'is_sent' alanı list_display ve list_filter'dan kaldırıldı.
    list_display = ('timestamp', 'recipient', 'subject')
    list_filter = ('timestamp',)

@admin.register(AnomalyLog)
class AnomalyLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'sensor', 'anomaly_type')
    list_filter = ('sensor', 'anomaly_type', 'timestamp')

@admin.register(SystemHealthLog)
class SystemHealthLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'cpu_temp_c', 'cpu_usage_percent', 'memory_usage_percent')