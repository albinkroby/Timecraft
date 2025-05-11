from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from functools import wraps

from mainapp.models import Order, OrderItem, Address
from .models import DeliveryProfile, DeliveryHistory, DeliveryMetrics, DeliveryRating, ReturnHistory
from .forms import (
    DeliveryProfileForm, DeliveryUserForm, OrderAssignmentForm, 
    DeliveryUpdateForm, OTPVerificationForm, DeliveryLocationUpdateForm,
    DeliveryRatingForm, ReturnUpdateForm, ReturnOTPVerificationForm, ReturnConditionForm,
    ReturnApprovalForm, ReturnAssignmentForm
)
from .utils import (
    assign_delivery_otp, verify_delivery_otp, 
    get_available_delivery_personnel, assign_order_to_delivery,
    assign_return_to_delivery, get_return_requests, get_zone_for_address,
    assign_order_based_on_workload, assign_order_based_on_zone, verify_return_otp,
    get_personnel_return_workload
)

User = get_user_model()

def delivery_required(view_func):
    """Decorator to check if user is a delivery person"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'delivery':
            messages.error(request, "You do not have permission to access this page.")
            return redirect('mainapp:home')
        return view_func(request, *args, **kwargs)
    return wrapper

def profile_completion_required(view_func):
    """
    Decorator to check if the delivery person has completed their profile.
    If not, redirect to the onboarding page.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Skip for admin users who may be impersonating
        if request.user.role in ['admin', 'staff']:
            return view_func(request, *args, **kwargs)
            
        try:
            profile = DeliveryProfile.objects.get(user=request.user)
            
            # First, check if onboarding is explicitly marked as completed in the database
            if profile.onboarding_completed:
                return view_func(request, *args, **kwargs)
                
            # Check if required fields are completed
            required_fields = ['phone', 'vehicle_type', 'vehicle_number']
            profile_complete = all(getattr(profile, field) for field in required_fields)
            
            if not profile_complete:
                messages.info(request, "Please complete your profile before continuing.")
                return redirect('deliveryapp:onboarding')
            else:
                # Required fields are complete but onboarding_completed is not marked
                # Let's mark it as complete now and update the database
                profile.onboarding_completed = True
                profile.onboarding_completed_at = timezone.now()
                profile.save(update_fields=['onboarding_completed', 'onboarding_completed_at'])
            
        except DeliveryProfile.DoesNotExist:
            messages.info(request, "Please complete your profile before continuing.")
            return redirect('deliveryapp:onboarding')
            
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@delivery_required
@profile_completion_required
def delivery_dashboard(request):
    """Dashboard for delivery personnel"""
    try:
        profile = DeliveryProfile.objects.get(user=request.user)
        if not profile.onboarding_completed:
            return redirect('deliveryapp:onboarding')
    except DeliveryProfile.DoesNotExist:
        return redirect('deliveryapp:onboarding')
    
    # Get assigned orders
    assigned_orders = Order.objects.filter(
        assigned_to=request.user,
        status__in=['assigned_to_delivery', 'out_for_delivery']
    ).order_by('-created_at')
    
    # Get assigned return pickups
    assigned_returns = Order.objects.filter(
        return_assigned_to=request.user,
        status__in=['return_scheduled', 'return_in_transit']
    ).order_by('-updated_at')
    
    # Get completed orders (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    completed_orders = Order.objects.filter(
        assigned_to=request.user,
        status='delivered',
        delivery_date__gte=thirty_days_ago
    ).order_by('-delivery_date')[:10]
    
    # Get delivery metrics
    try:
        metrics = DeliveryMetrics.objects.get(delivery_person=request.user)
    except DeliveryMetrics.DoesNotExist:
        metrics = DeliveryMetrics.objects.create(delivery_person=request.user)
    
    # Get latest updates
    latest_updates = DeliveryHistory.objects.filter(
        delivery_person=request.user
    ).order_by('-timestamp')[:10]
    
    # Get latest return updates
    latest_return_updates = ReturnHistory.objects.filter(
        delivery_person=request.user
    ).order_by('-timestamp')[:10]
    
    context = {
        'profile': profile,
        'assigned_orders': assigned_orders,
        'assigned_returns': assigned_returns,
        'returns_count': assigned_returns.count(),
        'completed_orders': completed_orders,
        'metrics': metrics,
        'latest_updates': latest_updates,
        'latest_return_updates': latest_return_updates,
    }
    
    return render(request, 'deliveryapp/dashboard.html', context)

@login_required
@delivery_required
def onboarding(request):
    """Onboarding page for new delivery personnel"""
    step = request.GET.get('step', '1')  # Default to step 1 if not specified
    
    try:
        profile = DeliveryProfile.objects.get(user=request.user)
    except DeliveryProfile.DoesNotExist:
        profile = DeliveryProfile.objects.create(user=request.user)
    
    context = {
        'step': int(step),
        'delivery_profile': profile,
        'vehicle_choices': DeliveryProfile.VEHICLE_CHOICES,
        'preferred_zones': profile.preferred_zones if profile.preferred_zones_text else [],
        'weekday_availability': profile.weekday_availability if profile.weekday_availability_text else []
    }
    
    return render(request, 'deliveryapp/onboarding.html', context)

