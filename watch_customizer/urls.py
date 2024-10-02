from django.urls import path
from . import views

app_name = 'watch_customizer'
urlpatterns = [
    path('', views.customize_watch, name='customize_watch'),
]