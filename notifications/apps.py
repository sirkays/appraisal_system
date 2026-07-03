"""
App configuration for the Notifications app.
"""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Configuration for the Notifications application."""

    name = 'notifications'
    verbose_name = 'Notifications'
    default_auto_field = 'django.db.models.BigAutoField'
