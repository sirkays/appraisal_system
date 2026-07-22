"""
URL configuration for the Staff Performance Appraisal System.

Routes to each app's URL namespace and serves media files in development.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('departments/', include('departments.urls')),
    path('appraisals/', include('appraisals.urls')),
    path('notifications/', include('notifications.urls')),
    path('hr/', include('hr_admin.urls')),
    path('cbt/', include('cbt.urls')),
    path('api/', include('api.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customisation
admin.site.site_header = 'Staff Appraisal Organization - Staff Appraisal System'
admin.site.site_title = 'Appraisal Admin'
admin.site.index_title = 'System Administration'
