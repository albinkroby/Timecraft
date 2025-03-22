from django.contrib import admin
from .models import DeliveryProfile, DeliveryHistory, DeliveryMetrics, DeliveryRating

@admin.register(DeliveryProfile)
class DeliveryProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'vehicle_type', 'is_active')
    list_filter = ('is_active', 'vehicle_type')
    search_fields = ('user__username', 'user__email', 'phone')

@admin.register(DeliveryHistory)
class DeliveryHistoryAdmin(admin.ModelAdmin):
    list_display = ('order', 'delivery_person', 'status', 'timestamp')
    list_filter = ('status',)
    search_fields = ('order__order_id', 'delivery_person__username')
    date_hierarchy = 'timestamp'

@admin.register(DeliveryMetrics)
class DeliveryMetricsAdmin(admin.ModelAdmin):
    list_display = ('delivery_person', 'total_deliveries', 'completed_deliveries', 'avg_rating')
    search_fields = ('delivery_person__username', 'delivery_person__email')

@admin.register(DeliveryRating)
class DeliveryRatingAdmin(admin.ModelAdmin):
    list_display = ('order', 'delivery_person', 'rating', 'timestamp')
    list_filter = ('rating',)
    search_fields = ('order__order_id', 'delivery_person__username')
