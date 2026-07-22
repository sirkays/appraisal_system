from rest_framework import permissions


class IsNotHRAdmin(permissions.BasePermission):
    """
    Legacy permission class - retains basic authentication check.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsHRAdmin(permissions.BasePermission):
    """
    Allows access only to HR Admin users or superusers.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'HR_ADMIN' or request.user.is_superuser
