from django.contrib import admin
from .models import Brand, Collection, Material, Feature, Category, WatchType, BaseWatch, WatchImage, SmartWatchFeature, PremiumWatchFeature

admin.site.register(Brand)
admin.site.register(Collection)
admin.site.register(Material)
admin.site.register(Feature)
admin.site.register(Category)
admin.site.register(WatchType)
admin.site.register(BaseWatch)
admin.site.register(WatchImage)
admin.site.register(SmartWatchFeature)
admin.site.register(PremiumWatchFeature)