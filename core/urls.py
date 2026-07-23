"""
URL configuration for the Staff Performance Appraisal System.

Routes to each app's URL namespace and serves media files.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('departments/', include('departments.urls')),
    path('appraisals/', include('appraisals.urls')),
    path('notifications/', include('notifications.urls')),
    path('hr/', include('hr_admin.urls')),
    path('cbt/', include('cbt.urls')),
    path('api/', include('api.urls')),

    # Serve media files in all environments.
    # Caddy (Docker) proxies directly to Gunicorn, bypassing Nginx,
    # so Django must handle media file serving.
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# Admin site customisation
admin.site.site_header = 'Staff Appraisal Organization - Staff Appraisal System'
admin.site.site_title = 'Appraisal Admin'
admin.site.index_title = 'System Administration'
