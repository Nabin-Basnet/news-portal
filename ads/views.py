from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Advertisement, AdImpression, AdClick
from .serializers import AdvertisementSerializer, AdminAdvertisementSerializer, AdInteractionSerializer
from .permissions import CanEditAdvertisement
from user.permissions import IsAdminRole, IsAdminOrStaffRole
from articles.permissions import CanPublishArticle


class AdvertisementViewSet(viewsets.ModelViewSet):
    queryset = Advertisement.objects.all()
    serializer_class = AdvertisementSerializer

    def get_permissions(self):
        """
        Permissions:
        - Public:
            GET    /ads/
            GET    /ads/trending/
            POST   /ads/impressions/
            POST   /ads/click/

        - Staff & Admin:
            GET    /ads/<id>/
            POST   /ads/
            PUT    /ads/<id>/
            PATCH  /ads/<id>/
            DELETE /ads/<id>/
        """

        public_actions = ["list", "track_impression", "track_click", "trending"]
        if self.action in public_actions:
            return [permissions.AllowAny()]
        if self.action == "admin_advertisements":
            return [IsAdminRole()]
        if self.action in ["start_review", "approve", "reject", "publish", "archive"]:
            return [CanPublishArticle()]
        if self.action in ["update", "partial_update", "destroy", "submit"]:
            return [CanEditAdvertisement()]
        return [IsAdminOrStaffRole()]

    def get_active_queryset(self):
        """
        Returns advertisements that are currently active
        based on their schedule.
        """
        now = timezone.now()

        return Advertisement.objects.filter(
            status=Advertisement.Status.PUBLISHED,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now,
        )

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user, status=Advertisement.Status.DRAFT)

    def _workflow_response(self, advertisement):
        return Response({"status": advertisement.status, "review_note": advertisement.review_note})

    @action(detail=False, methods=["get"], url_path="admin/ads")
    def admin_advertisements(self, request):
        """Return every advertisement status for the custom admin dashboard."""
        selected_status = request.query_params.get("status")
        if selected_status and selected_status not in Advertisement.Status.values:
            return Response(
                {"status": f"Invalid status. Choose one of: {', '.join(Advertisement.Status.values)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        advertisements = Advertisement.objects.all().select_related(
            "creator", "reviewer", "category"
        ).annotate(
            impression_count=Count("impressions", distinct=True),
            click_count=Count("clicks", distinct=True),
        )
        if selected_status:
            advertisements = advertisements.filter(status=selected_status)

        self.search_fields = ["title", "client_name", "target_url", "creator__email", "category__name"]
        self.ordering_fields = [
            "title", "client_name", "status", "created_at", "updated_at", "published_at",
            "start_date", "end_date", "impression_count", "click_count",
        ]
        self.ordering = ["-created_at"]
        advertisements = self.filter_queryset(advertisements)
        page = self.paginate_queryset(advertisements)
        if page is not None:
            return self.get_paginated_response(AdminAdvertisementSerializer(page, many=True).data)
        return Response({"count": advertisements.count(), "results": AdminAdvertisementSerializer(advertisements, many=True).data})

    def list(self, request):
        """
        GET /api/ads/

        Returns active advertisements grouped by position.

        Optional:
            ?category=sports

        If a category is provided, category-specific ads are
        prioritized over site-wide advertisements.
        """

        queryset = self.get_active_queryset()
        category_slug = request.query_params.get("category")

        if category_slug:
            queryset = queryset.filter(
                Q(category__slug=category_slug) |
                Q(category__isnull=True)
            )

        positions = [
            "top_banner",
            "sidebar",
            "in_article",
            "footer",
            "popup",
        ]

        response_data = {}

        for position in positions:

            position_ads = queryset.filter(position=position)

            if category_slug:

                targeted_ad = (
                    position_ads
                    .filter(category__slug=category_slug)
                    .order_by("?")
                    .first()
                )

                ad = (
                    targeted_ad
                    if targeted_ad
                    else position_ads.filter(category__isnull=True)
                    .order_by("?")
                    .first()
                )

            else:

                ad = position_ads.order_by("?").first()

            response_data[position] = (
                AdvertisementSerializer(
                    ad,
                    context={"request": request}
                ).data
                if ad
                else None
            )

        return Response(response_data)

    @action(detail=False, methods=["post"], url_path="impressions")
    def track_impression(self, request):
        """
        POST /api/ads/impressions/

        Records an advertisement impression.
        """

        serializer = AdInteractionSerializer(data=request.data)

        if serializer.is_valid():

            ad = get_object_or_404(
                self.get_active_queryset(),
                id=serializer.validated_data["ad_id"],
            )

            AdImpression.objects.create(
                ad=ad,
                user=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response(
                {"status": "Impression verified"},
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["post"], url_path="click")
    def track_click(self, request):
        """
        POST /api/ads/click/

        Records an advertisement click.
        """

        serializer = AdInteractionSerializer(data=request.data)

        if serializer.is_valid():

            ad = get_object_or_404(
                self.get_active_queryset(),
                id=serializer.validated_data["ad_id"],
            )

            AdClick.objects.create(
                ad=ad,
                user=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get("REMOTE_ADDR"),
            )

            return Response(
                {
                    "status": "Click verified",
                    "target_url": ad.target_url,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        advertisement = self.get_object()
        try:
            advertisement.submit_for_review()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._workflow_response(advertisement)

    @action(detail=True, methods=["post"], url_path="start-review")
    def start_review(self, request, pk=None):
        advertisement = self.get_object()
        try:
            advertisement.start_review(request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._workflow_response(advertisement)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        advertisement = self.get_object()
        try:
            advertisement.approve(request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._workflow_response(advertisement)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        advertisement = self.get_object()
        try:
            advertisement.reject(request.user, request.data.get("note", ""))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._workflow_response(advertisement)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        advertisement = self.get_object()
        try:
            advertisement.publish(request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return self._workflow_response(advertisement)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        advertisement = self.get_object()
        advertisement.archive(request.user)
        return self._workflow_response(advertisement)

    @action(detail=False, methods=["get"], url_path="trending")
    def trending(self, request):
        """
        GET /api/ads/trending/

        Returns the top five advertisements
        ordered by click count.
        """

        trending_ads = (
            self.get_active_queryset()
            .annotate(click_count=Count("clicks"))
            .order_by("-click_count")[:5]
        )

        serializer = self.get_serializer(
            trending_ads,
            many=True,
        )

        return Response(serializer.data)