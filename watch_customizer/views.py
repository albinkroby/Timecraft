from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import CustomizableWatch, CustomizableWatchPart, CustomWatchSavedDesign, CustomWatchOrder, CustomWatchOrderPart,WatchCertificate, WatchPart, WatchPartOption
from django.db import IntegrityError
import json
import logging
import base64
from django.core.files.base import ContentFile
from django.contrib import messages
from mainapp.models import Address
import stripe
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from django.conf import settings
from django.views.decorators.cache import never_cache
from userapp.forms import AddressForm
import json
from django.db import transaction
from web3 import Web3
from blockchain.blockchain_utils import store_certificate_on_blockchain, verify_certificate_on_blockchain
from django.views.decorators.csrf import ensure_csrf_cookie
from decimal import Decimal

logger = logging.getLogger(__name__)

# Create your views here.

def customize_watch(request, watch_id=None):
    if watch_id is None:
        customizable_watch = CustomizableWatch.objects.first()
    else:
        customizable_watch = get_object_or_404(CustomizableWatch, id=watch_id)
    
    customizable_parts = CustomizableWatchPart.objects.filter(customizable_watch=customizable_watch).select_related('part__part_name').prefetch_related('options')
    
    saved_design = None
    if 'design_id' in request.GET:
        design_id = request.GET['design_id']
        logger.info(f"Attempting to load design with id: {design_id}")
        try:
            saved_design = CustomWatchSavedDesign.objects.get(id=design_id, user=request.user)
            logger.info(f"Loaded saved design: {saved_design.name}")
            logger.info(f"Design data: {saved_design.design_data}")
        except CustomWatchSavedDesign.DoesNotExist:
            logger.warning(f"Design with id {design_id} not found for user {request.user}")
    
    context = {
        'customizable_watch': customizable_watch,
        'customizable_parts': customizable_parts,
        'saved_design': saved_design,
    }
    return render(request, 'watch_customizer/custom_watch.html', context)

@login_required
@require_POST
def save_design(request, design_id=None):
    try:
        data = json.loads(request.body)

        design_name = data.get('name')
        design_data = data.get('design_data')
        watch_id = data.get('watch_id')

        if not design_name:
            return JsonResponse({'status': 'error', 'message': 'Design name is required'}, status=400)

        if not watch_id:
            return JsonResponse({'status': 'error', 'message': 'Watch ID is missing'}, status=400)

        if design_id:
            # Update existing design
            try:
                saved_design = CustomWatchSavedDesign.objects.get(id=design_id, user=request.user)
                saved_design.name = design_name
                saved_design.design_data = design_data
                saved_design.save()
                return JsonResponse({'status': 'success', 'design_id': saved_design.id, 'message': 'Design updated successfully'})
            except CustomWatchSavedDesign.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Design not found'}, status=404)
        else:
            # Create new design
            try:
                saved_design = CustomWatchSavedDesign.objects.create(
                    user=request.user,
                    customizable_watch_id=watch_id,
                    name=design_name,
                    design_data=design_data
                )
                return JsonResponse({'status': 'success', 'design_id': saved_design.id, 'message': 'Design saved successfully'})
            except IntegrityError:
                return JsonResponse({'status': 'error', 'message': 'Design name already exists'}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def saved_designs(request):
    designs = CustomWatchSavedDesign.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'watch_customizer/saved_designs.html', {'designs': designs})

@login_required
@require_POST
def delete_design(request, design_id):
    try:
        design = CustomWatchSavedDesign.objects.get(id=design_id, user=request.user)
        design.delete()
        return JsonResponse({'status': 'success'})
    except CustomWatchSavedDesign.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Design not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_POST
