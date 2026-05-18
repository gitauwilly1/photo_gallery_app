from django.views.generic import TemplateView
from django.shortcuts import render


class HomeView(TemplateView):
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            from gallery.models import Photo
            context['featured_photos'] = Photo.objects.filter(
                is_approved=True, 
                is_featured=True
            )[:12]
            context['recent_photos'] = Photo.objects.filter(
                is_approved=True
            ).order_by('-created_at')[:12]
        except:
            context['featured_photos'] = []
            context['recent_photos'] = []
        
        # Get popular tags
        try:
            from gallery.models import Tag
            from django.db.models import Count, Q
            context['popular_tags'] = Tag.objects.annotate(
                approved_photo_count=Count('photos', filter=Q(photos__is_approved=True))
            ).filter(approved_photo_count__gt=0).order_by('-approved_photo_count')[:10]
        except:
            context['popular_tags'] = []
        
        return context


class AboutView(TemplateView):
    template_name = 'core/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Photo Gallery'
        context['version'] = '1.0.0'
        return context


class ContactView(TemplateView):
    template_name = 'core/contact.html'