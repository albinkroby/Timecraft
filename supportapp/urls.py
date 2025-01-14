from django.urls import path
from . import views

app_name = 'supportapp'

urlpatterns = [
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
]
