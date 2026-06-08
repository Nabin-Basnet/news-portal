from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import User, Role, RefreshToken, PasswordResetToken
from .serializers import (
    UserSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
    ChangePasswordSerializer,
    RoleSerializer,
    RefreshTokenSerializer,
    PasswordResetTokenSerializer,
)


@extend_schema_view(
    list=extend_schema(
        tags=['Roles'],
        summary='List All Roles',
    ),
    create=extend_schema(
        tags=['Roles'],
        summary='Create Role',
    ),
    retrieve=extend_schema(
        tags=['Roles'],
        summary='Get Role Details',
    ),
    update=extend_schema(
        tags=['Roles'],
        summary='Update Role',
    ),
    partial_update=extend_schema(
        tags=['Roles'],
        summary='Partially Update Role',
    ),
    destroy=extend_schema(
        tags=['Roles'],
        summary='Delete Role',
    ),
)
class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user roles.
    List: GET /api/roles/
    Create: POST /api/roles/
    Retrieve: GET /api/roles/{id}/
    Update: PUT /api/roles/{id}/
    Partial Update: PATCH /api/roles/{id}/
    Destroy: DELETE /api/roles/{id}/
    """
    
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['role_name']
    ordering_fields = ['role_name', 'created_at']
    ordering = ['role_name']


@extend_schema_view(
    create=extend_schema(
        tags=['Authentication'],
        summary='Sign Up / Register',
        description='Register a new user account',
    ),
    list=extend_schema(
        tags=['Users'],
        summary='List All Users',
        description='Get a list of all users (Admin/Staff only)',
    ),
    retrieve=extend_schema(
        tags=['Users'],
        summary='Get User Details',
        description='Get details of a specific user',
    ),
    update=extend_schema(
        tags=['Users'],
        summary='Update User',
        description='Update a user\'s information',
    ),
    partial_update=extend_schema(
        tags=['Users'],
        summary='Partially Update User',
        description='Partially update a user\'s information',
    ),
    destroy=extend_schema(
        tags=['Users'],
        summary='Delete User',
        description='Delete a user account',
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.
    
    Endpoints:
    - List: GET /api/users/
    - Create (Register): POST /api/users/
    - Retrieve: GET /api/users/{id}/
    - Update: PUT /api/users/{id}/
    - Partial Update: PATCH /api/users/{id}/
    - Destroy: DELETE /api/users/{id}/
    - My Profile: GET /api/users/me/
    - Change Password: POST /api/users/change-password/
    - Logout: POST /api/users/logout/
    """
    
    queryset = User.objects.all()
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['role', 'is_verified', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['created_at', 'username', 'email']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'create':
            return UserRegistrationSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action == 'change_password':
            return ChangePasswordSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action == 'create':
            permission_classes = [AllowAny]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @extend_schema(
        tags=['Authentication'],
        summary='Get My Profile',
        description='Get the current logged-in user\'s profile information',
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get current user's profile.
        GET /api/users/me/
        """
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Authentication'],
        summary='Change Password',
        description='Change the current user\'s password. Requires old password and new password.',
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change the current user's password.
        POST /api/users/change-password/
        Body: {
            "old_password": "string",
            "new_password": "string",
            "new_password2": "string"
        }
        """
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"old_password": ["Wrong password."]},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response(
                {"detail": "Password changed successfully."},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=['Authentication'],
        summary='Logout',
        description='Logout user by revoking refresh token(s). Can logout from single device or all devices.',
    )
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Logout user by revoking refresh token.
        POST /api/users/logout/
        Body: {
            "token_id": integer (optional - specific token),
            "all": boolean (optional - logout from all devices)
        }
        """
        user = request.user
        logout_all = request.data.get('all', False)
        token_id = request.data.get('token_id')
        
        if logout_all:
            # Revoke all tokens for this user
            RefreshToken.objects.filter(user=user).update(is_revoked=True)
            return Response(
                {"detail": "Logged out from all devices."},
                status=status.HTTP_200_OK
            )
        elif token_id:
            # Revoke specific token
            token = get_object_or_404(RefreshToken, id=token_id, user=user)
            token.is_revoked = True
            token.save()
            return Response(
                {"detail": "Token revoked successfully."},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "Provide either 'token_id' or 'all' parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        tags=['Users'],
        summary='Assign Role to User',
        description='Assign a role to a user (Admin only)',
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def set_role(self, request, pk=None):
        """
        Assign a role to a user (Admin only).
        POST /api/users/{id}/set-role/
        Body: {
            "role_id": integer
        }
        """
        user = self.get_object()
        role_id = request.data.get('role_id')
        
        if not role_id:
            return Response(
                {"detail": "role_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            role = Role.objects.get(id=role_id)
            user.role = role
            user.save()
            serializer = self.get_serializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Role.DoesNotExist:
            return Response(
                {"detail": "Role not found."},
                status=status.HTTP_404_NOT_FOUND
            )


class RefreshTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing refresh tokens.
    
    Endpoints:
    - List user tokens: GET /api/refresh-tokens/
    - Retrieve: GET /api/refresh-tokens/{id}/
    - Destroy (revoke): DELETE /api/refresh-tokens/{id}/
    - Revoke All: POST /api/refresh-tokens/revoke-all/
    """
    
    serializer_class = RefreshTokenSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'expires_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Users can only see their own tokens."""
        if self.request.user.is_staff:
            return RefreshToken.objects.all()
        return RefreshToken.objects.filter(user=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Revoke a refresh token."""
        instance = self.get_object()
        instance.is_revoked = True
        instance.save()
        return Response(
            {"detail": "Token revoked successfully."},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def revoke_all(self, request):
        """
        Revoke all refresh tokens for current user.
        POST /api/refresh-tokens/revoke-all/
        """
        RefreshToken.objects.filter(
            user=request.user,
            is_revoked=False
        ).update(is_revoked=True)
        
        return Response(
            {"detail": "All tokens revoked successfully."},
            status=status.HTTP_200_OK
        )


class PasswordResetTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing password reset tokens.
    
    Endpoints:
    - List: GET /api/password-reset-tokens/
    - Retrieve: GET /api/password-reset-tokens/{id}/
    """
    
    queryset = PasswordResetToken.objects.all()
    serializer_class = PasswordResetTokenSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'expires_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Users can only see their own password reset tokens."""
        if self.request.user.is_staff:
            return PasswordResetToken.objects.all()
        return PasswordResetToken.objects.filter(user=self.request.user)    
