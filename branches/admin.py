"""
Django admin configuration for the ``branches`` app.
"""

from django.contrib import admin
from accounts.admin import AppraisalAdminPermissionMixin
from .models import Branch


@admin.register(Branch)
class BranchAdmin(AppraisalAdminPermissionMixin, admin.ModelAdmin):
    """Admin view for the Branch model."""

    list_display = ("name", "code", "member_count", "department_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "code")
    filter_horizontal = ("departments", "members")
