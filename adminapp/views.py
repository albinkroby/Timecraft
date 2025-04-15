import io
from django.forms import formset_factory, inlineformset_factory
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from mainapp.decorators import user_type_required
from vendorapp.models import VendorProfile
from .models import Brand, Category, BaseWatch, WatchImage, Feature, Material, StaffMember
from .forms import BrandForm, CategoryForm, BaseWatchForm, FeatureForm, MaterialForm, StaffCreationForm, StaffProfileForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import get_user_model,update_session_auth_hash
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.cache import never_cache
from mainapp.models import Order, OrderItem
import re
from django.db import IntegrityError
from django.db.models import Q, Sum, Count, F
from django.views.decorators.http import require_POST
from watch_customizer.models import CustomizableWatch, CustomizableWatchPart, CustomWatchOrder, CustomWatchOrderPart, WatchPart, WatchPartName, WatchPartOption
from watch_customizer.forms import CustomizableWatchForm, WatchPartForm, WatchPartOptionForm, ModelUploadForm
from django.forms.models import modelformset_factory
from django.views.decorators.csrf import csrf_protect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db.models.functions import TruncDate
from dateutil.relativedelta import relativedelta
import json
import random
from django.db.models import Sum, F, Count
from django.db.models.functions import TruncHour, TruncDate
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import calendar
from django.utils import timezone
from django.utils.timezone import make_aware
import pytz
from django.template.loader import render_to_string
from django.db import transaction
from django.http import JsonResponse
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User, Permission
from deliveryapp.models import DeliveryProfile, DeliveryMetrics
from .forms import DeliveryAgentCreationForm, DeliveryAgentProfileForm
# Create your views here.
User=get_user_model()

@never_cache
@login_required
@user_type_required('admin')
def index(request):
    # Get total users
    total_users = User.objects.exclude(is_superuser=True).count()
    recent_orders = Order.objects.all().order_by('-created_at')[:5]
    # Get new users this week
    one_week_ago = timezone.now() - timedelta(days=7)
    new_users_this_week = User.objects.filter(date_joined__gte=one_week_ago).count()
    user_growth_percentage = (new_users_this_week / total_users) * 100 if total_users > 0 else 0
    
    # Get total products
    total_products = BaseWatch.objects.count()
    
    # Get new products this week
    # new_products_this_week = BaseWatch.objects.filter(created_at__gte=one_week_ago).count()
    new_products_this_week = BaseWatch.objects.filter().count()
    product_growth_percentage = (new_products_this_week / total_products) * 100 if total_products > 0 else 0
    
    
    total_orders = Order.objects.count()
    new_orders_this_week = Order.objects.filter(created_at__gte=one_week_ago).count()
    order_growth_percentage = (new_orders_this_week / total_orders) * 100 if total_orders > 0 else 0
    
    context = {
        'total_users': total_users,
        'user_growth_percentage': round(user_growth_percentage, 1),
        'total_products': total_products,
        'product_growth_percentage': round(product_growth_percentage, 1),
        'total_orders': total_orders,
        'order_growth_percentage': order_growth_percentage,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'adminapp/index.html', context)

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def seller_approval(request):
    pending_vendors = VendorProfile.objects.filter(approval_status='Pending')
    return render(request, 'adminapp/seller_approval.html', {'pending_vendors': pending_vendors})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def approve_vendor(request, user_id):
    vendor = VendorProfile.objects.get(user_id=user_id)     
    vendor.approval_status = 'Approved'
    vendor.save()
    messages.success(request, f"Vendor {vendor.company_name} has been approved.")
    return redirect('adminapp:seller_approval')

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def reject_vendor(request, user_id):
    vendor = VendorProfile.objects.get(user_id=user_id)
    vendor.approval_status = 'Rejected'
    vendor.save()
    messages.success(request, f"Vendor {vendor.company_name} has been rejected.")
    return redirect('adminapp:seller_approval')

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def all_sellers(request):
    approved_vendors = VendorProfile.objects.exclude(approval_status='Pending')
    return render(request, 'adminapp/all_sellers.html', {'approved_vendors': approved_vendors})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def brand_list(request):
    brands = Brand.objects.all()
    form = BrandForm()

    if request.method == 'POST':
        form = BrandForm(request.POST, request.FILES)
        if form.is_valid():
            brand = form.save(commit=False)
            if 'brand_image' in request.FILES:
                brand.brand_image = request.FILES['brand_image']
            brand.save()
            if request.is_ajax():
                return JsonResponse({'success': True})
            return redirect('adminapp:brand_list')

    return render(request, 'adminapp/brand_list.html', {'brands': brands, 'form': form})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def category_list(request):
    categories = Category.objects.all()
    form = CategoryForm()

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category_name = form.cleaned_data['name']
            if Category.category_exists(category_name):
                return JsonResponse({'success': False, 'errors': {'name': ['A category with this name already exists.']}})
            else:
                form.save()
                return JsonResponse({'success': True})

    return render(request, 'adminapp/category_list.html', {'categories': categories, 'form': form})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated successfully.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('adminapp:category_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = CategoryForm(instance=category)
    
    return JsonResponse({
        'success': True, 
        'html': render(request, 'adminapp/category_form.html', {'form': form}).content.decode('utf-8'),
        'category': {
            'id': category.id,
            'name': category.name,
            'parent_category': category.parent_category.id if category.parent_category else ''
        }
    })

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    messages.success(request, 'Category deleted successfully.')
    return redirect('adminapp:category_list')

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def add_product(request):
    if request.method == 'POST':
        form = BaseWatchForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.vendor = VendorProfile.objects.get(user=request.user)
            product.save()
            
            images = request.FILES.getlist('product_images')
            for image in images:
                WatchImage.objects.create(base_watch=product, image=image)
            
            messages.success(request, 'Product added successfully.')
            return redirect('adminapp:product_list')
    else:
        form = BaseWatchForm()
    return render(request, 'adminapp/add_product.html', {'form': form})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def product_list(request):
    products = BaseWatch.objects.all()
    return render(request, 'adminapp/product_list.html', {'products': products})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def delete_product(request, product_id):
    product = get_object_or_404(BaseWatch, id=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully.')
    return redirect('adminapp:product_list')

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    return render(request, 'adminapp/user_list.html', {'users': users})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def toggle_user_active(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save()
        status = 'activated' if user.is_active else 'deactivated' 
        return JsonResponse({'success': True, 'is_active': user.is_active , 'message': f"User {user.username} has been {status}."})
    return JsonResponse({'success': False}, status=400)


@never_cache
@user_passes_test(lambda u: u.is_superuser)
def feature_list(request):
    features = Feature.objects.all()
    form = FeatureForm()
    return render(request, 'adminapp/feature_list.html', {'features': features, 'form': form})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def add_feature(request):
    form = FeatureForm(request.POST, request.FILES)
    if form.is_valid():
        feature = form.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'errors': form.errors})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def edit_feature(request, feature_id):
    feature = get_object_or_404(Feature, id=feature_id)
    if request.method == 'POST':
        form = FeatureForm(request.POST, request.FILES, instance=feature)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = FeatureForm(instance=feature)
    
    form_html = render(request, 'adminapp/form/feature_form.html', {'form': form, 'feature': feature}).content.decode('utf-8')
    return JsonResponse({'success': True, 'html': form_html})


@never_cache
@user_passes_test(lambda u: u.is_superuser)
def toggle_feature(request, feature_id):
    feature = get_object_or_404(Feature, id=feature_id)
    feature.is_active = not feature.is_active
    feature.save()
    status = 'activated' if feature.is_active else 'deactivated'
    messages.success(request, f"Feature {feature.name} has been {status}.")
    return JsonResponse({'success': True, 'is_active': feature.is_active, 'message': f"Feature {feature.name} has been {status}."})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def material_list(request):
    materials = Material.objects.all()
    form = MaterialForm()
    return render(request, 'adminapp/material_list.html', {'materials': materials, 'form': form})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
@require_POST
def add_material(request):
    form = MaterialForm(request.POST)
    if form.is_valid():
        material = form.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'errors': form.errors})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def edit_material(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = MaterialForm(instance=material)
    
    form_html = render(request, 'adminapp/form/material_form.html', {'form': form, 'material': material}).content.decode('utf-8')
    return JsonResponse({'success': True, 'html': form_html})

@never_cache
@user_passes_test(lambda u: u.is_superuser)
def toggle_material(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    material.is_active = not material.is_active
    material.save()
    status = 'activated' if material.is_active else 'deactivated'
    messages.success(request, f"Material {material.name} has been {status}.")
    return JsonResponse({'success': True, 'is_active': material.is_active, 'message': f"Material {material.name} has been {status}."})

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_profile(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        else:
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, 'Password updated successfully.')
            # Re-authenticate the user
            update_session_auth_hash(request, request.user)
            return redirect('adminapp:admin_profile')
    
    context = {
        'title': 'Admin Profile',
    }
    return render(request, 'adminapp/admin_profile.html', context)

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            # Additional custom validation
            new_password = form.cleaned_data.get('new_password1')
            if len(new_password) < 8:
                form.add_error('new_password1', 'Password must be at least 8 characters long.')
            elif not re.search(r'[A-Z]', new_password):
                form.add_error('new_password1', 'Password must contain at least one uppercase letter.')
            elif not re.search(r'[a-z]', new_password):
                form.add_error('new_password1', 'Password must contain at least one lowercase letter.')
            elif not re.search(r'\d', new_password):
                form.add_error('new_password1', 'Password must contain at least one number.')
            
            if not form.errors:
                user = form.save()
                update_session_auth_hash(request, user)  # Important!
                messages.success(request, 'Your password was successfully updated!')
                return JsonResponse({'success': True, 'message': 'Your password was successfully updated!'})
        
        # If form is not valid or custom validation failed
        errors = {field: form.errors[field] for field in form.errors}
        return JsonResponse({'success': False, 'errors': errors})
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'adminapp/admin_profile.html', {'form': form})


@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def order_list(request):
    orders = Order.objects.all().distinct().order_by('-created_at')

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
    return render(request, 'adminapp/order_list.html', context)

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def download_orders(request):
    import pandas as pd
    try:
        orders = Order.objects.all().distinct().order_by('-created_at')
    except Exception as e:
        orders = Order.objects.none()
        messages.error(request, f"Error retrieving orders: {str(e)}")

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
        for item in order.items.all():
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

@never_cache
@login_required
@user_type_required('admin')
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related(
            'user',
            'user__profile',
            'address'
        ).prefetch_related(
            'items',
            'items__watch'
        ),
        order_id=order_id
    )
    
    context = {
        'order': order,
        'title': f'Order #{order.order_id}',
    }
    
    return render(request, 'adminapp/order_detail.html', context)