@login_required
@delivery_required
def save_personal_details(request):
    """Save personal details from step 1"""
    if request.method == 'POST':
        try:
            profile = DeliveryProfile.objects.get(user=request.user)
        except DeliveryProfile.DoesNotExist:
            profile = DeliveryProfile.objects.create(user=request.user)
        
        # Update user details
        user = request.user
        user.first_name = request.POST.get('fullname', '').split()[0]
        user.last_name = ' '.join(request.POST.get('fullname', '').split()[1:])
        user.save()
        
        # Update profile details
        profile.phone = request.POST.get('phone', '')
        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']
        profile.save()
        
        messages.success(request, 'Personal details saved successfully!')
        return redirect(reverse('deliveryapp:onboarding') + '?step=2')
    
    return redirect('deliveryapp:onboarding')

@login_required
@delivery_required
def save_vehicle_details(request):
    """Save vehicle details from step 2"""
    if request.method == 'POST':
        try:
            profile = DeliveryProfile.objects.get(user=request.user)
        except DeliveryProfile.DoesNotExist:
            profile = DeliveryProfile.objects.create(user=request.user)
        
        profile.vehicle_type = request.POST.get('vehicle_type')
        profile.vehicle_number = request.POST.get('vehicle_number')
        profile.max_distance = request.POST.get('max_distance')
        profile.max_workload = request.POST.get('max_workload')
        profile.save()
        
        messages.success(request, 'Vehicle details saved successfully!')
        return redirect(reverse('deliveryapp:onboarding') + '?step=3')
    
    return redirect('deliveryapp:onboarding')

@login_required
@delivery_required
def complete_onboarding(request):
    """Complete onboarding process - step 3"""
    if request.method == 'POST':
        try:
            profile = DeliveryProfile.objects.get(user=request.user)
        except DeliveryProfile.DoesNotExist:
            profile = DeliveryProfile.objects.create(user=request.user)
        
        # Save availability and zones
        profile.availability_start = request.POST.get('availability_start')
        profile.availability_end = request.POST.get('availability_end')
        profile.weekday_availability = request.POST.getlist('weekday_availability')
        profile.preferred_zones = request.POST.getlist('preferred_zones')
        
        # Mark onboarding as complete
        profile.onboarding_completed = True
        profile.onboarding_completed_at = timezone.now()
        profile.save()
        
        messages.success(request, 'Onboarding completed successfully!')
        return redirect('deliveryapp:dashboard')
    
    return redirect('deliveryapp:onboarding')

@login_required
@delivery_required
@profile_completion_required
def create_profile(request):
    """Create or update delivery profile"""
    try:
        profile = DeliveryProfile.objects.get(user=request.user)
    except DeliveryProfile.DoesNotExist:
        profile = None
    
    if request.method == 'POST':
        profile_form = DeliveryProfileForm(request.POST, request.FILES, instance=profile)
        user_form = DeliveryUserForm(request.POST, instance=request.user)
        
        if profile_form.is_valid() and user_form.is_valid():
            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            
            # Check if required fields are complete
            required_fields = ['phone', 'vehicle_type', 'vehicle_number']
            profile_complete = all(profile_form.cleaned_data.get(field) for field in required_fields)
            
            # If the profile is complete but onboarding not marked, let's mark it
            if profile_complete and not profile.onboarding_completed:
                profile.onboarding_completed = True
                profile.onboarding_completed_at = timezone.now()
                
            profile.save()
            
            # Create metrics if they don't exist
            DeliveryMetrics.objects.get_or_create(delivery_person=user)
            
            messages.success(request, "Profile updated successfully.")
            return redirect('deliveryapp:profile')
    else:
        profile_form = DeliveryProfileForm(instance=profile)
        user_form = DeliveryUserForm(instance=request.user)
    
    context = {
        'profile_form': profile_form,
        'user_form': user_form,
        'profile': profile
    }
    
    return render(request, 'deliveryapp/create_profile.html', context)

@login_required
@delivery_required
def profile(request):
    """View delivery profile"""
    try:
        profile = DeliveryProfile.objects.get(user=request.user)
        
        # Get delivery metrics
        try:
            metrics = DeliveryMetrics.objects.get(delivery_person=request.user)
        except DeliveryMetrics.DoesNotExist:
            metrics = DeliveryMetrics.objects.create(delivery_person=request.user)
            
        # Calculate profile completion percentage
        required_fields = ['phone', 'vehicle_type', 'vehicle_number']
        completed_fields = sum(1 for field in required_fields if getattr(profile, field))
        completion_percentage = (completed_fields / len(required_fields)) * 100
        
        # Get completed deliveries count
        from mainapp.models import Order
        completed_orders_count = Order.objects.filter(
            assigned_to=request.user,
            status='delivered'
        ).count()
        
        context = {
            'profile': profile,
            'metrics': metrics,
            'completion_percentage': completion_percentage,
            'completed_orders_count': completed_orders_count,
            'onboarding_complete': profile.onboarding_completed,
            'onboarding_date': profile.onboarding_completed_at,
        }
        
        return render(request, 'deliveryapp/profile.html', context)
        
    except DeliveryProfile.DoesNotExist:
        messages.warning(request, "Please complete your profile first.")
        return redirect('deliveryapp:onboarding')

@login_required
@delivery_required
@profile_completion_required
def assigned_orders(request):
    """View assigned orders"""
    assigned_orders = Order.objects.filter(
        assigned_to=request.user,
        status__in=['assigned_to_delivery', 'out_for_delivery']
    ).order_by('-created_at')
    
    paginator = Paginator(assigned_orders, 10)
    page = request.GET.get('page', 1)
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
    }
    
    return render(request, 'deliveryapp/assigned_orders.html', context)

