from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ArticleViewSet, UserInteractionViewSet

app_name = "articles"

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')

urlpatterns = [
    # Router (Handles category routing dynamically)
    path("", include(router.urls)),

    # DASHBOARDS & WORKFLOWS
    path("admin/activity/", ArticleViewSet.as_view({"get": "admin_activity_dashboard"}), name="admin_activity_dashboard"),
    path("reporter/articles/", ArticleViewSet.as_view({"get": "list_reporter_articles"}), name="reporter_articles"),
    path("pending/", ArticleViewSet.as_view({"get": "list_pending_articles"}), name="pending_articles"),

    # PUBLIC FEEDS
    path("feed/", ArticleViewSet.as_view({"get": "list"}), name="list_published_articles"),
    path("trending/", ArticleViewSet.as_view({"get": "trending"}), name="trending_articles"),
    path("news-of-the-day/", ArticleViewSet.as_view({"get": "news_of_the_day"}), name="news_of_the_day"),
    path("search/", ArticleViewSet.as_view({"get": "search_feed"}), name="search_feed"),
    path("tag/<slug:tag_slug>/", ArticleViewSet.as_view({"get": "articles_by_tag"}), name="articles_by_tag"),

    # ARTICLE CRUD (Using standardized pk lookup for DRF compatibility)
    path("create/", ArticleViewSet.as_view({"post": "create"}), name="create_article"),
    path("<int:pk>/", ArticleViewSet.as_view({"get": "retrieve"}), name="article_detail"),
    path(
        "<int:pk>/update/",
        ArticleViewSet.as_view({"put": "update", "patch": "partial_update", "post": "partial_update"}),
        name="update_article"
    ),
    path("<int:pk>/delete/", ArticleViewSet.as_view({"delete": "destroy"}), name="delete_article"),

    # ARTICLE WORKFLOW
    path("<int:pk>/submit/", ArticleViewSet.as_view({"post": "submit"}), name="submit_article"),
    path("<int:pk>/review/", ArticleViewSet.as_view({"post": "review"}), name="review_article"),

    # USER INTERACTIONS & COMMENTS
    path("<int:pk>/comment/", ArticleViewSet.as_view({"post": "add_comment"}), name="add_comment"),
    path("<int:pk>/react/", ArticleViewSet.as_view({"post": "toggle_reaction"}), name="toggle_reaction"),
    path("<int:pk>/bookmark/", ArticleViewSet.as_view({"post": "toggle_bookmark"}), name="toggle_bookmark"),
    path("my-bookmarks/", UserInteractionViewSet.as_view({"get": "user_bookmarks"}), name="my_bookmarks"),
]