def save_preview_image(request, design_id):
    try:
        design = CustomWatchSavedDesign.objects.get(id=design_id, user=request.user)
        data = json.loads(request.body)
        preview_image_data = data.get('preview_image')

        if preview_image_data:
            format, imgstr = preview_image_data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'{design.name}_preview.{ext}')
            design.preview_image.save(f'{design.name}_preview.{ext}', data, save=True)

        return JsonResponse({'status': 'success', 'message': 'Preview image saved successfully'})
    except CustomWatchSavedDesign.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Design not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def place_custom_order(request):
    design_id = request.GET.get('design_id')
    design = get_object_or_404(CustomWatchSavedDesign, id=design_id, user=request.user)

    addresses = Address.objects.filter(user=request.user)
    primary_address = addresses.filter(is_primary=True).first()
    form = AddressForm()

    # Calculate total price
    total_price = design.customizable_watch.base_price  # This is already Decimal
    
    if isinstance(design.design_data, str):
        try:
            design_data = json.loads(design.design_data)
        except json.JSONDecodeError:
            design_data = []
    else:
        design_data = design.design_data

    # Process the design data to get part details
    processed_parts = []
    for part_name, option_id in design_data.items():
        try:
            # Use filter().first() instead of get() to avoid MultipleObjectsReturned error
            part = WatchPart.objects.filter(part_name__name__iexact=part_name).first()
            if part is None:
                logger.error(f"No part found with name {part_name}")
                continue
                
            option = WatchPartOption.objects.get(id=option_id.replace('btnCheck', ''))
            processed_parts.append({
                'part_name': part.part_name.name,
                'option_name': option.name,
                'price': option.price,  # Keep as Decimal
                'part_id': part.id,
                'option_id': option.id
            })
            total_price += option.price  # Add Decimal to Decimal
        except (WatchPart.DoesNotExist, WatchPartOption.DoesNotExist) as e:
            logger.error(f"Error processing part {part_name}: {str(e)}")
            continue

    # Create CustomWatchOrder with existing code...
    with transaction.atomic():
        custom_order = CustomWatchOrder.objects.create(
            user=request.user,
            customizable_watch=design,
            address=primary_address,
            total_price=total_price,
            status='pending'
        )
        # Create order parts with the processed data
        for part_data in processed_parts:
            CustomWatchOrderPart.objects.create(
                order=custom_order,
                part_id=part_data['part_id'],
                selected_option_id=part_data['option_id']
            )

    context = {
        'design': design,
        'addresses': addresses,
        'primary_address': primary_address,
        'stripe_publishable_key': settings.STRIPE_PUBLIC_KEY,
        'form': form,
        'total': total_price,
        'final_total': total_price,  # Keep the same as total since delivery is free
        'total_savings': Decimal('30'),  # Add delivery charge as savings
        'processed_parts': processed_parts,
        'custom_order_id': custom_order.id if 'custom_order' in locals() else None,
    }
    return render(request, 'watch_customizer/place_custom_order.html', context)

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(CustomWatchOrder, id=order_id, user=request.user)
    return render(request, 'watch_customizer/order_confirmation.html', {'order': order})

@never_cache 
@login_required
def custom_payment_success(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return render(request, 'watch_customizer/custom_payment_success.html', 
                     {'paid': False, 'error': 'No session ID provided.'})

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            custom_order = CustomWatchOrder.objects.filter(stripe_session_id=session_id).first()
            if custom_order:
                # Send order confirmation email
                send_custom_order_confirmation_email(custom_order, request)
                return render(request, 'watch_customizer/custom_payment_success.html', 
                            {'paid': True, 'order': custom_order})
            else:
                return render(request, 'watch_customizer/custom_payment_success.html', 
                            {'paid': False, 'error': 'Order not found.'})
        else:
            return render(request, 'watch_customizer/custom_payment_success.html', 
                        {'paid': False, 'error': 'Payment not successful.'})
    except Exception as e:
        return render(request, 'watch_customizer/custom_payment_success.html', 
                     {'paid': False, 'error': f'An error occurred: {str(e)}'})

@never_cache 
@login_required
def custom_payment_cancel(request):
    return render(request, 'watch_customizer/custom_payment_cancel.html')

def send_custom_order_confirmation_email(order, request):
    subject = f'Custom Watch Order Confirmation - Order #{order.order_id}'
    html_message = render_to_string('emails/custom_order_confirmation.html', {
        'order': order,
        'user': order.user,
        'view_order_history_url': request.build_absolute_uri(reverse('userapp:my_orders')),
        'refund_policy_url': '#',
    })
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = order.user.email

    send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)