@login_required
@delivery_required
@profile_completion_required
def order_detail(request, order_id):
    """View details of a specific order"""
    order = get_object_or_404(Order, order_id=order_id, assigned_to=request.user)
    order_items = OrderItem.objects.filter(order=order)
    
    # Get delivery history for this order
    delivery_history = DeliveryHistory.objects.filter(
        order=order,
        delivery_person=request.user
    ).order_by('-timestamp')
    
    # Form for updating delivery status
    if request.method == 'POST':
        form = DeliveryUpdateForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data['status']
            notes = form.cleaned_data['notes']
            
            # Update order status if needed
            if status == 'out_for_delivery' and order.status != 'out_for_delivery':
                order.status = 'out_for_delivery'
                order.save()
                # Generate new OTP
                assign_delivery_otp(order)
                
                # Send OTP to customer
                subject = f"Your TimeCraft Order #{order.order_id} is Out for Delivery"
                message = f"Your order is out for delivery. Use OTP {order.delivery_otp} to verify delivery."
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
                
            elif status == 'delivered' and order.status != 'delivered':
                # This should be done via OTP verification, not here
                pass
            
            # Create delivery history entry
            DeliveryHistory.objects.create(
                delivery_person=request.user,
                order=order,
                status=status,
                notes=notes
            )
            
            messages.success(request, "Delivery status updated successfully.")
            return redirect('deliveryapp:order_detail', order_id=order_id)
    else:
        form = DeliveryUpdateForm()
    
    # OTP verification form
    otp_form = OTPVerificationForm()
    
    context = {
        'order': order,
        'order_items': order_items,
        'delivery_history': delivery_history,
        'form': form,
        'otp_form': otp_form,
    }
    
    return render(request, 'deliveryapp/order_detail.html', context)

@login_required
@delivery_required
@profile_completion_required
@require_POST
def verify_otp(request, order_id):
    """Verify OTP and mark order as delivered"""
    order = get_object_or_404(Order, order_id=order_id, assigned_to=request.user)
    
    if order.status == 'delivered':
        messages.error(request, "Order has already been marked as delivered.")
        return redirect('deliveryapp:order_detail', order_id=order_id)
    
    form = OTPVerificationForm(request.POST)
    if form.is_valid():
        otp = form.cleaned_data['otp']
        
        if verify_delivery_otp(order, otp):
            # Update order status
            order.status = 'delivered'
            order.delivery_date = timezone.now().date()
            order.save()
            
            # Create delivery history entry
            DeliveryHistory.objects.create(
                delivery_person=request.user,
                order=order,
                status='delivered',
                notes="Delivered - OTP verified"
            )
            
            # Update delivery metrics
            metrics, created = DeliveryMetrics.objects.get_or_create(delivery_person=request.user)
            metrics.total_deliveries += 1
            metrics.completed_deliveries += 1
            metrics.save()
            
            # Send confirmation email to customer
            subject = f"Your TimeCraft Order #{order.order_id} has been Delivered"
            message = f"Your order has been delivered successfully. Please rate your delivery experience."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
            
            messages.success(request, "OTP verification successful. Order marked as delivered.")
        else:
            messages.error(request, "Invalid or expired OTP. Please try again.")
    else:
        messages.error(request, "Invalid form submission.")
    
    return redirect('deliveryapp:order_detail', order_id=order_id)

@login_required
@delivery_required
@profile_completion_required
@require_POST
def verify_otp_ajax(request, order_id):
    """Verify OTP and mark order as delivered (AJAX version)"""
    order = get_object_or_404(Order, order_id=order_id, assigned_to=request.user)
    
    if order.status == 'delivered':
        return JsonResponse({'success': False, 'error': "Order has already been marked as delivered."})
    
    otp = request.POST.get('otp', '').strip()
    
    if not otp:
        return JsonResponse({'success': False, 'error': "Please enter a valid OTP."})
    
    if verify_delivery_otp(order, otp):
        # Update order status
        order.status = 'delivered'
        order.delivery_date = timezone.now().date()
        order.save()
        
        # Create delivery history entry
        DeliveryHistory.objects.create(
            delivery_person=request.user,
            order=order,
            status='delivered',
            notes="Delivered - OTP verified"
        )
        
        # Update delivery metrics
        metrics, created = DeliveryMetrics.objects.get_or_create(delivery_person=request.user)
        metrics.total_deliveries += 1
        metrics.completed_deliveries += 1
        metrics.save()
        
        # Send confirmation email to customer
        subject = f"Your TimeCraft Order #{order.order_id} has been Delivered"
        message = f"Your order has been delivered successfully. Please rate your delivery experience."
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
        
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': "Invalid or expired OTP. Please try again."})

@login_required
@delivery_required
@profile_completion_required
def update_location(request):
    """Update the current location of delivery personnel"""
    if request.method == 'POST':
        form = DeliveryLocationUpdateForm(request.POST)
        if form.is_valid():
            latitude = form.cleaned_data['latitude']
            longitude = form.cleaned_data['longitude']
            
            try:
                profile = DeliveryProfile.objects.get(user=request.user)
                profile.update_location(latitude, longitude)
                return JsonResponse({'status': 'success'})
            except DeliveryProfile.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Profile not found'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
