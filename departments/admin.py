"""
Admin configuration for the Departments app.
"""

from django.contrib import admin

from accounts.admin import AppraisalAdminPermissionMixin
from .models import Department


@admin.register(Department)
class DepartmentAdmin(AppraisalAdminPermissionMixin, admin.ModelAdmin):
    """Admin view for managing departments."""

    list_display = ("name", "code", "hod", "staff_count", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "code")
    readonly_fields = ("created_at", "updated_at")

    # Expose the model property as a column in the admin list view.
    @admin.display(description="Staff Count", ordering="name")
    def staff_count(self, obj: Department) -> int:  # noqa: D401
        return obj.staff_count
