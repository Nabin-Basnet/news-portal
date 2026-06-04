from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from user.models import Role
from .models import Article, ArticleView, Bookmark, Category, Comment, Reaction

User = get_user_model()

class ArticlePermissionTests(TestCase):
    def setUp(self):
        # Setting up roles to perfectly match model constraints
        self.author_role = Role.objects.create(role_name="Author")
        self.editor_role = Role.objects.create(role_name="Editor")
        self.admin_role = Role.objects.create(role_name="Admin")
        self.user_role = Role.objects.create(role_name="User")

        self.reporter = User.objects.create_user(
            username="rep1",
            email="reporter@example.com",
            password="password123",
            role=self.author_role,
        )
        self.editor = User.objects.create_user(
            username="editor1",
            email="editor@example.com",
            password="password123",
            role=self.editor_role,
        )
        self.admin = User.objects.create_user(
            username="admin1",
            email="admin@example.com",
            password="password123",
            role=self.admin_role,
        )

        self.article = Article.objects.create(
            title="Draft article",
            body="Draft body",
            author=self.reporter,
        )

    def test_guest_cannot_comment(self):
        url = reverse("add_comment", kwargs={"article_id": self.article.id})
        response = self.client.post(
            url,
            data='{"content": "hello"}',
            content_type="application/json",
        )
        # 302 Redirect to login or 401/403 Unauthorized depending on your auth setup
        self.assertIn(response.status_code, [302, 401, 403])
        self.assertEqual(Comment.objects.count(), 0)

    def test_registered_user_can_comment_react_bookmark_and_track_view(self):
        self.article.approve(self.editor)

        user = User.objects.create_user(
            username="reader1",
            email="reader@example.com",
            password="password123",
            role=self.user_role,
        )
        self.client.login(email="reader@example.com", password="password123")

        detail_url = reverse("article_detail", kwargs={"article_id": self.article.id})
        self.client.get(detail_url)
        self.assertEqual(ArticleView.objects.filter(article=self.article, user=user).count(), 1)

        comment_url = reverse("add_comment", kwargs={"article_id": self.article.id})
        react_url = reverse("react_article", kwargs={"article_id": self.article.id})
        bookmark_url = reverse("bookmark_article", kwargs={"article_id": self.article.id})

        self.client.post(comment_url, data='{"content":"Nice"}', content_type="application/json")
        self.client.post(react_url, data='{"reaction":"like"}', content_type="application/json")
        self.client.post(bookmark_url)

        self.assertEqual(Comment.objects.filter(article=self.article, user=user).count(), 1)
        self.assertEqual(Reaction.objects.filter(article=self.article, user=user).count(), 1)
        self.assertEqual(Bookmark.objects.filter(article=self.article, user=user).count(), 1)

    def test_editor_can_approve_pending_article(self):
        self.client.login(email="reporter@example.com", password="password123")
        submit_url = reverse("submit_article", kwargs={"article_id": self.article.id})
        submit_response = self.client.post(submit_url)
        self.assertEqual(submit_response.status_code, 200)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.PENDING_REVIEW)

        self.client.logout()
        self.client.login(email="editor@example.com", password="password123")
        review_url = reverse("review_article", kwargs={"article_id": self.article.id})
        review_response = self.client.post(
            review_url,
            data='{"action":"approve"}',
            content_type="application/json",
        )
        self.assertEqual(review_response.status_code, 200)

        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.PUBLISHED)

    def test_editor_cannot_create_article(self):
        self.client.login(email="editor@example.com", password="password123")
        create_url = reverse("create_article")
        response = self.client.post(
            create_url,
            data='{"title":"x","body":"y"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_reporter_can_create_article_with_new_category_name(self):
        self.client.login(email="reporter@example.com", password="password123")
        create_url = reverse("create_article")
        response = self.client.post(
            create_url,
            data='{"title":"Sports update","body":"Match report","category_name":"Sports"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        article = Article.objects.get(id=response.json()["id"])
        self.assertEqual(article.category.name, "Sports")
        self.assertEqual(article.category.slug, "sports")

    def test_reporter_update_article_can_create_category_from_name(self):
        self.client.login(email="reporter@example.com", password="password123")
        update_url = reverse("update_article", kwargs={"article_id": self.article.id})
        response = self.client.post(
            update_url,
            data='{"title":"Movie news","body":"Cinema story","category_name":"Movies"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.article.refresh_from_db()
        self.assertEqual(self.article.category.name, "Movies")
        self.assertEqual(Category.objects.filter(slug="movies").count(), 1)

    def test_admin_can_view_activity_dashboard(self):
        category = Category.objects.create(name="Sports", slug="sports")
        self.article.category = category
        self.article.save(update_fields=["category", "updated_at"])
        self.article.approve(self.editor)
        
        self.client.login(email="admin@example.com", password="password123")
        activity_url = reverse("admin_activity_dashboard")
        response = self.client.get(activity_url)
        self.assertEqual(response.status_code, 200)
        
        payload = response.json()
        self.assertIn("article_counts", payload)
        self.assertIn("engagement_counts", payload)
        self.assertEqual(payload["categories"][0]["name"], "Sports")
        self.assertEqual(payload["recent_articles"][0]["category__name"], "Sports")

    def test_non_admin_cannot_view_activity_dashboard(self):
        self.client.login(email="reporter@example.com", password="password123")
        activity_url = reverse("admin_activity_dashboard")
        response = self.client.get(activity_url)
        self.assertEqual(response.status_code, 403)