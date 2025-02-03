from .models import OrderChat
from django.db.models import Q

def support_context(request):
    if request.user.is_authenticated and request.user.is_staff:
        unread_chats_count = OrderChat.objects.filter(
            status='active',
            messages__is_read=False,
            messages__sender__is_staff=False
        ).distinct().count()
        return {'unread_chats_count': unread_chats_count}
    return {} 