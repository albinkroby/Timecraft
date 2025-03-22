from django.urls import path
from . import views

app_name = 'blockchain'

urlpatterns = [
    # Add blockchain-related URLs here when needed
    path('', views.blockchain_home, name='home'),
] 