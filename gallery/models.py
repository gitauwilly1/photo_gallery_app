from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinLengthValidator, MaxLengthValidator, FileExtensionValidator
from django.utils.text import slugify
from cloudinary.models import CloudinaryField


class Tag(models.Model):
    
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['slug']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    @property
    def photo_count(self):
        return self.photos.filter(is_approved=True).count()


class Photo(models.Model):
    
    # Basic information
    title = models.CharField(max_length=200, validators=[MinLengthValidator(3)])
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(max_length=1000, blank=True)
    
    # Media
    image = models.URLField(max_length=500, help_text="Cloudinary image URL")
    thumbnail = models.URLField(max_length=500, blank=True, help_text="Cloudinary thumbnail URL")
        
    # Metadata
    tags = models.ManyToManyField(Tag, related_name='photos', blank=True)
    
    # User association
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    
    # Status and moderation
    is_approved = models.BooleanField(default=False, help_text="Approved by moderator")
    is_featured = models.BooleanField(default=False, help_text="Featured on homepage")
    is_public = models.BooleanField(default=True, help_text="Visible to all users")
    
    # Statistics
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # EXIF data (optional)
    camera_make = models.CharField(max_length=100, blank=True)
    camera_model = models.CharField(max_length=100, blank=True)
    aperture = models.CharField(max_length=20, blank=True)
    shutter_speed = models.CharField(max_length=20, blank=True)
    iso = models.CharField(max_length=10, blank=True)
    focal_length = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_approved', '-created_at']),
            models.Index(fields=['slug']),
            models.Index(fields=['views_count']),
            models.Index(fields=['likes_count']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Photo.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    @property
    def is_owner(self, user):
        """Check if given user is the owner"""
        if not user or not user.is_authenticated:
            return False
        return self.user == user
    
    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def update_likes_count(self):
        """Update total likes count"""
        self.likes_count = self.likes.filter(is_like=True).count()
        self.save(update_fields=['likes_count'])
    
    def update_comments_count(self):
        """Update total comments count"""
        self.comments_count = self.comments.filter(is_approved=True).count()
        self.save(update_fields=['comments_count'])
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('gallery:photo_detail', kwargs={'slug': self.slug})


class Like(models.Model):
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    is_like = models.BooleanField(default=True)  # True = like, False = dislike
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'photo']
        indexes = [
            models.Index(fields=['user', 'photo']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        action = "likes" if self.is_like else "dislikes"
        return f"{self.user.username} {action} {self.photo.title}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update photo like count
        self.photo.update_likes_count()


class Comment(models.Model):
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    content = models.TextField(max_length=500, validators=[MinLengthValidator(1)])
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['photo', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.photo.title}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.photo.update_comments_count()


class Favorite(models.Model):
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'photo']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} favorited {self.photo.title}"


class PhotoView(models.Model):
    
    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name='views'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='photo_views'
    )
    ip_address = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['photo', '-viewed_at']),
            models.Index(fields=['viewed_at']),
        ]
    
    def __str__(self):
        return f"View of {self.photo.title} at {self.viewed_at}"