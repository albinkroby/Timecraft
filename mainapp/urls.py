from django.urls import path,reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name="mainapp"
urlpatterns = [
    path('',views.index,name='index'),
    path('login/',views.signin,name='login'),
    path('signup/',views.signup,name='signup'),
    path('logout/',views.signout,name='logout'),
    
    # path('google-login/', views.google_login, name='google_login'),
    path('login-redirect/', views.login_redirect, name='login_redirect'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    
    path('check-username/', views.check_username, name='check_username'),
    path('check-email/', views.check_email, name='check_email'),
    
    
]
