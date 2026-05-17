from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, UpdateView, DetailView
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q, Count
from .models import User, UserActivityLog, UserRoles
from .forms import (
    UserRegistrationForm, UserLoginForm, UserProfileForm, 
    UserPasswordChangeForm, UserRoleChangeForm
)
# from gallery.models import Photo, Like, Comment
from django.core.exceptions import PermissionDenied


class RoleRequiredMixin(UserPassesTestMixin):
    
    allowed_roles = []
    
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if self.allowed_roles and self.request.user.role not in self.allowed_roles:
            raise PermissionDenied("You don't have permission to access this page.")
        return True
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('accounts:login')
        raise PermissionDenied("Access denied. Insufficient permissions.")


class RegisterView(View):
    
    template_name = 'accounts/register.html'
    
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:home')
        form = UserRegistrationForm()
        return render(request, self.template_name, {'form': form})
    
    @method_decorator(csrf_protect)
    def post(self, request):
        if request.user.is_authenticated:
            return redirect('core:home')
        
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.role = UserRoles.VIEWER  # Default role
            user.save()
            
            # Log the activity
            UserActivityLog.objects.create(
                user=user,
                action='register',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'method': 'email_registration'}
            )
            
            # Auto-login after registration
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account has been created.')
            return redirect('core:home')
        
        return render(request, self.template_name, {'form': form})


