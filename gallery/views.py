from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Photo, Tag, Like, Comment, Favorite
from accounts.models import UserRoles, UserActivityLog
from .forms import PhotoUploadForm, PhotoEditForm, CommentForm


class GalleryView(ListView):
    
    model = Photo
    template_name = 'gallery/gallery.html'
    context_object_name = 'photos'
    paginate_by = 24
    
    def get_queryset(self):
        queryset = Photo.objects.filter(is_approved=True, is_public=True)
        
        # Filter by tag if provided
        tag_slug = self.kwargs.get('tag_slug')
        if tag_slug:
            tag = get_object_or_404(Tag, slug=tag_slug)
            queryset = queryset.filter(tags=tag)
            self.tag_filter = tag
        else:
            self.tag_filter = None
        
        # Apply search if provided
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(tags__name__icontains=search_query)
            ).distinct()
            self.search_query = search_query
        
        # Order by latest first
        queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all tags for filter bar
        context['all_tags'] = Tag.objects.annotate(
            approved_photo_count=Count('photos', filter=Q(photos__is_approved=True))
        ).filter(approved_photo_count__gt=0).order_by('-approved_photo_count')[:20]
        
        context['tag_filter'] = getattr(self, 'tag_filter', None)
        context['search_query'] = getattr(self, 'search_query', '')
        
        # Get featured photos for sidebar
        context['featured_photos'] = Photo.objects.filter(
            is_approved=True, is_featured=True
        )[:8]
        
        # Get popular tags
        context['popular_tags'] = Tag.objects.annotate(
            approved_photo_count=Count('photos', filter=Q(photos__is_approved=True))
        ).filter(approved_photo_count__gt=0).order_by('-approved_photo_count')[:10]
        
        return context


class PhotoDetailView(DetailView):
    
    model = Photo
    template_name = 'gallery/photo_detail.html'
    context_object_name = 'photo'
    
    def get_queryset(self):
        # Show unapproved photos only to owners, admins, and moderators
        queryset = Photo.objects.all()
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_approved=True, is_public=True)
        elif not (self.request.user.is_admin or self.request.user.is_moderator):
            queryset = queryset.filter(
                Q(is_approved=True, is_public=True) |
                Q(user=self.request.user)
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        photo = self.get_object()
        
        # Increment view count
        photo.increment_views()
        
        # Check if user has liked/favorited
        if self.request.user.is_authenticated:
            context['user_liked'] = Like.objects.filter(
                user=self.request.user, photo=photo, is_like=True
            ).exists()
            context['user_disliked'] = Like.objects.filter(
                user=self.request.user, photo=photo, is_like=False
            ).exists()
            context['user_favorited'] = Favorite.objects.filter(
                user=self.request.user, photo=photo
            ).exists()
        else:
            context['user_liked'] = False
            context['user_disliked'] = False
            context['user_favorited'] = False
        
        # Get comments
        context['comments'] = photo.comments.filter(
            is_approved=True, parent__isnull=True
        ).order_by('-created_at')
        
        # Get related photos (same tags)
        if photo.tags.exists():
            tag_ids = photo.tags.values_list('id', flat=True)
            context['related_photos'] = Photo.objects.filter(
                tags__id__in=tag_ids, is_approved=True
            ).exclude(id=photo.id).distinct()[:8]
        else:
            context['related_photos'] = []
        
        # Comment form
        context['comment_form'] = CommentForm()
        
        # Log view activity
        if self.request.user.is_authenticated:
            UserActivityLog.objects.create(
                user=self.request.user,
                action='view',
                ip_address=self.request.META.get('REMOTE_ADDR'),
                user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                details={'photo_id': photo.id, 'photo_title': photo.title}
            )
        
        return context


class PhotoUploadView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    
    model = Photo
    form_class = PhotoUploadForm
    template_name = 'gallery/photo_upload.html'
    success_url = reverse_lazy('gallery:gallery')
    
    def test_func(self):
        return self.request.user.can_upload()
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # Auto-approve for admins and moderators
        if self.request.user.is_admin or self.request.user.is_moderator:
            form.instance.is_approved = True
        
        response = super().form_valid(form)
        
        # Log activity
        UserActivityLog.objects.create(
            user=self.request.user,
            action='upload',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            details={'photo_id': self.object.id, 'photo_title': self.object.title}
        )
        
        messages.success(self.request, f'Photo "{self.object.title}" has been uploaded successfully!')
        if not self.object.is_approved:
            messages.info(self.request, 'Your photo will be visible after moderator approval.')
        
        return response


class PhotoEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    
    model = Photo
    form_class = PhotoEditForm
    template_name = 'gallery/photo_edit.html'
    
    def test_func(self):
        photo = self.get_object()
        return (self.request.user == photo.user or 
                self.request.user.is_admin or 
                self.request.user.is_moderator)
    
    def get_success_url(self):
        return reverse('gallery:photo_detail', kwargs={'slug': self.object.slug})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log activity
        UserActivityLog.objects.create(
            user=self.request.user,
            action='edit',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            details={'photo_id': self.object.id, 'photo_title': self.object.title}
        )
        
        messages.success(self.request, f'Photo "{self.object.title}" has been updated!')
        return response


class PhotoDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    
    model = Photo
    template_name = 'gallery/photo_confirm_delete.html'
    success_url = reverse_lazy('gallery:gallery')
    
    def test_func(self):
        photo = self.get_object()
        return (self.request.user == photo.user or 
                self.request.user.is_admin or 
                self.request.user.is_moderator)
    
    def delete(self, request, *args, **kwargs):
        photo = self.get_object()
        photo_title = photo.title
        
        # Log activity
        UserActivityLog.objects.create(
            user=self.request.user,
            action='delete',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            details={'photo_id': photo.id, 'photo_title': photo_title}
        )
        
        messages.success(self.request, f'Photo "{photo_title}" has been deleted.')
        return super().delete(request, *args, **kwargs)


class LikeToggleView(LoginRequiredMixin, View):
    
    def post(self, request, slug):
        photo = get_object_or_404(Photo, slug=slug, is_approved=True)
        like_type = request.POST.get('type', 'like')  # 'like' or 'dislike'
        is_like = like_type == 'like'
        
        # Check if existing like/dislike exists
        existing = Like.objects.filter(user=request.user, photo=photo).first()
        
        if existing:
            if existing.is_like == is_like:
                # Remove if same action (toggle off)
                existing.delete()
                action = 'removed'
            else:
                # Update to opposite action
                existing.is_like = is_like
                existing.save()
                action = 'updated'
        else:
            # Create new like/dislike
            Like.objects.create(user=request.user, photo=photo, is_like=is_like)
            action = 'created'
        
        # Get updated counts
        likes_count = photo.likes.filter(is_like=True).count()
        dislikes_count = photo.likes.filter(is_like=False).count()
        
        # Log activity for first time liking (not for removal)
        if action != 'removed':
            UserActivityLog.objects.create(
                user=request.user,
                action='like',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'photo_id': photo.id, 'photo_title': photo.title, 'action': like_type}
            )
        
        return JsonResponse({
            'success': True,
            'likes_count': likes_count,
            'dislikes_count': dislikes_count,
            'user_liked': likes_count > 0 and Like.objects.filter(user=request.user, photo=photo, is_like=True).exists(),
            'user_disliked': dislikes_count > 0 and Like.objects.filter(user=request.user, photo=photo, is_like=False).exists()
        })


