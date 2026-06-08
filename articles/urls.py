from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ArticleViewSet, UserInteractionViewSet

app_name = "articles"

# 1. Register standard CRUD endpoints via router
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')

urlpatterns = [
    # Router endpoints (Handles GET/POST /articles/categories/)
    path("", include(router.urls)),

    # Dashboards & Pipelines
    path("admin/activity/", ArticleViewSet.as_view({"get": "admin_dashboard"}), name="admin_activity_dashboard"),
    path("reporter/articles/", ArticleViewSet.as_view({"get": "reporter_dashboard"}), name="list_reporter_articles"),
    path("pending/", ArticleViewSet.as_view({"get": "review_queue"}), name="list_pending_articles"),
    
    # Core Feeds
    path("", ArticleViewSet.as_view({"get": "list"}), name="list_published_articles"),
    path("trending/", ArticleViewSet.as_view({"get": "trending"}), name="trending_articles"),
    path("news-of-the-day/", ArticleViewSet.as_view({"get": "news_of_the_day"}), name="news_of_the_day"),
    path("search/", ArticleViewSet.as_view({"get": "search_feed"}), name="search_articles"),
    
    # Classification Lookups
    path("categories/create/", CategoryViewSet.as_view({"post": "create"}), name="create_category"),
    path("tag/<slug:tag_slug>/", ArticleViewSet.as_view({"get": "articles_by_tag"}), name="articles_by_tag"),
    
    # Content Modification Lifecycles
    path("create/", ArticleViewSet.as_view({"post": "create"}), name="create_article"),
    path("<int:pk>/", ArticleViewSet.as_view({"get": "retrieve"}), name="article_detail"),
    path("<int:pk>/update/", ArticleViewSet.as_view({"post": "update", "put": "update", "patch": "partial_update"}), name="update_article"),
    path("<int:pk>/submit/", ArticleViewSet.as_view({"post": "submit"}), name="submit_article"),
    path("<int:pk>/review/", ArticleViewSet.as_view({"post": "review"}), name="review_article"),
    path("<int:pk>/delete/", ArticleViewSet.as_view({"post": "destroy", "delete": "destroy"}), name="delete_article"),
    
    # User Interaction Integrations
    # Note: Retaining your direct retrieval setup inside retrieve() for list_comments if needed,
    # or explicitly pointing to custom view routing handlers:
    path("<int:pk>/comments/", ArticleViewSet.as_view({"get": "retrieve"}), name="list_comments"), 
    path("<int:pk>/comments/add/", ArticleViewSet.as_view({"post": "retrieve"}), name="add_comment"), # Handled via dynamic detail context payload
    path("<int:pk>/react/", ArticleViewSet.as_view({"post": "toggle_reaction"}), name="toggle_reaction"),
    path("<int:pk>/bookmark/", ArticleViewSet.as_view({"post": "toggle_bookmark"}), name="toggle_bookmark"),
    path("my-bookmarks/", UserInteractionViewSet.as_view({"get": "saved_bookmarks"}), name="user_bookmarks"),
]