# ... (previous imports)
import zipfile
import os
from django.conf import settings

import logging
from django.utils import timezone
from django.urls import reverse
from datetime import datetime

logger = logging.getLogger(__name__)

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_customizable_watch(request):
    if request.method == 'POST':
        logger.debug(f"POST data: {request.POST}")
        logger.debug(f"FILES data: {request.FILES}")
        
        form = ModelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                model_file = form.cleaned_data['model_file']
                logger.debug(f"Cleaned data: {form.cleaned_data}")
                logger.debug(f"Model file name: {model_file.name}")
                logger.debug(f"Model file size: {model_file.size}")
                
                if not model_file.name:
                    raise ValueError("File name is empty")
                
                # Create a unique folder name using timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                folder_name = f"custom_watch_models/model_{timestamp}"
                
                file_extension = os.path.splitext(model_file.name)[1].lower()
                main_file_path = None
                
                if file_extension == '.zip':
                    # Handle ZIP file
                    with zipfile.ZipFile(model_file) as zf:
                        for file_info in zf.infolist():
                            if file_info.filename.endswith('/'):  # Skip directories
                                continue
                            file_name = os.path.basename(file_info.filename)  # Get only the file name, not the full path
                            file_content = zf.read(file_info.filename)
                            file_path = default_storage.save(f"{folder_name}/{file_name}", ContentFile(file_content))
                            logger.debug(f"Saved file from ZIP: {file_path}")
                            if file_name.lower().endswith(('.gltf', '.glb')) and main_file_path is None:
                                main_file_path = file_path
                else:
                    # Handle single file (GLTF or GLB)
                    main_file_path = default_storage.save(f"{folder_name}/{model_file.name}", model_file)
                    logger.debug(f"Saved single file: {main_file_path}")
                
                if main_file_path is None:
                    raise ValueError("No GLTF or GLB file found in the uploaded content")
                
                messages.success(request, 'Model uploaded successfully!')
                return redirect(reverse('adminapp:add_watch_details', kwargs={'model_path': main_file_path}))
            except Exception as e:
                logger.error(f"Error saving file: {str(e)}")
                messages.error(request, f'Error uploading file: {str(e)}')
        else:
            logger.error(f"Form errors: {form.errors}")
            messages.error(request, 'There was an error with your submission. Please check the form.')
    else:
        form = ModelUploadForm()
    
    return render(request, 'adminapp/add_customizable_watch.html', {'form': form})

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_watch_details(request, model_path):
    if request.method == 'POST':
        form = CustomizableWatchForm(request.POST, request.FILES)
        if form.is_valid():
            watch = form.save(commit=False)
            watch.model_file = model_path
            watch.save()
            messages.success(request, 'Customizable watch added successfully.')
            return redirect('adminapp:add_watch_parts', watch_id=watch.id)
    else:
        form = CustomizableWatchForm()
    
    return render(request, 'adminapp/add_watch_details.html', {'form': form, 'model_path': model_path})

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def check_watch_name(request):
    name = request.GET.get('name', '').strip()
    is_unique = not CustomizableWatch.objects.filter(name__iexact=name).exists()
    return JsonResponse({'is_unique': is_unique})

