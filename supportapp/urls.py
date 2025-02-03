from django.urls import path
from . import views

app_name = 'supportapp'

urlpatterns = [
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/profile/', views.staff_profile, name='staff_profile'),
    path('staff/change-password/', views.change_password, name='change_password'),
    path('chat/start/<str:order_id>/', views.start_chat, name='start_chat'),
    path('chat/<int:chat_id>/', views.chat_room, name='chat_room'),
    path('chat/<int:chat_id>/messages/', views.get_messages, name='get_messages'),
    path('chat/<int:chat_id>/send/', views.send_message, name='send_message'),
    path('chat/<int:chat_id>/mark-read/', views.mark_messages_read, name='mark_messages_read'),
    path('chat/<int:chat_id>/status/', views.update_chat_status, name='update_chat_status'),
    path('staff/chats/', views.staff_chats, name='staff_chats'),
]
