from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from mainapp.models import Address, UserProfile, User, Order, OrderItem
from watch_customizer.models import CustomWatchOrder
from .forms import AddressForm, UserProfileForm, ReviewForm, ReturnRequestForm
from django.db import IntegrityError
from django.http import Http404, JsonResponse, HttpResponseRedirect, HttpResponse
from .models import Wishlist, Review, ReviewImage
from mainapp.models import Address
from adminapp.models import BaseWatch
from django.views.decorators.cache import never_cache
from django.db.models import Q, Prefetch
from datetime import datetime, timedelta
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from io import BytesIO
from django.conf import settings
import os
from django.core.cache import cache
from mainapp.utils import verify_pincode
from django.core.mail import send_mail
from django.utils import timezone

@never_cache
@login_required
def profile(request):
    user = request.user
    google_login = user.social_auth.filter(provider='google-oauth2').exists()

    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            user.fullname = form.cleaned_data['fullname']
            user.username = form.cleaned_data['username']
            if not google_login:
                user.email = form.cleaned_data['email']
            user.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = UserProfileForm(instance=profile, initial={
            'fullname': user.fullname,
            'username': user.username,
            'email': user.email,
            'mobilephone': profile.phone,
        })
        form.user = user

    return render(request, 'userapp/profile.html', {
        'user': user,
        'google_login': google_login,
        'profile': profile,
        'form': form,
    })

@never_cache
@login_required
def address_list(request):
    try:
        addresses = Address.objects.filter(user=request.user)
        form = AddressForm()
        print(f"Loaded {len(addresses)} addresses for user {request.user.id}")
        return render(request, 'userapp/address.html', {'addresses': addresses, 'form': form})
    except Exception as e:
        print(f"Error in address_list view: {e}")
        messages.error(request, "An error occurred while loading your addresses.")
        return redirect('userapp:profile')