from django.forms import formset_factory, BaseFormSet
from django.core.exceptions import ValidationError

class BaseWatchPartFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        part_names = []
        for form in self.forms:
            if form.cleaned_data:
                part_name = form.cleaned_data.get('part_name')
                if part_name in part_names:
                    raise ValidationError("Each part must be unique.")
                part_names.append(part_name)

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_watch_parts(request, watch_id):
    watch = get_object_or_404(CustomizableWatch, id=watch_id)
    parts = WatchPart.objects.filter(customizablewatchpart__customizable_watch=watch)
    form = WatchPartForm()
    
    context = {
        'watch': watch,
        'parts': parts,
        'form': form,
    }
    return render(request, 'adminapp/add_watch_parts.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_watch_part_ajax(request, watch_id):
    if request.method == 'POST':
        form = WatchPartForm(request.POST)
        if form.is_valid():
            # Check if part type already exists for this watch
            part_name = form.cleaned_data['part_name']
            existing_part = CustomizableWatchPart.objects.filter(
                customizable_watch_id=watch_id,
                part__part_name=part_name
            ).exists()
            
            if existing_part:
                return JsonResponse({
                    'success': False,
                    'duplicate_part': True,
                    'message': 'This part type has already been added to the watch'
                })
            
            part = form.save()
            CustomizableWatchPart.objects.create(
                customizable_watch_id=watch_id,
                part=part
            )
            
            # Render the new part card
            html = render_to_string('adminapp/partials/part_card.html', {
                'part': part
            }, request=request)
            
            return JsonResponse({
                'success': True,
                'html': html,
                'part_name_id': str(part.part_name.id)
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
    
    return JsonResponse({'success': False}, status=400)

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_part_options(request, watch_id):
    watch = get_object_or_404(CustomizableWatch, id=watch_id)
    # Fetch the parts associated with this watch
    customizable_parts = CustomizableWatchPart.objects.filter(customizable_watch=watch).select_related('part', 'part__part_name')
    form = WatchPartOptionForm()
    
    context = {
        'watch': watch,
        'parts': customizable_parts,
        'form': form,
    }
    return render(request, 'adminapp/add_part_options.html', context)

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def customizable_watch_list(request):
    watches = CustomizableWatch.objects.all()
    return render(request, 'adminapp/customizable_watch_list.html', {'watches': watches})

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def view_customizable_watch(request, watch_id):
    watch = get_object_or_404(CustomizableWatch, id=watch_id)
    customizable_parts = CustomizableWatchPart.objects.filter(customizable_watch=watch).prefetch_related('part', 'part__part_name', 'options')
    
    parts_data = []
    for customizable_part in customizable_parts:
        part_data = {
            'name': customizable_part.part.part_name.name,
            'description': customizable_part.part.description,
            'model_path': customizable_part.part.model_path,
            'options': []
        }
        for option in customizable_part.options.all():
            option_data = {
                'name': option.name,
                'price': option.price,
                'stock': option.stock,
                'texture_url': option.texture.url if option.texture else None,
                'thumbnail_url': option.thumbnail.url if option.thumbnail else None,
            }
            part_data['options'].append(option_data)
        parts_data.append(part_data)

    context = {
        'watch': watch,
        'parts_data': parts_data,
    }
    return render(request, 'adminapp/view_customizable_watch.html', context)

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_customizable_watch(request, watch_id):
    try:
        watch = get_object_or_404(CustomizableWatch, id=watch_id)
        watch.delete()
        return JsonResponse({'success': True, 'message': 'Customizable watch deleted successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@require_POST
@csrf_protect
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_watch_part_ajax(request):
    if request.method == 'POST':
        part_id = request.POST.get('part_id')
        watch_id = request.POST.get('watch_id')
        
        if not part_id or not watch_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing required parameters'
            }, status=400)
        
        try:
            customizable_part = CustomizableWatchPart.objects.get(
                customizable_watch_id=watch_id,
                part_id=part_id
            )
            # Delete the WatchPart and its associated CustomizableWatchPart
            part = customizable_part.part
            customizable_part.delete()
            part.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Part deleted successfully'
            })
        except CustomizableWatchPart.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Part not found'
            }, status=404)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@require_POST
