"""Permissions for user and role administration."""

from rest_framework.permissions import BasePermission


def is_admin_role(user):
    return bool(
        user and user.is_authenticated and (
            user.is_superuser or getattr(getattr(user, "role", None), "role_name", "").strip().lower() == "admin"
        )
    )


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return is_admin_role(request.user)


class IsSelfOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return is_admin_role(request.user) or obj.pk == request.user.pk
