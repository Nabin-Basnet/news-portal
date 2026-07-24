def get_permissions(self):
    if self.action in [
        "list",
        "track_impression",
        "track_click",
        "trending",
    ]:
        return [permissions.AllowAny()]

    return [IsAdminOrStaffRole()]