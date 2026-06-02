from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class Role(models.Model):
    """
    User roles:
    Admin
    Editor
    Author
    User
    """

    role_name = models.CharField(
        max_length=20,
        unique=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['role_name']

    def __str__(self):
        return self.role_name


class User(AbstractUser):
    """
    Custom User Model
    Login using email instead of username.
    """

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='users',
        null=True,
    )

    email = models.EmailField(
        unique=True,
        db_index=True
    )

    bio = models.TextField(
        blank=True,
        null=True
    )

    profile_pic = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True
    )

    is_verified = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class RefreshToken(models.Model):
    """
    Stores refresh tokens for JWT authentication.
    Allows token revocation and logout from devices.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='refresh_tokens'
    )

    token_hash = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )

    device_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True
    )

    expires_at = models.DateTimeField()

    is_revoked = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - Refresh Token"


class PasswordResetToken(models.Model):
    """
    Stores password reset tokens.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens'
    )

    token_hash = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )

    expires_at = models.DateTimeField()

    is_used = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - Password Reset"
    