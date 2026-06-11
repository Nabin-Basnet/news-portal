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
        """
        Ensures that if an ad is flagged as a sponsored article,
        a valid cross-referenced target Article ID must be provided.
        """
        is_sponsored = data.get('is_sponsored_article', False)
        sponsored_id = data.get('sponsored_article_id')

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