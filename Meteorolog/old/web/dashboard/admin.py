from django.contrib import admin
from .models import Reading, ApiQueue, AnomalyLog, EmailLog, SystemHealthLog

class ReadOnlyAdmin(admin.ModelAdmin):
    """
    Bu model admin sınıfı, verilerin admin panelinden
    eklenmesini, değiştirilmesini veya silinmesini engeller.
    Sadece görüntüleme amaçlıdır.
    """
    def has_add_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Reading)
class ReadingAdmin(ReadOnlyAdmin):
    list_display = ('timestamp', 'temperature_c', 'humidity_percent', 'snow_height_mm', 'swe_mm', 'data_source')
    list_filter = ('timestamp', 'data_source')
    search_fields = ('id',)
    date_hierarchy = 'timestamp'

@admin.register(AnomalyLog)
class AnomalyLogAdmin(ReadOnlyAdmin):
    list_display = ('timestamp', 'sensor', 'anomaly_type', 'value')
    list_filter = ('timestamp', 'sensor', 'anomaly_type')
    search_fields = ('details', 'value')
    date_hierarchy = 'timestamp'

@admin.register(SystemHealthLog)
class SystemHealthLogAdmin(ReadOnlyAdmin):
    list_display = ('timestamp', 'cpu_temp_c', 'cpu_usage_percent', 'memory_usage_percent', 'disk_usage_percent')
    list_filter = ('timestamp',)
    date_hierarchy = 'timestamp'

@admin.register(EmailLog)
class EmailLogAdmin(ReadOnlyAdmin):
    list_display = ('timestamp', 'recipient', 'subject')
    list_filter = ('timestamp', 'recipient')
    search_fields = ('subject', 'recipient')
    date_hierarchy = 'timestamp'

@admin.register(ApiQueue)
class ApiQueueAdmin(ReadOnlyAdmin):
    list_display = ('id', 'timestamp', 'attempts')
    list_filter = ('timestamp',)
    search_fields = ('payload',)