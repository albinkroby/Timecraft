from django.urls import path,reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name="vendorapp"
urlpatterns = [
    path('',views.index,name='index'),
    path('home/',views.home,name='home'),
    path('register/step1/', views.vendor_register_step1, name='vendor_register_step1'),
    path('register/step2/', views.vendor_register_step2, name='vendor_register_step2'),
    path('onboarding/', views.vendor_onboarding, name='vendor_onboarding'),
    path('login/', views.vendor_login, name='vendor_login'),
    
    path('send-verification-email/', views.vendor_send_verification_email, name='vendor_send_verification_email'),
    path('verify-email/<uuid:token>/', views.vendor_verify_email, name='vendor_verify_email'),
    path('check-email-status/', views.vendor_check_email_status, name='vendor_check_email_status'),
    
    path('profile/', views.vendor_profile, name='vendor_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    path('validate_company_name/', views.validate_company_name, name='validate_company_name'),
    
    path('analysis/', views.analysis_view, name='analysis'),
    
    path('products/', views.product_list, name='product_list'),
    path('toggle-product-status/', views.toggle_product_status, name='toggle_product_status'),
    path('add-product/', views.add_product_step1, name='add_product_step1'),
    path('add-product/step2/', views.add_product_step2, name='add_product_step2'),
    
    path('bulk-product-upload/', views.bulk_product_upload, name='bulk_product_upload'),
    path('download-template/', views.download_template, name='download_template'),
    path('upload-product-images/', views.upload_product_images, name='upload_product_images'),
    
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete-product-image/<int:image_id>/', views.delete_product_image, name='delete_product_image'),
    
    path('request-brand-approval/<int:brand_id>/', views.request_brand_approval, name='request_brand_approval'),
    
    path('manage-stock/', views.manage_stock, name='manage_stock'),
    path('update-stock/<int:product_id>/', views.update_stock, name='update_stock'),
    
    path('orders/', views.order_list, name='order_list'),
    path('check-unique-model-name/', views.check_unique_model_name, name='check_unique_model_name'),
    path('orders/download/', views.download_orders, name='download_orders'),
    path('orders/<str:order_id>/', views.order_detail, name='order_detail'),

]
