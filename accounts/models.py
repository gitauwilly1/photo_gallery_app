from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserRoles(models.TextChoices):
    ADMIN = 'admin', _('Administrator')
    MODERATOR = 'moderator', _('Moderator')
    ARTIST = 'artist', _('Artist')
    VIEWER = 'viewer', _('Viewer')


class CustomUserManager(BaseUserManager):
    
    def create_user(self, email, username, password=None, **extra_fields):
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


class User(AbstractUser):
    
    email = models.EmailField(_('email address'), unique=True, null=False, blank=False)
    
    # Profile fields
    profile_picture = models.ImageField(
        upload_to='profile_pictures/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Profile Picture')
    )
    bio = models.TextField(max_length=500, blank=True, null=True, verbose_name=_('Biography'))
    
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
    updated_at = models.DateTimeField(auto_now=True)
    
    # Social login integration
    google_id = models.CharField(max_length=100, blank=True, null=True)
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def has_role(self, role):
        return self.role == role
    
    def can_upload(self):
        return self.role in [UserRoles.ADMIN, UserRoles.ARTIST]
    
    def can_manage_users(self):
        return self.role == UserRoles.ADMIN
    
    def can_moderate(self):
        return self.role in [UserRoles.ADMIN, UserRoles.MODERATOR]
    
    def get_profile_completion_percentage(self):
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
    
    ACTION_CHOICES = [
        ('register', 'Register'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('upload', 'Photo Upload'),
        ('edit', 'Photo Edit'),
        ('delete', 'Photo Delete'),
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('favorite', 'Favorite'),
        ('profile_update', 'Profile Update'),
        ('view', 'View'),
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
    
    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} at {self.timestamp}"