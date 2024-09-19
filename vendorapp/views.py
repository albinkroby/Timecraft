from django.shortcuts import render,redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from mainapp.decorators import user_type_required
from .forms import VendorProfileForm, VendorRegistrationFormStep1, VendorRegistrationFormStep2, BaseWatchForm, BrandSelectionForm, BrandApprovalRequestForm, WatchDetailsForm, WatchMaterialsForm, WatchImageFormSet, VendorOnboardingForm
from .forms import BaseWatchUpdateForm, WatchDetailsUpdateForm, WatchMaterialsUpdateForm, WatchImageUpdateFormSet
from django.contrib import messages
from .models import VendorProfile
from mainapp.utils import hash_url
from django.urls import reverse
from adminapp.models import Category, BaseWatch, WatchImage, WatchType, BrandApproval, Brand
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
import io,json 
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import modelformset_factory

User = get_user_model()
@never_cache
def home(request):
    return render(request,'vendorapp/home.html')

@never_cache
def vendor_register_step1(request):
    if request.method == 'POST':
        user_form = VendorRegistrationFormStep1(request.POST)
        if user_form.is_valid():
            # Store form data in session
            request.session['vendor_user_data'] = user_form.cleaned_data
            return redirect('vendorapp:vendor_register_step2')
    else:
        user_form = VendorRegistrationFormStep1()
    
    # Always pass the form to the template, whether it's a new form or one with errors
    return render(request, 'vendorapp/register_step1.html', {'user_form': user_form})

@never_cache
def vendor_register_step2(request):
    if 'vendor_user_data' not in request.session:
        return redirect('vendorapp:vendor_register_step1')

    if request.method == 'POST':
        profile_form = VendorProfileForm(request.POST)
        password_form = VendorRegistrationFormStep2(request.POST)
        if profile_form.is_valid() and password_form.is_valid():
            user_data = request.session['vendor_user_data']
            user = User.objects.create_user(
                fullname=user_data['fullname'],
                email=user_data['email'],
                username=user_data['email'],
                role='vendor',
                password=password_form.cleaned_data['password1']
            )
            user.set_password(password_form.cleaned_data['password1'])
            user.save()

            vendor_profile = profile_form.save(commit=False)
            vendor_profile.user = user
            vendor_profile.contact_email = user_data['contact_email']
            vendor_profile.gst_number = user_data['gst_number']
            vendor_profile.contact_phone = user_data['contact_phone']
            vendor_profile.save()

            # Clear session data
            del request.session['vendor_user_data']

            messages.success(request, "You have successfully registered as a vendor.")
            return redirect('vendorapp:vendor_onboarding')
        else:
            print(profile_form.errors)  # Debug: Print form errors if the form is not valid
            print(password_form.errors)  # Debug: Print form errors if the form is not valid
    else:
        profile_form = VendorProfileForm()
        password_form = VendorRegistrationFormStep2()
    return render(request, 'vendorapp/register_step2.html', {'profile_form': profile_form, 'password_form': password_form})

@never_cache
@login_required
@user_type_required('vendor')
def vendor_onboarding(request):
    vendor_profile = request.user.vendorprofile
    
    if request.method == 'POST':
        form = VendorOnboardingForm(request.POST, instance=vendor_profile)
        if form.is_valid():
            form.save()
            vendor_profile.is_onboarding_completed = True
            vendor_profile.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('vendorapp:index')
    else:
        form = VendorOnboardingForm(instance=vendor_profile)
    
    context = {
        'form': form,
        'vendor_profile': vendor_profile,
    }
    return render(request, 'vendorapp/vendor_onboarding.html', context)

def validate_company_name(request):
    company_name = request.GET.get('company_name', None)
    if company_name:
        company_name = company_name.lower()
        data = {
            'is_taken': VendorProfile.objects.filter(company_name__iexact=company_name.lower()).exists()
        }
    else:
        data = {'is_taken': False}
    return JsonResponse(data)

@never_cache
@login_required
@user_type_required('vendor')
def index(request):
    vendor_profile = VendorProfile.objects.get(user=request.user)
    if vendor_profile.is_onboarding_completed:
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
    else:
        return redirect('vendorapp:vendor_onboarding')

@never_cache
@login_required
@user_type_required('vendor')
def check_unique_model_name(request):
    model_name = request.GET.get('model_name', '')
    model_name = model_name.replace('%20', ' ')
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


