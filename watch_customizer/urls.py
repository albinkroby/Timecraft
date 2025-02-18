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
    
    path('place_custom_order/', views.place_custom_order, name='place_custom_order'),
    path('order_confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('custom-orders/<int:order_id>/cancel/', views.cancel_custom_watch_order, name='cancel_custom_watch_order'),
    path('custom-orders/<int:order_id>/return/', views.return_custom_watch_order, name='return_custom_watch_order'),
    
    path('custom_payment_success/', views.custom_payment_success, name='custom_payment_success'),
    path('custom_payment_cancel/', views.custom_payment_cancel, name='custom_payment_cancel'),
    path('custom_order_details/<str:order_id>/', views.custom_order_details, name='custom_order_details'),
    path('certificate/<str:order_id>/', views.view_certificate, name='view_certificate'),
    path('certificate/verify/<int:certificate_id>/', views.verify_certificate, name='verify_certificate'),
    path('verify-certificate/', views.verify_certificate_page, name='verify_certificate_page'),
    path('api/verify-certificate/', views.verify_certificate_public, name='verify_certificate_public'),
]