class LoginView(View):
    
    template_name = 'accounts/login.html'
    
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:home')
        form = UserLoginForm()
        return render(request, self.template_name, {'form': form})
    
    @method_decorator(csrf_protect)
    def post(self, request):
        if request.user.is_authenticated:
            return redirect('core:home')
        
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Log login activity
                UserActivityLog.objects.create(
                    user=user,
                    action='login',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
                
                messages.success(request, f'Welcome back, {user.username}!')
                
                # Redirect to appropriate dashboard based on role
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                
                if user.role == UserRoles.ADMIN:
                    return redirect('accounts:admin_dashboard')
                elif user.role == UserRoles.MODERATOR:
                    return redirect('accounts:moderator_dashboard')
                elif user.role == UserRoles.ARTIST:
                    return redirect('accounts:artist_dashboard')
                else:
                    return redirect('core:home')
            else:
                messages.error(request, 'Invalid username or password.')
        
        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    
    def get(self, request):
        if request.user.is_authenticated:
            # Log logout activity
            UserActivityLog.objects.create(
                user=request.user,
                action='logout',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            logout(request)
            messages.info(request, 'You have been logged out successfully.')
        return redirect('core:home')


class ProfileView(LoginRequiredMixin, DetailView):
    
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    profile_user = self.get_object()
    
    context['is_own_profile'] = (profile_user == self.request.user)
    
    # Temporarily handle missing gallery models
    try:
        from gallery.models import Photo, Like, Comment
        
        if profile_user.role in [UserRoles.ADMIN, UserRoles.ARTIST]:
            context['recent_photos'] = Photo.objects.filter(
                user=profile_user,
                is_approved=True
            ).order_by('-created_at')[:6]
            context['total_photos'] = Photo.objects.filter(
                user=profile_user, is_approved=True
            ).count()
        
        context['total_likes'] = Like.objects.filter(user=profile_user).count()
        context['total_comments'] = Comment.objects.filter(user=profile_user).count()
    except ImportError:
        context['recent_photos'] = []
        context['total_photos'] = 0
        context['total_likes'] = 0
        context['total_comments'] = 0
    
    context['profile_completion'] = profile_user.get_profile_completion_percentage()
    context['recent_activities'] = UserActivityLog.objects.filter(
        user=profile_user
    ).order_by('-timestamp')[:10]
    
    return context

class ProfileEditView(LoginRequiredMixin, UpdateView):
    
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self, queryset=None):
        return self.request.user
    
    def get_success_url(self):
        return reverse('accounts:profile', kwargs={'username': self.request.user.username})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log profile update
        UserActivityLog.objects.create(
            user=self.request.user,
            action='profile_update',
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            details={'updated_fields': list(form.changed_data)}
        )
        
        messages.success(self.request, 'Your profile has been updated successfully!')
        return response


class ChangePasswordView(LoginRequiredMixin, View):
    
    template_name = 'accounts/change_password.html'
    
    def get(self, request):
        form = UserPasswordChangeForm(user=request.user)
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = UserPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            
            # Log password change
            UserActivityLog.objects.create(
                user=request.user,
                action='profile_update',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={'action': 'password_change'}
            )
            
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('accounts:profile', username=request.user.username)
        
        return render(request, self.template_name, {'form': form})


class UserDashboardView(LoginRequiredMixin, TemplateView):
    
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context['user'] = user
        context['recent_activities'] = UserActivityLog.objects.filter(
            user=user
        ).order_by('-timestamp')[:15]
        
        # Statistics
        context['stats'] = {
            'photos_uploaded': Photo.objects.filter(user=user).count(),
            'photos_liked': Like.objects.filter(user=user).count(),
            'comments_made': Comment.objects.filter(user=user).count(),
            'profile_views': 0,  # Would need a view tracking model
        }
        
        return context


class AdminDashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    
    allowed_roles = [UserRoles.ADMIN]
    template_name = 'accounts/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # User statistics
        context['total_users'] = User.objects.count()
        context['total_admins'] = User.objects.filter(role=UserRoles.ADMIN).count()
        context['total_moderators'] = User.objects.filter(role=UserRoles.MODERATOR).count()
        context['total_artists'] = User.objects.filter(role=UserRoles.ARTIST).count()
        context['total_viewers'] = User.objects.filter(role=UserRoles.VIEWER).count()
        
        # Content statistics
        context['total_photos'] = Photo.objects.count()
        context['pending_photos'] = Photo.objects.filter(is_approved=False).count()
        context['total_likes'] = Like.objects.count()
        context['total_comments'] = Comment.objects.count()
        
        # Recent activity
        context['recent_users'] = User.objects.order_by('-date_joined')[:10]
        context['recent_photos'] = Photo.objects.order_by('-created_at')[:10]
        context['recent_activities'] = UserActivityLog.objects.order_by('-timestamp')[:20]
        
        return context


class ModeratorDashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    
    allowed_roles = [UserRoles.ADMIN, UserRoles.MODERATOR]
    template_name = 'accounts/moderator_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pending content for moderation
        context['pending_photos'] = Photo.objects.filter(is_approved=False)[:20]
        context['reported_content'] = []  # Would need reporting feature
        
        # Statistics
        context['stats'] = {
            'total_photos': Photo.objects.count(),
            'approved_photos': Photo.objects.filter(is_approved=True).count(),
            'pending_approval': Photo.objects.filter(is_approved=False).count(),
            'total_users': User.objects.count(),
        }
        
        return context


class ArtistDashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    
    allowed_roles = [UserRoles.ADMIN, UserRoles.MODERATOR, UserRoles.ARTIST]
    template_name = 'accounts/artist_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Artist's photos
        context['user_photos'] = Photo.objects.filter(user=user).order_by('-created_at')
        
        # Statistics for artist's content
        context['stats'] = {
            'total_photos': Photo.objects.filter(user=user).count(),
            'total_likes': Like.objects.filter(photo__user=user).count(),
            'total_views': 0,  # Would need view tracking
            'total_comments': Comment.objects.filter(photo__user=user).count(),
        }
        
        return context


class UserManagementView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    
    allowed_roles = [UserRoles.ADMIN]
    template_name = 'accounts/user_management.html'
    
    def get(self, request, *args, **kwargs):
        users = User.objects.all().order_by('-date_joined')
        
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Filter by role
        role_filter = request.GET.get('role', '')
        if role_filter:
            users = users.filter(role=role_filter)
        
        paginator = Paginator(users, 20)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context = {
            'users': page_obj,
            'search_query': search_query,
            'role_filter': role_filter,
            'roles': UserRoles.choices,
        }
        return render(request, self.template_name, context)


class ChangeUserRoleView(LoginRequiredMixin, RoleRequiredMixin, View):
    
    allowed_roles = [UserRoles.ADMIN]
    
    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        new_role = request.POST.get('role')
        
        if new_role in dict(UserRoles.choices):
            old_role = user.role
            user.role = new_role
            user.save()
            
            # Log role change
            UserActivityLog.objects.create(
                user=request.user,
                action='profile_update',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                details={
                    'action': 'role_change',
                    'target_user': user.username,
                    'old_role': old_role,
                    'new_role': new_role
                }
            )
            
            messages.success(request, f"Role for {user.username} has been changed to {user.get_role_display()}")
        else:
            messages.error(request, "Invalid role selected")
        
        return redirect('accounts:user_management')


class ToggleUserStatusView(LoginRequiredMixin, RoleRequiredMixin, View):
    
    allowed_roles = [UserRoles.ADMIN]
    
    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        
        if user == request.user:
            messages.error(request, "You cannot deactivate your own account")
            return redirect('accounts:user_management')
        
        user.is_active = not user.is_active
        user.save()
        
        status = "activated" if user.is_active else "deactivated"
        
        UserActivityLog.objects.create(
            user=request.user,
            action='profile_update',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            details={
                'action': 'user_status_change',
                'target_user': user.username,
                'new_status': status
            }
        )
        
        messages.success(request, f"User {user.username} has been {status}")
        return redirect('accounts:user_management')