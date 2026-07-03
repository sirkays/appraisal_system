"""
Application configuration for the ``accounts`` app.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for the Staff Accounts application."""

    name = "accounts"
    verbose_name = "Staff Accounts"
    default_auto_field = "django.db.models.BigAutoField"
