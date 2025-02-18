from django.urls import path
from . import views

app_name = 'supportapp'

urlpatterns = [
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/profile/', views.staff_profile, name='staff_profile'),
    path('staff/change-password/', views.change_password, name='change_password'),
]