class FavoriteToggleView(LoginRequiredMixin, View):
    
    def post(self, request, slug):
        photo = get_object_or_404(Photo, slug=slug, is_approved=True)
        
        favorite = Favorite.objects.filter(user=request.user, photo=photo).first()
        
        if favorite:
            favorite.delete()
            is_favorited = False
            message = 'removed'
        else:
            Favorite.objects.create(user=request.user, photo=photo)
            is_favorited = True
            message = 'added'
            
            # Log activity
            UserActivityLog.objects.create(
                user=request.user,
                action='favorite',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'photo_id': photo.id, 'photo_title': photo.title}
            )
        
        return JsonResponse({
            'success': True,
            'is_favorited': is_favorited,
            'message': message
        })


class AddCommentView(LoginRequiredMixin, View):
    
    def post(self, request, slug):
        photo = get_object_or_404(Photo, slug=slug, is_approved=True)
        form = CommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.photo = photo
            
            parent_id = request.POST.get('parent_id')
            if parent_id:
                try:
                    parent = Comment.objects.get(id=parent_id)
                    comment.parent = parent
                except Comment.DoesNotExist:
                    pass
            
            comment.save()
            
            # Log activity
            UserActivityLog.objects.create(
                user=request.user,
                action='comment',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'photo_id': photo.id, 'photo_title': photo.title, 'comment_id': comment.id}
            )
            
            messages.success(request, 'Your comment has been posted!')
        else:
            messages.error(request, 'Please enter valid comment content.')
        
        return redirect('gallery:photo_detail', slug=slug)


class SearchView(ListView):
    
    model = Photo
    template_name = 'gallery/search_results.html'
    context_object_name = 'photos'
    paginate_by = 24
    
    def get_queryset(self):
        query = self.request.GET.get('q', '')
        if query:
            return Photo.objects.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__name__icontains=query),
                is_approved=True
            ).distinct().order_by('-created_at')
        return Photo.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class UserGalleryView(LoginRequiredMixin, ListView):
    
    model = Photo
    template_name = 'gallery/user_gallery.html'
    context_object_name = 'photos'
    paginate_by = 24
    
    def get_queryset(self):
        return Photo.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_photos'] = self.get_queryset().count()
        context['approved_photos'] = self.get_queryset().filter(is_approved=True).count()
        context['pending_photos'] = self.get_queryset().filter(is_approved=False).count()
        return context


class UserFavoritesView(LoginRequiredMixin, ListView):
    
    model = Favorite
    template_name = 'gallery/user_favorites.html'
    context_object_name = 'favorites'
    paginate_by = 24
    
    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related('photo').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_favorites'] = self.get_queryset().count()
        return context