from django.urls import path
from . import views

app_name = 'deliveryapp'

urlpatterns = [
    # Delivery personnel urls
    path('', views.delivery_dashboard, name='dashboard'),
    path('onboarding/', views.onboarding, name='onboarding'),
    path('onboarding/save-personal-details/', views.save_personal_details, name='save_personal_details'),
    path('onboarding/save-vehicle-details/', views.save_vehicle_details, name='save_vehicle_details'),
    path('onboarding/complete/', views.complete_onboarding, name='complete_onboarding'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.create_profile, name='create_profile'),
    path('send-verification-email/', views.send_verification_email, name='send_verification_email'),
    path('check-email-status/', views.check_email_status, name='check_email_status'),
    path('orders/assigned/', views.assigned_orders, name='assigned_orders'),
    path('orders/<str:order_id>/', views.order_detail, name='order_detail'),
    path('location/update/', views.update_location, name='update_location'),
    path('orders/<str:order_id>/verify-otp/', views.verify_otp, name='verify_otp'),
    path('orders/<str:order_id>/verify-otp-ajax/', views.verify_otp_ajax, name='verify_otp_ajax'),
    path('history/', views.delivery_history, name='delivery_history'),
    
    # Admin urls - use consistent naming for URLs
    path('admin/order-assignment/<str:order_id>/', views.admin_assign_delivery, name='order-assignment'),
    path('admin/order-auto-assign/', views.admin_auto_assign_delivery, name='order-auto-assign'),
    path('admin/order-batch-assign/', views.admin_batch_order_assignment, name='order-batch-assign'),
    
    # Customer urls
    path('track/<str:order_id>/', views.track_order, name='track_order'),
    path('rate/<str:order_id>/', views.rate_delivery, name='rate_delivery'),
    
    # Return URLs for delivery personnel
    path('returns/', views.return_list, name='return_list'),
    path('returns/<str:order_id>/', views.return_detail, name='return_detail'),
    path('returns/<str:order_id>/verify-otp/', views.verify_return_otp, name='verify_return_otp'),
    path('returns/<str:order_id>/request-otp/', views.request_return_otp, name='request_return_otp'),
    path('returns/<str:order_id>/complete/', views.complete_return, name='complete_return'),
    path('returns/<str:order_id>/condition/', views.submit_return_condition, name='submit_return_condition'),
    path('returns/<str:order_id>/update-status/', views.update_return_status, name='update_return_status'),
    
    # Return Management - Admin
    path('admin/return-requests/', views.admin_return_requests, name='admin_return_requests'),
    path('admin/return-approve/<str:order_id>/', views.admin_approve_return, name='admin_approve_return'),
    path('admin/return-assign/<str:order_id>/', views.admin_assign_return, name='admin_assign_return'),
    path('admin/return-status/', views.admin_return_status, name='admin_return_status'),
    path('admin/batch-return-assignment/', views.admin_batch_return_assignment, name='admin_batch_return_assignment'),
]