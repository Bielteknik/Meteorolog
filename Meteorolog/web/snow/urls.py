# Projenizin ana urls.py dosyası (örneğin myproject/urls.py)

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')), # Dashboard uygulamanızın URL'lerini dahil ediyoruz
]

# Geliştirme ortamında media dosyalarını sunmak için
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)