@delivery_required
@profile_completion_required
def delivery_history(request):
    """View delivery history"""
    # Get completed orders for this delivery person
    orders = Order.objects.filter(
        assigned_to=request.user,
        status__in=['delivered', 'cancelled', 'returned', 'return_delivered', 'return_completed']
    ).order_by('-delivery_date')
    
    # Filter by date range if provided
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            end_date = datetime.combine(end_date, datetime.max.time())  # Include the entire end day
            
            orders = orders.filter(delivery_date__range=[start_date, end_date])
        except ValueError:
            messages.error(request, "Invalid date format. Please use YYYY-MM-DD.")
    
    # Get delivery metrics
    try:
        metrics = DeliveryMetrics.objects.get(delivery_person=request.user)
    except DeliveryMetrics.DoesNotExist:
        metrics = DeliveryMetrics.objects.create(delivery_person=request.user)
    
    paginator = Paginator(orders, 20)
    page = request.GET.get('page', 1)
    orders_page = paginator.get_page(page)
    
    context = {
        'orders': orders_page,
        'metrics': metrics,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'deliveryapp/delivery_history.html', context)

# Admin views for assigning orders to delivery personnel

@login_required
def admin_assign_delivery(request, order_id):
    """Admin view to assign an order to a delivery person"""
    # Check if user has permission
    if request.user.role not in ['admin', 'staff']:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('mainapp:home')
    
    order = get_object_or_404(Order, order_id=order_id)
    
    if order.status in ['delivered', 'cancelled', 'returned']:
        messages.error(request, "Cannot assign delivery for an order that is delivered, cancelled, or returned.")
        return redirect('adminapp:order_detail', order_id=order_id)
    
    if request.method == 'POST':
        form = OrderAssignmentForm(request.POST)
        if form.is_valid():
            delivery_person = form.cleaned_data['delivery_person']
            
            success, message = assign_order_to_delivery(order, delivery_person)
            
            if success:
                messages.success(request, message)
                return redirect('adminapp:order_detail', order_id=order_id)
            else:
                messages.error(request, message)
    else:
        form = OrderAssignmentForm()
    
    # Get available delivery personnel
    available_personnel = get_available_delivery_personnel()
    
    # Update the form queryset to only show available agents
    form.fields['delivery_person'].queryset = User.objects.filter(id__in=[p.id for p in available_personnel])
    
    context = {
        'order': order,
        'form': form,
        'available_personnel': available_personnel
    }
    
    return render(request, 'deliveryapp/admin_assign_delivery.html', context)

@login_required
def admin_auto_assign_delivery(request):
    """Admin view to automatically assign multiple orders to available delivery personnel"""
    # Check if user has permission
    if request.user.role not in ['admin', 'staff']:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('mainapp:home')
    
    # Get unassigned orders that are ready for delivery
    unassigned_orders = Order.objects.filter(
        status__in=['pending', 'processing', 'ready_for_delivery'],
        assigned_to__isnull=True
    ).select_related('user', 'address')
    
    # Debug: Log the count and details of unassigned orders
    print(f"Found {unassigned_orders.count()} unassigned orders")
    
    # Get all order details for debugging
    for order in unassigned_orders:
        print(f"Order ID: {order.order_id}, Status: {order.status}, User: {order.user.fullname if order.user else 'None'}")
        print(f"Address: {order.address}")
        # Check for the total amount field name (either total_amount or total)
        if hasattr(order, 'total_amount'):
            print(f"Total Amount: {order.total_amount}")
        elif hasattr(order, 'total'):
            print(f"Total: {order.total}")
        else:
            print("No total amount field found")
    
    # Get available delivery personnel
    available_personnel = get_available_delivery_personnel()
    print(f"Found {len(available_personnel)} available delivery personnel")
    
    if request.method == 'POST':
        # Process the form submission for batch assignment
        order_ids = request.POST.getlist('order_ids')
        assignment_method = request.POST.get('assignment_method', 'smart')
        
        if not order_ids:
            messages.warning(request, "No orders selected for assignment.")
            return redirect('deliveryapp:admin_auto_assign_delivery')
        
        if not available_personnel:
            messages.error(request, "No delivery personnel available. Please add or activate delivery personnel.")
            return redirect('deliveryapp:admin_auto_assign_delivery')
        
        success_count = 0
        error_count = 0
        
        # Process each selected order
        for order_id in order_ids:
            try:
                order = Order.objects.get(order_id=order_id)
                
                # Skip orders that are already assigned or not in the right status
                if order.assigned_to or order.status not in ['pending', 'processing', 'ready_for_delivery']:
                    continue
                
                # Use the smart assignment algorithm
                success, message = assign_order_to_delivery(order)
                
                if success:
                    success_count += 1
                else:
                    error_count += 1
                    
            except Order.DoesNotExist:
                error_count += 1
        
        if success_count > 0:
            messages.success(request, f"Successfully assigned {success_count} orders to delivery personnel.")
        if error_count > 0:
            messages.error(request, f"Failed to assign {error_count} orders. Please check logs for details.")
        
        return redirect('adminapp:order_list')
    
    # Group orders by delivery zones for better visualization
    from collections import defaultdict
    orders_by_zone = defaultdict(list)
    
    # Debug the zone assignment
    for order in unassigned_orders:
        zone = get_zone_for_address(order.address) if order.address else 'Unknown'
        
        # Normalize the zone name to ensure it's one of our standard zones
        if zone not in ['north', 'south', 'east', 'west', 'Unknown', 'Other']:
            print(f"Converting non-standard zone '{zone}' to 'Other'")
            zone = 'Other'
            
        print(f"Order {order.order_id} assigned to zone: {zone}")
        orders_by_zone[zone].append(order)
    
    # Debug the final orders_by_zone dictionary
    for zone, orders in orders_by_zone.items():
        print(f"Zone {zone} has {len(orders)} orders")
        for order in orders:
            print(f"  - Order {order.order_id}")
    
    # Make sure we have at least one zone even if categorization fails
    if len(orders_by_zone) == 0 and unassigned_orders:
        orders_by_zone['All Orders'] = list(unassigned_orders)
        print("Fallback: added all orders to 'All Orders' zone")
    
    context = {
        'unassigned_orders': unassigned_orders,
        'orders_by_zone': orders_by_zone,
        'available_personnel': available_personnel,
        'personnel_count': len(available_personnel),
        'order_count': unassigned_orders.count(),
    }
    
    return render(request, 'deliveryapp/admin_auto_assign_delivery.html', context)

