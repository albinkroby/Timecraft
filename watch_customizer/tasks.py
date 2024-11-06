from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomWatchOrder

def process_shipping_status(order_id):
    order = CustomWatchOrder.objects.get(id=order_id)
    current_time = timezone.now()
    
    if order.status == 'shipped' and order.shipping_started_date:
        days_in_transit = (current_time - order.shipping_started_date).days
        
        if days_in_transit >= 3:  # After 3 days, mark as out for delivery
            order.status = 'out_for_delivery'
            send_mail(
                'Your Order is Out for Delivery!',
                f'Your order #{order.order_id} will be delivered today.',
                settings.DEFAULT_FROM_EMAIL,
                [order.user.email],
                fail_silently=False,
            )
        
        if days_in_transit >= 4:  # After 4 days, mark as delivered
            order.status = 'delivered'
            order.delivery_date = timezone.now().date()
            send_mail(
                'Order Delivered Successfully',
                f'Your order #{order.order_id} has been delivered. Thank you for shopping with us!',
                settings.DEFAULT_FROM_EMAIL,
                [order.user.email],
                fail_silently=False,
            )
        
        order.save()
