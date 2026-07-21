"""Reusable role and object permissions for the editorial workflow."""

from rest_framework import permissions


ROLE_ADMIN = "admin"
ROLE_EDITOR = "editor"
ROLE_STAFF = "staff"
ROLE_REPORTER = "reporter"
ROLE_USER = "user"

# ``Author`` was used by earlier versions of the API.  Keep it working while
# treating it exactly as Reporter during the transition.
ROLE_ALIASES = {"author": ROLE_REPORTER}


def get_role(user):
    """Return a normalized application role without querying Django Groups."""
    if not user or not user.is_authenticated:
        return ""
    if user.is_superuser:
        return ROLE_ADMIN
    role = getattr(user, "role", None)
    name = getattr(role, "role_name", "")
    return ROLE_ALIASES.get(name.strip().lower(), name.strip().lower())


def has_role(user, *roles):
    return bool(user and user.is_authenticated and get_role(user) in roles)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, ROLE_ADMIN)


class IsEditor(permissions.BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, ROLE_EDITOR)


class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, ROLE_STAFF)


class IsReporter(permissions.BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, ROLE_REPORTER)


class IsUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, ROLE_USER)


class IsEditorialUser(permissions.BasePermission):
    """Reporter, Staff, Editor, and Admin may create editorial content."""
    def has_permission(self, request, view):
        return has_role(request.user, ROLE_REPORTER, ROLE_STAFF, ROLE_EDITOR, ROLE_ADMIN)


class CanRequestRevision(permissions.BasePermission):
    """Staff may return reporter content; editors/admins may return any content."""
    def has_permission(self, request, view):
        return has_role(request.user, ROLE_STAFF, ROLE_EDITOR, ROLE_ADMIN)


class CanEditArticle(permissions.BasePermission):
    """Enforce edit rights at the object level for every write endpoint."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        role = get_role(request.user)
        if role in (ROLE_ADMIN, ROLE_EDITOR):
            return True
        if role == ROLE_REPORTER:
            return obj.author_id == request.user.id and obj.status == obj.Status.DRAFT
        if role == ROLE_STAFF:
            return obj.status != obj.Status.PUBLISHED and (
                obj.author_id == request.user.id or get_role(obj.author) == ROLE_REPORTER
            )
        return False


class CanDeleteArticle(CanEditArticle):
    def has_object_permission(self, request, view, obj):
        role = get_role(request.user)
        if role == ROLE_ADMIN:
            return True
        if role == ROLE_EDITOR:
            return obj.status != obj.Status.PUBLISHED
        return role in (ROLE_REPORTER, ROLE_STAFF) and obj.author_id == request.user.id and obj.status == obj.Status.DRAFT


class CanPublishArticle(permissions.BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, ROLE_EDITOR, ROLE_ADMIN)


class CanApproveArticle(CanPublishArticle):
    pass


class IsArticleOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.author_id == request.user.id


# Backwards-compatible names used by existing imports and integrations.
IsAdminUserRole = IsAdmin
IsEditorOrAdmin = CanApproveArticle
IsReporterRole = IsReporter
IsAuthorOrEditorialStaff = CanEditArticle