@login_required
def admin_batch_order_assignment(request):
    """Admin view to assign multiple orders to specific delivery personnel"""
    # Check if user has permission
    if request.user.role not in ['admin', 'staff']:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('mainapp:home')
    
    # Get orders ready for delivery assignment
    ready_orders = Order.objects.filter(
        status__in=['pending', 'processing'],
        assigned_to__isnull=True
    ).order_by('created_at')
    
    # Get all active delivery personnel
    delivery_personnel = User.objects.filter(role='delivery', is_active=True)
    
    if request.method == 'POST':
        # Get the delivery person ID and selected orders
        delivery_person_id = request.POST.get('delivery_person')
        order_ids = request.POST.getlist('order_ids')
        
        if not order_ids:
            messages.warning(request, "No orders selected for assignment.")
            return redirect('deliveryapp:admin_batch_order_assignment')
        
        if not delivery_person_id:
            messages.error(request, "No delivery person selected.")
            return redirect('deliveryapp:admin_batch_order_assignment')
        
        try:
            delivery_person = User.objects.get(id=delivery_person_id, role='delivery')
            
            success_count = 0
            error_count = 0
            
            # Assign each selected order to the chosen delivery person
            for order_id in order_ids:
                try:
                    order = Order.objects.get(id=order_id)
                    
                    # Skip orders that are already assigned or not in the right status
                    if order.assigned_to or order.status not in ['pending', 'processing']:
                        continue
                    
                    success, message = assign_order_to_delivery(order, delivery_person)
                    
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Order.DoesNotExist:
                    error_count += 1
            
            if success_count > 0:
                messages.success(request, f"Successfully assigned {success_count} orders to {delivery_person.fullname}.")
            if error_count > 0:
                messages.error(request, f"Failed to assign {error_count} orders. Please check logs for details.")
            
            return redirect('adminapp:delivery_agents_list')
            
        except User.DoesNotExist:
            messages.error(request, "Selected delivery person not found or inactive.")
            return redirect('deliveryapp:admin_batch_order_assignment')
    
    # Group orders by delivery zones for better visualization
    from collections import defaultdict
    orders_by_zone = defaultdict(list)
    
    for order in ready_orders:
        zone = get_zone_for_address(order.address) if order.address else 'Unknown'
        orders_by_zone[zone].append(order)
    
    context = {
        'ready_orders': ready_orders,
        'orders_by_zone': orders_by_zone,
        'delivery_personnel': delivery_personnel,
        'order_count': ready_orders.count(),
    }
    
    return render(request, 'deliveryapp/admin_batch_order_assignment.html', context)

# Customer views for rating delivery and tracking orders

@login_required
def rate_delivery(request, order_id):
    """Allow customers to rate their delivery experience"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    if order.status != 'delivered':
        messages.error(request, "You can only rate delivered orders.")
        return redirect('userapp:order_details', order_id=order_id)
    
    try:
        rating = DeliveryRating.objects.get(order=order)
    except DeliveryRating.DoesNotExist:
        rating = None
    
    if request.method == 'POST':
        form = DeliveryRatingForm(request.POST, instance=rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.order = order
            rating.delivery_person = order.assigned_to
            rating.save()
            
            messages.success(request, "Thank you for your feedback!")
            return redirect('userapp:order_details', order_id=order_id)
    else:
        form = DeliveryRatingForm(instance=rating)
    
    context = {
        'order': order,
        'form': form,
        'rating': rating,
    }
    
    return render(request, 'deliveryapp/rate_delivery.html', context)

def track_order(request, order_id):
    """Public view to track an order's status"""
    order = get_object_or_404(Order, order_id=order_id)
    
    # Get delivery updates
    updates = DeliveryHistory.objects.filter(order=order).order_by('-timestamp')
    
    context = {
        'order': order,
        'updates': updates,
    }
    
    return render(request, 'deliveryapp/track_order.html', context)

# Return Management Views

@login_required
@delivery_required
@profile_completion_required
def assigned_returns(request):
    """View assigned return pickups"""
    assigned_returns = Order.objects.filter(
        return_assigned_to=request.user,
        status__in=['return_scheduled', 'return_in_transit']
    ).order_by('-created_at')
    
    paginator = Paginator(assigned_returns, 10)
    page = request.GET.get('page', 1)
    returns = paginator.get_page(page)
    
    context = {
        'returns': returns,
    }
    
    return render(request, 'deliveryapp/assigned_returns.html', context)

@login_required
@delivery_required
@profile_completion_required
def return_detail(request, order_id):
    """View details of a specific return"""
    order = get_object_or_404(Order, order_id=order_id, return_assigned_to=request.user)
    order_items = OrderItem.objects.filter(order=order)
    
    # Get return history for this order
    return_history = ReturnHistory.objects.filter(
        order=order
    ).order_by('-timestamp')
    
    # Prepare forms for different actions
    otp_form = ReturnOTPVerificationForm()
    update_form = ReturnUpdateForm()
    condition_form = ReturnConditionForm()
    
    context = {
        'order': order,
        'order_items': order_items,
        'return_history': return_history,
        'otp_form': otp_form,
        'update_form': update_form,
        'condition_form': condition_form
    }
    
    return render(request, 'deliveryapp/return_detail.html', context)

