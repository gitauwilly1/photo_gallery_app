from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    path('', views.GalleryView.as_view(), name='gallery'),
    path('photo/<slug:slug>/', views.PhotoDetailView.as_view(), name='photo_detail'),
    
    path('upload/', views.PhotoUploadView.as_view(), name='photo_upload'),
    path('photo/<slug:slug>/edit/', views.PhotoEditView.as_view(), name='photo_edit'),
    path('photo/<slug:slug>/delete/', views.PhotoDeleteView.as_view(), name='photo_delete'),
    
    path('photo/<slug:slug>/like/', views.LikeToggleView.as_view(), name='like_toggle'),
    path('photo/<slug:slug>/favorite/', views.FavoriteToggleView.as_view(), name='favorite_toggle'),
    path('photo/<slug:slug>/comment/', views.AddCommentView.as_view(), name='add_comment'),
    
    path('tag/<slug:tag_slug>/', views.GalleryView.as_view(), name='tag_filter'),
    path('search/', views.SearchView.as_view(), name='search'),
    
    path('my-photos/', views.UserGalleryView.as_view(), name='user_gallery'),
    path('my-favorites/', views.UserFavoritesView.as_view(), name='user_favorites'),
]