@never_cache
@login_required
def add_address(request):
    addresses = Address.objects.filter(user=request.user)
    
    if request.method == 'POST':
        form_data = request.POST.copy()
        
        # Format latitude and longitude to match model constraints
        if 'latitude' in form_data and form_data['latitude']:
            try:
                lat = float(form_data['latitude'])
                form_data['latitude'] = format_coordinate(lat)
            except ValueError:
                pass
                
        if 'longitude' in form_data and form_data['longitude']:
            try:
                lng = float(form_data['longitude'])
                form_data['longitude'] = format_coordinate(lng)
            except ValueError:
                pass
                
        form = AddressForm(form_data)
        if form.is_valid():
            try:
                # Verify pincode before saving
                pincode = form.cleaned_data.get('pincode')
                if pincode:
                    pincode_data = verify_pincode(pincode)
                    if not pincode_data:
                        form.add_error('pincode', 'Invalid pincode. Please enter a valid Indian pincode.')
                        messages.error(request, "Invalid pincode. Please enter a valid Indian pincode.")
                        return render(request, 'userapp/address.html', {
                            'form': form, 
                            'addresses': addresses,
                        })
                
                address = form.save(commit=False)
                address.user = request.user
                
                # Check if this is the first address for the user
                if not Address.objects.filter(user=request.user).exists():
                    address.is_primary = True
                
                address.save()
                messages.success(request, "Address added successfully.")
                
                # Check if the request came from the order review page
                referer = request.META.get('HTTP_REFERER', '')
                if 'order_review' in referer:
                    return redirect('mainapp:order_review')
                else:
                    return redirect('userapp:Address')
            except IntegrityError:
                form.add_error(None, "This address already exists for your account.")
                messages.error(request, "This address already exists for your account.")
            except Exception as e:
                print(f"Error saving address: {e}")
                form.add_error(None, f"An error occurred: {str(e)}")
                messages.error(request, f"Error saving address: {str(e)}")
        else:
            # Log form errors for debugging
            print(f"Form errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = AddressForm()
    
    return render(request, 'userapp/address.html', {
        'form': form, 
        'addresses': addresses,
    })

@never_cache
@login_required
def edit_address(request, address_id):
    try:
        address = get_object_or_404(Address, id=address_id, user=request.user)
        addresses = Address.objects.filter(user=request.user)
        
        if request.method == 'POST':
            form_data = request.POST.copy()
            
            # Format latitude and longitude to match model constraints
            if 'latitude' in form_data and form_data['latitude']:
                try:
                    lat = float(form_data['latitude'])
                    form_data['latitude'] = format_coordinate(lat)
                except ValueError:
                    pass
                    
            if 'longitude' in form_data and form_data['longitude']:
                try:
                    lng = float(form_data['longitude'])
                    form_data['longitude'] = format_coordinate(lng)
                except ValueError:
                    pass
                    
            form = AddressForm(form_data, instance=address)
            if form.is_valid():
                # Verify pincode before saving
                pincode = form.cleaned_data.get('pincode')
                if pincode:
                    pincode_data = verify_pincode(pincode)
                    if not pincode_data:
                        form.add_error('pincode', 'Invalid pincode. Please enter a valid Indian pincode.')
                        messages.error(request, "Invalid pincode. Please enter a valid Indian pincode.")
                        return render(request, 'userapp/address.html', {
                            'form': form,
                            'addresses': addresses,
                            'edit_address': address
                        })
                
                form.save()
                messages.success(request, "Address updated successfully.")
                return redirect('userapp:Address')
            else:
                # Log form errors for debugging
                print(f"Form errors: {form.errors}")
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                
                return render(request, 'userapp/address.html', {
                    'form': form,
                    'addresses': addresses,
                    'edit_address': address
                })
        else:
            # Check if it's an AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
            if is_ajax:
                try:
                    # Safely convert decimal values to float or None
                    latitude = None
                    longitude = None
                    
                    if address.latitude:
                        try:
                            latitude = float(address.latitude)
                        except (ValueError, TypeError):
                            latitude = None
                    
                    if address.longitude:
                        try:
                            longitude = float(address.longitude)
                        except (ValueError, TypeError):
                            longitude = None
                    
                    # Return address data as JSON
                    return JsonResponse({
                        'flat_house_no': address.flat_house_no,
                        'area_street': address.area_street,
                        'landmark': address.landmark or '',
                        'pincode': address.pincode,
                        'town_city': address.town_city,
                        'state': address.state,
                        'country': address.country,
                        'address_type': address.address_type,
                        'latitude': latitude,
                        'longitude': longitude,
                    })
                except Exception as e:
                    print(f"Error serializing address data: {e}")
                    return JsonResponse({'error': str(e)}, status=400)
            
            # Regular GET request - show edit form
            form = AddressForm(instance=address)
            return render(request, 'userapp/address.html', {
                'form': form,
                'addresses': addresses,
                'edit_address': address
            })
    except Exception as e:
        print(f"Error in edit_address view: {e}")
        messages.error(request, f"Error loading address: {str(e)}")
        
        # Check if it's an AJAX request to return appropriate response
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        
        return redirect('userapp:Address')

@never_cache
@login_required
def delete_address(request, address_id):
    try:
        address = get_object_or_404(Address, id=address_id, user=request.user)
        address.delete()
        messages.success(request, "Address deleted successfully.")
    except Exception as e:
        print(f"Error deleting address: {e}")
        messages.error(request, "An error occurred while deleting your address.")
    return redirect('userapp:Address')

@never_cache
@login_required
def make_primary_address(request, address_id):
    try:
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        # Set all addresses to non-primary
        Address.objects.filter(user=request.user).update(is_primary=False)
        
        # Set the selected address as primary
        address.is_primary = True
        address.save()
        messages.success(request, "Primary address updated successfully.")
    except Exception as e:
        print(f"Error setting primary address: {e}")
        messages.error(request, "An error occurred while updating your primary address.")
    
    return redirect('userapp:Address')

@never_cache
def check_username(request):
    username = request.GET.get('username', None)
    data = {
        'exists': User.objects.filter(username__iexact=username).exists()
    }
    return JsonResponse(data)

@never_cache
def check_email(request):
    email = request.GET.get('email', None)
    data = {
        'exists': User.objects.filter(email__iexact=email).exists()
    }
    return JsonResponse(data)

@never_cache
@login_required
def wishlist(request):
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    return render(request, 'userapp/wishlist.html', {'wishlist': wishlist})

@never_cache
@login_required
def add_to_wishlist(request, watch_id):
    if request.method == 'POST':
        watch = BaseWatch.objects.get(id=watch_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        if watch not in wishlist.watches.all():
            wishlist.watches.add(watch)
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'already_in_wishlist'})
    return JsonResponse({'status': 'error'}, status=400)

