from django.urls import path,reverse_lazy, include
from . import views
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import redirect

app_name="adminapp"
urlpatterns = [
    path('',views.index,name='index'),
    path('profile/', views.admin_profile, name='admin_profile'),
    path('change-password/', views.change_password, name='change_password'),
    
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/toggle-active/', views.toggle_user_active, name='toggle_user_active'),
    
    path('seller-approval/', views.seller_approval, name='seller_approval'),
    path('approve-vendor/<int:user_id>/', views.approve_vendor, name='approve_vendor'),
    path('reject-vendor/<int:user_id>/', views.reject_vendor, name='reject_vendor'),
    path('all-sellers/', views.all_sellers, name='all_sellers'),
    
    path('analysis/', views.analysis_view, name='analysis'),
    
    path('brands/', views.brand_list, name='brand_list'),
    
    path('categories/', views.category_list, name='category_list'),
    path('edit-category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    
    path('add-product/', views.add_product, name='add_product'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    
    path('features/', views.feature_list, name='feature_list'),
    path('features/add/', views.add_feature, name='add_feature'),
    path('features/edit/<int:feature_id>/', views.edit_feature, name='edit_feature'),
    path('features/toggle/<int:feature_id>/', views.toggle_feature, name='toggle_feature'),
    
    path('materials/', views.material_list, name='material_list'),
    path('materials/add/', views.add_material, name='add_material'),
    path('materials/edit/<int:material_id>/', views.edit_material, name='edit_material'),
    path('materials/toggle/<int:material_id>/', views.toggle_material, name='toggle_material'),
    
    path('add-customizable-watch/', views.add_customizable_watch, name='add_customizable_watch'),
    path('add-watch-details/<path:model_path>/', views.add_watch_details, name='add_watch_details'),
    path('check-watch-name/', views.check_watch_name, name='check_watch_name'),
    path('customizable-watches/', views.customizable_watch_list, name='customizable_watch_list'),
    path('customizable-watches/<int:watch_id>/', views.view_customizable_watch, name='view_customizable_watch'),
    path('add-watch-parts/<int:watch_id>/', views.add_watch_parts, name='add_watch_parts'),
    path('add-part-options/<int:watch_id>/', views.add_part_options, name='add_part_options'),
    path('configure-watch-parts/<int:watch_id>/', views.configure_watch_parts, name='configure_watch_parts'),
    path('get-model-path/<int:watch_id>/', views.get_model_path, name='get_model_path'),
    
    path('order-list/', views.order_list, name='order_list'),
    path('download-orders/', views.download_orders, name='download_orders'),
    
    # Batch order assignment
    path('orders/batch-assign/', 
         lambda request: redirect('deliveryapp:order-batch-assign'), 
         name='batch_assign_delivery'),
         
    # Auto-assign orders
    path('orders/auto-assign/', 
         lambda request: redirect('deliveryapp:order-auto-assign'), 
         name='auto_assign_delivery'),
         
    # Order Management
    path('orders/', views.manage_orders, name='manage_orders'),
    path('orders/<str:order_id>/', views.order_detail, name='order_detail'),
    
    # Return Management
    path('returns/', views.manage_returns, name='manage_returns'),
    path('returns/<str:order_id>/', views.return_detail, name='return_detail'),
    
    path('customizable-watch/<int:watch_id>/edit/', views.edit_customizable_watch, name='edit_customizable_watch'),
    # path('watch-part/<int:part_id>/edit/', views.edit_watch_part, name='edit_watch_part'),
    # path('watch-part-option/<int:option_id>/edit/', views.edit_watch_part_option, name='edit_watch_part_option'),
    path('customizable-watch/<int:watch_id>/delete/', views.delete_customizable_watch, name='delete_customizable_watch'),
    path('watch-part/<int:part_id>/delete/', views.delete_watch_part, name='delete_watch_part'),
    path('delete-watch-part/', views.delete_watch_part_ajax, name='delete_watch_part_ajax'),
    path('watch-part-option/<int:option_id>/delete/', views.delete_watch_part_option, name='delete_watch_part_option'),
    path('add-watch-part-ajax/<int:watch_id>/', views.add_watch_part_ajax, name='add_watch_part_ajax'),
    path('add-part-option-ajax/', views.add_part_option_ajax, name='add_part_option_ajax'),
    path('delete-part-option/', views.delete_part_option, name='delete_part_option'),
    path('edit-watch-part-ajax/', views.edit_watch_part_ajax, name='edit_watch_part_ajax'),
    path('edit-part-option/', views.edit_part_option_ajax, name='edit_part_option_ajax'),
    
    path('manage-prices/', views.manage_prices, name='manage_prices'),
    path('update-watch-price/', views.update_watch_price, name='update_watch_price'),
    path('update-option-price/', views.update_option_price, name='update_option_price'),
    path('get-watch-parts/', views.get_watch_parts, name='get_watch_parts'),
    path('get-part-options/', views.get_part_options, name='get_part_options'),
    
    path('custom-watch-orders/', views.custom_watch_orders, name='custom_watch_orders'),
    path('custom-watch-order/<int:order_id>/', views.custom_watch_order_detail, name='custom_watch_order_detail'),
    path('custom-watch-order/<int:order_id>/update-status/', views.update_custom_watch_order_status, name='update_custom_watch_order_status'),
    
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.add_staff, name='add_staff'),
    path('staff/toggle-access/<int:staff_id>/', views.toggle_staff_access, name='toggle_staff_access'),

    # Delivery Agent Management
    path('delivery-agents/', views.delivery_agents_list, name='delivery_agents_list'),
    path('delivery-agents/create/', views.create_delivery_agent, name='create_delivery_agent'),
    path('delivery-agents/<int:user_id>/', views.view_delivery_agent, name='view_delivery_agent'),
    path('delivery-agents/<int:user_id>/edit/', views.edit_delivery_agent, name='edit_delivery_agent'),
    path('delivery-agents/<int:user_id>/toggle/', views.toggle_delivery_agent, name='toggle_delivery_agent'),
    
    # 3D Model Editor
    path('model-editor/<int:watch_id>/', views.model_editor, name='model_editor'),
    
    # Redirect to delivery app for order assignment
    path('orders/<str:order_id>/assign-delivery/', 
         lambda request, order_id: redirect('deliveryapp:order-assignment', order_id=order_id), 
         name='assign_delivery_agent'),
]
