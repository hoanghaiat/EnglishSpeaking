from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

from speaking_practice.admin_site import esp_admin_site

urlpatterns = [
    path('admin/', esp_admin_site.urls),
    path('', include('speaking_practice.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