@never_cache
@login_required
def remove_from_wishlist(request, watch_id):
    watch = get_object_or_404(BaseWatch, id=watch_id)
    wishlist = get_object_or_404(Wishlist, user=request.user)
    wishlist.watches.remove(watch)
    return JsonResponse({'status': 'success'})

@never_cache
@login_required
def my_orders(request):
    # Fetch both normal orders and custom watch orders
    normal_orders = Order.objects.filter(user=request.user).order_by('-created_at')
    custom_orders = CustomWatchOrder.objects.filter(user=request.user).order_by('-created_at')

    # Prefetch related items and reviews for normal orders
    normal_orders = normal_orders.prefetch_related(
        Prefetch(
            'items',
            queryset=OrderItem.objects.select_related('watch').prefetch_related(
                Prefetch(
                    'watch__reviews',
                    queryset=Review.objects.filter(user=request.user),
                    to_attr='user_review'
                )
            )
        )
    )

    # Prefetch related parts for custom orders
    custom_orders = custom_orders.prefetch_related('selected_parts__part', 'selected_parts__selected_option')

    # Combine and sort all orders
    all_orders = sorted(
        [(order, 'normal') for order in normal_orders] + 
        [(order, 'custom') for order in custom_orders],
        key=lambda x: x[0].created_at,
        reverse=True
    )

    # Filter by status
    status = request.GET.getlist('status')
    if status:
        all_orders = [order for order, _ in all_orders if order.status in status]

    # Filter by time
    order_time = request.GET.get('time')
    if order_time:
        if order_time == 'last_30_days':
            start_date = datetime.now() - timedelta(days=30)
            all_orders = [order for order, _ in all_orders if order.created_at >= start_date]
        elif order_time.isdigit():
            year = int(order_time)
            all_orders = [order for order, _ in all_orders if order.created_at.year == year]

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        all_orders = [
            order for order, _ in all_orders
            if (isinstance(order, Order) and any(search_query.lower() in item.watch.model_name.lower() for item in order.items.all()))
            or (isinstance(order, CustomWatchOrder) and search_query.lower() in order.customizable_watch.name.lower())
            or search_query.lower() in order.order_id.lower()
        ]

    current_year = datetime.now().year
    year_range = range(current_year, 2019, -1)  # Adjust the start year as needed

    context = {
        'orders': all_orders,
        'current_year': current_year,
        'year_range': year_range,
    }
    return render(request, 'userapp/my_orders.html', context)


