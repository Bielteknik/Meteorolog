from rest_framework import serializers, views, status
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Reading

# 1. Serializer: Gelen JSON verisini Django modeline çevirir.
class ReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reading
        # IoT cihazından sadece bu alanların gelmesini bekliyoruz.
        # 'id', 'timestamp' gibi alanlar sunucuda otomatik oluşacak.
        fields = [
            'distance_mm', 'snow_weight_kg', 'snow_height_mm',
            'snow_density_kg_m3', 'swe_mm', 'temperature_c',
            'humidity_percent', 'data_source'
        ]

# 2. API View: Gelen istekleri işleyen kısım.
class ReadingCreateAPIView(views.APIView):
    # Bu endpoint'e sadece token ile kimliği doğrulanmış kullanıcılar erişebilir.
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        IoT cihazından POST metoduyla gelen yeni bir sensör okumasını kaydeder.
        """
        serializer = ReadingSerializer(data=request.data)
        if serializer.is_valid():
            # Veri geçerliyse, veritabanına kaydet.
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # Veri geçerli değilse, hata mesajı döndür.
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)