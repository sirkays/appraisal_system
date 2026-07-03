"""
Django admin configuration for the ``accounts`` app.

Registers :class:`~accounts.models.CustomUser` using Django's built-in
``UserAdmin`` as the base class, adding fieldsets for the extra fields
introduced by the Staff Performance Appraisal System.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


class AppraisalAdminPermissionMixin:
    """Mixin to grant full admin permissions to active HR_ADMIN users."""

    def has_module_permission(self, request):
        return request.user.is_active and (request.user.is_superuser or getattr(request.user, 'role', None) == 'HR_ADMIN')

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and (request.user.is_superuser or getattr(request.user, 'role', None) == 'HR_ADMIN')

    def has_add_permission(self, request, obj=None):
        return request.user.is_active and (request.user.is_superuser or getattr(request.user, 'role', None) == 'HR_ADMIN')

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and (request.user.is_superuser or getattr(request.user, 'role', None) == 'HR_ADMIN')

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and (request.user.is_superuser or getattr(request.user, 'role', None) == 'HR_ADMIN')


@admin.register(CustomUser)
class CustomUserAdmin(AppraisalAdminPermissionMixin, UserAdmin):
    """Admin view for the CustomUser model."""

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = (
        "username",
        "staff_id",
        "get_full_name",
        "department",
        "role",
        "is_active",
    )
    list_filter = ("role", "department", "is_active")
    search_fields = ("username", "first_name", "last_name", "staff_id", "email")

    # ------------------------------------------------------------------
    # Detail / change view fieldsets
    # ------------------------------------------------------------------
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            "Appraisal System Info",
            {
                "fields": (
                    "staff_id",
                    "role",
                    "department",
                    "designation",
                    "supervisor",
                    "phone",
                    "profile_picture",
                ),
                "description": (
                    "Fields specific to the Staff Performance Appraisal System."
                ),
            },
        ),
    )

    # ------------------------------------------------------------------
    # Add-user view fieldsets
    # ------------------------------------------------------------------
    add_fieldsets = (
        *UserAdmin.add_fieldsets,
        (
            "Appraisal System Info",
            {
                "fields": (
                    "staff_id",
                    "role",
                    "department",
                    "designation",
                    "supervisor",
                    "phone",
                    "profile_picture",
                ),
            },
        ),
    )
