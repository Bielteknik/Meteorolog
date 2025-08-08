class IoTDataRouter:
    """
    Dashboard uygulamasının modellerini 'iot_data' veritabanına yönlendirir.
    'Setting' modeli hariç, çünkü o Django'nun kendi veritabanında kalmalı.
    """
    route_app_labels = {'dashboard'}
    iot_models = {'reading', 'apiqueue', 'emaillog', 'anomalylog', 'systemhealthlog'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels and model._meta.model_name in self.iot_models:
            return 'iot_data'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels and model._meta.model_name in self.iot_models:
            # IoT veritabanına Django'dan yazma işlemi yapmıyoruz.
            return None 
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Aynı veritabanı içindeki ilişkilere izin ver
        if obj1._meta.app_label in self.route_app_labels and obj2._meta.app_label in self.route_app_labels:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Sadece 'default' veritabanı için migration'lara izin ver.
        # Bu, Django'nun 'station_data.db'ye dokunmasını kesin olarak engeller.
        if db == 'iot_data':
            return False
        return True