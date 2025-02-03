from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from .models import OrderChat, SupportMessage
from django.core.exceptions import PermissionDenied
from mainapp.models import Order
from django.views.decorators.http import require_POST
import json


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

@login_required
def start_chat(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        
        # Check if there's an existing active chat
        chat = OrderChat.objects.filter(order=order, status='active').first()
        if not chat:
            chat = OrderChat.objects.create(order=order, customer=request.user)
        
        return JsonResponse({'success': True, 'chat_id': chat.id})
    
    return JsonResponse({'success': False}, status=400)

@login_required
def chat_room(request, chat_id):
    chat = get_object_or_404(OrderChat, id=chat_id)
    
    # Verify access rights
    if not (request.user == chat.customer or (request.user.is_staff and request.user.staff_profile.role == 'support')):
        raise PermissionDenied
    
    # If staff member, assign them to the chat if not already assigned
    if request.user.is_staff and not chat.staff:
        chat.staff = request.user
        chat.save()
    
    # Get existing messages
    existing_messages = chat.messages.all().order_by('created_at')
    
    context = {
        'chat': chat,
        'existing_messages': existing_messages,
        'order': chat.order,
    }
    return render(request, 'supportapp/chat_room.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff and u.staff_profile.role == 'support')
def staff_chats(request):
    # Get active and resolved chats
    active_chats = OrderChat.objects.filter(status='active').order_by('-updated_at')
    resolved_chats = OrderChat.objects.filter(
        Q(status='resolved') | Q(status='closed')
    ).order_by('-updated_at')
    
    # Get unread messages count
    unread_chats_count = OrderChat.objects.filter(
        status='active',
        messages__is_read=False,
        messages__sender__is_staff=False
    ).distinct().count()
    
    context = {
        'active_chats': active_chats,
        'resolved_chats': resolved_chats,
        'unread_chats_count': unread_chats_count
    }
    return render(request, 'supportapp/staff_chats.html', context)

@login_required
def get_new_messages(request, chat_id):
    chat = get_object_or_404(OrderChat, id=chat_id)
    last_message_id = request.GET.get('last_id')
    
    new_messages = chat.messages.filter(id__gt=last_message_id)
    messages_data = [{
        'id': msg.id,
        'message': msg.message,
        'sender': msg.sender.get_full_name(),
        'is_staff': msg.sender.is_staff,
        'timestamp': msg.created_at.strftime('%I:%M %p'),
        'attachment_url': msg.attachment.url if msg.attachment else None
    } for msg in new_messages]
    
    return JsonResponse({'messages': messages_data})

@login_required
def get_messages(request, chat_id):
    chat = get_object_or_404(OrderChat, id=chat_id)
    last_id = request.GET.get('last_id', 0)
    
    # Get new messages
    new_messages = chat.messages.filter(id__gt=last_id).order_by('created_at')
    
    messages_data = [{
        'id': msg.id,
        'message': msg.message,
        'sender_name': msg.sender.get_full_name() or msg.sender.username,  # Fallback to username if no full name
        'is_staff': msg.sender.is_staff,
        'created_at': msg.created_at.isoformat(),  # Send ISO format timestamp
        'attachment': msg.attachment.url if msg.attachment else None
    } for msg in new_messages]
    
    return JsonResponse({'messages': messages_data})

@require_POST
@login_required
def send_message(request, chat_id):
    chat = get_object_or_404(OrderChat, id=chat_id)
    
    if chat.status != 'active':
        return JsonResponse({'success': False, 'error': 'Chat is not active'})
    
    message = request.POST.get('message')
    attachment = request.FILES.get('attachment')
    
    if message or attachment:
        SupportMessage.objects.create(
            chat=chat,
            sender=request.user,
            message=message,
            attachment=attachment
        )
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'No message or attachment provided'})

@require_POST
@login_required
def mark_messages_read(request, chat_id):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
        
    chat = get_object_or_404(OrderChat, id=chat_id)
    chat.messages.filter(is_read=False).update(is_read=True)
    return JsonResponse({'success': True})

@require_POST
@login_required
def update_chat_status(request, chat_id):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
        
    chat = get_object_or_404(OrderChat, id=chat_id)
    data = json.loads(request.body)
    new_status = data.get('status')
    
    if new_status in dict(OrderChat.CHAT_STATUS):
        chat.status = new_status
        chat.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid status'})

