from django.urls import path,reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

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
    
    path('brands/', views.brand_list, name='brand_list'),
    
    path('categories/', views.category_list, name='category_list'),
    path('edit-category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('delete-category/<int:category_id>/', views.delete_category, name='delete_category'),
    
    path('add-product/', views.add_product, name='add_product'),
    path('products/', views.product_list, name='product_list'),
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
    path('check-watch-name/', views.check_watch_name, name='check_watch_name'),
    path('customizable-watches/', views.customizable_watch_list, name='customizable_watch_list'),
    path('customizable-watches/<int:watch_id>/', views.view_customizable_watch, name='view_customizable_watch'),
    path('add-watch-parts/<int:watch_id>/', views.add_watch_parts, name='add_watch_parts'),
    path('add-part-options/<int:watch_id>/', views.add_part_options, name='add_part_options'),
    
    path('customizable-watch/<int:watch_id>/edit/', views.edit_customizable_watch, name='edit_customizable_watch'),
    path('watch-part/<int:part_id>/edit/', views.edit_watch_part, name='edit_watch_part'),
    path('watch-part-option/<int:option_id>/edit/', views.edit_watch_part_option, name='edit_watch_part_option'),
     path('customizable-watch/<int:watch_id>/delete/', views.delete_customizable_watch, name='delete_customizable_watch'),
    path('watch-part/<int:part_id>/delete/', views.delete_watch_part, name='delete_watch_part'),
    path('watch-part-option/<int:option_id>/delete/', views.delete_watch_part_option, name='delete_watch_part_option'),
]