@require_POST
@login_required
@user_type_required('vendor')
def toggle_product_status(request):
    product_id = request.POST.get('product_id')
    status = request.POST.get('status')
    
    try:
        product = BaseWatch.objects.get(id=product_id, vendor=request.user.vendorprofile)
        
        # Convert status to boolean
        new_status = status.lower() == 'true'
        
        # Toggle the status
        product.is_active = new_status
        product.save()
        
        return JsonResponse({'success': True, 'new_status': product.is_active})
    except BaseWatch.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

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
        base_watch_form = BaseWatchUpdateForm(request.POST, request.FILES, instance=product)
        details_form = WatchDetailsUpdateForm(request.POST, instance=product.details)
        materials_form = WatchMaterialsUpdateForm(request.POST, instance=product.materials)
        
        if all([base_watch_form.is_valid(), details_form.is_valid(), materials_form.is_valid()]):
            try:
                base_watch = base_watch_form.save()
                details_form.save()
                materials_form.save()
                
                # Handle primary image
                if 'primary_image' in request.FILES:
                    base_watch.primary_image = request.FILES['primary_image']
                    base_watch.save()
                
                # Handle deletion of existing images
                images_to_delete = request.POST.getlist('delete_images')
                WatchImage.objects.filter(id__in=images_to_delete).delete()
                
                # Handle new additional images
                new_images = request.FILES.getlist('additional_images')
                for image in new_images:
                    WatchImage.objects.create(base_watch=base_watch, image=image)
                
                messages.success(request, f"Product {base_watch.model_name} has been updated successfully.")
                return redirect('vendorapp:product_list')
            except Exception as e:
                messages.error(request, f"An error occurred while saving the product: {str(e)}")
        else:
            messages.error(request, "There were errors in the form. Please check below for details.")
    else:
        base_watch_form = BaseWatchUpdateForm(instance=product)
        details_form = WatchDetailsUpdateForm(instance=product.details)
        materials_form = WatchMaterialsUpdateForm(instance=product.materials)
    
    context = {
        'base_watch_form': base_watch_form,
        'details_form': details_form,
        'materials_form': materials_form,
        'product': product,
    }
    return render(request, 'vendorapp/edit_product.html', context)

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


# test

@login_required
@user_type_required('vendor')
def add_product_step1(request):
    vendor = request.user.vendorprofile
    brands = Brand.objects.all()
    brand_approvals = BrandApproval.objects.filter(vendor=vendor)

    if request.method == 'POST':
        selected_brand_id = request.POST.get('brand')
        if selected_brand_id:
            brand = get_object_or_404(Brand, id=selected_brand_id)
            approval = brand_approvals.filter(brand=brand).first()
            
            return redirect('vendorapp:add_product_step2', brand_id=brand.id)
            if approval and approval.is_approved:
                return redirect('vendorapp:add_product_step2', brand_id=brand.id)
            elif approval and not approval.is_approved:
                if approval.requested_at + timedelta(days=30) > timezone.now():
                    messages.warning(request, f"Please wait 30 days before requesting approval for {brand.brand_name} again.")
                else:
                    return redirect('vendorapp:request_brand_approval', brand_id=brand.id)
            else:
                return redirect('vendorapp:request_brand_approval', brand_id=brand.id)
    
    brand_status = {}
    for brand in brands:
        approval = brand_approvals.filter(brand=brand).first()
        if approval:
            if approval.is_approved:
                status = "Approved"
            elif approval.requested_at + timedelta(days=30) > timezone.now():
                status = "Waiting"
            else:
                status = "Request Again"
        else:
            status = "Not Requested"
        brand_status[str(brand.id)] = status  # Convert brand.id to string

    # brand_status_json = json.dumps(brand_status)
    brand_status_json = json.dumps({"1": "Approved"})

    context = {
        'brands': brands,
        'brand_status': brand_status_json,
    }
    return render(request, 'vendorapp/add_product_step1.html', context)

@login_required
@user_type_required('vendor')
def request_brand_approval(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    vendor = request.user.vendorprofile

    if request.method == 'POST':
        form = BrandApprovalRequestForm(request.POST)
        if form.is_valid():
            approval_request = form.save(commit=False)
            approval_request.vendor = vendor
            approval_request.brand = brand
            approval_request.save()
            messages.success(request, f"Approval request for {brand.brand_name} has been submitted.")
            return redirect('vendorapp:vendor_dashboard')
    else:
        form = BrandApprovalRequestForm(initial={'brand': brand})

    return render(request, 'vendorapp/request_brand_approval.html', {'form': form, 'brand': brand})

@login_required
@user_type_required('vendor')
def add_product_step2(request, brand_id):
    brand = get_object_or_404(Brand, id=brand_id)
    vendor = request.user.vendorprofile

    if request.method == 'POST':
        base_watch_form = BaseWatchForm(request.POST, request.FILES)
        details_form = WatchDetailsForm(request.POST)
        materials_form = WatchMaterialsForm(request.POST)

        if all([base_watch_form.is_valid(), details_form.is_valid(), materials_form.is_valid()]):
            
            base_watch = base_watch_form.save(commit=False)
            base_watch.vendor = vendor
            base_watch.brand = brand

            # Handle primary image upload
            if 'primary_image' in request.FILES:
                base_watch.primary_image = request.FILES['primary_image']

            base_watch.save()
            base_watch_form.save_m2m()

            details = details_form.save(commit=False)
            details.base_watch = base_watch
            details.save()

            materials = materials_form.save(commit=False)
            materials.base_watch = base_watch
            materials.save()


            # Handle multiple image uploads
            images = request.FILES.getlist('images')
            for image in images:
                WatchImage.objects.create(base_watch=base_watch, image=image)

            messages.success(request, f"Product {base_watch.model_name} has been added successfully.")
            return redirect('vendorapp:product_list')
        else:
            # If there are errors, we'll render the form again with error messages
            context = {
                'base_watch_form': base_watch_form,
                'details_form': details_form,
                'materials_form': materials_form,
                'brand': brand,
            }
            return render(request, 'vendorapp/add_product.html', context)
    else:
        base_watch_form = BaseWatchForm()
        details_form = WatchDetailsForm()
        materials_form = WatchMaterialsForm()

    context = {
        'base_watch_form': base_watch_form,
        'details_form': details_form,
        'materials_form': materials_form,
        'brand': brand,
    }
    return render(request, 'vendorapp/add_product.html', context)