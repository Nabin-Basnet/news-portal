from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status="published")


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending Review"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"

    # Core Content
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(unique=True, max_length=300, blank=True)
    summary = models.TextField(max_length=500, blank=True)
    body = models.TextField()
    image = models.ImageField(upload_to="article_images/", null=True, blank=True)
    
    # Workflow Roles
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="articles_authored",
        null=True,
        blank=True,
        limit_choices_to={"role__role_name__iexact": "author"},
    )
    author_name = models.CharField(max_length=255, blank=True)
    
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="articles_reviewed",
        null=True,
        blank=True,
        limit_choices_to={"role__role_name__iexact": "editor"},
    )
    
    # Status & Feedback
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    review_note = models.TextField(blank=True)
    
    # Metadata Timestamps
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Classifications
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="articles")

    objects = ArticleQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def view_count(self):
        return self.views.count()

    @property
    def comment_count(self):
        return self.comments.count()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    # Workflow Actions
    def submit_for_review(self):
        self.status = self.Status.PENDING_REVIEW
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])

    def approve(self, reviewer):
        now = timezone.now()
        self.status = self.Status.PUBLISHED
        self.reviewer = reviewer
        self.reviewed_at = now
        self.published_at = now
        self.save(
            update_fields=[
                "status",
                "reviewer",
                "reviewed_at",
                "published_at",
                "updated_at",
            ]
        )

    def reject(self, reviewer, note=""):
        self.status = self.Status.REJECTED
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save(
            update_fields=[
                "status",
                "reviewer",
                "reviewed_at",
                "review_note",
                "updated_at",
            ]
        )


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="article_comments")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.article.title}"


class Reaction(models.Model):
    class Type(models.TextChoices):
        LIKE = "like", "Like"
        LOVE = "love", "Love"
        WOW = "wow", "Wow"

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="article_reactions")
    reaction = models.CharField(max_length=10, choices=Type.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["article", "user"],
                name="unique_user_reaction",
            )
        ]

    def __str__(self):
        return f"{self.user.email} {self.reaction} {self.article.title}"


class Bookmark(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="bookmarks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="article_bookmarks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["article", "user"],
                name="unique_bookmark",
            )
        ]
        indexes = [
            models.Index(fields=["user", "article"]),
        ]

    def __str__(self):
        return f"{self.user.email} bookmarked {self.article.title}"


class ArticleView(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="views")
    # Changed to on_delete=models.CASCADE and removed null/blank so ONLY registered users can have a view row
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="article_views")
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at"]
        # This is the magic line that stops duplicate counts at the database layer
        unique_together = ('article', 'user')
        indexes = [
            models.Index(fields=["article"]),
            models.Index(fields=["viewed_at"]),
        ]

    def __str__(self):
        return f"{self.user} viewed {self.article.title} at {self.viewed_at}"