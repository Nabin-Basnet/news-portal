from django.db import models
from django.conf import settings
from django.utils import timezone
from cloudinary.models import CloudinaryField
from user.models import User  # Adjust import path based on your user app location
from articles.models import Category  # For Category-based targeting

class Advertisement(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    class Position(models.TextChoices):
        TOP_BANNER = "top_banner", "Top Banner (728x90)"
        SIDEBAR = "sidebar", "Sidebar Box (300x250)"
        IN_ARTICLE = "in_article", "In-Article Strip (468x60)"
        FOOTER = "footer", "Footer Banner (728x90)"
        POPUP = "popup", "Overlay Popup"

    title = models.CharField(max_length=255, db_index=True)
    client_name = models.CharField(max_length=150)
    image = CloudinaryField("image", null=True, blank=True)
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

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="advertisements_created",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="advertisements_reviewed",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    review_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_position_display()}] {self.title}"

    def submit_for_review(self):
        if self.status not in (self.Status.DRAFT, self.Status.REJECTED):
            raise ValueError("Only draft or rejected advertisements can be submitted.")
        self.status = self.Status.SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])

    def start_review(self, reviewer):
        if self.status != self.Status.SUBMITTED:
            raise ValueError("Only submitted advertisements can be moved to review.")
        self.status = self.Status.UNDER_REVIEW
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewer", "reviewed_at", "updated_at"])

    def approve(self, reviewer):
        if self.status != self.Status.UNDER_REVIEW:
            raise ValueError("Only advertisements under review can be approved.")
        self.status = self.Status.APPROVED
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewer", "reviewed_at", "updated_at"])

    def reject(self, reviewer, note=""):
        if self.status not in (self.Status.SUBMITTED, self.Status.UNDER_REVIEW, self.Status.APPROVED):
            raise ValueError("Only submitted, under-review, or approved advertisements can be rejected.")
        self.status = self.Status.REJECTED
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save(update_fields=["status", "reviewer", "reviewed_at", "review_note", "updated_at"])

    def publish(self, reviewer):
        if self.status != self.Status.APPROVED:
            raise ValueError("Only approved advertisements can be published.")
        self.status = self.Status.PUBLISHED
        self.reviewer = reviewer
        self.published_at = timezone.now()
        self.save(update_fields=["status", "reviewer", "published_at", "updated_at"])

    def archive(self, reviewer):
        self.status = self.Status.ARCHIVED
        self.reviewer = reviewer
        self.save(update_fields=["status", "reviewer", "updated_at"])


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
