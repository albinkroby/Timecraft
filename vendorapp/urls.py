from django.urls import path,reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name="vendorapp"
urlpatterns = [
    path('',views.index,name='index'),
    path('home/',views.home,name='home'),
    path('register/', views.vendor_register, name='register'),
    
    path('add-product/', views.add_product, name='add_product'),
    path('products/', views.product_list, name='product_list'),
    path('delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('delete-product-image/<int:image_id>/', views.delete_product_image, name='delete_product_image'),
    
    path('manage-stock/', views.manage_stock, name='manage_stock'),
    path('update-stock/<int:product_id>/', views.update_stock, name='update_stock'),
    
    path('orders/', views.order_list, name='order_list'),
    path('check-unique-model-name/', views.check_unique_model_name, name='check_unique_model_name'),
    path('orders/download/', views.download_orders, name='download_orders'),

]
