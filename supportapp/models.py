from django.db import models
from mainapp.models import User
from adminapp.models import BaseWatch

class Ticket(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    CATEGORY_CHOICES = [
        ('order', 'Order Related'),
        ('product', 'Product Related'),
        ('payment', 'Payment Related'),
        ('technical', 'Technical Issue'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_to = models.ForeignKey(User, 
                                  on_delete=models.SET_NULL, 
                                  null=True, 
                                  related_name='assigned_tickets')
    related_order = models.ForeignKey('mainapp.Order', 
                                    on_delete=models.SET_NULL, 
                                    null=True, 
                                    blank=True)
    related_product = models.ForeignKey(BaseWatch, 
                                      on_delete=models.SET_NULL, 
                                      null=True, 
                                      blank=True)

    def __str__(self):
        return f"Ticket #{self.id} - {self.subject}"

class TicketResponse(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='responses')
    responder = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to='ticket_attachments/', null=True, blank=True)

    class Meta:
        ordering = ['created_at']

class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='ticket_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
