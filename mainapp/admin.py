from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User,Address,UserProfile,Cart,CartItem,Order,OrderItem,ChatSession,ChatMessage,SupportTicket,SupportMessage
# Register your models here.
admin.site.register(User)
admin.site.register(Address)
admin.site.register(UserProfile)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ChatSession)
admin.site.register(ChatMessage)
admin.site.register(SupportTicket)
admin.site.register(SupportMessage)
