def get_role(user):
    if not user or not user.is_authenticated:
        return ""

    if user.is_superuser:
        return "admin"

    role = getattr(user, "role", None)
    if not role:
        return ""

    if hasattr(role, "role_name"):
        return role.role_name.lower()

    return str(role).lower()