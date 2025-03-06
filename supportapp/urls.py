from django.urls import path
from . import views

app_name = 'supportapp'

urlpatterns = [
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('profile/', views.staff_profile, name='staff_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/<str:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<str:ticket_id>/respond/', views.ticket_respond, name='ticket_respond'),
    path('tickets/<str:ticket_id>/responses/', views.get_new_responses, name='get_new_responses'),
    path('tickets/<str:ticket_id>/join/', views.join_conversation, name='join_conversation'),
    path('tickets/<str:ticket_id>/assign/', views.assign_ticket, name='assign_ticket'),
    path('tickets/<str:ticket_id>/update-status/', views.update_ticket_status, name='update_ticket_status'),
    path('reports/', views.support_reports, name='support_reports'),
    path('customer-feedback/', views.customer_feedback, name='customer_feedback'),
]
