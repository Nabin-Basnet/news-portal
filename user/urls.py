from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    UserViewSet,
    RoleViewSet,
    RefreshTokenViewSet,
    PasswordResetTokenViewSet,
)

"""
===============================================
USER MANAGEMENT API - URL CONFIGURATION
===============================================

AUTHENTICATION FLOW:
1. Sign Up: POST /api/users/
2. Login: POST /api/token/
3. Use Token: Add "Authorization: Bearer <access_token>" to headers
4. Refresh: POST /api/token/refresh/ (when token expires)
5. Logout: POST /api/users/logout/

MAIN ENDPOINTS:
✓ Authentication:
  - POST /api/token/                 (Login with username/password)
  - POST /api/token/refresh/          (Refresh access token)
  - POST /api/users/                 (Sign up/Register)
  - GET  /api/users/me/              (Get current user profile)
  - POST /api/users/change-password/ (Change password)
  - POST /api/users/logout/          (Logout/Revoke tokens)

✓ User Management:
  - GET    /api/users/               (List all users)
  - GET    /api/users/{id}/          (Get user details)
  - PUT    /api/users/{id}/          (Update user)
  - PATCH  /api/users/{id}/          (Partially update user)
  - DELETE /api/users/{id}/          (Delete user)
  - POST   /api/users/{id}/set-role/ (Assign role to user)

✓ Roles:
  - GET    /api/roles/               (List all roles)
  - POST   /api/roles/               (Create role)
  - GET    /api/roles/{id}/          (Get role details)
  - PUT    /api/roles/{id}/          (Update role)
  - DELETE /api/roles/{id}/          (Delete role)
"""

# Create a router for API endpoints
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'roles', RoleViewSet, basename='role')

# Internal token management endpoints (not exposed in public API)
# router.register(r'refresh-tokens', RefreshTokenViewSet, basename='refresh-token')
# router.register(r'password-reset-tokens', PasswordResetTokenViewSet, basename='password-reset-token')

# URL patterns
urlpatterns = [
    path('api/', include(router.urls)),
    # JWT Token Endpoints (from SimpleJWT)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]