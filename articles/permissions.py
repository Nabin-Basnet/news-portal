from rest_framework import permissions

def get_role(user):
    if not user or not user.is_authenticated or not hasattr(user, "role") or not user.role:
        return ""
    return user.role.role_name.lower()


class IsAdminUserRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_superuser or get_role(request.user) == 'admin'
        )


class IsEditorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_superuser or get_role(request.user) in ['editor', 'admin']


class IsReporterRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and get_role(request.user) in ['reporter', 'author']


class IsAuthorOrEditorialStaff(permissions.BasePermission):
    """
    Handles request-level verification and object-level ownership checks 
    simultaneously, allowing Editors and Admins to pass through seamlessly.
    """
    def has_permission(self, request, view):
        # Anyone authenticated can access the request lifecycle safely initially
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = get_role(user)
        
        # Superusers, Admins, and Editors have universal override clearance
        if user.is_superuser or role in ['admin', 'editor']:
            return True
            
        # Reporters/Authors can ONLY modify their own text instances
        return role in ['reporter', 'author'] and obj.author_id == user.id