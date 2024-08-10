from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Brand, Category, BaseWatch, WatchImage

admin.site.register(Brand)
admin.site.register(Category)
admin.site.register(BaseWatch)
admin.site.register(WatchImage)