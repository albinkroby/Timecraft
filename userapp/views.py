from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from mainapp.models import Address,UserProfile, User
from .forms import AddressForm
from django.db import IntegrityError
from django.http import JsonResponse

@login_required
def profile(request):
    user = request.user
    google_login = user.social_auth.filter(provider='google-oauth2').exists()
    return render(request, 'userapp/profile.html', {
        'user': user,
        'google_login': google_login
    })

@login_required
def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    form = AddressForm()
    return render(request, 'userapp/address.html', {'addresses': addresses, 'form': form})

@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            try:
                address = form.save(commit=False)
                address.user = request.user
                address.save()
                return redirect('userapp:Address')
            except IntegrityError:
                form.add_error(None, "This address already exists for your account.")
    else:
        form = AddressForm()
    return render(request, 'userapp/address.html', {'form': form})

@login_required
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect('userapp:Address')
    else:
        # Return address data as JSON
        return JsonResponse({
            'flat_house_no': address.flat_house_no,
            'area_street': address.area_street,
            'landmark': address.landmark,
            'pincode': address.pincode,
            'town_city': address.town_city,
            'state': address.state,
            'country': address.country,
            'address_type': address.address_type,
        })
    
    return render(request, 'userapp/address.html', {'form': form, 'edit_address': address})

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    address.delete()
    return redirect('userapp:Address')

@login_required
def make_primary_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # Set all addresses to non-primary
    Address.objects.filter(user=request.user).update(is_primary=False)
    
    # Set the selected address as primary
    address.is_primary = True
    address.save()
    
    return redirect('userapp:Address')