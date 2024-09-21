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
from mainapp.models import Order
import re
from django.db import IntegrityError
from django.db.models import Q
from django.views.decorators.http import require_POST

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

