from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomWatchOrder, WatchCertificate
from web3 import Web3

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
            
            # Generate certificate after delivery
            if not hasattr(order, 'certificate'):
                try:
                    certificate = WatchCertificate.objects.create(order=order)
                    certificate_hash = certificate.generate_certificate_hash()
                    certificate.certificate_hash = certificate_hash
                    
                    # Connect to Ethereum network
                    w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
                    contract = w3.eth.contract(
                        address=settings.CERTIFICATE_CONTRACT_ADDRESS,
                        abi=settings.CERTIFICATE_CONTRACT_ABI
                    )
                    
                    # Store hash on blockchain
                    tx_hash = contract.functions.storeCertificate(
                        str(order.order_id),
                        certificate_hash
                    ).transact({'from': settings.ETHEREUM_ACCOUNT})
                    
                    certificate.blockchain_tx_hash = tx_hash.hex()
                    certificate.is_verified = True
                    certificate.save()
                    
                    # Send certificate notification email
                    send_mail(
                        'Your Watch Certificate is Ready',
                        f'Your order #{order.order_id} has been delivered and your certificate of authenticity is now available. '
                        f'You can view it in your order details.',
                        settings.DEFAULT_FROM_EMAIL,
                        [order.user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.error(f"Error generating certificate for order {order.order_id}: {str(e)}")
            
            send_mail(
                'Order Delivered Successfully',
                f'Your order #{order.order_id} has been delivered. Thank you for shopping with us!',
                settings.DEFAULT_FROM_EMAIL,
                [order.user.email],
                fail_silently=False,
            )
    
    order.save()
