from django.contrib import admin
from django.utils import timezone
from .models import Category, Tag, Article, Comment, Reaction, Bookmark, ArticleView


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "status", "created_at", "published_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("title", "body", "author__email", "category__name")
    prepopulated_fields = {"slug": ("title",)}
    
    # Custom administrative actions for Editors and Admins
    actions = ["bulk_approve_articles", "bulk_reject_articles"]

    def get_queryset(self, request):
        """
        Filters the articles displayed based on the logged-in user's role.
        """
        qs = super().get_queryset(request)
        user = request.user
        
        # Superusers and Admins see everything
        if user.is_superuser or (hasattr(user, 'role') and user.role.role_name.lower() == 'admin'):
            return qs
            
        # Editors see everything except raw drafts (they focus on review queues)
        if hasattr(user, 'role') and user.role.role_name.lower() == 'editor':
            return qs.exclude(status='draft')
            
        # Authors can ONLY see and manage their own articles
        if hasattr(user, 'role') and user.role.role_name.lower() == 'author':
            return qs.filter(author=user)
            
        # Standard users shouldn't have admin access, but fallback to nothing
        return qs.none()

    def get_readonly_fields(self, request, obj=None):
        """
        Locks down workflow and tracking fields so users can't manually forge data.
        """
        base_readonly = [
            "submitted_at", "reviewed_at", "published_at", 
            "created_at", "updated_at", "reviewer"
        ]
        
        user = request.user
        role_name = getattr(user.role, 'role_name', '').lower() if hasattr(user, 'role') else ''

        # Authors shouldn't be allowed to change an article's status or review note manually
        if role_name == 'author' or not user.is_superuser:
            return base_readonly + ["status", "review_note"]
            
        return base_readonly

    def save_model(self, request, obj, form, change):
        """
        Automatically sets the author field when an author creates an article.
        """
        if not change or not obj.author:
            user = request.user
            role_name = getattr(user.role, 'role_name', '').lower() if hasattr(user, 'role') else ''
            if role_name == 'author':
                obj.author = user
                obj.author_name = f"{user.first_name} {user.last_name}".strip() or user.email
        super().save_model(request, obj, form, change)

    # --- Custom Workflow Actions ---
    
    @admin.action(description="Approve selected articles for publication")
    def bulk_approve_articles(self, request, queryset):
        user = request.user
        role_name = getattr(user.role, 'role_name', '').lower() if hasattr(user, 'role') else ''
        
        if role_name not in ['editor', 'admin'] and not user.is_superuser:
            self.message_user(request, "You do not have permission to approve articles.", level="error")
            return

        updated_count = 0
        for article in queryset.filter(status='pending_review'):
            article.approve(reviewer=user)
            updated_count += 1
            
        self.message_user(request, f"Successfully published {updated_count} articles.")

    @admin.action(description="Reject selected articles")
    def bulk_reject_articles(self, request, queryset):
        user = request.user
        role_name = getattr(user.role, 'role_name', '').lower() if hasattr(user, 'role') else ''
        
        if role_name not in ['editor', 'admin'] and not user.is_superuser:
            self.message_user(request, "You do not have permission to reject articles.", level="error")
            return

        updated_count = 0
        for article in queryset.filter(status='pending_review'):
            article.reject(reviewer=user, note="Rejected via bulk admin actions.")
            updated_count += 1
            
        self.message_user(request, f"Rejected {updated_count} articles and sent back to authors.")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "article", "user", "created_at")
    search_fields = ("article__title", "user__email", "content")
    readonly_fields = ("created_at",)


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ("id", "article", "user", "reaction", "created_at")
    list_filter = ("reaction",)
    readonly_fields = ("created_at",)


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("id", "article", "user", "created_at")
    readonly_fields = ("created_at",)


@admin.register(ArticleView)
class ArticleViewAdmin(admin.ModelAdmin):
    # REMOVED 'ip_address' from this tuple
    list_display = ('id', 'article', 'user', 'viewed_at') 
    
    # REMOVED 'ip_address' from this tuple
    readonly_fields = ('viewed_at',)