@csrf_protect
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_watch_part_option(request, option_id):
    try:
        option = get_object_or_404(WatchPartOption, id=option_id)
        option.delete()
        return JsonResponse({'success': True, 'message': 'Watch part option deleted successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_watch_part(request, part_id):
    if request.method == 'POST':
        customizable_part = get_object_or_404(CustomizableWatchPart, id=part_id)
        customizable_part.delete()
        return JsonResponse({'success': True, 'message': 'Watch part deleted successfully.'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_customizable_watch(request, watch_id):
    watch = get_object_or_404(CustomizableWatch, id=watch_id)
    customizable_parts = CustomizableWatchPart.objects.filter(customizable_watch=watch)
    
    # Get existing part types for this watch
    existing_part_types = customizable_parts.values_list('part__part_name_id', flat=True)
    
    # Get all part names and filter out existing ones
    all_part_names = WatchPartName.objects.all()
    available_part_names = [pn for pn in all_part_names if pn.id not in existing_part_types]
    
    if request.method == 'POST':
        form = CustomizableWatchForm(request.POST, request.FILES, instance=watch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Watch updated successfully.')
            return redirect('adminapp:customizable_watch_list')
    else:
        form = CustomizableWatchForm(instance=watch)
    
    context = {
        'watch': watch,
        'form': form,
        'customizable_parts': customizable_parts,
        'part_names': all_part_names,
        'existing_part_types': existing_part_types,
        'available_part_names': available_part_names,
        'option_form': WatchPartOptionForm()
    }
    return render(request, 'adminapp/edit_customizable_watch.html', context)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_watch_part_ajax(request, watch_id):
    watch = get_object_or_404(CustomizableWatch, id=watch_id)
    form = WatchPartForm(request.POST)
    
    if form.is_valid():
        part_name = form.cleaned_data['part_name']
        
        # Check if this part type already exists for the watch
        existing_part = CustomizableWatchPart.objects.filter(
            customizable_watch=watch,
            part__part_name=part_name
        ).exists()
        
        if existing_part:
            return JsonResponse({
                'success': False,
                'errors': {
                    'part_name': ['This part type has already been added to the watch.']
                }
            })
        
        try:
            with transaction.atomic():
                part = form.save()
                CustomizableWatchPart.objects.create(
                    customizable_watch=watch,
                    part=part
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Part added successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'errors': {'__all__': [str(e)]}
            })
    
    return JsonResponse({
        'success': False,
        'errors': form.errors
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def analysis_view(request):
    # Get the selected time range from the request, default to 28 days
    time_range = request.GET.get('time_range', '28')
    
    # Define time ranges
    time_ranges = {
        '7': timedelta(days=7),
        '28': timedelta(days=28),
        '90': timedelta(days=90),
        '365': timedelta(days=365),
    }
    
    # Handle custom date range
    if time_range == 'custom':
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date and end_date:
            start_date = make_aware(timezone.datetime.strptime(start_date, '%Y-%m-%d'))
            end_date = make_aware(timezone.datetime.strptime(end_date, '%Y-%m-%d')).replace(hour=23, minute=59, second=59)
        else:
            # Default to last 28 days if custom dates are not provided
            end_date = timezone.now()
            start_date = end_date - timedelta(days=27)
    elif time_range in time_ranges:
        end_date = timezone.now()
        start_date = end_date - time_ranges[time_range]
    else:
        # Handle year and month selections
        year = int(time_range[:4])
        if len(time_range) == 4:  # Year selection
            start_date = make_aware(timezone.datetime(year, 1, 1))
            end_date = make_aware(timezone.datetime(year, 12, 31, 23, 59, 59))
        else:  # Month selection
            month = int(time_range[5:])
            start_date = make_aware(timezone.datetime(year, month, 1))
            _, last_day = calendar.monthrange(year, month)
            end_date = make_aware(timezone.datetime(year, month, last_day, 23, 59, 59))

    # Total watches sold
    total_watches = OrderItem.objects.filter(order__created_at__gte=start_date, order__created_at__lte=end_date).aggregate(Sum('quantity'))['quantity__sum'] or 0

    # Calculate revenue
    total_revenue = OrderItem.objects.filter(order__created_at__gte=start_date, order__created_at__lte=end_date).aggregate(
        total=Sum(F('quantity') * F('price')))['total'] or 0

    # Compare with previous period
    previous_start = start_date - (end_date - start_date)
    previous_revenue = OrderItem.objects.filter(order__created_at__gte=previous_start, order__created_at__lt=start_date).aggregate(
        total=Sum(F('quantity') * F('price')))['total'] or 0

    if previous_revenue > 0:
        revenue_comparison = round(((total_revenue - previous_revenue) / previous_revenue) * 100, 2)
    elif total_revenue > 0:
        revenue_comparison = 100  # 100% increase if there was no previous revenue but there is current revenue
    else:
        revenue_comparison = 0  # No change if both periods have zero revenue

    # New customers
    new_customers = User.objects.filter(date_joined__gte=start_date, date_joined__lte=end_date).count()
    previous_new_customers = User.objects.filter(date_joined__gte=previous_start, date_joined__lt=start_date).count()
    customer_comparison = round(((new_customers - previous_new_customers) / previous_new_customers) * 100 if previous_new_customers else 0, 2)
    
    # Create a list of all dates in the range
    all_dates = [start_date.date() + timedelta(days=x) for x in range((end_date.date() - start_date.date()).days + 1)]

    # Get the sales data
    sales_data = OrderItem.objects.filter(
        order__created_at__date__gte=start_date.date(),
        order__created_at__date__lte=end_date.date()
    ).annotate(
        date=TruncDate('order__created_at')
    ).values('date').annotate(
        sales=Sum('quantity')
    ).order_by('date')

    # Convert to a dictionary for easy lookup
    sales_dict = {item['date']: item['sales'] for item in sales_data}

    # Create the final data, including zero sales days
    daily_sales = [{'date': date, 'sales': sales_dict.get(date, 0)} for date in all_dates]

    date_labels = [item['date'].strftime('%d %b') for item in daily_sales]
    daily_sales_data = [item['sales'] for item in daily_sales]

    # Realtime data (last 48 hours)
    last_48_hours = timezone.now() - timedelta(hours=48)
    realtime_sales = OrderItem.objects.filter(order__created_at__gte=last_48_hours)\
        .annotate(hour=TruncHour('order__created_at'))\
        .values('hour')\
        .annotate(sales=Sum('quantity'))\
        .order_by('hour')

    realtime_labels = [(timezone.now() - timedelta(hours=i)).strftime('%H:%M') for i in range(48, 0, -1)]
    realtime_data = [0] * 48

    for sale in realtime_sales:
        hours_ago = int((timezone.now() - sale['hour']).total_seconds() / 3600)
        if hours_ago < 48:
            realtime_data[47 - hours_ago] = sale['sales']

    recent_sales = sum(realtime_data)

    # Top selling watches
    top_watches = BaseWatch.objects.annotate(
        sales_count=Sum('orderitem__quantity')
    ).filter(
        orderitem__order__created_at__gte=start_date,
        orderitem__order__created_at__lte=end_date,
        primary_image__isnull=False
    ).order_by('-sales_count')[:5]

    # Total customers
    total_customers = User.objects.count()

    # Prepare date range options for the template
    current_year = timezone.now().year
    date_range_options = [
        {'value': '7', 'label': 'Last 7 days'},
        {'value': '28', 'label': 'Last 28 days'},
        {'value': '90', 'label': 'Last 90 days'},
        {'value': '365', 'label': 'Last 365 days'},
        {'value': str(current_year), 'label': str(current_year)},
        {'value': str(current_year - 1), 'label': str(current_year - 1)},
    ]

    # Add current year's months
    current_date = timezone.now()
    current_year = current_date.year
    current_month = current_date.month

    for month_offset in range(2, -1, -1):
        target_date = current_date - relativedelta(months=month_offset)
        date_range_options.append({
            'value': f"{target_date.year}-{target_date.month:02d}",
            'label': f"{calendar.month_name[target_date.month]} {target_date.year}"
        })

    context = {
        'total_watches': total_watches,
        'total_revenue': total_revenue,  # Changed from formatted string to raw value
        'revenue_comparison': revenue_comparison,
        'new_customers': new_customers,
        'customer_comparison': customer_comparison,
        'start_date': start_date,
        'end_date': end_date,
        'date_labels': json.dumps(date_labels),
        'daily_sales': json.dumps(daily_sales_data),
        'recent_sales': recent_sales,
        'realtime_labels': json.dumps(realtime_labels),
        'realtime_data': json.dumps(realtime_data),
        'top_watches': top_watches,
        'total_customers': total_customers,
        'date_range_options': date_range_options,
        'selected_range': time_range,
    }

    return render(request, 'adminapp/analysis.html', context)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_part_option_ajax(request):
    part_id = request.POST.get('part_id')
    
    if not part_id:
        return JsonResponse({
            'success': False,
            'message': 'Part ID is required'
        }, status=400)
    
    try:
        # Check if we're getting a CustomizableWatchPart or a WatchPart
        try:
            customizable_part = CustomizableWatchPart.objects.get(id=part_id)
            part = customizable_part.part
            is_customizable_part = True
        except CustomizableWatchPart.DoesNotExist:
            try:
                part = WatchPart.objects.get(id=part_id)
                is_customizable_part = False
            except WatchPart.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Part not found'
                }, status=404)
        
        # Handle direct color submission (without form)
        if 'color' in request.POST:
            name = request.POST.get('name')
            price = request.POST.get('price')
            stock = request.POST.get('stock', 0)
            color = request.POST.get('color')
            
            if not name or not price:
                return JsonResponse({
                    'success': False,
                    'message': 'Name and price are required'
                }, status=400)
            
            # Create option
            option = WatchPartOption.objects.create(
                part=part,
                name=name,
                price=price,
                stock=stock,
                color=color
            )
            
            # If this is a customizable part, add the option to it
            if is_customizable_part:
                customizable_part.options.add(option)
            
            return JsonResponse({
                'success': True,
                'option_id': option.id,
                'message': 'Option added successfully'
            })
        else:
            # Handle form submission (with files)
            form = WatchPartOptionForm(request.POST, request.FILES)
            
            if form.is_valid():
                option = form.save(commit=False)
                option.part = part
                
                # Add color if specified
                if 'color' in request.POST and request.POST.get('color'):
                    option.color = request.POST.get('color')
                    
                option.save()
                
                # If this is a customizable part, add the option to it
                if is_customizable_part:
                    customizable_part.options.add(option)
                
                html = render_to_string('adminapp/partials/option_card.html', {
                    'option': option
                }, request=request)
                
                return JsonResponse({
                    'success': True,
                    'html': html,
                    'option_id': option.id
                })
            
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_part_option(request):
    option_id = request.POST.get('option_id')
    
    if not option_id:
        return JsonResponse({
            'success': False,
            'message': 'Option ID is required'
        }, status=400)
    
    try:
        option = WatchPartOption.objects.get(id=option_id)
        
        # Delete associated files if they exist
        if option.texture:
            option.texture.delete()
        if option.thumbnail:
            option.thumbnail.delete()
            
        # Delete the option
        option.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Option deleted successfully'
        })
    except WatchPartOption.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Option not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_watch_part_ajax(request):
    part_id = request.POST.get('part_id')
    description = request.POST.get('description')
    model_path = request.POST.get('model_path')
    
    if not part_id:
        return JsonResponse({
            'success': False,
            'message': 'Part ID is required'
        }, status=400)
    
    try:
        customizable_part = CustomizableWatchPart.objects.get(id=part_id)
        part = customizable_part.part
        
        part.description = description
        part.model_path = model_path
        part.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Part updated successfully'
        })
    except CustomizableWatchPart.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Part not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@require_POST
