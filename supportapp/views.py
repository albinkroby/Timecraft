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
from .models import SupportTicket, TicketResponse

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

@login_required
@user_passes_test(lambda u: u.is_staff)
def ticket_list(request):
    tickets = SupportTicket.objects.all().order_by('-created_at')
    
    # Filter handling
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    ticket_type = request.GET.get('type')
    
    if status:
        tickets = tickets.filter(status=status)
    if priority:
        tickets = tickets.filter(priority=priority)
    if ticket_type:
        tickets = tickets.filter(ticket_type=ticket_type)
        
    context = {
        'tickets': tickets,
        'open_count': tickets.filter(status='open').count(),
        'urgent_count': tickets.filter(priority='urgent').count(),
    }
    return render(request, 'supportapp/ticket_list.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    responses = ticket.responses.all().order_by('created_at')
    
    context = {
        'ticket': ticket,
        'responses': responses,
    }
    return render(request, 'supportapp/ticket_detail.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def ticket_respond(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    message = request.POST.get('message')
    is_internal = request.POST.get('is_internal', False)
    
    response = TicketResponse.objects.create(
        ticket=ticket,
        responder=request.user,
        message=message,
        is_internal_note=is_internal
    )
    
    # Handle file attachment
    if 'attachment' in request.FILES:
        response.attachment = request.FILES['attachment']
        response.save()
        
    # Send email notification to customer
    if not is_internal:
        send_ticket_response_email(ticket, message)
        
    return JsonResponse({'status': 'success'})

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def assign_ticket(request, ticket_id):
    """Assign a support ticket to a staff member"""
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    staff_id = request.POST.get('staff_id')
    
    try:
        staff_member = get_object_or_404('adminapp.StaffMember', id=staff_id)
        # Update ticket assignment
        ticket.assigned_to = staff_member
        ticket.status = 'assigned'
        ticket.save()
        
        # Create an internal note about the assignment
        TicketResponse.objects.create(
            ticket=ticket,
            responder=request.user,
            message=f"Ticket assigned to {staff_member.user.get_full_name()}",
            is_internal_note=True
        )
        
        return JsonResponse({
            'status': 'success',
            'message': f'Ticket successfully assigned to {staff_member.user.get_full_name()}'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def update_ticket_status(request, ticket_id):
    """Update the status of a support ticket"""
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    new_status = request.POST.get('status')
    
    if new_status not in dict(SupportTicket.STATUS_CHOICES):
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid status'
        }, status=400)
    
    try:
        old_status = ticket.status
        ticket.status = new_status
        
        # If resolving or closing, require resolution notes
        if new_status in ['resolved', 'closed']:
            resolution_notes = request.POST.get('resolution')
            if resolution_notes:
                ticket.resolution = resolution_notes
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Resolution notes are required when resolving or closing a ticket'
                }, status=400)
        
        ticket.save()
        
        # Create an internal note about the status change
        TicketResponse.objects.create(
            ticket=ticket,
            responder=request.user,
            message=f"Status changed from {old_status} to {new_status}",
            is_internal_note=True
        )
        
        # Send email notification to customer for specific status changes
        if new_status in ['resolved', 'closed']:
            send_mail(
                f'Your ticket #{ticket.ticket_id} has been {new_status}',
                f'Your support ticket has been marked as {new_status}.\n\n'
                f'Resolution: {ticket.resolution}\n\n'
                f'If you have any further questions, please create a new ticket.',
                'from@yourdomain.com',
                [ticket.user.email],
                fail_silently=False,
            )
        
        return JsonResponse({
            'status': 'success',
            'message': f'Ticket status updated to {new_status}'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
@user_passes_test(lambda u: u.is_staff)
@require_POST
def join_conversation(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    
    if not ticket.assigned_to:
        ticket.assigned_to = request.user
        ticket.status = 'in_progress'
        ticket.save()
        
        # Create system message about staff joining
        TicketResponse.objects.create(
            ticket=ticket,
            responder=request.user,
            message=f"Staff member {request.user.get_full_name()} has joined the conversation.",
            is_internal_note=True
        )
        
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error', 'message': 'Ticket is already assigned'}, status=400)

@login_required
@user_passes_test(lambda u: u.is_staff)
def support_reports(request):
    """Generate support ticket reports and statistics"""
    # Get date range from request or default to last 30 days
    end_date = timezone.now()
    start_date = request.GET.get('start_date', (end_date - timedelta(days=30)).date())
    
    # Get tickets in date range
    tickets = SupportTicket.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    # Calculate key metrics
    total_tickets = tickets.count()
    resolved_tickets = tickets.filter(status__in=['resolved', 'closed']).count()
    avg_resolution_time = tickets.filter(status__in=['resolved', 'closed']).aggregate(
        avg_time=Avg(F('updated_at') - F('created_at'))
    )['avg_time']
    
    # Tickets by priority
    priority_distribution = tickets.values('priority').annotate(
        count=Count('id')
    ).order_by('priority')
    
    # Tickets by type
    type_distribution = tickets.values('ticket_type').annotate(
        count=Count('id')
    ).order_by('ticket_type')
    
    # Staff performance
    staff_performance = tickets.values(
        'assigned_to__user__username'
    ).annotate(
        total_assigned=Count('id'),
        resolved=Count('id', filter=Q(status__in=['resolved', 'closed'])),
        avg_resolution_time=Avg(
            F('updated_at') - F('created_at'),
            filter=Q(status__in=['resolved', 'closed'])
        )
    ).exclude(assigned_to__isnull=True)
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_tickets': total_tickets,
        'resolved_tickets': resolved_tickets,
        'resolution_rate': (resolved_tickets / total_tickets * 100) if total_tickets else 0,
        'avg_resolution_time': avg_resolution_time,
        'priority_distribution': priority_distribution,
        'type_distribution': type_distribution,
        'staff_performance': staff_performance,
    }
    
    return render(request, 'supportapp/support_reports.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def customer_feedback(request):
    """View customer feedback and satisfaction metrics"""
    # Get tickets with feedback
    tickets_with_feedback = SupportTicket.objects.exclude(
        customer_feedback__isnull=True
    ).select_related('user', 'assigned_to')
    
    # Calculate average feedback score
    avg_feedback = tickets_with_feedback.aggregate(
        avg_score=Avg('customer_feedback')
    )['avg_score'] or 0
    
    # Get feedback distribution
    feedback_distribution = tickets_with_feedback.values(
        'customer_feedback'
    ).annotate(
        count=Count('id')
    ).order_by('customer_feedback')
    
    # Staff feedback performance
    staff_feedback = tickets_with_feedback.values(
        'assigned_to__user__username'
    ).annotate(
        total_feedback=Count('id'),
        avg_rating=Avg('customer_feedback'),
        five_star=Count('id', filter=Q(customer_feedback=5)),
        four_star=Count('id', filter=Q(customer_feedback=4)),
        three_star=Count('id', filter=Q(customer_feedback=3)),
        two_star=Count('id', filter=Q(customer_feedback=2)),
        one_star=Count('id', filter=Q(customer_feedback=1))
    ).exclude(assigned_to__isnull=True)
    
    context = {
        'avg_feedback': round(avg_feedback, 2),
        'feedback_distribution': feedback_distribution,
        'staff_feedback': staff_feedback,
        'total_feedback': tickets_with_feedback.count(),
        'recent_feedback': tickets_with_feedback.order_by('-updated_at')[:10]
    }
    
    return render(request, 'supportapp/customer_feedback.html', context)

@login_required
@require_http_methods(["GET"])
def get_new_responses(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    last_id = request.GET.get('last_id', 0)
    
    new_responses = TicketResponse.objects.filter(
        ticket=ticket,
        id__gt=last_id
    ).select_related('responder').order_by('created_at')
    
    responses_data = [{
        'id': response.id,
        'message': response.message,
        'responder_name': response.responder.get_full_name(),
        'created_at': response.created_at.strftime("%b %d, %Y %H:%M"),
        'is_internal_note': response.is_internal_note,
        'attachment': response.attachment.url if response.attachment else None
    } for response in new_responses]
    
    return JsonResponse({'responses': responses_data})


