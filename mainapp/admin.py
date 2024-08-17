from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User,Address,UserProfile,Cart,CartItem,Order,OrderItem
# Register your models here.
admin.site.register(User)
admin.site.register(Address)
admin.site.register(UserProfile)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Order)
admin.site.register(OrderItem)