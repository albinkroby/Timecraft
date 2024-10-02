from django.contrib import admin
from .models import CustomizableWatch, CustomizableWatchPart, CustomWatchOrder, CustomWatchOrderPart, WatchPart, WatchPartOption, WatchPartName

# Register your models here.
admin.site.register(CustomizableWatch)
admin.site.register(CustomizableWatchPart)
admin.site.register(CustomWatchOrder)
admin.site.register(CustomWatchOrderPart)
admin.site.register(WatchPart)
admin.site.register(WatchPartOption)
admin.site.register(WatchPartName)
