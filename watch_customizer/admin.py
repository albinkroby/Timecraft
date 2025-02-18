from django.contrib import admin
from .models import CustomizableWatch, CustomizableWatchPart, CustomWatchOrder, CustomWatchOrderPart, WatchPart, WatchPartOption, WatchPartName, CustomWatchSavedDesign, WatchCertificate

# Register your models here.
admin.site.register(CustomizableWatch)
admin.site.register(CustomizableWatchPart)
admin.site.register(CustomWatchOrder)
admin.site.register(CustomWatchOrderPart)
admin.site.register(WatchPart)
admin.site.register(WatchPartOption)
admin.site.register(WatchPartName)
admin.site.register(CustomWatchSavedDesign)
admin.site.register(WatchCertificate)   
