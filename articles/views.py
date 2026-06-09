from datetime import timedelta

from django.utils import timezone
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Article, ArticleView, Reaction, Bookmark, Comment, Category, Tag
)

from .serializers import (
    CategorySerializer,
    TagSerializer,
    ArticleListSerializer,
    ArticleDetailSerializer,
    ArticleWriteSerializer
)

from .permissions import (
    IsAdminUserRole,
    IsEditorOrAdmin,
    IsReporterRole,
    IsAuthorOrEditorialStaff,
)

from .utils import get_role


# ======================================================
# CATEGORY VIEWSET
# ======================================================
class CategoryViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        role = get_role(request.user)

        if role not in ['reporter', 'author', 'editor', 'admin'] and not request.user.is_superuser:
            return Response(
                {"detail": "Access denied for non-editorial users."},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().create(request, *args, **kwargs)


# ======================================================
# ARTICLE VIEWSET
# ======================================================
class ArticleViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication]
    queryset = Article.objects.all()
    lookup_url_kwarg = "article_id"

    # ---------------- SERIALIZER ----------------
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ArticleWriteSerializer
        if self.action == 'retrieve':
            return ArticleDetailSerializer
        return ArticleListSerializer

    # ---------------- PERMISSION ----------------
    def get_permissions(self):
        if self.action == 'create':
            return [IsReporterRole()]

        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthorOrEditorialStaff()]

        if self.action in ['list_pending_articles', 'review']:
            return [IsEditorOrAdmin()]

        if self.action in ['list_reporter_articles', 'submit']:
            return [IsReporterRole()]

        if self.action == 'admin_activity_dashboard':
            return [IsAdminUserRole()]

        if self.action in ['add_comment', 'toggle_reaction', 'toggle_bookmark']:
            return [permissions.IsAuthenticated()]

        return [permissions.AllowAny()]

    # ---------------- QUERYSET ----------------
    def get_queryset(self):
        qs = super().get_queryset()

        public_actions = [
            'list',
            'trending',
            'search_feed',
            'news_of_the_day',
            'retrieve'
        ]

        if self.action in public_actions:
            return qs.filter(status=Article.Status.PUBLISHED)

        return qs

    # ---------------- CREATE ----------------
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    # ---------------- DELETE ----------------
    def destroy(self, request, *args, **kwargs):
        article = self.get_object()
        user = request.user
        role = get_role(user)

        if article.author_id == user.id and role in ['reporter', 'author']:
            article.delete()
            return Response({"message": "Deleted by author."})

        if role in ['editor', 'admin'] or user.is_superuser:
            article.delete()
            return Response({"message": "Deleted by admin/editor."})

        return Response(
            {"detail": "Permission denied."},
            status=status.HTTP_403_FORBIDDEN
        )

    # ---------------- RETRIEVE ----------------
    def retrieve(self, request, *args, **kwargs):
        article = get_object_or_404(
            Article,
            id=kwargs['article_id'],
            status=Article.Status.PUBLISHED
        )

        if request.user.is_authenticated:
            ip = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = ip.split(',')[0].strip() if ip else request.META.get('REMOTE_ADDR')

            ArticleView.objects.get_or_create(
                article=article,
                user=request.user,
                defaults={'ip_address': ip}
            )

        comments_tree = self._comments_tree(article)

        serializer = self.get_serializer(article, context={
            "comments_tree": comments_tree
        })

        return Response(serializer.data)

    def _get_article_from_url(self):
        return get_object_or_404(Article, id=self.kwargs.get(self.lookup_url_kwarg))

    def _comments_tree(self, article):
        comments = Comment.objects.filter(article=article).select_related("user", "parent")
        by_parent = {}

        for comment in comments:
            by_parent.setdefault(comment.parent_id, []).append(comment)

        def serialize(comment):
            user = comment.user
            return {
                "id": comment.id,
                "content": comment.content,
                "user": getattr(user, "username", "") or getattr(user, "email", ""),
                "created_at": comment.created_at,
                "replies": [serialize(reply) for reply in by_parent.get(comment.id, [])],
            }

        return [serialize(comment) for comment in by_parent.get(None, [])]

    # ---------------- REPORTER LIST ----------------
    @action(detail=False, methods=['get'])
    def list_reporter_articles(self, request):
        articles = Article.objects.filter(author=request.user)
        return Response({
            "results": ArticleListSerializer(articles, many=True).data
        })

    # ---------------- PENDING LIST ----------------
    @action(detail=False, methods=['get'])
    def list_pending_articles(self, request):
        articles = Article.objects.filter(status=Article.Status.PENDING_REVIEW)
        return Response({
            "results": ArticleListSerializer(articles, many=True).data
        })

    # ---------------- SUBMIT ----------------
    @action(detail=True, methods=['post'])
    def submit(self, request, article_id=None):
        article = self._get_article_from_url()

        if article.author_id != request.user.id:
            return Response(
                {"detail": "Only the article author can submit it for review."},
                status=status.HTTP_403_FORBIDDEN
            )

        article.submit_for_review()
        return Response({"status": article.status})

    # ---------------- REVIEW ----------------
    @action(detail=True, methods=['post'])
    def review(self, request, article_id=None):
        article = self._get_article_from_url()
        action_name = request.data.get("action")

        if action_name == "approve":
            article.approve(request.user)
            return Response({"status": article.status})

        if action_name == "reject":
            article.reject(request.user, request.data.get("note", ""))
            return Response({"status": article.status, "review_note": article.review_note})

        return Response(
            {"detail": "Action must be either 'approve' or 'reject'."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # ---------------- COMMENT ----------------
    @action(detail=True, methods=['post'])
    def add_comment(self, request, article_id=None):
        article = self._get_article_from_url()
        content = request.data.get("content", "").strip()
        parent_id = request.data.get("parent_id")

        if not content:
            return Response(
                {"detail": "Comment content is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, id=parent_id, article=article)

        comment = Comment.objects.create(
            article=article,
            user=request.user,
            content=content,
            parent=parent
        )

        return Response({
            "id": comment.id,
            "content": comment.content
        }, status=status.HTTP_201_CREATED)

    # ---------------- REACTION ----------------
    @action(detail=True, methods=['post'])
    def toggle_reaction(self, request, article_id=None):
        article = self._get_article_from_url()
        reaction_type = request.data.get("reaction_type") or request.data.get("reaction")

        valid_reactions = {choice[0] for choice in Reaction.ReactionType.choices}
        if reaction_type not in valid_reactions:
            return Response(
                {"detail": "Invalid reaction type."},
                status=status.HTTP_400_BAD_REQUEST
            )

        reaction, created = Reaction.objects.get_or_create(
            article=article,
            user=request.user,
            defaults={"reaction": reaction_type}
        )

        if not created and reaction.reaction == reaction_type:
            reaction.delete()
            return Response({"reacted": False, "reaction": None})

        reaction.reaction = reaction_type
        reaction.save(update_fields=["reaction", "reacted_at"])
        return Response({
            "reacted": True,
            "reaction": reaction.reaction
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    # ---------------- BOOKMARK ----------------
    @action(detail=True, methods=['post'])
    def toggle_bookmark(self, request, article_id=None):
        article = self._get_article_from_url()
        bookmark = Bookmark.objects.filter(article=article, user=request.user).first()

        if bookmark:
            bookmark.delete()
            return Response({"bookmarked": False, "message": "Bookmark removed"})

        Bookmark.objects.create(article=article, user=request.user)
        return Response(
            {"bookmarked": True, "message": "Bookmarked"},
            status=status.HTTP_201_CREATED
        )

    # ---------------- TRENDING ----------------
    @action(detail=False, methods=['get'])
    def trending(self, request):
        articles = Article.objects.annotate(
            views_count=Count('views')
        ).order_by('-views_count')[:10]

        return Response({
            "results": ArticleListSerializer(articles, many=True).data,
            "categories": CategorySerializer(Category.objects.all(), many=True).data
        })

    # ---------------- SEARCH ----------------
    @action(detail=False, methods=['get'])
    def search_feed(self, request):
        q = request.query_params.get("q", "")
        cat = request.query_params.get("category", "")

        qs = Article.objects.filter(status=Article.Status.PUBLISHED)

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))

        if cat:
            qs = qs.filter(category__slug=cat)

        return Response({
            "results": ArticleListSerializer(qs, many=True).data
        })

    # ---------------- NEWS OF DAY ----------------
    @action(detail=False, methods=['get'])
    def news_of_the_day(self, request):
        last_24h = timezone.now() - timedelta(hours=24)

        article = Article.objects.filter(
            views__viewed_at__gte=last_24h
        ).annotate(
            views_count=Count('views')
        ).order_by('-views_count').first()

        if not article:
            article = Article.objects.filter(
                status=Article.Status.PUBLISHED
            ).order_by('-published_at').first()

        if not article:
            return Response({"message": "No articles found"}, status=404)

        return Response({
            "id": article.id,
            "title": article.title
        })

    # ---------------- TAG FILTER ----------------
    @action(detail=False, methods=['get'], url_path='by-tag/(?P<tag_slug>[^/.]+)')
    def articles_by_tag(self, request, tag_slug=None):
        tag = get_object_or_404(Tag, slug=tag_slug)

        articles = tag.articles.filter(
            status=Article.Status.PUBLISHED
        )

        return Response({
            "tag": tag.name,
            "results": ArticleListSerializer(articles, many=True).data
        })

    # ---------------- ADMIN DASHBOARD ----------------
    @action(detail=False, methods=['get'])
    def admin_activity_dashboard(self, request):
        return Response({
            "article_counts": {
                "total": Article.objects.count(),
                "draft": Article.objects.filter(status=Article.Status.DRAFT).count(),
                "pending_review": Article.objects.filter(status=Article.Status.PENDING_REVIEW).count(),
                "published": Article.objects.filter(status=Article.Status.PUBLISHED).count(),
                "rejected": Article.objects.filter(status=Article.Status.REJECTED).count(),
            },
            "engagement_counts": {
                "views": ArticleView.objects.count(),
                "comments": Comment.objects.count(),
                "reactions": Reaction.objects.count(),
                "bookmarks": Bookmark.objects.count(),
            },
            "categories": CategorySerializer(Category.objects.all(), many=True).data
        })


# ======================================================
# USER INTERACTION VIEWSET
# ======================================================
class UserInteractionViewSet(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='bookmarks')
    def user_bookmarks(self, request):
        bookmarks = Bookmark.objects.filter(
            user=request.user
        ).select_related('article', 'article__category')

        data = [{
            "bookmark_id": b.id,
            "article_id": b.article.id,
            "title": b.article.title,
            "image": b.article.image.url if b.article.image else None,
            "category_name": getattr(b.article.category, 'name', None),
            "bookmarked_at": b.bookmarked_at
        } for b in bookmarks]

        return Response({"bookmarks": data})