@login_required
def custom_order_details(request, order_id):
    order = get_object_or_404(CustomWatchOrder, order_id=order_id, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'watch_customizer/custom_order_details.html', context)

@never_cache
@login_required
def cancel_custom_watch_order(request, order_id):
    order = get_object_or_404(CustomWatchOrder, id=order_id, user=request.user)
    
    if request.method == 'POST':
        reason = request.POST.get('cancellation_reason', '')
        if reason == 'Other':
            custom_reason = request.POST.get('custom_reason', '')
            reason = custom_reason if custom_reason else reason
            
        order.status = 'cancelled'
        order.cancellation_reason = reason
        order.save()
        
        if order.cancel_order(reason):
            messages.success(request, 'Custom watch order cancelled successfully.')
        else:
            messages.error(request, 'Custom watch order cannot be cancelled.')
        return redirect('userapp:my_orders')
    
    return render(request, 'userapp/cancel_order.html', {'order': order})

@never_cache
@login_required
def return_custom_watch_order(request, order_id):
    order = get_object_or_404(CustomWatchOrder, id=order_id, user=request.user)
    
    if order.is_returnable():
        if request.method == 'POST':
            return_reason = request.POST.get('return_reason', '')
            if return_reason == 'Other':
                custom_reason = request.POST.get('custom_reason', '')
                return_reason = custom_reason if custom_reason else return_reason
            
            order.status = 'returned'
            order.return_reason = return_reason
            order.save()
            messages.success(request, 'Custom watch order returned successfully.')
            return redirect('userapp:my_orders')
    else:
        messages.error(request, 'Custom watch order cannot be returned. Return period has expired.')
        return redirect('userapp:my_orders')
    
    return render(request, 'userapp/return_order.html', {'order': order})

@login_required
def view_certificate(request, order_id):
    order = get_object_or_404(CustomWatchOrder, order_id=order_id, user=request.user)
    
    # Generate certificate if it doesn't exist
    if not hasattr(order, 'certificate'):
        try:
            # Create certificate
            certificate = WatchCertificate.objects.create(order=order)
            certificate_hash = certificate.generate_certificate_hash()
            certificate.certificate_hash = certificate_hash
            
            # Connect to blockchain and store the hash
            w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
            contract = w3.eth.contract(
                address=settings.CERTIFICATE_CONTRACT_ADDRESS,
                abi=settings.CERTIFICATE_CONTRACT_ABI
            )
            
            # Store hash on blockchain
            tx_hash = contract.functions.storeCertificate(
                str(order.order_id),
                certificate_hash
            ).transact({'from': w3.eth.accounts[0]})
            
            # Wait for transaction to be mined
            tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            certificate.blockchain_tx_hash = tx_receipt['transactionHash'].hex()
            certificate.is_verified = True  # Mark as verified since we just stored it
            certificate.save()
            
            messages.success(request, 'Certificate has been generated and stored on blockchain.')
            
        except Exception as e:
            logger.error(f"Error generating certificate for order {order.order_id}: {str(e)}")
            messages.error(request, 'There was an error generating your certificate. Please try again later.')
            return redirect('watch_customizer:custom_order_details', order_id=order.order_id)
    
    # If certificate exists but not verified, verify it
    elif not order.certificate.is_verified:
        try:
            w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
            contract = w3.eth.contract(
                address=settings.CERTIFICATE_CONTRACT_ADDRESS,
                abi=settings.CERTIFICATE_CONTRACT_ABI
            )
            
            # Check if hash matches on blockchain
            stored_hash = contract.functions.getCertificate(str(order.order_id)).call()
            if stored_hash == order.certificate.certificate_hash:
                order.certificate.is_verified = True
                order.certificate.save()
        except Exception as e:
            logger.error(f"Error verifying certificate: {str(e)}")
    
    context = {
        'order': order,
        'contract_address': settings.CERTIFICATE_CONTRACT_ADDRESS,
        'contract_abi': json.dumps(settings.CERTIFICATE_CONTRACT_ABI),
        'is_verified': order.certificate.is_verified if hasattr(order, 'certificate') else False,
        'is_metamask_verified': order.certificate.is_metamask_verified if hasattr(order, 'certificate') else False,
    }
    
    return render(request, 'watch_customizer/certificate_view.html', context)

