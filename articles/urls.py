from django.urls import path

from . import views

urlpatterns = [
    path("admin/activity/", views.admin_activity_dashboard, name="admin_activity_dashboard"),
    path("", views.list_published_articles, name="list_published_articles"),
    path("categories/", views.list_categories, name="list_categories"),
    path("categories/create/", views.create_category, name="create_category"),
    path("trending/", views.trending_articles, name="trending_articles"),
    path("search/", views.search_articles, name="search_articles"),
    path("<int:article_id>/", views.article_detail, name="article_detail"),
    path("<int:article_id>/comments/", views.list_article_comments, name="list_comments"),
    path("<int:article_id>/comments/add/", views.add_comment, name="add_comment"),
    path("<int:article_id>/react/", views.react_to_article, name="react_article"),
    path("<int:article_id>/bookmark/", views.bookmark_article, name="bookmark_article"),
    path("create/", views.create_article, name="create_article"),
    path("<int:article_id>/submit/", views.submit_article, name="submit_article"),
    path("<int:article_id>/review/", views.review_article, name="review_article"),
    path("reporter/articles/", views.list_reporter_articles, name="list_reporter_articles"),
    path("<int:article_id>/update/", views.update_article, name="update_article"),
    path("pending/", views.list_pending_articles, name="list_pending_articles"),
]
