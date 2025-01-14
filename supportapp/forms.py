from django import forms
from .models import Ticket, TicketResponse

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['subject', 'description', 'category', 'related_order', 'related_product']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class TicketResponseForm(forms.ModelForm):
    class Meta:
        model = TicketResponse
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3}),
        }

class TicketUpdateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['status', 'priority', 'assigned_to']
