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
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"#{self.name}"


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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()

    # Self-referencing foreign key for nested replies
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="replies"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # FIXED: Ascending sort makes conversation flows readable (top-to-bottom)
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["article", "created_at"]),
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.article.title}"
    
    @property
    def is_reply(self):
        return self.parent is not None


class Reaction(models.Model):
    class ReactionType(models.TextChoices):
        LIKE = "like", "Like"
        LOVE = "love", "Love"
        WOW = "wow", "Wow"
        SAD = "sad", "Sad"  # FIXED: Lowercase key consistency

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="article_reactions")
    reaction = models.CharField(
        max_length=10,
        choices=ReactionType.choices,
        default=ReactionType.LIKE
    )
    reacted_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('article', 'user')
        indexes = [
            models.Index(fields=["article", "reaction"]),
        ]

    def __str__(self):
        # FIXED: Replaced crashing field name with functional property string method
        return f"{self.user.username} reacted {self.get_reaction_display()} to {self.article.title}"  


class Bookmark(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="bookmarks")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="article_bookmarks")
    bookmarked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-bookmarked_at"]
        unique_together = ('article', 'user')

    def __str__(self):
        return f"{self.user.username} bookmarked {self.article.title}"


class ArticleView(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="article_views")
    ip_address = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at"]
        unique_together = ('article', 'user', 'ip_address')
        indexes = [
            models.Index(fields=["article"]),
            models.Index(fields=["viewed_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} viewed {self.article.title} from {self.ip_address}"