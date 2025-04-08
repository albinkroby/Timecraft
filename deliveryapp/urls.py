from django.urls import path
from . import views

app_name = 'deliveryapp'

urlpatterns = [
    # Delivery personnel urls
    path('', views.delivery_dashboard, name='dashboard'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.create_profile, name='create_profile'),
    path('orders/assigned/', views.assigned_orders, name='assigned_orders'),
    path('orders/<str:order_id>/detail/', views.order_detail, name='order_detail'),
    path('location/update/', views.update_location, name='update_location'),
    path('orders/<str:order_id>/verify-otp/', views.verify_otp, name='verify_otp'),
    path('history/', views.delivery_history, name='delivery_history'),
    
    # Admin urls - use consistent naming for URLs
    path('order-assignment/<str:order_id>/', views.admin_assign_delivery, name='order-assignment'),
    path('order-auto-assign/', views.admin_auto_assign_delivery, name='order-auto-assign'),
    path('order-batch-assign/', views.admin_batch_order_assignment, name='order-batch-assign'),
    
    # Customer urls
    path('track/<str:order_id>/', views.track_order, name='track_order'),
    path('rate/<str:order_id>/', views.rate_delivery, name='rate_delivery'),
] 