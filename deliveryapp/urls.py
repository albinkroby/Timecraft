from django.urls import path
from . import views

app_name = 'deliveryapp'

urlpatterns = [
    # Delivery personnel urls
    path('', views.delivery_dashboard, name='dashboard'),
    path('profile/', views.create_profile, name='profile'),
    path('profile/create/', views.create_profile, name='create_profile'),
    path('orders/assigned/', views.assigned_orders, name='assigned_orders'),
    path('order/<str:order_id>/', views.order_detail, name='order_detail'),
    path('order/<str:order_id>/verify-otp/', views.verify_otp, name='verify_otp'),
    path('update-location/', views.update_location, name='update_location'),
    path('history/', views.delivery_history, name='delivery_history'),
    
    # Admin urls
    path('admin/order/<str:order_id>/assign/', views.admin_assign_delivery, name='admin_assign_delivery'),
    
    # Customer urls
    path('order/<str:order_id>/rate/', views.rate_delivery, name='rate_delivery'),
    path('track/<str:order_id>/', views.track_order, name='track_order'),
] 