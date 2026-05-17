from django.contrib import admin
from django.utils.html import format_html
from .models import Tag, Photo, Like, Comment, Favorite


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'photo_count', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['photo_count']
    
    def photo_count(self, obj):
        return obj.photo_count
    photo_count.short_description = 'Number of Photos'


class LikeInline(admin.TabularInline):
    model = Like
    extra = 0
    readonly_fields = ['user', 'is_like', 'created_at']
    can_delete = False


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ['user', 'content', 'created_at']


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'is_approved', 'is_featured', 'likes_count', 
                   'views_count', 'created_at', 'thumbnail_preview']
    list_filter = ['is_approved', 'is_featured', 'created_at', 'tags']
    search_fields = ['title', 'description', 'user__username']
    readonly_fields = ['slug', 'views_count', 'likes_count', 'comments_count', 'thumbnail_preview']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [LikeInline, CommentInline]
    actions = ['approve_photos', 'feature_photos']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'image', 'thumbnail_preview')
        }),
        ('Classification', {
            'fields': ('tags', 'user')
        }),
        ('Status', {
            'fields': ('is_approved', 'is_featured', 'is_public')
        }),
        ('Statistics', {
            'fields': ('views_count', 'likes_count', 'comments_count'),
            'classes': ('collapse',)
        }),
        ('EXIF Data', {
            'fields': ('camera_make', 'camera_model', 'aperture', 'shutter_speed', 'iso', 'focal_length', 'location'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="border-radius: 8px;" />', obj.image.url)
        return "No image"
    thumbnail_preview.short_description = 'Preview'
    
    def approve_photos(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f"{queryset.count()} photos have been approved.")
    approve_photos.short_description = "Approve selected photos"
    
    def feature_photos(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f"{queryset.count()} photos have been featured.")
    feature_photos.short_description = "Feature selected photos"


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'photo', 'is_like', 'created_at']
    list_filter = ['is_like', 'created_at']
    search_fields = ['user__username', 'photo__title']
    readonly_fields = ['user', 'photo', 'is_like', 'created_at']
    
    def has_add_permission(self, request):
        return False


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'photo', 'content_preview', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['user__username', 'photo__title', 'content']
    actions = ['approve_comments']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Comment'
    
    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
        for comment in queryset:
            comment.photo.update_comments_count()
        self.message_user(request, f"{queryset.count()} comments have been approved.")
    approve_comments.short_description = "Approve selected comments"


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'photo', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'photo__title']
    readonly_fields = ['user', 'photo', 'created_at']
    
    def has_add_permission(self, request):
        return False