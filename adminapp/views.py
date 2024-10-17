from django.forms import formset_factory, inlineformset_factory
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from mainapp.decorators import user_type_required
from vendorapp.models import VendorProfile
from .models import Brand, Category, BaseWatch, WatchImage, Feature, Material
from .forms import BrandForm, CategoryForm, BaseWatchForm, FeatureForm, MaterialForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import get_user_model,update_session_auth_hash
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.cache import never_cache
from mainapp.models import Order, OrderItem
import re
from django.db import IntegrityError
from django.db.models import Q, Sum, Count, F
from django.views.decorators.http import require_POST
from watch_customizer.models import CustomizableWatch, CustomizableWatchPart, CustomWatchOrder, CustomWatchOrderPart, WatchPart, WatchPartOption
from watch_customizer.forms import CustomizableWatchForm, WatchPartForm, WatchPartOptionForm, ModelUploadForm
from django.forms.models import modelformset_factory
from django.views.decorators.csrf import csrf_protect
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db.models.functions import TruncDate
from dateutil.relativedelta import relativedelta
import json
import random
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
            
            # Handle image uploads
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
    admin = request.user
    context = {
        'admin': admin,
        # Add any additional context data you want to display
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
    WatchPartFormSet = formset_factory(WatchPartForm, formset=BaseWatchPartFormSet, extra=1, can_delete=True)
    
    if request.method == 'POST':
        formset = WatchPartFormSet(request.POST, prefix='watchpart')
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    part = form.save(commit=False)
                    part.save()
                    CustomizableWatchPart.objects.create(customizable_watch=watch, part=part)
            messages.success(request, 'Watch parts added successfully.')
            return redirect('adminapp:add_part_options', watch_id=watch.id)
    else:
        formset = WatchPartFormSet(prefix='watchpart')
    
    return render(request, 'adminapp/add_watch_parts.html', {'formset': formset, 'watch': watch})

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_part_options(request, watch_id):
    watch = get_object_or_404(CustomizableWatch, id=watch_id)
    customizable_parts = CustomizableWatchPart.objects.filter(customizable_watch=watch)
    
    if request.method == 'POST':
        all_valid = True
        for part in customizable_parts:
            OptionFormSet = modelformset_factory(WatchPartOption, form=WatchPartOptionForm, extra=0)
            formset = OptionFormSet(request.POST, request.FILES, prefix=f'options_{part.id}')
            
            if formset.is_valid():
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.part = part.part
                    instance.save()
                part.options.add(*instances)
            else:
                all_valid = False
                break
        
        if all_valid:
            messages.success(request, 'Customizable watch options added successfully.')
            return redirect('adminapp:customizable_watch_list')
        else:
            messages.error(request, 'There was an error adding the options. Please check the form and try again.')
    else:
        formsets = []
        for part in customizable_parts:
            OptionFormSet = modelformset_factory(WatchPartOption, form=WatchPartOptionForm, extra=1)
            formset = OptionFormSet(queryset=WatchPartOption.objects.none(), prefix=f'options_{part.id}')
            formsets.append((part, formset))
    
    return render(request, 'adminapp/add_part_options.html', {'watch': watch, 'formsets': formsets})

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
                'roughness': option.roughness,
                'metalness': option.metalness,
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
def delete_watch_part(request, part_id):
    try:
        customizable_part = get_object_or_404(CustomizableWatchPart, id=part_id)
        customizable_part.delete()
        return JsonResponse({'success': True, 'message': 'Watch part deleted successfully.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

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
def delete_watch_part_option(request, option_id):
    if request.method == 'POST':
        option = get_object_or_404(WatchPartOption, id=option_id)
        option.delete()
        return JsonResponse({'success': True, 'message': 'Watch part option deleted successfully.'})
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_customizable_watch(request, watch_id):
    watch = get_object_or_404(CustomizableWatch, id=watch_id)
    customizable_parts = CustomizableWatchPart.objects.filter(customizable_watch=watch).prefetch_related('part', 'part__part_name', 'options')
    
    if request.method == 'POST':
        form = CustomizableWatchForm(request.POST, request.FILES, instance=watch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customizable watch updated successfully.')
            return redirect('adminapp:view_customizable_watch', watch_id=watch.id)
    else:
        form = CustomizableWatchForm(instance=watch)
    
    context = {
        'form': form,
        'watch': watch,
        'customizable_parts': customizable_parts,
    }
    return render(request, 'adminapp/edit_customizable_watch.html', context)

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_watch_part(request, part_id):
    customizable_part = get_object_or_404(CustomizableWatchPart, id=part_id)
    watch = customizable_part.customizable_watch
    
    if request.method == 'POST':
        form = WatchPartForm(request.POST, instance=customizable_part.part)
        if form.is_valid():
            form.save()
            messages.success(request, 'Watch part updated successfully.')
            return redirect('adminapp:edit_customizable_watch', watch_id=watch.id)
    else:
        form = WatchPartForm(instance=customizable_part.part)
    
    context = {
        'form': form,
        'customizable_part': customizable_part,
        'watch': watch,
    }
    return render(request, 'adminapp/edit_watch_part.html', context)

@never_cache
@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_watch_part_option(request, option_id):
    option = get_object_or_404(WatchPartOption, id=option_id)
    customizable_part = CustomizableWatchPart.objects.get(options=option)
    watch = customizable_part.customizable_watch
    
    if request.method == 'POST':
        form = WatchPartOptionForm(request.POST, request.FILES, instance=option)
        if form.is_valid():
            form.save()
            messages.success(request, 'Watch part option updated successfully.')
            return redirect('adminapp:edit_customizable_watch', watch_id=watch.id)
    else:
        form = WatchPartOptionForm(instance=option)
    
    context = {
        'form': form,
        'option': option,
        'customizable_part': customizable_part,
        'watch': watch,
    }
    return render(request, 'adminapp/edit_watch_part_option.html', context)

from django.db.models import Sum, F, Count
from django.db.models.functions import TruncHour, TruncDate
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import json
import calendar

from django.utils import timezone
from django.utils.timezone import make_aware
import pytz

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