from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from mainapp.decorators import user_type_required
from .forms import VendorRegistrationForm, BaseWatchForm
from django.contrib import messages
from .models import VendorProfile
from mainapp.utils import hash_url
from django.urls import reverse
from adminapp.models import Category, BaseWatch, WatchImage
from django.shortcuts import get_object_or_404
import os

# Create your views here.


def home(request):
    return render(request,'vendorapp/home.html')

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

@login_required
@user_type_required('vendor')
def index(request):
    vendor_profile = VendorProfile.objects.get(user=request.user)
    if vendor_profile.approval_status == 'Approved':
        return render(request, 'vendorapp/index.html')
    else:
        return render(request, 'vendorapp/vendor_application_pending.html')
    
    
@user_type_required('vendor')
def add_product(request):
    if request.method == 'POST':
        form = BaseWatchForm(request.POST, request.FILES)
        if form.is_valid():
            watch = form.save(commit=False)
            watch.vendor = request.user.vendorprofile
            watch.save()

            # Handle primary image
            if 'primary_image' in request.FILES:
                watch.primary_image = request.FILES['primary_image']
                watch.save()

            # Handle additional images
            images = request.FILES.getlist('product_images')
            for image in images:
                WatchImage.objects.create(base_watch=watch, image=image)

            messages.success(request, f'Product "{watch.model_name}" has been added successfully!')
            return redirect('vendorapp:add_product')  # Redirect back to the same page
    else:
        form = BaseWatchForm()

    return render(request, 'vendorapp/add_product.html', {'form': form})

@user_type_required('vendor')
def product_list(request):
    vendor_profile = VendorProfile.objects.get(user=request.user)
    products = BaseWatch.objects.filter(vendor=vendor_profile)
    return render(request, 'vendorapp/product_list.html', {'products': products})

@user_type_required('vendor')
def delete_product(request, product_id):
    product = get_object_or_404(BaseWatch, id=product_id)
    product.delete()
    messages.success(request, 'Product deleted successfully.')
    return redirect('vendorapp:product_list')

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
                # If no primary image is uploaded and there's no existing primary image,
                # set the first additional image as the primary image
                first_additional_image = watch.additional_images.first()
                if first_additional_image:
                    from django.core.files import File
                    watch.primary_image.save(
                        f"primary/{os.path.basename(first_additional_image.image.name)}",
                        File(first_additional_image.image.file),
                        save=False
                    )
            # If there's an existing primary image, do nothing (keep the existing one)

            watch.save()

            # Handle additional images
            if 'product_images' in request.FILES:
                images = request.FILES.getlist('product_images')
                for image in images:
                    WatchImage.objects.create(base_watch=watch, image=image)

            messages.success(request, f'Product "{watch.model_name}" has been updated successfully!')
            return redirect('vendorapp:product_list')
    else:
        form = BaseWatchForm(instance=product)

    return render(request, 'vendorapp/edit_product.html', {'form': form, 'product': product})

from django.http import JsonResponse

@user_type_required('vendor')
def delete_product_image(request, image_id):
    image = get_object_or_404(WatchImage, id=image_id)
    if image.base_watch.vendor == request.user.vendorprofile:
        image.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=403)