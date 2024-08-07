from django.urls import path,reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name="adminapp"
urlpatterns = [
    path('',views.index,name='index'),
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
    
]

