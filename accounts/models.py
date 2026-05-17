from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """Custom user manager for handling user creation with roles"""
    
    def create_user(self, email, username, password=None, **extra_fields):
        """Create and save a regular user"""
        if not email:
            raise ValueError(_('Email address is required'))
        if not username:
            raise ValueError(_('Username is required'))
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        """Create and save a superuser with admin role"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRoles.ADMIN)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, username, password, **extra_fields)
    
    def create_moderator(self, email, username, password=None, **extra_fields):
        """Create a moderator user"""
        extra_fields.setdefault('role', UserRoles.MODERATOR)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('email_verified', True)
        return self.create_user(email, username, password, **extra_fields)
    
    def create_artist(self, email, username, password=None, **extra_fields):
        """Create an artist user"""
        extra_fields.setdefault('role', UserRoles.ARTIST)
        extra_fields.setdefault('email_verified', True)
        return self.create_user(email, username, password, **extra_fields)
    
    def create_viewer(self, email, username, password=None, **extra_fields):
        """Create a viewer user"""
        extra_fields.setdefault('role', UserRoles.VIEWER)
        extra_fields.setdefault('email_verified', True)
        return self.create_user(email, username, password, **extra_fields)


class UserRoles(models.TextChoices):
    """User role choices for RBAC"""
    ADMIN = 'admin', _('Administrator')
    MODERATOR = 'moderator', _('Moderator')
    ARTIST = 'artist', _('Artist')
    VIEWER = 'viewer', _('Viewer')


class User(AbstractUser):
    """
    Custom User model with role-based access control and additional profile fields
    """
    # Override email to be unique and required
    email = models.EmailField(_('email address'), unique=True, null=False, blank=False)
    
    # Profile fields
    profile_picture = models.ImageField(
        upload_to='profile_pictures/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Profile Picture')
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Biography')
    )
    
    # Role-based access control
    role = models.CharField(
        max_length=20,
        choices=UserRoles.choices,
        default=UserRoles.VIEWER,
        verbose_name=_('User Role')
    )
    
    # Verification and status
    email_verified = models.BooleanField(default=False, verbose_name=_('Email Verified'))
    is_approved = models.BooleanField(default=True, verbose_name=_('Is Approved'))
    
    # Timestamps
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Social login integration
    google_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Custom manager
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active', 'role']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def has_role(self, role):
        """Check if user has a specific role"""
        return self.role == role
    
    def has_permission(self, permission):
        """Check if user has a specific permission based on role"""
        role_permissions = {
            UserRoles.ADMIN: ['can_delete_all', 'can_edit_all', 'can_manage_users', 
                             'can_approve_photos', 'can_upload_photos', 'can_edit_own',
                             'can_delete_own', 'can_view_photos', 'can_like_photos'],
            UserRoles.MODERATOR: ['can_edit_all', 'can_approve_photos', 
                                 'can_delete_inappropriate', 'can_view_photos', 'can_like_photos'],
            UserRoles.ARTIST: ['can_upload_photos', 'can_edit_own', 'can_delete_own',
                              'can_view_photos', 'can_like_photos'],
            UserRoles.VIEWER: ['can_view_photos', 'can_like_photos'],
        }
        return permission in role_permissions.get(self.role, [])
    
    def can_upload(self):
        """Check if user can upload photos"""
        return self.role in [UserRoles.ADMIN, UserRoles.ARTIST]
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.role == UserRoles.ADMIN
    
    def can_moderate(self):
        """Check if user can moderate content"""
        return self.role in [UserRoles.ADMIN, UserRoles.MODERATOR]
    
    def get_profile_completion_percentage(self):
        """Calculate profile completion percentage"""
        fields = [self.bio, self.profile_picture, self.first_name, self.last_name]
        filled = sum(1 for field in fields if field)
        return int((filled / len(fields)) * 100)
    
    @property
    def is_admin(self):
        return self.role == UserRoles.ADMIN
    
    @property
    def is_moderator(self):
        return self.role == UserRoles.MODERATOR
    
    @property
    def is_artist(self):
        return self.role == UserRoles.ARTIST
    
    @property
    def is_viewer(self):
        return self.role == UserRoles.VIEWER


class UserActivityLog(models.Model):
    """
    Track user activities for audit and analytics
    """
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('upload', 'Photo Upload'),
        ('delete', 'Photo Delete'),
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('profile_update', 'Profile Update'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name_plural = 'User Activity Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.timestamp}"