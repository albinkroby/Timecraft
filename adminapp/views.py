from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from mainapp.decorators import user_type_required
from vendorapp.models import VendorProfile
from .models import Brand, Category, BaseWatch, WatchImage
from .forms import BrandForm, CategoryForm, BaseWatchForm
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.cache import never_cache
# Create your views here.
User=get_user_model()

@never_cache
@login_required
@user_type_required('admin')
def index(request):
    # Get total users
    total_users = User.objects.count()
    
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
    
    
    # total_orders = Order.objects.count()
    # new_orders_this_week = Order.objects.filter(created_at__gte=one_week_ago).count()
    # order_growth_percentage = (new_orders_this_week / total_orders) * 100 if total_orders > 0 else 0
    
    total_orders = 0
    order_growth_percentage = 0
    
    context = {
        'total_users': total_users,
        'user_growth_percentage': round(user_growth_percentage, 1),
        'total_products': total_products,
        'product_growth_percentage': round(product_growth_percentage, 1),
        'total_orders': total_orders,
        'order_growth_percentage': order_growth_percentage,
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
    users = User.objects.all().order_by('-date_joined')
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