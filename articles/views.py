from datetime import timedelta
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count
from django.shortcuts import get_object_or_404

from .models import Category, Tag, Article, Comment, Reaction, Bookmark, ArticleView
from .serializers import (
    CategorySerializer, TagSerializer, ArticleListSerializer, 
    ArticleDetailSerializer, ArticleWriteSerializer
)
# 🟢 Cleaned Imports: Using IsAuthorOrEditorialStaff exclusively
from .permissions import IsAdminUserRole, IsEditorOrAdmin, IsReporterRole, IsAuthorOrEditorialStaff, get_role


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        role = get_role(request.user)
        if role not in ['reporter', 'author', 'editor', 'admin'] and not request.user.is_superuser:
            return Response({"detail": "Access Cleared for Editorial Staff Only."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ArticleWriteSerializer
        if self.action == 'retrieve':
            return ArticleDetailSerializer
        return ArticleListSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsReporterRole()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthorOrEditorialStaff()]
        if self.action in ['list_pending_articles', 'review']:
            return [IsEditorOrAdmin()]
        if self.action == 'admin_activity_dashboard':
            return [IsAdminUserRole()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action in ['list', 'trending', 'search_feed', 'news_of_the_day']:
            return qs.filter(status=Article.Status.PUBLISHED)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        article = self.get_object()
        user = request.user
        role = get_role(user)

        if article.author_id == user.id and role in ['reporter', 'author']:
            article.delete()
            return Response({"message": "Draft successfully deleted by author."})
        
        if role in ['editor', 'admin'] or user.is_superuser:
            article.delete()
            return Response({"message": "Article removed from portal ecosystem by editorial team."})

        return Response({"detail": "Administrative clearance missing."}, status=status.HTTP_403_FORBIDDEN)

    # --- Standard Public Detail Fetch View ---
    def retrieve(self, request, *args, **kwargs):
        article = get_object_or_404(Article, id=kwargs['pk'], status=Article.Status.PUBLISHED)

        # 1. User Engagement Audits
        if request.user.is_authenticated:
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            client_ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')
            ArticleView.objects.get_or_create(article=article, user=request.user, defaults={'ip_address': client_ip})

        # 2. Optimized Threaded Tree Matrix Assembly
        all_comments = article.comments.select_related("user").order_by("created_at")
        parent_nodes = {}
        for c in all_comments:
            comment_data = {
                "id": c.id, "user_id": c.user.id, "username": c.user.username,
                "content": c.content, "created_at": c.created_at, "replies": []
            }
            if c.parent_id is None:
                parent_nodes[c.id] = comment_data
            else:
                if c.parent_id in parent_nodes:
                    parent_nodes[c.parent_id]["replies"].append({
                        "id": c.id, "user_id": c.user.id, "username": c.user.username,
                        "content": c.content, "created_at": c.created_at, "parent_id": c.parent_id
                    })
        comments_tree = list(parent_nodes.values())

        # 3. Aggregate Reactions
        reaction_counts = article.reactions.values('reaction').annotate(count=Count('id'))
        reactions_summary = {k: 0 for k in Reaction.ReactionType.values}
        for item in reaction_counts:
            reactions_summary[item['reaction']] = item['count']

        user_current_reaction = None
        if request.user.is_authenticated:
            user_react_obj = article.reactions.filter(user=request.user).first()
            if user_react_obj:
                user_current_reaction = user_react_obj.reaction

        # 4. Inject Dynamic Context into Serializer Pipelines
        annotated_article = Article.objects.filter(id=article.id).annotate(
            view_count=Count('views', distinct=True),
            reactions_total=Count('reactions', distinct=True)
        ).first()

        annotated_article.reactions_breakdown = reactions_summary
        annotated_article.user_has_reacted = user_current_reaction

        serializer = self.get_serializer(annotated_article, context={'comments_tree': comments_tree})
        return Response(serializer.data)

    # --- Custom Dynamic Filtration Feed Actions ---

    @action(detail=False, methods=['get'], url_path='trending')
    def trending(self, request):
        articles = self.get_queryset().annotate(view_count=Count('views')).order_by('-view_count')[:10]
        results = ArticleListSerializer(articles, many=True).data
        active_categories = CategorySerializer(Category.objects.all(), many=True).data
        return Response({"results": results, "categories": active_categories})

    @action(detail=False, methods=['get'], url_path='search')
    def search_feed(self, request):
        query = request.query_params.get("q", "").strip()
        category_slug = request.query_params.get("category", "").strip()
        
        articles = self.get_queryset()
        if query:
            articles = articles.filter(title__icontains=query)
        if category_slug:
            articles = articles.filter(category__slug=category_slug)
            
        serializer = ArticleListSerializer(articles, many=True)
        return Response({"query": query, "category": category_slug, "results": serializer.data})

    @action(detail=False, methods=['get'], url_path='news-of-the-day')
    def news_of_the_day(self, request):
        twenty_four_hours_ago = timezone.now() - timedelta(hours=24)
        top_article = self.get_queryset().filter(views__viewed_at__gte=twenty_four_hours_ago).annotate(
            daily_views=Count('views')
        ).order_by('-daily_views').first()

        if not top_article:
            top_article = self.get_queryset().order_by('-published_at').first()

        if not top_article:
            return Response({"message": "No articles available today."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "id": top_article.id,
            "title": top_article.title,
            "published_at": top_article.published_at,
            "daily_views_count": getattr(top_article, 'daily_views', 0)
        })

    @action(detail=False, methods=['get'], url_path='by-tag/(?P<tag_slug>[^/.]+)')
    def articles_by_tag(self, request, tag_slug=None):
        tag = get_object_or_404(Tag, slug=tag_slug)
        articles = tag.articles.filter(status=Article.Status.PUBLISHED).annotate(view_count=Count('views')).order_by('-published_at')
        
        article_list = [{
            "id": art.id, "title": art.title, "image": art.image.url if art.image else None,
            "published_at": art.published_at, "category_name": getattr(art.category, 'name', None), "view_count": art.view_count
        } for art in articles]

        return Response({"tag_name": tag.name, "total_articles": len(article_list), "articles": article_list})

    # --- Workflow State Machines Transitions ---

    @action(detail=True, methods=['post'], url_path='submit', permission_classes=[permissions.IsAuthenticated])
    def submit(self, request, pk=None):
        article = self.get_object()
        if article.author_id != request.user.id:
            return Response({"detail": "Submission denied. Reporter owner boundary error."}, status=status.HTTP_403_FORBIDDEN)
        if article.status != Article.Status.DRAFT:
            return Response({"detail": "Only draft records can be routed into review queues."}, status=status.HTTP_400_BAD_REQUEST)

        article.submit_for_review()
        return Response({"id": article.id, "status": article.status})

    @action(detail=True, methods=['post'], url_path='review')
    def review(self, request, pk=None):
        article = self.get_object()
        if article.status != Article.Status.PENDING_REVIEW:
            return Response({"detail": "Target article is not pending review."}, status=status.HTTP_400_BAD_REQUEST)

        action_type = request.data.get("action")
        note = request.data.get("note", "").strip()

        if action_type == "approve":
            article.approve(request.user)
        elif action_type == "reject":
            article.reject(request.user, note=note)
        else:
            return Response({"detail": "Action must be either 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({"id": article.id, "status": article.status})

    # --- Interaction Systems ---

    @action(detail=True, methods=['post'], url_path='toggle-reaction', permission_classes=[permissions.IsAuthenticated])
    def toggle_reaction(self, request, pk=None):
        article = get_object_or_404(Article, id=pk, status=Article.Status.PUBLISHED)
        requested_type = str(request.data.get("reaction_type", "")).lower().strip()

        if requested_type not in Reaction.ReactionType.values:
            return Response({"detail": "Invalid reaction type."}, status=status.HTTP_400_BAD_REQUEST)

        existing_reaction = Reaction.objects.filter(article=article, user=request.user).first()
        if existing_reaction:
            if existing_reaction.reaction == requested_type:
                existing_reaction.delete()
                return Response({"action": "removed", "reaction_type": None, "message": "Reaction removed."})
            
            existing_reaction.reaction = requested_type
            existing_reaction.save()
            return Response({"action": "updated", "reaction_type": existing_reaction.reaction, "message": f"Reaction shifted."})
        
        new_reaction = Reaction.objects.create(article=article, user=request.user, reaction=requested_type)
        return Response({"action": "created", "reaction_type": new_reaction.reaction, "message": "Reacted successfully."}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='toggle-bookmark', permission_classes=[permissions.IsAuthenticated])
    def toggle_bookmark(self, request, pk=None):
        article = get_object_or_404(Article, id=pk, status=Article.Status.PUBLISHED)
        bookmark_qs = Bookmark.objects.filter(article=article, user=request.user)
        
        if bookmark_qs.exists():
            bookmark_qs.delete()
            return Response({"bookmarked": False, "message": "Bookmark dropped."})
        
        Bookmark.objects.create(article=article, user=request.user)
        return Response({"bookmarked": True, "message": "Bookmark pinned."}, status=status.HTTP_201_CREATED)

    # --- Internal Operational Dashboard Feeds (🟢 Methods Renamed to Match URLs) ---

    @action(detail=False, methods=['get'], url_path='reporter-dashboard')
    def list_reporter_articles(self, request):
        articles = Article.objects.filter(author=request.user).order_by("-updated_at")
        data = [{
            "id": a.id, "title": a.title, "status": a.status, "submitted_at": a.submitted_at,
            "reviewed_at": a.reviewed_at, "published_at": a.published_at, "review_note": a.review_note
        } for a in articles]
        return Response({"results": data})

    @action(detail=False, methods=['get'], url_path='review-queue')
    def list_pending_articles(self, request):
        articles = Article.objects.filter(status=Article.Status.PENDING_REVIEW).order_by("submitted_at")
        data = [{
            "id": a.id, "title": a.title, "author__username": a.author.username, "submitted_at": a.submitted_at
        } for a in articles]
        return Response({"results": data})

    @action(detail=False, methods=['get'], url_path='admin-dashboard')
    def admin_activity_dashboard(self, request):
        recent_articles = Article.objects.order_by("-updated_at").select_related('category')[:20]
        recent_data = [{
            "id": a.id, "title": a.title, "status": a.status, "category_id": a.category_id,
            "category__name": getattr(a.category, 'name', None), "category__slug": getattr(a.category, 'slug', None),
            "author_id": a.author_id, "reviewer_id": a.reviewer_id, "submitted_at": a.submitted_at,
            "reviewed_at": a.reviewed_at, "published_at": a.published_at
        } for a in recent_articles]

        return Response({
            "article_counts": {
                "draft": Article.objects.filter(status=Article.Status.DRAFT).count(),
                "pending": Article.objects.filter(status=Article.Status.PENDING_REVIEW).count(),
                "published": Article.objects.filter(status=Article.Status.PUBLISHED).count(),
                "rejected": Article.objects.filter(status=Article.Status.REJECTED).count(),
            },
            "engagement_counts": {
                "comments": Comment.objects.count(), "reactions": Reaction.objects.count(),
                "bookmarks": Bookmark.objects.count(), "views": ArticleView.objects.count(),
            },
            "categories": list(Category.objects.order_by("name").values("id", "name", "slug")),
            "recent_articles": recent_data
        })


class UserInteractionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    # 🟢 Method Renamed to Match URL Configuration
    @action(detail=False, methods=['get'], url_path='bookmarks')
    def user_bookmarks(self, request):
        bookmarks = Bookmark.objects.filter(user=request.user).select_related('article', 'article__category')
        data = [{
            "bookmark_id": b.id, "article_id": b.article.id, "title": b.article.title,
            "image": b.article.image.url if b.article.image else None,
            "category_name": getattr(b.article.category, 'name', None), "bookmarked_at": b.bookmarked_at
        } for b in bookmarks]
        return Response({"bookmarks": data})