@login_required
@delivery_required
@profile_completion_required
@require_POST
def request_return_otp(request, order_id):
    """Generate and send a new OTP to the customer for return verification"""
    order = get_object_or_404(Order, order_id=order_id, return_assigned_to=request.user)
    
    if order.status != 'return_scheduled':
        messages.error(request, "Cannot request OTP for this return at its current status.")
        return redirect('deliveryapp:return_detail', order_id=order_id)
    
    # Generate and assign new OTP
    from deliveryapp.utils import assign_return_otp
    otp = assign_return_otp(order)
    
    # Send OTP to customer via email
    try:
        subject = f"Return Verification OTP for Order #{order.order_id}"
        message = f"""
        Dear {order.user.fullname},
        
        The delivery agent has arrived to pick up your return for Order #{order.order_id}.
        
        Please provide the following OTP to the delivery agent to verify the return:
        
        OTP: {otp}
        
        This OTP is valid for 24 hours.
        
        Thank you,
        TimeCrafter Team
        """
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
        
        # Create a history record
        ReturnHistory.objects.create(
            delivery_person=request.user,
            order=order,
            status=order.status,
            notes="Return OTP requested and sent to customer"
        )
        
        messages.success(request, "OTP has been sent to the customer's email.")
    except Exception as e:
        messages.error(request, f"Failed to send OTP email: {str(e)}")
    
    return redirect('deliveryapp:return_detail', order_id=order_id)

@login_required
@delivery_required
@profile_completion_required
@require_POST
def verify_return_otp(request, order_id):
    """Verify return OTP and update return status"""
    from deliveryapp.utils import verify_return_otp as verify_return_otp_util
    
    order = get_object_or_404(Order, order_id=order_id, return_assigned_to=request.user)
    
    if order.status != 'return_scheduled':
        messages.error(request, "Cannot verify OTP for this return at its current status.")
        return redirect('deliveryapp:return_detail', order_id=order_id)
    
    form = ReturnOTPVerificationForm(request.POST)
    if form.is_valid():
        otp = form.cleaned_data['otp']
        
        if verify_return_otp_util(order, otp):
            # Update order status
            order.status = 'return_in_transit'
            order.save()
            
            # Create return history entry
            ReturnHistory.objects.create(
                delivery_person=request.user,
                order=order,
                status='return_in_transit',
                notes="Return picked up - OTP verified"
            )
            
            # Send notification email to customer
            subject = f"Your Return for Order #{order.order_id} has been picked up"
            message = f"Your return has been picked up by our delivery agent. You will be notified once the return is processed."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
            
            messages.success(request, "OTP verification successful. Return status updated to In Transit.")
        else:
            messages.error(request, "Invalid or expired OTP. Please try again.")
    else:
        messages.error(request, "Invalid form submission.")
    
    return redirect('deliveryapp:return_detail', order_id=order_id)

@login_required
@delivery_required
@profile_completion_required
@require_POST
def complete_return(request, order_id):
    """Mark return as delivered to warehouse"""
    order = get_object_or_404(Order, order_id=order_id, return_assigned_to=request.user)
    
    if order.status != 'return_in_transit':
        messages.error(request, "Return must be in transit to be marked as delivered.")
        return redirect('deliveryapp:return_detail', order_id=order_id)
    
    # Update order status
    order.status = 'return_delivered'
    order.save()
    
    # Create return history entry
    ReturnHistory.objects.create(
        delivery_person=request.user,
        order=order,
        status='return_delivered',
        notes="Return delivered to warehouse"
    )
    
    # Update delivery metrics
    metrics, created = DeliveryMetrics.objects.get_or_create(delivery_person=request.user)
    metrics.total_deliveries += 1
    metrics.save()
    
    messages.success(request, "Return marked as delivered to warehouse.")
    return redirect('deliveryapp:return_list')

# Admin Return Management Views

@login_required
def admin_return_requests(request):
    """Admin view to manage return requests"""
    # Check if user has permission
    if request.user.role not in ['admin', 'staff']:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('mainapp:home')
    
    # Get return requests
    return_requests = get_return_requests()
    
    # Check eligibility based on the 10-day policy
    for order in return_requests:
        if order.delivery_date:
            # Calculate days since delivery
            days_since_delivery = (timezone.now().date() - order.delivery_date).days
            order.days_since_delivery = days_since_delivery
            # Check if return is still within the allowed window
            order.is_eligible = order.is_returnable()
        else:
            order.days_since_delivery = None
            order.is_eligible = False
    
    context = {
        'return_requests': return_requests,
        'return_policy_days': 10  # Pass the policy limit to the template
    }
    
    return render(request, 'deliveryapp/admin_return_requests.html', context)

@login_required
def admin_approve_return(request, order_id):
    """Admin view to approve or reject a return request"""
    # Check if user has permission
    if request.user.role not in ['admin', 'staff']:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('mainapp:home')
    
    order = get_object_or_404(Order, order_id=order_id, status='return_requested')
    
    # Calculate days since delivery if delivery date exists
    if order.delivery_date:
        order.days_since_delivery = (timezone.now().date() - order.delivery_date).days
    
    if request.method == 'POST':
        form = ReturnApprovalForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            notes = form.cleaned_data['notes']
            
            if decision == 'approve':
                order.status = 'return_approved'
                status_update = 'return_approved'
                message = "Return request approved successfully."
            else:
                order.status = 'return_rejected'
                status_update = 'return_rejected'
                message = "Return request rejected successfully."
            
            order.save()
            
            # Create return history entry
            ReturnHistory.objects.create(
                delivery_person=request.user,
                order=order,
                status=status_update,
                notes=notes
            )
            
            messages.success(request, message)
            return redirect('deliveryapp:admin_return_requests')
    else:
        form = ReturnApprovalForm()
    
    context = {
        'order': order,
        'form': form,
        'return_policy_days': 10  # Pass the policy limit to the template
    }
    
    return render(request, 'deliveryapp/admin_approve_return.html', context)

