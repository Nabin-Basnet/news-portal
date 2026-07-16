from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm
from django.utils.html import format_html
from .models import User, Role, RefreshToken, PasswordResetToken


class UserCreationForm(BaseUserCreationForm):
    """Admin form for an email-only user model."""

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ('email', 'first_name', 'last_name')


class UserUpdateForm(UserChangeForm):
    """Admin change form that does not expect a username field."""

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'role_name', 'user_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['role_name']
    readonly_fields = ['created_at']
    
    def user_count(self, obj):
        return obj.users.count()
    user_count.short_description = 'Users with this role'


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserUpdateForm
    list_display = [
        'id', 'email', 'first_name', 'last_name',
        'role', 'verification_badge', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'is_verified', 'role', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['email']
    
    fieldsets = (
        ('Account Information', {
            'fields': ( 'email', 'password')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'bio', 'profile_pic')
        }),
        ('Permissions & Roles', {
            'fields': ('role', 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        ('Account Information', {
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2')
        }),
        ('Permissions & Roles', {
            'fields': ('role', 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
    )
    
    def verification_badge(self, obj):
        if obj.is_verified:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>',
                '✓ Verified',
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">{}</span>',
            '✗ Unverified',
        )


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_email', 'device_name', 'ip_address',
        'revocation_status', 'expires_at', 'created_at'
    ]
    list_filter = ['is_revoked', 'created_at', 'expires_at']
    search_fields = ['user__email', 'device_name', 'ip_address']
    readonly_fields = ['user', 'token_hash', 'created_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def revocation_status(self, obj):
        if obj.is_revoked:
            return format_html(
                '<span style="color: red; font-weight: bold;">{}</span>',
                'REVOKED',
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">{}</span>',
            'ACTIVE',
        )
    revocation_status.short_description = 'Status'


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_email', 'usage_status', 'expires_at', 'created_at'
    ]
    list_filter = ['is_used', 'created_at', 'expires_at']
    search_fields = ['user__email']
    readonly_fields = ['user', 'token_hash', 'created_at']
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    
    def usage_status(self, obj):
        if obj.is_used:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>',
                'USED',
            )
        return format_html(
            '<span style="color: orange; font-weight: bold;">{}</span>',
            'UNUSED',
        )
    usage_status.short_description = 'Status'
