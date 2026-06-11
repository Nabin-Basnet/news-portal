from django.db import models
from django.conf import settings
from django.utils import timezone
from user.models import User  # Adjust import path based on your user app location
from articles.models import Category  # For Category-based targeting

class Advertisement(models.Model):
    class Position(models.TextChoices):
        TOP_BANNER = "top_banner", "Top Banner (728x90)"
        SIDEBAR = "sidebar", "Sidebar Box (300x250)"
        IN_ARTICLE = "in_article", "In-Article Strip (468x60)"
        FOOTER = "footer", "Footer Banner (728x90)"
        POPUP = "popup", "Overlay Popup"

    title = models.CharField(max_length=255, db_index=True)
    client_name = models.CharField(max_length=150)
    image = models.ImageField(upload_to="ad_banners/")
    target_url = models.URLField()
    position = models.CharField(max_length=20, choices=Position.choices, db_index=True)
    
    category = models.ForeignKey(
        'articles.Category', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="targeted_ads",
        help_text="Choose a specific category to target (e.g., Sports). Leave blank for site-wide ads."
    )
    
    # Realistic Feature: Sponsored Article Link Variant
    is_sponsored_article = models.BooleanField(default=False, db_index=True)
    sponsored_article_id = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        help_text="If this is a sponsored article, provide its Article ID"
    )

    is_active = models.BooleanField(default=True, db_index=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(help_text="Campaign expiration date")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_position_display()}] {self.title}"


class AdImpression(models.Model):
    ad = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name="impressions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="ad_impressions")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-viewed_at"]


class AdClick(models.Model):
    ad = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name="clicks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="ad_clicks")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-clicked_at"]