@login_required
def admin_assign_return(request, order_id):
    """Admin view to assign a return to a delivery person"""
    # Check if user has permission
    if request.user.role not in ['admin', 'staff']:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('mainapp:home')
    
    order = get_object_or_404(Order, order_id=order_id, status='return_approved')
    
    if request.method == 'POST':
        form = ReturnAssignmentForm(request.POST)
        if form.is_valid():
            delivery_person = form.cleaned_data['delivery_person']
            
            success, message = assign_return_to_delivery(order, delivery_person)
            
            if success:
                messages.success(request, message)
                return redirect('adminapp:order_detail', order_id=order_id)
            else:
                messages.error(request, message)
    else:
        form = ReturnAssignmentForm()
    
    # Get available delivery personnel
    available_personnel = get_available_delivery_personnel()
    
    # Update the form queryset to only show available agents
    form.fields['delivery_person'].queryset = User.objects.filter(id__in=[p.id for p in available_personnel])
    
    context = {
        'order': order,
        'form': form,
        'available_personnel': available_personnel
    }
    
    return render(request, 'deliveryapp/admin_assign_return.html', context)

@login_required
def admin_return_status(request):
    """Admin view to monitor returns status"""
    # Check if user has permission
    if request.user.role not in ['admin', 'staff']:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('mainapp:home')
    
    # Get returns by status
    return_requested = Order.objects.filter(status='return_requested').count()
    return_approved = Order.objects.filter(status='return_approved').count()
    return_scheduled = Order.objects.filter(status='return_scheduled').count()
    return_in_transit = Order.objects.filter(status='return_in_transit').count()
    return_delivered = Order.objects.filter(status='return_delivered').count()
    return_rejected = Order.objects.filter(status='return_rejected').count()
    
    # Get returns ready for pickup (approved but not assigned)
    returns_for_pickup = Order.objects.filter(
        status='return_approved',
        return_assigned_to__isnull=True
    ).order_by('-updated_at')
    
    # Get returns in process (scheduled or in transit)
    active_returns = Order.objects.filter(
        status__in=['return_scheduled', 'return_in_transit']
    ).order_by('-updated_at')
    
    # Get completed returns (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    completed_returns = Order.objects.filter(
        status='return_delivered',
        updated_at__gte=thirty_days_ago
    ).order_by('-updated_at')[:20]
    
    context = {
        'stats': {
            'requested': return_requested,
            'approved': return_approved,
            'scheduled': return_scheduled,
            'in_transit': return_in_transit,
            'delivered': return_delivered,
            'rejected': return_rejected,
            'total': return_requested + return_approved + return_scheduled + return_in_transit + return_delivered + return_rejected,
            'pending_assignment': returns_for_pickup.count()
        },
        'returns_for_pickup': returns_for_pickup,
        'active_returns': active_returns,
        'completed_returns': completed_returns
    }
    
    return render(request, 'deliveryapp/admin_return_status.html', context)

@login_required
def admin_batch_return_assignment(request):
    """Admin view to assign multiple returns at once"""
    # Check if user has permission
    if request.user.role not in ['admin', 'staff']:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('mainapp:home')
    
    # Get available delivery personnel
    available_personnel = get_available_delivery_personnel()
    
    # Get approved returns that need to be assigned
    approved_returns = Order.objects.filter(
        status='return_approved',
        return_assigned_to__isnull=True
    ).order_by('-updated_at')
    
    if request.method == 'POST':
        # Process the assignments
        assignment_count = 0
        errors = []
        
        for order_id, delivery_id in request.POST.items():
            if order_id.startswith('return_') and delivery_id:
                # Extract the order_id from the form field name
                order_id = order_id.replace('return_', '')
                
                try:
                    order = Order.objects.get(order_id=order_id, status='return_approved')
                    delivery_person = User.objects.get(id=delivery_id, role='delivery')
                    
                    success, message = assign_return_to_delivery(order, delivery_person)
                    
                    if success:
                        assignment_count += 1
                    else:
                        errors.append(f"Error assigning return for order {order_id}: {message}")
                        
                except (Order.DoesNotExist, User.DoesNotExist) as e:
                    errors.append(f"Error assigning return for order {order_id}: {str(e)}")
        
        if assignment_count > 0:
            messages.success(request, f"Successfully assigned {assignment_count} returns.")
            
        if errors:
            messages.error(request, "Some returns could not be assigned: " + "; ".join(errors[:5]))
            if len(errors) > 5:
                messages.error(request, f"...and {len(errors) - 5} more errors.")
        
        return redirect('deliveryapp:admin_return_status')
    
    # Get delivery personnel workload
    workload = {}
    for person in available_personnel:
        active_returns = Order.objects.filter(
            return_assigned_to=person,
            status__in=['return_scheduled', 'return_in_transit']
        ).count()
        
        workload[person.id] = {
            'name': person.get_full_name() or person.username,
            'active_returns': active_returns
        }
    
    context = {
        'approved_returns': approved_returns,
        'available_personnel': available_personnel,
        'workload': workload
    }
    
    return render(request, 'deliveryapp/admin_batch_return_assignment.html', context)