def edit_part_option_ajax(request):
    try:
        option_id = request.POST.get('option_id')
        option = WatchPartOption.objects.get(id=option_id)
        
        # Update name
        option.name = request.POST.get('name')
        
        # Update price if provided
        if 'price' in request.POST:
            option.price = request.POST.get('price')
            
        # Update stock if provided
        if 'stock' in request.POST:
            option.stock = request.POST.get('stock')
        
        # Update color if provided
        if 'color' in request.POST:
            option.color = request.POST.get('color')
        
        # Update thumbnail if provided
        if 'thumbnail' in request.FILES:
            if option.thumbnail:
                option.thumbnail.delete()
            option.thumbnail = request.FILES['thumbnail']
            
        # Update texture if provided
        if 'texture' in request.FILES:
            if option.texture:
                option.texture.delete()
            option.texture = request.FILES['texture']
            
        option.save()
        
        return JsonResponse({'success': True})
    except WatchPartOption.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Option not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def manage_prices(request):
    watches = CustomizableWatch.objects.all()
    parts = CustomizableWatchPart.objects.all().prefetch_related(
        'part__part_name', 
        'options'
    )
    
    context = {
        'watches': watches,
        'parts': parts,
    }
    return render(request, 'adminapp/custom_watch_manage_prices.html', context)

