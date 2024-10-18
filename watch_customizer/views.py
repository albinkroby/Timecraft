from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import CustomizableWatch, CustomizableWatchPart, CustomWatchSavedDesign, CustomWatchOrder, CustomWatchOrderPart
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
    total_price = design.customizable_watch.base_price
    
    if isinstance(design.design_data, str):
        try:
            design_data = json.loads(design.design_data)
        except json.JSONDecodeError:
            design_data = []
    else:
        design_data = design.design_data

    for part_data in design_data:
        if isinstance(part_data, dict) and 'price' in part_data:
            total_price += float(part_data['price'])

    # Create CustomWatchOrder
    with transaction.atomic():
        custom_order = CustomWatchOrder.objects.create(
            user=request.user,
            customizable_watch=design,
            address=primary_address,
            total_price=total_price,
            status='pending'
        )
        for part_data in design_data:
            if isinstance(part_data, dict) and 'part_id' in part_data and 'option_id' in part_data:
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
        'final_total': total_price,
        'total_savings': 0,
        'design_data': design_data,
        'custom_order_id': custom_order.id,
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
        return render(request, 'watch_customizer/custom_payment_success.html', {'paid': False, 'error': 'No session ID provided.'})

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            custom_order = CustomWatchOrder.objects.filter(stripe_session_id=session_id).first()
            if custom_order:
                # Send order confirmation email
                send_custom_order_confirmation_email(custom_order, request)
                return render(request, 'watch_customizer/custom_payment_success.html', {'paid': True, 'order': custom_order})
            else:
                return render(request, 'watch_customizer/custom_payment_success.html', {'paid': False, 'error': 'Order not found.'})
        else:
            return render(request, 'watch_customizer/custom_payment_success.html', {'paid': False, 'error': 'Payment not successful. Please try again or contact support.'})
    except stripe.error.InvalidRequestError:
        return render(request, 'watch_customizer/custom_payment_success.html', {'paid': False, 'error': 'Invalid session ID. Please contact support if this persists.'})
    except stripe.error.StripeError as e:
        return render(request, 'watch_customizer/custom_payment_success.html', {'paid': False, 'error': f'An error occurred: {str(e)}. Please contact support.'})
    except Exception as e:
        return render(request, 'watch_customizer/custom_payment_success.html', {'paid': False, 'error': f'An unexpected error occurred: {str(e)}. Please contact support.'})

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
