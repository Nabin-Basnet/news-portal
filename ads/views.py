from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Advertisement, AdImpression, AdClick
from .serializers import AdvertisementSerializer, AdInteractionSerializer

class AdvertisementViewSet(viewsets.ModelViewSet):
    queryset = Advertisement.objects.all()
    serializer_class = AdvertisementSerializer

    def get_permissions(self):
        # Public endpoints for fetching and tracking interactions
        if self.action in ['list', 'track_impression', 'track_click', 'trending']:
            return [permissions.AllowAny()]
        # Full CRUD operations (POST, PUT, DELETE) restricted to Admins
        return [permissions.IsAdminUser()]

    def get_active_queryset(self):
        """
        Helper to filter ads within their scheduled active timeframe.
        """
        now = timezone.now()
        return Advertisement.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )

    def list(self, request):
        """
        GET /api/ads/
        Serves active ads grouped by layout positions.
        Supports category-specific targeting via slug query param: ?category=sports
        """
        queryset = self.get_active_queryset()
        category_slug = request.query_params.get('category')

        # 🟢 CATEGORY-BASED FILTERING LOGIC
        if category_slug:
            # Match ads targeting this specific category slug OR generic sitewide ads
            queryset = queryset.filter(
                Q(category__slug=category_slug) | Q(category__isnull=True)
            )

        # Define all available layout spots
        positions = ['top_banner', 'sidebar', 'in_article', 'footer', 'popup']
        response_data = {}

        for pos in positions:
            pos_queryset = queryset.filter(position=pos)
            
            # 🟢 SMART PRIORITIZATION: Target match comes first; fallback comes second
            if category_slug:
                targeted_ad = pos_queryset.filter(category__slug=category_slug).order_by('?').first()
                ad = targeted_ad if targeted_ad else pos_queryset.filter(category__isnull=True).order_by('?').first()
            else:
                ad = pos_queryset.order_by('?').first()
                
            response_data[pos] = AdvertisementSerializer(ad, context={'request': request}).data if ad else None

        return Response(response_data)

    @action(detail=False, methods=['post'], url_path='impressions')
    def track_impression(self, request):
        """
        POST /api/ads/impressions/
        Triggered via JavaScript frontend when an ad element appears on screen.
        """
        serializer = AdInteractionSerializer(data=request.data)
        if serializer.is_valid():
            ad = get_object_or_404(Advertisement, id=serializer.validated_data['ad_id'])
            
            AdImpression.objects.create(
                ad=ad,
                user=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({"status": "Impression verified"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='click')
    def track_click(self, request):
        """
        POST /api/ads/click/
        Triggered via JavaScript frontend when a user clicks an ad element.
        """
        serializer = AdInteractionSerializer(data=request.data)
        if serializer.is_valid():
            ad = get_object_or_404(Advertisement, id=serializer.validated_data['ad_id'])
            
            AdClick.objects.create(
                ad=ad,
                user=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response({"status": "Click verified", "target_url": ad.target_url}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='trending')
    def trending(self, request):
        """
        GET /api/ads/trending/
        Returns the top 5 ads sorted dynamically by total click interaction volume.
        """
        trending_ads = self.get_active_queryset().annotate(
            click_count=Count('clicks')
        ).order_by('-click_count')[:5]
        
        serializer = self.get_serializer(trending_ads, many=True)
        return Response(serializer.data)