from django.urls import path,reverse_lazy
from django.contrib.auth import views as auth_views
from .forms import CustomSetPasswordForm, CustomPasswordResetForm
from . import views

app_name="userapp"
urlpatterns = [
    path('profile/',views.profile,name='profile'),
    path('Address/',views.address_list,name='Address'),
    path('add-address/', views.add_address, name='add_address'),
    path('edit-address/<int:address_id>/', views.edit_address, name='edit_address'),
    path('delete-address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('make-primary-address/<int:address_id>/', views.make_primary_address, name='make_primary_address'),
    
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:watch_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:watch_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    
    path('my-orders/', views.my_orders, name='my_orders'),
    path('orders/<str:order_id>/', views.order_details, name='order_details'),
    path('orders/<str:order_id>/invoice/', views.download_invoice, name='download_invoice'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('orders/<int:order_id>/return/', views.return_order, name='return_order'),
    
    path('write-review/<int:item_id>/', views.write_review, name='write_review'),
    path('edit-review/<int:item_id>/', views.edit_review, name='edit_review'),
    
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html',
        email_template_name='registration/password_reset_email.html',
        success_url=reverse_lazy('userapp:password_reset_done')
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        success_url=reverse_lazy('userapp:password_reset_complete'),
        template_name='registration/password_reset_confirm.html',
        form_class=CustomSetPasswordForm
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    
]

#email_template_name='registration/password_reset_email.html'