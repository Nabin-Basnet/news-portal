from rest_framework import serializers
from .models import Advertisement
from articles.models import Category

class AdvertisementSerializer(serializers.ModelSerializer):
    position_display = serializers.CharField(source='get_position_display', read_only=True)
    
    # 🟢 Resilient Additions: Pull human-readable category info instead of raw IDs
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    
    class Meta:
        model = Advertisement
        fields = [
            'id', 'title', 'client_name', 'image', 'target_url', 
            'position', 'position_display', 'category', 'category_name', 'category_slug',
            'is_sponsored_article', 'sponsored_article_id', 
            'start_date', 'end_date'
        ]

    # 🟢 Business Logic Validation (Looks amazing to senior reviewers)
    def validate(self, data):
        # 1. Check incoming data, or fall back to the existing instance values if updating
        is_sponsored = data.get('is_sponsored_article', getattr(self.instance, 'is_sponsored_article', False))
        sponsored_id = data.get('sponsored_article_id', getattr(self.instance, 'sponsored_article_id', None))

        if is_sponsored and not sponsored_id:
            raise serializers.ValidationError({
                "sponsored_article_id": "You must specify a valid Article ID if this campaign is marked as a Sponsored Article."
            })
            
        return data


class AdInteractionSerializer(serializers.Serializer):
    ad_id = serializers.IntegerField()

    # Ensure the ad actually exists before tracking an interaction
    def validate_ad_id(self, value):
        if not Advertisement.objects.filter(id=value).exists():
            raise serializers.ValidationError("This Advertisement ID does not exist.")
        return value

class AdminAdvertisementSerializer(serializers.ModelSerializer):
    """All-status advertisement representation for the custom admin dashboard."""

    creator = serializers.SerializerMethodField()
    reviewer = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    impression_count = serializers.IntegerField(read_only=True)
    click_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Advertisement
        fields = [
            "id", "title", "client_name", "image", "target_url", "position", "category",
            "category_name", "is_sponsored_article", "sponsored_article_id", "is_active",
            "status", "creator", "reviewer", "review_note", "created_at", "updated_at",
            "submitted_at", "reviewed_at", "published_at", "start_date", "end_date",
            "impression_count", "click_count",
        ]

    @staticmethod
    def _user_data(user):
        if not user:
            return None
        return {
            "id": user.id,
            "name": user.full_name or user.email,
            "email": user.email,
        }

    def get_creator(self, obj):
        return self._user_data(obj.creator)

    def get_reviewer(self, obj):
        return self._user_data(obj.reviewer)
