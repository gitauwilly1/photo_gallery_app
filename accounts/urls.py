from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    path('profile/<str:username>/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('profile/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    path('dashboard/', views.UserDashboardView.as_view(), name='dashboard'),
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('dashboard/moderator/', views.ModeratorDashboardView.as_view(), name='moderator_dashboard'),
    path('dashboard/artist/', views.ArtistDashboardView.as_view(), name='artist_dashboard'),
    
    path('users/', views.UserManagementView.as_view(), name='user_management'),
    path('users/<int:user_id>/change-role/', views.ChangeUserRoleView.as_view(), name='change_user_role'),
    path('users/<int:user_id>/toggle-status/', views.ToggleUserStatusView.as_view(), name='toggle_user_status'),
]