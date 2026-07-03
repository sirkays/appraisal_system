"""
App configuration for the Departments app.
"""

from django.apps import AppConfig


class DepartmentsConfig(AppConfig):
    """Configuration for the departments application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "departments"
    verbose_name = "Departments"
