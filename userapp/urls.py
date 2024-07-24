from django.urls import path,reverse_lazy
from django.contrib.auth import views as auth_views
from .forms import CustomSetPasswordForm, CustomPasswordResetForm
from . import views

app_name="userapp"
urlpatterns = [
    path('profile/',views.profile,name='profile'),
    path('Address/',views.Address,name='Address'),
    
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html',
        email_template_name='registration/password_reset_email.html',
        success_url=reverse_lazy('userapp:password_reset_done')
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        success_url=reverse_lazy('userapp:password_reset_complete'),
        template_name='registration/password_reset_confirm.html',
        form_class=CustomSetPasswordForm
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
]

#email_template_name='registration/password_reset_email.html'