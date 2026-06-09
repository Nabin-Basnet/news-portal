from rest_framework import serializers
from .models import User, Role, RefreshToken, PasswordResetToken
from django.contrib.auth.password_validation import validate_password


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""
    
    class Meta:
        model = Role
        fields = ['id', 'role_name', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True
    )
    role = RoleSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'password', 'password2', 'bio', 'role', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        if data['password'] != data.pop('password2'):
            raise serializers.ValidationError(
                {"password": "Passwords don't match."}
            )
        return data
    
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (Read/Update)."""
    
    role = RoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(),
        source='role',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'bio', 'profile_pic', 'role', 'role_id', 'is_verified',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_verified', 'created_at', 'updated_at'
        ]


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for user profile."""
    
    role = RoleSerializer(read_only=True)
    refresh_tokens_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'bio', 'profile_pic', 'role', 'is_verified', 'is_active',
            'created_at', 'updated_at', 'refresh_tokens_count'
        ]
        read_only_fields = [
            'id', 'is_verified', 'created_at', 'updated_at'
        ]
    
    def get_refresh_tokens_count(self, obj):
        return obj.refresh_tokens.filter(is_revoked=False).count()


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password."""
    
    old_password = serializers.CharField(
        write_only=True,
        required=True
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    new_password2 = serializers.CharField(
        write_only=True,
        required=True
    )
    
    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError(
                {"new_password": "Passwords don't match."}
            )
        return data


class RefreshTokenSerializer(serializers.ModelSerializer):
    """Serializer for RefreshToken model."""
    
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    
    class Meta:
        model = RefreshToken
        fields = [
            'id', 'user', 'user_email', 'device_name',
            'ip_address', 'expires_at', 'is_revoked', 'created_at'
        ]
        read_only_fields = [
            'id', 'user', 'token_hash', 'created_at'
        ]


class PasswordResetTokenSerializer(serializers.ModelSerializer):
    """Serializer for PasswordResetToken model."""
    
    user_email = serializers.CharField(
        source='user.email',
        read_only=True
    )
    
    class Meta:
        model = PasswordResetToken
        fields = [
            'id', 'user', 'user_email', 'expires_at',
            'is_used', 'created_at'
        ]
        read_only_fields = [
            'id', 'user', 'token_hash', 'created_at'
        ]