@never_cache
@login_required
def order_details(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    # Calculate order summary
    subtotal = sum(item.price * item.quantity for item in order.items.all())
    shipping_cost = order.shipping_cost if hasattr(order, 'shipping_cost') else 0
    discount = order.discount if hasattr(order, 'discount') else 0
    final_price = subtotal + shipping_cost - discount
    
    for item in order.items.all():
        item.user_review = Review.objects.filter(user=request.user, watch=item.watch).first()
    
    context = {
        'order': order,
        'order_summary': {
            'subtotal': subtotal,
            'shipping_cost': shipping_cost,
            'discount': discount,
            'final_price': final_price
        }
    }
    return render(request, 'userapp/order_details.html', context)

@never_cache
@login_required
def write_review(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.watch = item.watch
            review.save()
            
            # Handle multiple image uploads
            for image in request.FILES.getlist('image[]'):
                ReviewImage.objects.create(review=review, image=image)
            
            return redirect('userapp:my_orders')
    else:
        form = ReviewForm()
    
    context = {
        'form': form,
        'item': item,
    }
    return render(request, 'userapp/write_review.html', context)

@never_cache
@login_required
def edit_review(request, item_id):
    item = get_object_or_404(OrderItem, id=item_id, order__user=request.user)
    review = get_object_or_404(Review, user=request.user, watch=item.watch)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            form.save()
            
            # Handle multiple image uploads
            for image in request.FILES.getlist('image[]'):
                ReviewImage.objects.create(review=review, image=image)
            
            # Handle image deletions
            for image_id in request.POST.getlist('delete_images[]'):
                ReviewImage.objects.filter(id=image_id, review=review).delete()
            
            return redirect('userapp:my_orders')
    else:
        form = ReviewForm(instance=review)
    
    context = {
        'form': form,
        'item': item,
        'review_images': review.images.all(),
    }
    return render(request, 'userapp/write_review.html', context)

@never_cache
@login_required
def download_invoice(request, order_id):
    if order_id.startswith('CWH'):
        # Custom Watch Order
        order = get_object_or_404(CustomWatchOrder, order_id=order_id, user=request.user)
        is_custom = True
        vendor = {
            'company_name': 'Time Craft',
            'address': 'NDR warehousing private ltd, SF No. 525, 526, 529-533, Okkilipalayam, Palladam Road, Othakalmandapam, Coimbatore, Tamilnadu, India - 641032, IN-TN.',
            'gstin': '33AAECS1679J1Z5',
        }
    elif order_id.startswith('WH'):
        # Regular Order
        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        is_custom = False
        vendor = order.items.first().watch.vendor
    else:
        raise Http404("Invalid order ID")

    company_name = vendor['company_name'] if isinstance(vendor, dict) else vendor.company_name

    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()

    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer, pagesize=letter)

    # Set up some variables
    width, height = letter
    margin = 0.5 * inch

    # Add the Time Craft logo at the top right corner
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    p.drawImage(logo_path, width - 2.2*inch, height - 12*margin - inch, width=2*inch, height=inch, preserveAspectRatio=True)

    # Add seller details
    p.setFont("Helvetica-Bold", 12)
    p.drawString(margin, height - margin, f"Sold By: {company_name}")
    p.setFont("Helvetica", 10)
    p.drawString(margin, height - margin - 15, "Ship from Address: NDR warehousing private ltd, SF No. 525, 526, 529-533,")
    p.drawString(margin, height - margin - 30, "Okkilipalayam, Palladam Road, Othakalmandapam, Coimbatore, Tamilnadu, India - 641032, IN-TN.")
    p.drawString(margin, height - margin - 45, "GSTIN: 33AAECS1679J1Z5")

    # Add invoice title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(width / 2 - inch, height - 3*margin, "  Tax Invoice")

    # Add order details on the left side
    p.setFont("Helvetica", 10)
    p.drawString(margin, height - 4*margin, f"Order ID: {order.order_id}")
    p.drawString(margin, height - 4.4*margin, f"Order Date: {order.created_at.strftime('%d-%m-%Y')}")
    p.drawString(margin, height - 4.8*margin, f"Invoice Date: {datetime.now().strftime('%d-%m-%Y')}")
    p.drawString(margin, height - 5.2*margin, f"PAN: AAECS1679J")

    # Add customer details on the right side
    p.drawString(width / 2 + 1.5*inch, height - 4*margin, "Bill To:")
    p.drawString(width / 2 + 1.5*inch, height - 4.4*margin, order.user.fullname)
    p.drawString(width / 2 + 1.5*inch, height - 4.8*margin, f"{order.address.flat_house_no}, {order.address.area_street}")
    p.drawString(width / 2 + 1.5*inch, height - 5.2*margin, f"{order.address.town_city}, {order.address.state} - {order.address.pincode}")
    p.drawString(width / 2 + 1.5*inch, height - 5.6*margin, f"Phone: {order.user.profile.phone}")

    def format_price(price):
        return f"Rs.{price:.2f}"

    # Create table for order items
    data = [['Product', 'Qty', 'Gross Amount', 'Discounts', 'Taxable Value', 'IGST', 'Total']]
    
    if is_custom:
        # For custom watch order
        item_name = f"Custom Watch: {order.customizable_watch.name}"
        price = order.total_price
        data.append([
            item_name,
            "1",
            format_price(price),
            format_price(0),  # Assuming no discount for custom watches
            format_price(price),
            format_price(0),  # Assuming no IGST for custom watches
            format_price(price)
        ])
        total_amount = price
        total_discount = 0
        total_igst = 0
    else:
        # For regular order
        for item in order.items.all():
            item_price = item.price * item.quantity
            data.append([
                item.watch.model_name,
                str(item.quantity),
                format_price(item_price),
                format_price(0),  # Assuming no discount per item
                format_price(item_price),
                format_price(0),  # Assuming no IGST per item
                format_price(item_price)
            ])
        total_amount = sum(item.price * item.quantity for item in order.items.all())
        total_discount = 0  # Assuming no discount
        total_igst = 0  # Assuming no IGST

    grand_total = total_amount - total_discount + total_igst

    data.extend([
        ['', '', '', '', '', '', ''],
        ['Total', '', format_price(total_amount), format_price(total_discount), '', format_price(total_igst), format_price(grand_total)],
        ['Grand Total', '', '', '', '', '', format_price(grand_total)]
    ])

    table = Table(data, colWidths=[2*inch, 0.75*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.black)
    ]))

    table_width = 1  # Set table width based on number of columns
    table_height = len(data) * 0.3 * inch  # Approximate height based on number of rows
    table_position = height - 7*margin - table_height

    table.wrapOn(p, table_width, table_height)
    table.drawOn(p, margin, table_position)

    # Add footer with grand total
    p.setFont("Helvetica-Bold", 12)
    p.drawString(width - 2.2*inch, height - 9*margin - inch, f"Grand Total: {format_price(grand_total)}")
    p.setFont("Helvetica-Bold", 11)
    p.drawString(width - 2.2*inch, height - 9.4*margin - inch, company_name.upper())

    # Close the PDF object cleanly, and we're done.
    p.showPage()
    p.save()

    # FileResponse sets the Content-Disposition header so that browsers
    # present the option to save the file.
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

