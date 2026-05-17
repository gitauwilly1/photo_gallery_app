from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, UserActivityLog

class CustomUserAdmin(UserAdmin):
    """Custom admin interface for User model with RBAC"""
    
    list_display = ('username', 'email', 'role', 'is_active', 'email_verified', 
                   'date_joined', 'profile_preview')
    list_filter = ('role', 'is_active', 'email_verified', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'bio', 'profile_picture')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser',
                                   'groups', 'user_permissions')}),
        ('Verification', {'fields': ('email_verified', 'is_approved')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Metadata', {'fields': ('last_login_ip', 'google_id')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )
    
    def profile_preview(self, obj):
        """Display profile picture thumbnail in admin"""
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', 
                             obj.profile_picture.url)
        return format_html('<span style="color: gray;">No image</span>')
    profile_preview.short_description = 'Profile'


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    """Admin interface for user activity logs"""
    list_display = ('user', 'action', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('user', 'action', 'ip_address', 'user_agent', 'timestamp', 'details')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(User, CustomUserAdmin)