@require_POST
def update_verification_status(request, order_id):
    try:
        order = get_object_or_404(CustomWatchOrder, order_id=order_id)
        if hasattr(order, 'certificate'):
            order.certificate.is_metamask_verified = True
            order.certificate.save()
            return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def verify_certificate(request, certificate_id):
    certificate = get_object_or_404(WatchCertificate, id=certificate_id)
    
    try:
        # Connect to Ethereum network
        w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_NODE_URL))
        contract = w3.eth.contract(
            address=settings.CERTIFICATE_CONTRACT_ADDRESS,
            abi=settings.CERTIFICATE_CONTRACT_ABI
        )
        
        # Verify certificate on blockchain
        stored_hash = contract.functions.getCertificate(
            str(certificate.order.order_id)
        ).call()
        
        # Verify the hash matches
        is_verified = stored_hash == certificate.certificate_hash
        certificate.is_verified = is_verified
        certificate.save()
        
        return JsonResponse({
            'verified': is_verified,
            'stored_hash': stored_hash,
            'certificate_hash': certificate.certificate_hash
        })
    except Exception as e:
        return JsonResponse({
            'verified': False,
            'error': str(e)
        }, status=500)

@ensure_csrf_cookie
def verify_certificate_page(request):
    order_id = request.GET.get('order_id')
    hash_value = request.GET.get('hash')
    
    return render(request, 'watch_customizer/verify_certificate.html', {
        'order_id': order_id,
        'hash': hash_value
    })

@require_POST
def verify_certificate_public(request):
    """Public API endpoint for certificate verification"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        certificate_hash = data.get('certificate_hash')

        if not order_id or not certificate_hash:
            return JsonResponse({
                'verified': False,
                'error': 'Order ID and Certificate Hash are required'
            }, status=400)

        # Try to find the certificate in database
        try:
            certificate = WatchCertificate.objects.select_related('order').get(
                order__order_id=order_id,
                certificate_hash=certificate_hash
            )
        except WatchCertificate.DoesNotExist:
            return JsonResponse({
                'verified': False,
                'error': 'Certificate not found'
            }, status=404)

        try:
            # Connect to local blockchain
            w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))  # Local Ganache URL
            
            if not w3.is_connected():
                return JsonResponse({
                    'verified': False,
                    'error': 'Blockchain network is currently unavailable'
                }, status=503)

            # Get the stored hash from blockchain
            contract = w3.eth.contract(
                address=settings.CERTIFICATE_CONTRACT_ADDRESS,
                abi=settings.CERTIFICATE_CONTRACT_ABI
            )
            
            stored_hash = contract.functions.getCertificate(str(order_id)).call()
            
            is_verified = stored_hash == certificate_hash
            if certificate.is_metamask_verified == False:
                is_verified = False
            print(is_verified)

            return JsonResponse({
                'verified': is_verified,
                'certificate': {
                    'order_id': certificate.order.order_id,
                    'issue_date': certificate.issued_date.strftime('%B %d, %Y'),
                    'tx_hash': certificate.blockchain_tx_hash or 'Pending',
                    'stored_hash': stored_hash
                }
            })

        except Exception as e:
            logger.error(f"Blockchain verification error: {str(e)}")
            return JsonResponse({
                'verified': False,
                'error': 'Unable to verify on blockchain. Please ensure local blockchain is running.'
            }, status=503)

    except json.JSONDecodeError:
        return JsonResponse({
            'verified': False,
            'error': 'Invalid request data'
        }, status=400)
    except Exception as e:
        logger.error(f"Certificate verification error: {str(e)}")
        return JsonResponse({
            'verified': False,
            'error': str(e)
        }, status=500)
