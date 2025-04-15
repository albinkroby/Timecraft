from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Avg, Count, F
from django.core.exceptions import PermissionDenied
from mainapp.models import Order
from django.views.decorators.http import require_POST, require_http_methods
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import json

def send_ticket_response_email(ticket, message):
    send_mail(
        f'Response to your ticket #{ticket.ticket_id}',
        message,
        'from@yourdomain.com',
        [ticket.customer.email],
        fail_silently=False,
    )

@login_required
@user_passes_test(lambda u: u.is_staff)
def staff_dashboard(request):
    return render(request, 'supportapp/staff_dashboard.html')

@login_required
@user_passes_test(lambda u: u.is_staff)
def staff_profile(request):
    if request.method == 'POST':
        # Get the current user
        user = request.user
        
        # Update user information
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('supportapp:staff_profile')
    
    return render(request, 'supportapp/staff_profile.html')

@login_required
@user_passes_test(lambda u: u.is_staff)
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Update the session with new password hash
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('supportapp:staff_profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'supportapp/change_password.html', {'form': form})
