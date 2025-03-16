from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'ar_tryout'

urlpatterns = [
    path('viewer/<slug:slug>/', views.ar_viewer, name='ar_viewer'),
    path('marker/', views.ar_marker, name='ar_marker'),
    path('save-image/<int:watch_id>/', views.save_ar_image, name='save_ar_image'),
    path('debug/', views.ar_debug, name='ar_debug'),
] 

# Ensure model files are served in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)