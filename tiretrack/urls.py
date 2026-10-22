from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from tires import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.homepage),
    path('users/', include('users.urls', namespace='users')),
    path('tires/', include('tires.urls', namespace='tires')),
    path('warehouse/', include('warehouse.urls', namespace='warehouse')),
    path('qr/', include('qr_processing.urls')),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
