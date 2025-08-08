from rest_framework import serializers
from .models import Reading

class ReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reading
        # 'timestamp' hariç tüm alanları al, çünkü o otomatik eklenecek
        exclude = ['timestamp']