@never_cache
@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        reason = request.POST.get('cancellation_reason', '')
        if reason == 'Other':
            custom_reason = request.POST.get('custom_reason', '')
            reason = custom_reason if custom_reason else reason
        
        if order.cancel_order(reason):
            messages.success(request, 'Order cancelled successfully.')
        else:
            messages.error(request, 'Order cannot be cancelled.')
        return redirect('userapp:my_orders')
    
    return render(request, 'userapp/cancel_order.html', {'order': order})

from django.utils import timezone

def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.is_returnable():
        if request.method == 'POST':
            return_reason = request.POST.get('return_reason', '')
            if return_reason == 'Other':
                custom_reason = request.POST.get('custom_reason', '')
                return_reason = custom_reason if custom_reason else return_reason
            
            order.status = 'return_requested'
            order.return_reason = return_reason
            order.save()
            
            # Create initial return history entry
            from deliveryapp.models import ReturnHistory
            ReturnHistory.objects.create(
                delivery_person=order.user,  # Placeholder, will be updated when assigned
                order=order,
                status='return_requested',
                notes=f"Return requested by customer. Reason: {return_reason}"
            )
            
            messages.success(request, 'Return request submitted successfully. You will be notified once it is approved.')
            return redirect('userapp:my_orders')
    else:
        messages.error(request, 'Order cannot be returned. Return period has expired.')
        return redirect('userapp:my_orders')
    
    return render(request, 'userapp/return_order.html', {'order': order})