@login_required
@require_POST
def update_watch_price(request):
    try:
        watch_id = request.POST.get('watch_id')
        price = request.POST.get('price')
        
        watch = CustomizableWatch.objects.get(id=watch_id)
        watch.base_price = price
        watch.save()
        
        return JsonResponse({'success': True})
    except CustomizableWatch.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Watch not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
@require_POST
def update_option_price(request):
    try:
        option_id = request.POST.get('option_id')
        price = float(request.POST.get('price'))
        
        option = WatchPartOption.objects.get(id=option_id)
        if price < 0:
            return JsonResponse({'success': False, 'message': 'Price cannot be negative'})
        
        option.price = price
        option.save()
        return JsonResponse({'success': True})
        
    except WatchPartOption.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Option not found'})
    except ValueError:
        return JsonResponse({'success': False, 'message': 'Invalid price format'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def get_watch_parts(request):
    """
    API endpoint to get watch parts for the selected watch
    """
    watch_id = request.GET.get('watch_id')
    if not watch_id:
        return JsonResponse({'success': False, 'message': 'Watch ID is required'})
    
    try:
        watch = CustomizableWatch.objects.get(id=watch_id)
        parts = []
        
        for part in watch.customizable_parts.all():
            parts.append({
                'id': part.part.id,
                'name': part.part.part_name.name,
                'model_path': part.part.model_path
            })
        
        return JsonResponse({'success': True, 'parts': parts})
    except CustomizableWatch.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Watch not found'})

@login_required
def get_part_options(request):
    """
    API endpoint to get options for a specific part
    """
    part_id = request.GET.get('part_id')
    if not part_id:
        return JsonResponse({'success': False, 'message': 'Part ID is required'})
    
    try:
        part = WatchPart.objects.get(id=part_id)
        options = []
        
        for option in part.options.all():
            options.append({
                'id': option.id,
                'name': option.name,
                'price': str(option.price),
                'stock': option.stock,
                'color': option.color
            })
        
        return JsonResponse({'success': True, 'options': options})
    except WatchPart.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Part not found'})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def configure_watch_parts(request, watch_id):
    """
    View for configuring watch parts with 3D interactive editor
    """
    try:
        watch = CustomizableWatch.objects.get(id=watch_id)
    except CustomizableWatch.DoesNotExist:
        messages.error(request, 'Watch not found')
        return redirect('adminapp:customizable_watch_list')
    
    if request.method == 'POST':
        # Process the submitted part configuration
        try:
            part_data = json.loads(request.POST.get('part_data', '[]'))
            
            # Process each configured part
            for part_config in part_data:
                # Get or create part name
                part_name, _ = WatchPartName.objects.get_or_create(name=part_config['category'])
                
                # Create the watch part
                part, created = WatchPart.objects.get_or_create(
                    part_name=part_name,
                    model_path=part_config['modelPath'],
                    defaults={
                        'description': part_config['description']
                    }
                )
                
                if not created:
                    # Update the description if part already exists
                    part.description = part_config['description']
                    part.save()
                
                # Get or create the customizable part
                customizable_part, _ = CustomizableWatchPart.objects.get_or_create(
                    customizable_watch=watch,
                    part=part
                )
                
                # Process color options
                if 'colorOptions' in part_config and part_config['colorOptions']:
                    for color_option in part_config['colorOptions']:
                        # Create the option
                        option = WatchPartOption.objects.create(
                            part=part,
                            name=color_option['name'],
                            price=color_option['price'],
                            color=color_option['color'],
                            stock=10  # Default stock
                        )
                        
                        # Add to customizable part
                        customizable_part.options.add(option)
            
            messages.success(request, 'Watch parts configured successfully!')
            return redirect('adminapp:view_customizable_watch', watch_id=watch.id)
            
        except Exception as e:
            messages.error(request, f'Error saving part configuration: {str(e)}')
    
    context = {
        'watch': watch
    }
    return render(request, 'adminapp/3d_part_configurator.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def get_model_path(request, watch_id):
    """
    API to get the model path for a watch
    """
    try:
        watch = CustomizableWatch.objects.get(id=watch_id)
        return JsonResponse({
            'success': True,
            'model_path': watch.model_file.url
        })
    except CustomizableWatch.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Watch not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
def custom_watch_orders(request):
    orders = CustomWatchOrder.objects.select_related(
        'user', 
        'customizable_watch'
    ).order_by('-created_at')
    
    return render(request, 'adminapp/custom_watch_orders.html', {
        'orders': orders
    })

@login_required
def custom_watch_order_detail(request, order_id):
    order = get_object_or_404(
        CustomWatchOrder.objects.select_related(
            'user', 
            'customizable_watch'
        ).prefetch_related(
            'selected_parts__part__part_name',
            'selected_parts__selected_option'
        ),
        id=order_id
    )
    
    return render(request, 'adminapp/custom_watch_order_detail.html', {
        'order': order
    })

@login_required
@require_POST
def update_custom_watch_order_status(request, order_id):
    try:
        order = CustomWatchOrder.objects.get(id=order_id)
        new_status = request.POST.get('status')
        
        if new_status == 'approved':
            order.status = new_status
            send_mail(
                'Order Approved',
                f'Your order #{order.order_id} has been approved and will be manufactured soon.',
                settings.DEFAULT_FROM_EMAIL,
                [order.user.email],
            )
            
        elif new_status == 'ready_to_ship':
            order.status = new_status
            # Set estimated delivery date (4-5 days from now)
            order.estimated_delivery_date = timezone.now().date() + timedelta(days=4)
            
        elif new_status == 'shipped':
            order.status = new_status
            order.shipping_started_date = timezone.now()
            send_mail(
                'Order Shipped',
                f'Your order #{order.order_id} has been shipped! Estimated delivery: {order.estimated_delivery_date}',
                settings.DEFAULT_FROM_EMAIL,
                [order.user.email],
            )
            
        order.save()
        return JsonResponse({'success': True})
        
    except CustomWatchOrder.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})

@permission_required('adminapp.can_manage_staff')
def staff_list(request):
    staff_members = StaffMember.objects.select_related('user').all()
    return render(request, 'adminapp/staff_list.html', {'staff_members': staff_members})

@permission_required('adminapp.can_manage_staff')
def add_staff(request):
    if request.method == 'POST':
        user_form = StaffCreationForm(request.POST)
        profile_form = StaffProfileForm(request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.is_staff = True
            user.save()
            
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            
            # Assign permissions based on role
            assign_role_permissions(user, profile.role)
            
            messages.success(request, 'Staff member created successfully')
            return redirect('adminapp:staff_list')
    else:
        user_form = StaffCreationForm()
        profile_form = StaffProfileForm()
    
    return render(request, 'adminapp/add_staff.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@permission_required('adminapp.can_manage_staff')
def toggle_staff_access(request, staff_id):
    if request.method == 'POST':
        staff = get_object_or_404(StaffMember, id=staff_id)
        staff.is_active = not staff.is_active
        staff.user.is_active = staff.is_active
        staff.save()
        staff.user.save()
        
        status = 'activated' if staff.is_active else 'deactivated'
        messages.success(request, f'Staff access {status} successfully')
        
        return JsonResponse({'success': True, 'is_active': staff.is_active})
    return JsonResponse({'success': False}, status=400)

def assign_role_permissions(user, role):
    """Helper function to assign permissions based on role"""
    permissions = {
        'support': [
            'view_ticket',
            'add_ticketresponse',
            'change_ticket',
            'view_basewatch',
            'view_category',
            'view_brand',
        ],
        'qa': [
            'view_basewatch',
            'change_basewatch',
            'view_category',
            'view_brand',
            'add_feature',
            'change_feature',
            'view_feature',
        ]
    }
    
    # Clear existing permissions
    user.user_permissions.clear()
    
    # Assign new permissions
    if role in permissions:
        for perm_codename in permissions[role]:
            perm = Permission.objects.get(codename=perm_codename)
            user.user_permissions.add(perm)

@login_required
@user_type_required('admin')
def delivery_agents_list(request):
    """View all delivery agents"""
    delivery_agents = User.objects.filter(role='delivery').select_related('delivery_profile')
    
    context = {
        'delivery_agents': delivery_agents,
    }
    
    return render(request, 'adminapp/delivery_agents_list.html', context)

@login_required
@user_type_required('admin')
def create_delivery_agent(request):
    """Create a new delivery agent"""
    if request.method == 'POST':
        user_form = DeliveryAgentCreationForm(request.POST)
        profile_form = DeliveryAgentProfileForm(request.POST, request.FILES)
        
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                # Create user
                user = user_form.save()
                
                # Create profile
                profile = profile_form.save(commit=False)
                profile.user = user
                profile.is_active = True
                profile.save()
                
                # Create metrics
                DeliveryMetrics.objects.create(delivery_person=user)
            
            messages.success(request, f"Delivery agent {user.fullname} created successfully.")
            return redirect('adminapp:delivery_agents_list')
    else:
        user_form = DeliveryAgentCreationForm()
        profile_form = DeliveryAgentProfileForm()
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'title': 'Add Delivery Agent',
    }
    
    return render(request, 'adminapp/create_delivery_agent.html', context)

@login_required
@user_type_required('admin')
def view_delivery_agent(request, user_id):
    """View details of a delivery agent"""
    delivery_agent = get_object_or_404(User.objects.filter(role='delivery'), id=user_id)
    
    try:
        profile = DeliveryProfile.objects.get(user=delivery_agent)
    except DeliveryProfile.DoesNotExist:
        profile = None
    
    try:
        metrics = DeliveryMetrics.objects.get(delivery_person=delivery_agent)
    except DeliveryMetrics.DoesNotExist:
        metrics = None
    
    # Get assigned orders
    assigned_orders = Order.objects.filter(
        assigned_to=delivery_agent,
        status__in=['assigned_to_delivery', 'out_for_delivery']
    ).order_by('-created_at')
    
    # Get completed orders
    completed_orders = Order.objects.filter(
        assigned_to=delivery_agent,
        status='delivered'
    ).order_by('-delivery_date')[:10]
    
    context = {
        'agent': delivery_agent,
        'profile': profile,
        'metrics': metrics,
        'assigned_orders': assigned_orders,
        'completed_orders': completed_orders,
        'title': f'Delivery Agent: {delivery_agent.fullname}',
    }
    
    return render(request, 'adminapp/view_delivery_agent.html', context)

@login_required
@user_type_required('admin')
@require_POST
def toggle_delivery_agent(request, user_id):
    """Toggle active status of a delivery agent"""
    print(f"Toggle requested for user_id: {user_id}")
    delivery_agent = get_object_or_404(User.objects.filter(role='delivery'), id=user_id)
    
    try:
        profile = DeliveryProfile.objects.get(user=delivery_agent)
        # Print before values for debugging
        print(f"BEFORE: user.is_active={delivery_agent.is_active}, profile.is_active={profile.is_active}")
        
        # Toggle both the profile and user's active status
        profile.is_active = not profile.is_active
        delivery_agent.is_active = profile.is_active
        
        # Save both models in a transaction to ensure consistency
        with transaction.atomic():
            profile.save(update_fields=['is_active'])
            delivery_agent.save(update_fields=['is_active'])
        
        # Verify the changes after saving
        # Refresh from database to confirm changes
        delivery_agent.refresh_from_db()
        profile.refresh_from_db()
        print(f"AFTER: user.is_active={delivery_agent.is_active}, profile.is_active={profile.is_active}")
        
        status = 'activated' if profile.is_active else 'deactivated'
        messages.success(request, f"Delivery agent {delivery_agent.fullname} has been {status}.")
        
        return JsonResponse({
            'success': True, 
            'is_active': profile.is_active,
            'user_active': delivery_agent.is_active,
            'message': f"Delivery agent has been {status}."
        })
    except DeliveryProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'})
    except Exception as e:
        print(f"Error in toggle_delivery_agent: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_type_required('admin')
def edit_delivery_agent(request, user_id):
    """Edit a delivery agent's details"""
    delivery_agent = get_object_or_404(User.objects.filter(role='delivery'), id=user_id)
    
    try:
        profile = DeliveryProfile.objects.get(user=delivery_agent)
    except DeliveryProfile.DoesNotExist:
        profile = None
    
    if request.method == 'POST':
        user_form = DeliveryAgentCreationForm(request.POST, instance=delivery_agent)
        profile_form = DeliveryAgentProfileForm(request.POST, request.FILES, instance=profile)
        
        # Remove password validation if no new password provided
        if not request.POST.get('password1'):
            user_form.fields.pop('password1')
            user_form.fields.pop('password2')
        
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                # Update user
                user = user_form.save(commit=False)
                if request.POST.get('password1'):
                    user.set_password(user_form.cleaned_data.get('password1'))
                user.save()
                
                # Update profile
                profile = profile_form.save(commit=False)
                profile.user = user
                profile.save()
            
            messages.success(request, f"Delivery agent {user.fullname} updated successfully.")
            return redirect('adminapp:view_delivery_agent', user_id=user.id)
    else:
        user_form = DeliveryAgentCreationForm(instance=delivery_agent)
        profile_form = DeliveryAgentProfileForm(instance=profile)
        
        # Remove password fields for edit form
        user_form.fields.pop('password1')
        user_form.fields.pop('password2')
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'agent': delivery_agent,
        'profile': profile,
        'title': f'Edit Delivery Agent: {delivery_agent.fullname}',
    }
    
    return render(request, 'adminapp/edit_delivery_agent.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def model_editor(request, watch_id):
    """
    Provides a 3D model editor interface for modifying watch models
    """
    try:
        watch = CustomizableWatch.objects.get(id=watch_id)
    except CustomizableWatch.DoesNotExist:
        messages.error(request, "Watch not found")
        return redirect('adminapp:customizable_watch_list')
    
    # Handle model data submission
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Get model data from request
            model_data = request.POST.get('model_data')
            
            if not model_data:
                return JsonResponse({'success': False, 'message': 'No model data received'})
            
            # Create temporary file for model data
            import tempfile
            import os
            import json
            from django.core.files import File
            
            # Create temp directory if it doesn't exist
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix='.gltf', dir=temp_dir, delete=False) as tmp:
                # Write model data to file
                tmp.write(json.dumps(json.loads(model_data), indent=2).encode('utf-8'))
                tmp_path = tmp.name
            
            # Update watch model file
            with open(tmp_path, 'rb') as f:
                watch.model_file.save(f'edited_model_{watch_id}.gltf', File(f), save=True)
            
            # Remove temp file
            os.unlink(tmp_path)
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    context = {
        'watch': watch,
        'page_title': f'3D Model Editor - {watch.name}'
    }
    return render(request, 'adminapp/3d_model_editor.html', context)

def manage_returns(request):
    """View and manage return requests"""
    # Get return requests
    return_requests = Order.objects.filter(
        status__in=['return_requested', 'return_approved', 'return_scheduled', 'return_in_transit', 'return_completed', 'return_rejected']
    ).order_by('-return_requested_at')
    
    # Filter options
    status_filter = request.GET.get('status', '')
    if status_filter:
        return_requests = return_requests.filter(status=status_filter)
    
    # Paginate
    paginator = Paginator(return_requests, 20)
    page_number = request.GET.get('page', 1)
    returns = paginator.get_page(page_number)
    
    # Get delivery personnel for assignment
    delivery_personnel = User.objects.filter(role='delivery', is_active=True)
    
    context = {
        'returns': returns,
        'status_filter': status_filter,
        'status_choices': ['return_requested', 'return_approved', 'return_scheduled', 'return_in_transit', 'return_completed', 'return_rejected'],
        'delivery_personnel': delivery_personnel,
    }
    
    return render(request, 'adminapp/manage_returns.html', context)

def return_detail(request, order_id):
    """View details of a return request"""
    order = get_object_or_404(Order, order_id=order_id)
    
    # Ensure it's a return
    if not order.status.startswith('return_'):
        messages.error(request, "This order is not a return request.")
        return redirect('adminapp:manage_returns')
    
    # Forms
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            # Approve return request
            order.status = 'return_approved'
            order.return_approved_at = timezone.now()
            order.save()
            
            # Notify customer
            subject = f"Your Return Request for Order #{order.order_id} has been Approved"
            message = f"Your return request has been approved. We'll schedule a pickup soon."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
            
            messages.success(request, f"Return request for order #{order.order_id} has been approved.")
            
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '')
            if not reason:
                messages.error(request, "Please provide a rejection reason.")
                return redirect('adminapp:return_detail', order_id=order_id)
                
            # Reject return request
            order.status = 'return_rejected'
            order.return_notes = f"{order.return_notes or ''}\n\nRejection reason: {reason}"
            order.save()
            
            # Notify customer
            subject = f"Your Return Request for Order #{order.order_id} has been Rejected"
            message = f"We're sorry, but your return request has been rejected. Reason: {reason}"
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
            
            messages.success(request, f"Return request for order #{order.order_id} has been rejected.")
            
        elif action == 'assign':
            delivery_id = request.POST.get('delivery_person')
            if not delivery_id:
                messages.error(request, "Please select a delivery person.")
                return redirect('adminapp:return_detail', order_id=order_id)
                
            delivery_person = get_object_or_404(User, id=delivery_id, role='delivery')
            
            # Assign return
            order.return_assigned_to = delivery_person
            order.status = 'return_scheduled'
            order.save()
            
            # Generate return OTP
            from deliveryapp.utils import generate_return_otp
            order.return_otp = generate_return_otp()
            order.return_otp_created_at = timezone.now()
            order.save()
            
            # Notify customer
            subject = f"Return Pickup Scheduled for Order #{order.order_id}"
            message = f"A return pickup has been scheduled for your order. Our delivery partner will contact you soon. Please use OTP {order.return_otp} to verify the pickup."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [order.user.email])
            
            # Notify delivery person
            subject = f"New Return Pickup Assigned: Order #{order.order_id}"
            message = f"A new return pickup has been assigned to you. Please check your dashboard for details."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [delivery_person.email])
            
            messages.success(request, f"Return pickup for order #{order.order_id} has been assigned to {delivery_person.get_full_name()}.")
    
    context = {
        'order': order,
        'delivery_personnel': User.objects.filter(role='delivery', is_active=True),
    }
    
    return render(request, 'adminapp/return_detail.html', context)

def manage_orders(request):
    """View and manage orders"""
    # Get orders
    orders = Order.objects.all().order_by('-created_at')
    
    # Filter options
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Paginate
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page', 1)
    order_list = paginator.get_page(page_number)
    
    context = {
        'orders': order_list,
        'status_filter': status_filter,
        'status_choices': Order.STATUS_CHOICES,
    }
    
    return render(request, 'adminapp/manage_orders.html', context)

