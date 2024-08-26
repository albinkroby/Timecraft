from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from mainapp.decorators import user_type_required
from .forms import VendorRegistrationForm, BaseWatchForm
from django.contrib import messages
from .models import VendorProfile
from mainapp.utils import hash_url
from django.urls import reverse
from adminapp.models import Category, BaseWatch, WatchImage, SmartWatchFeature, PremiumWatchFeature, WatchType
from mainapp.models import Order, OrderItem
from django.shortcuts import get_object_or_404
import os
from django.http import JsonResponse, HttpResponse
from django.views.decorators.cache import never_cache
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.paginator import Paginator
import pandas as pd
import io

@never_cache
def home(request):
    return render(request,'vendorapp/home.html')

@never_cache
def vendor_register(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to register as a vendor.")
        hashed_next = hash_url('vendorapp:register')
        login_url = reverse('mainapp:login')
        return redirect(f'{login_url}?next={hashed_next}')  

    if VendorProfile.objects.filter(user=request.user).exists():
        messages.info(request, "You are already registered as a vendor.")
        return redirect('vendorapp:index')

    if request.method == 'POST':
        form = VendorRegistrationForm(request.POST)
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.user = request.user
            vendor.save()
            request.user.role = 'vendor'
            request.user.save()
            messages.success(request, "You have successfully registered as a vendor.")
            return redirect('vendorapp:index')
    else:
        form = VendorRegistrationForm()
    return render(request, 'vendorapp/register.html', {'form': form})

@never_cache
@login_required
@user_type_required('vendor')
def index(request):
    vendor_profile = VendorProfile.objects.get(user=request.user)
    if vendor_profile.approval_status == 'Approved':
        # Get total products
        total_products = BaseWatch.objects.filter(vendor=vendor_profile).count()
        
        # Get new products added in the last week
        one_week_ago = timezone.now() - timedelta(days=7)
        # new_products_this_week = BaseWatch.objects.filter(vendor=vendor_profile, created_at__gte=one_week_ago).count()
        new_products_this_week = BaseWatch.objects.filter(vendor=vendor_profile).count()
        product_growth_percentage = (new_products_this_week / total_products * 100) if total_products > 0 else 0
        
        # Get total sales for the last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        total_sales = BaseWatch.objects.filter(
            vendor=vendor_profile,
            orderitem__order__created_at__gte=thirty_days_ago
        ).aggregate(
            total_sales=Sum('orderitem__quantity')
        )['total_sales'] or 0
        
        # Get sales growth percentage
        previous_thirty_days = timezone.now() - timedelta(days=60)
        previous_sales = BaseWatch.objects.filter(
            vendor=vendor_profile,
            orderitem__order__created_at__gte=previous_thirty_days,
            orderitem__order__created_at__lt=thirty_days_ago
        ).aggregate(
            total_sales=Sum('orderitem__quantity')
        )['total_sales'] or 0
        
        sales_growth_percentage = ((total_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else 0
        
        # Get total orders
        total_orders = BaseWatch.objects.filter(
            vendor=vendor_profile,
            orderitem__isnull=False
        ).aggregate(
            total_orders=Count('orderitem__order', distinct=True)
        )['total_orders'] or 0
        
        # Get order growth percentage
        new_orders_this_week = BaseWatch.objects.filter(
            vendor=vendor_profile,
            orderitem__order__created_at__gte=one_week_ago
        ).aggregate(
            new_orders=Count('orderitem__order', distinct=True)
        )['new_orders'] or 0
        
        order_growth_percentage = (new_orders_this_week / total_orders * 100) if total_orders > 0 else 0
        
        # Get 4 most recent orders
        recent_orders = Order.objects.filter(
            items__watch__vendor=vendor_profile
        ).distinct().order_by('-created_at')[:4]

        context = {
            'total_sales': total_sales,
            'sales_growth_percentage': round(sales_growth_percentage, 1),
            'total_products': total_products,
            'product_growth_percentage': round(product_growth_percentage, 1),
            'total_orders': total_orders,
            'order_growth_percentage': round(order_growth_percentage, 1),
            'recent_orders': recent_orders,
        }
        
        return render(request, 'vendorapp/index.html', context)
    else:
        return render(request, 'vendorapp/vendor_application_pending.html')
    
@never_cache
@login_required
@user_type_required('vendor')
def add_product(request):
    if request.method == 'POST':
        form = BaseWatchForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                watch = form.save(commit=False)
                watch.vendor = request.user.vendorprofile
                watch.save()
                form.save_m2m()  # Save many-to-many relationships

                # Handle primary image
                if 'primary_image' in request.FILES:
                    watch.primary_image = request.FILES['primary_image']
                    watch.save()

                # Handle additional images
                images = request.FILES.getlist('product_images')
                for image in images:
                    WatchImage.objects.create(base_watch=watch, image=image)

                # Handle SmartWatchFeature
                if watch.watch_type.type_name == 'Smart Watch':
                    SmartWatchFeature.objects.create(
                        base_watch=watch,
                        heart_rate_monitor=form.cleaned_data.get('heart_rate_monitor', False),
                        gps=form.cleaned_data.get('gps', False),
                        step_counter=form.cleaned_data.get('step_counter', False),
                        sleep_tracker=form.cleaned_data.get('sleep_tracker', False)
                    )

                # Handle PremiumWatchFeature
                elif watch.watch_type.type_name == 'Premium Watch':
                    PremiumWatchFeature.objects.create(
                        base_watch=watch,
                        sapphire_glass=form.cleaned_data.get('sapphire_glass', False),
                        automatic_movement=form.cleaned_data.get('automatic_movement', False),
                        chronograph=form.cleaned_data.get('chronograph', False)
                    )

                return JsonResponse({'success': True, 'message': f'Product "{watch.model_name}" has been added successfully!'})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
def addproducttest(request):
    form = BaseWatchForm()
    watch_types = WatchType.objects.all()
    return render(request,'vendorapp/add_product.html',{'form':form,'watch_types':watch_types})

@never_cache
@login_required
@user_type_required('vendor')
def check_unique_model_name(request):
    model_name = request.GET.get('model_name', '')
    is_unique = not BaseWatch.objects.filter(model_name=model_name).exists()
    return JsonResponse({'is_unique': is_unique})

@never_cache
@login_required
@user_type_required('vendor')
def product_list(request):
    vendor_profile = VendorProfile.objects.get(user=request.user)
    products = BaseWatch.objects.filter(vendor=vendor_profile).select_related('brand', 'category', 'watch_type')
    form = BaseWatchForm()
    form_fields = {field: str(form[field]) for field in form.fields}
    watch_types = WatchType.objects.all()
    return render(request, 'vendorapp/product_list.html', {
        'products': products,
        'form_fields': form_fields,
        'watch_types': watch_types
    })

@never_cache
@login_required
@user_type_required('vendor')
def delete_product(request, product_id):
    product = get_object_or_404(BaseWatch, id=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully.')
    return redirect('vendorapp:product_list')

@never_cache
@login_required
@user_type_required('vendor')
def edit_product(request, product_id):
    product = get_object_or_404(BaseWatch, id=product_id, vendor=request.user.vendorprofile)
    if request.method == 'POST':
        form = BaseWatchForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            watch = form.save(commit=False)

            # Handle primary image
            if 'primary_image' in request.FILES:
                watch.primary_image = request.FILES['primary_image']
            elif not watch.primary_image:
                watch.primary_image = None

            watch.save()
            form.save_m2m()  # Save many-to-many relationships

            # Handle additional images
            if 'product_images' in request.FILES:
                images = request.FILES.getlist('product_images')
                for image in images:
                    WatchImage.objects.create(base_watch=watch, image=image)

            # Handle SmartWatchFeature
            if watch.watch_type.type_name == 'Smart Watch':
                SmartWatchFeature.objects.update_or_create(
                    base_watch=watch,
                    defaults={
                        'heart_rate_monitor': form.cleaned_data.get('heart_rate_monitor', False),
                        'gps': form.cleaned_data.get('gps', False),
                        'step_counter': form.cleaned_data.get('step_counter', False),
                        'sleep_tracker': form.cleaned_data.get('sleep_tracker', False)
                    }
                )
            else:
                SmartWatchFeature.objects.filter(base_watch=watch).delete()

            # Handle PremiumWatchFeature
            if watch.watch_type.type_name == 'Premium Watch':
                PremiumWatchFeature.objects.update_or_create(
                    base_watch=watch,
                    defaults={
                        'sapphire_glass': form.cleaned_data.get('sapphire_glass', False),
                        'automatic_movement': form.cleaned_data.get('automatic_movement', False),
                        'chronograph': form.cleaned_data.get('chronograph', False)
                    }
                )
            else:
                PremiumWatchFeature.objects.filter(base_watch=watch).delete()

            messages.success(request, f'Product "{watch.model_name}" has been updated successfully!')
            return redirect('vendorapp:product_list')
        else:
            print(form.errors)  # Print form errors for debugging
    else:
        form = BaseWatchForm(instance=product)

    return render(request, 'vendorapp/edit_product.html', {'form': form, 'product': product})

@never_cache
@login_required
@user_type_required('vendor')
def delete_product_image(request, image_id):
    image = get_object_or_404(WatchImage, id=image_id)
    if image.base_watch.vendor == request.user.vendorprofile:
        image.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=403)

@never_cache
@login_required
@user_type_required('vendor')
def manage_stock(request):
    vendor_profile = request.user.vendorprofile
    products = BaseWatch.objects.filter(vendor=vendor_profile)
    return render(request, 'vendorapp/manage_stock.html', {'products': products})

@never_cache
@login_required
@user_type_required('vendor')
def update_stock(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(BaseWatch, id=product_id, vendor=request.user.vendorprofile)
        stock_to_add = request.POST.get('stock_quantity')
        try:
            stock_to_add = int(stock_to_add)
            if stock_to_add >= 0:
                product.total_stock += stock_to_add
                product.available_stock += stock_to_add
                product.save()
                return JsonResponse({
                    'success': True, 
                    'available_stock': product.available_stock,
                    'total_stock': product.total_stock,
                    'is_in_stock': product.is_in_stock
                })
            else:
                return JsonResponse({'success': False, 'error': 'Stock quantity must be non-negative'})
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid stock quantity'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@never_cache
@login_required
@user_type_required('vendor')
def order_list(request):
    vendor_profile = request.user.vendorprofile
    orders = Order.objects.filter(
        items__watch__vendor=vendor_profile
    ).distinct().order_by('-created_at')

    # Date filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        orders = orders.filter(created_at__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__lte=end_date)

    paginator = Paginator(orders, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'vendorapp/order_list.html', context)

@never_cache
@login_required
@user_type_required('vendor')
def download_orders(request):
    vendor_profile = request.user.vendorprofile
    orders = Order.objects.filter(
        items__watch__vendor=vendor_profile
    ).distinct().order_by('-created_at')

    # Date filtering
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        orders = orders.filter(created_at__gte=start_date)
    if end_date:
        orders = orders.filter(created_at__lte=end_date)

    # Prepare data for Excel
    data = []
    for order in orders:
        for item in order.items.filter(watch__vendor=vendor_profile):
            data.append({
                'Order ID': order.order_id,
                'Model Name': item.watch.model_name,
                'Customer': order.user.email,
                'Total Amount': item.price * item.quantity,
                'Status': order.get_status_display(),
                'Date': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Quantity': item.quantity,
            })

    # Create DataFrame and Excel file
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Orders')

    output.seek(0)
    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=orders.xlsx'
    return response