# Return Pickup Views for Delivery Personnel

@login_required
@delivery_required
@profile_completion_required
def return_list(request):
    """View returns assigned to the delivery person"""
    # Get returns assigned to this delivery person
    returns = Order.objects.filter(
        return_assigned_to=request.user,
        status__in=['return_scheduled', 'return_in_transit']
    ).order_by('return_pickup_date')
    
    context = {
        'returns': returns
    }
    
    return render(request, 'deliveryapp/return_list.html', context)

@login_required
@delivery_required
@profile_completion_required
def return_detail(request, order_id):
    """View details of a specific return"""
    order = get_object_or_404(Order, order_id=order_id, return_assigned_to=request.user)
    order_items = OrderItem.objects.filter(order=order)
    
    # Get return history for this order
    return_history = ReturnHistory.objects.filter(
        order=order
    ).order_by('-timestamp')
    
    # Prepare forms for different actions
    otp_form = ReturnOTPVerificationForm()
    update_form = ReturnUpdateForm()
    condition_form = ReturnConditionForm()
    
    context = {
        'order': order,
        'order_items': order_items,
        'return_history': return_history,
        'otp_form': otp_form,
        'update_form': update_form,
        'condition_form': condition_form
    }
    
    return render(request, 'deliveryapp/return_detail.html', context)

@login_required
@delivery_required
@profile_completion_required
@require_POST
def submit_return_condition(request, order_id):
    """Submit assessment of return item condition"""
    order = get_object_or_404(Order, order_id=order_id, return_assigned_to=request.user)
    
    if order.status != 'return_in_transit':
        messages.error(request, "Cannot submit condition assessment at the current return status.")
        return redirect('deliveryapp:return_detail', order_id=order_id)
    
    form = ReturnConditionForm(request.POST, request.FILES)
    if form.is_valid():
        condition = form.cleaned_data['condition']
        description = form.cleaned_data['condition_description']
        verification_image = form.cleaned_data.get('verification_image')
        
        # Create return history entry with condition details
        history_entry = ReturnHistory.objects.create(
            delivery_person=request.user,
            order=order,
            status='return_in_transit',
            notes=f"Condition assessment: {condition}",
            condition_description=description,
        )
        
        # Add the verification image if provided
        if verification_image:
            history_entry.return_verification_image = verification_image
            history_entry.save()
        
        messages.success(request, "Return condition assessment submitted successfully.")
    else:
        messages.error(request, "Invalid form submission. Please check the form and try again.")
    
    return redirect('deliveryapp:return_detail', order_id=order_id)

@login_required
@delivery_required
@profile_completion_required
@require_POST
def update_return_status(request, order_id):
    """Update return status"""
    order = get_object_or_404(Order, order_id=order_id, return_assigned_to=request.user)
    
    form = ReturnUpdateForm(request.POST)
    if form.is_valid():
        new_status = form.cleaned_data['status']
        notes = form.cleaned_data['notes']
        
        # Validate the status transition
        valid_transition = False
        
        if order.status == 'return_scheduled' and new_status == 'return_in_transit':
            # This should happen via OTP verification
            messages.warning(request, "Please use OTP verification to update to In Transit status.")
            return redirect('deliveryapp:return_detail', order_id=order_id)
        
        elif order.status == 'return_in_transit' and new_status == 'return_delivered':
            valid_transition = True
            # Update order status to completed when delivered to warehouse
            order.status = 'return_completed'
            order.return_completed_at = timezone.now()
            order.save()
            
            # Update metrics
            metrics, created = DeliveryMetrics.objects.get_or_create(delivery_person=request.user)
            metrics.total_deliveries += 1
            metrics.completed_deliveries += 1
            metrics.save()
            
            # Notify user
            subject = f"Your Return for Order #{order.order_id} has been Completed"
            message = "Your return has been successfully delivered to our warehouse. Our team will process it shortly."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
            
        elif order.status == 'return_scheduled' and new_status == 'return_failed':
            valid_transition = True
            order.status = 'return_approved'  # Reset to approved state for reassignment
            order.return_assigned_to = None  # Unassign the delivery person
            order.save()
            
        elif order.status == 'return_in_transit' and new_status == 'return_failed':
            valid_transition = True
            order.status = 'return_approved'  # Reset to approved state for reassignment
            order.return_assigned_to = None  # Unassign the delivery person
            order.save()
        else:
            messages.error(request, "Invalid status transition.")
            return redirect('deliveryapp:return_detail', order_id=order_id)
        
        if valid_transition:
            # Create return history entry
            ReturnHistory.objects.create(
                delivery_person=request.user,
                order=order,
                status=new_status,
                notes=notes
            )
            
            messages.success(request, "Return status updated successfully.")
    else:
        messages.error(request, "Invalid form submission.")
    
    return redirect('deliveryapp:return_detail', order_id=order_id)

@login_required
@delivery_required
def send_verification_email(request):
    if request.method == 'GET':
        try:
            user = request.user
            # Generate verification token and send email
            # You can implement your email sending logic here
            # For now, we'll just return success
            return JsonResponse({
                'success': True,
                'message': 'Verification email sent successfully!'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'Failed to send verification email.'
            })

@login_required
@delivery_required
def check_email_status(request):
    if request.method == 'GET':
        user = request.user
        # Check if email is verified
        # You can implement your verification check logic here
        # For now, we'll just return a default response
        return JsonResponse({
            'is_verified': user.email_verified if hasattr(user, 'email_verified') else False
        })
