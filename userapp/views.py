from django.shortcuts import render
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ProfileForm
from django.contrib import messages
from mainapp.models import Profile
from .forms import ProfileForm, NewAddressForm

@login_required
def profile(request):
    user = request.user
    google_login = user.social_auth.filter(provider='google-oauth2').exists()
    return render(request, 'userapp/profile.html', {
        'user': user,
        'google_login': google_login
    })

@login_required
def Address(request):
    try:
        profile = request.user.profile
        update_form = ProfileForm(request.POST or None, instance=profile)
    except Profile.DoesNotExist:
        update_form = None
    
    new_form = NewAddressForm(request.POST or None)
    
    if request.method == 'POST':
        if 'update_address' in request.POST and update_form:
            if update_form.is_valid():
                update_form.save()
                messages.success(request, 'Address updated successfully.')
                return redirect('userapp:Address')
            else:
                messages.error(request, 'Please correct the errors below in the update form.')
        
        if 'new_address' in request.POST:
            if new_form.is_valid():
                new_address = new_form.save(commit=False)
                new_address.user = request.user
                new_address.save()
                messages.success(request, 'New address added successfully.')
                return redirect('userapp:Address')
            else:
                messages.error(request, 'Please correct the errors below in the new address form.')

    context = {
        'update_form': update_form,
        'new_form': new_form,
    }

    return render(request, 'userapp/address.html', context)