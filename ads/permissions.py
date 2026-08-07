"""Advertisement object permissions built on the existing role permissions."""

from user.permissions import IsAdminOrStaffRole, is_admin_role


class CanEditAdvertisement(IsAdminOrStaffRole):
    """Admins may edit any ad; staff may edit only their own draft or rejected ads."""

    def has_object_permission(self, request, view, obj):
        return is_admin_role(request.user) or (
            obj.creator_id == request.user.id and obj.status in (
                obj.Status.DRAFT,
                obj.Status.REJECTED,
            )
        )
