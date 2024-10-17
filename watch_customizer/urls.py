from django.urls import path
from . import views

app_name = 'watch_customizer'
urlpatterns = [
    path('', views.customize_watch, name='customize_watch'),
    
    path('edit/<int:watch_id>/', views.customize_watch, name='customize_watch_with_id'),
    
    path('save_design/', views.save_design, name='save_design'),
    path('save_preview_image/<int:design_id>/', views.save_preview_image, name='save_preview_image'),
    path('save_design/<int:design_id>/', views.save_design, name='save_design_with_id'),
    path('saved_designs/', views.saved_designs, name='saved_designs'),
    
    path('delete_design/<int:design_id>/', views.delete_design, name='delete_design'),
]
