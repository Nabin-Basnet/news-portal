from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html  
from .models import Advertisement, AdImpression, AdClick

class InteractionInlineMixin:
    extra = 0
    readonly_fields = ('user', 'ip_address', 'clicked_at', 'viewed_at')
    def has_add_permission(self, request, obj=None): return False

class AdClickInline(InteractionInlineMixin, admin.TabularInline):
    model = AdClick
    readonly_fields = ('user', 'ip_address', 'clicked_at')

class AdImpressionInline(InteractionInlineMixin, admin.TabularInline):
    model = AdImpression
    readonly_fields = ('user', 'ip_address', 'viewed_at')


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "image_thumbnail",  
        "client_name", 
        "position", 
        "category",
        "is_active", 
        "is_sponsored_article", 
        "get_impressions", 
        "get_clicks", 
        "ctr_percentage"
    )
    list_filter = ("position", "is_active", "category", "is_sponsored_article")
    search_fields = ("title", "client_name")
    date_hierarchy = "start_date"
    
    inlines = [AdImpressionInline, AdClickInline]

    # 🟢 FIXED: Added the missing image_thumbnail method inside the class
    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 40px; width: auto; border-radius: 4px; border: 1px solid #ddd;" />', obj.image.url)
        return format_html('<span style="color: #999; font-style: italic;">No Image</span>')
    image_thumbnail.short_description = "Banner Preview"

    # Dynamic Aggregates Execution
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Select related category to keep the query optimized and prevent database lag
        return qs.select_related('category').annotate(
            cached_impressions_count=Count('impressions', distinct=True),
            cached_clicks_count=Count('clicks', distinct=True)
        )
    
    def get_impressions(self, obj):
        return obj.cached_impressions_count

    def get_clicks(self, obj):
        return obj.cached_clicks_count

    def ctr_percentage(self, obj):
        clicks = obj.cached_clicks_count
        impressions = obj.cached_impressions_count
        if impressions > 0:
            return f"{(clicks / impressions * 100):.2f}%"
        return "0.00%"
    ctr_percentage.short_description = "CTR Rate"