@require_POST
def verify_pincode_view(request):
    """Handle AJAX requests to verify pincodes"""
    pincode = request.POST.get('pincode')
    if not pincode:
        return JsonResponse({'success': False, 'message': 'Pincode is required'})
    
    # Validate pincode format
    if len(pincode) != 6 or not pincode.isdigit():
        return JsonResponse({
            'success': False, 
            'message': 'Pincode must be a 6-digit number'
        })
    
    try:
        # Log the pincode being verified
        print(f"Verifying pincode: {pincode}")
        
        pincode_data = verify_pincode(pincode)
        if pincode_data:
            print(f"Pincode data received: {pincode_data}")
            return JsonResponse({
                'success': True,
                'district': pincode_data.get('district', ''),
                'state': pincode_data.get('state', ''),
                'office': pincode_data.get('office', ''),
                'taluk': pincode_data.get('taluk', '')
            })
        else:
            print(f"Invalid pincode: {pincode}")
            # Return invalid response even in DEBUG mode
            return JsonResponse({
                'success': False, 
                'message': 'Invalid pincode or not found in database'
            })
    except Exception as e:
        print(f"Error in verify_pincode_view: {e}")
        return JsonResponse({
            'success': False, 
            'message': f'Error: {str(e)}'
        })

# Helper function to format coordinates to max 9 digits with 6 decimal places
def format_coordinate(coord):
    """Format a coordinate to comply with DecimalField(max_digits=9, decimal_places=6)"""
    # Format to 6 decimal places
    formatted = f"{coord:.6f}"
    
    # If total digits exceeds 9 (including the decimal point which we ignore),
    # truncate to ensure max_digits=9 constraint is met
    if len(formatted.replace('.', '')) > 9:
        # Split into integer and decimal parts
        parts = formatted.split('.')
        # Keep only 2 digits for integer part (max) and adjust decimal part to fit within 9 total
        integer_part = parts[0][-2:] if len(parts[0]) > 2 else parts[0]
        decimal_part = parts[1][:min(6, 9-len(integer_part))]
        formatted = f"{integer_part}.{decimal_part}"
    
    return formatted

@login_required
def request_return(request, order_id):
    """Request a return for an order"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    # Check if order is eligible for return
    if order.status != 'delivered':
        messages.error(request, "Only delivered orders can be returned.")
        return redirect('userapp:order_details', order_id=order_id)
    
    # Check if order is within the 10-day return window
    if not order.is_returnable():
        days_since_delivery = (timezone.now().date() - order.delivery_date).days
        messages.error(request, f"This order cannot be returned. The return period is limited to 10 days after delivery. It has been {days_since_delivery} days since delivery.")
        return redirect('userapp:order_details', order_id=order_id)
        
    # Check if return already exists
    if order.status in ['return_requested', 'return_approved', 'return_scheduled', 'return_in_transit', 'return_completed']:
        messages.info(request, "A return has already been initiated for this order.")
        return redirect('userapp:order_details', order_id=order_id)
    
    if request.method == 'POST':
        form = ReturnRequestForm(request.POST)
        if form.is_valid():
            # Update order status
            order.status = 'return_requested'
            order.return_reason = form.cleaned_data['reason']
            order.return_notes = form.cleaned_data['notes']
            order.return_requested_at = timezone.now()
            order.save()
            
            # Notify admin
            subject = f"New Return Request: Order #{order.order_id}"
            message = f"A new return request has been initiated for Order #{order.order_id}."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL])
            
            messages.success(request, "Return request submitted successfully. We'll review your request and get back to you.")
            return redirect('userapp:my_orders')
    else:
        form = ReturnRequestForm()
    
    context = {
        'order': order,
        'form': form,
        'days_remaining': 10 - (timezone.now().date() - order.delivery_date).days
    }
    
    return render(request, 'userapp/request_return.html', context)