from django.urls import path,reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name="mainapp"
urlpatterns = [
    path('',views.index,name='index'),
    path('login/',views.signin,name='login'),
    path('signup/',views.signup,name='signup'),
    path('logout/',views.signout,name='logout'),
    
    # path('google-login/', views.google_login, name='google_login'),
    path('login-redirect/', views.login_redirect, name='login_redirect'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    
    path('check-username/', views.check_username, name='check_username'),
    path('check-email/', views.check_email, name='check_email'),
    
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    
    path('cart/', views.cart, name='cart'),
    path('add-to-cart/<int:watch_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/', views.update_cart, name='update_cart'),
    
    path('search/', views.search_results, name='search_results'),
    
    path('order-review/', views.order_review, name='order_review'),
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'),
    
    path('notify-me/', views.notify_me, name='notify_me'),
    
]