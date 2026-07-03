"""
Django admin configuration for the Notifications app.
"""

from django.contrib import admin

from accounts.admin import AppraisalAdminPermissionMixin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(AppraisalAdminPermissionMixin, admin.ModelAdmin):
    """Admin view for managing Notification records."""

    list_display = (
        'recipient',
        'title',
        'notification_type',
        'is_read',
        'created_at',
    )
    list_filter = (
        'notification_type',
        'is_read',
        'created_at',
    )
    search_fields = (
        'title',
        'message',
        'recipient__first_name',
        'recipient__last_name',
    )
    readonly_fields = ('created_at',)
