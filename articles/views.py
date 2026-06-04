import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt  # <-- ADD THIS LINE
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from django.utils.text import slugify
from django.db.models import Count
from django.shortcuts import get_object_or_404
from .models import Article, ArticleView, Bookmark, Comment, Reaction, Category
# --- Internal Helper Utilities ---

def _role_name(user):
    if not user.is_authenticated or not hasattr(user, "role") or not user.role:
        return ""
    return user.role.role_name.lower()


def _is_reporter(user):
    return _role_name(user) in ["reporter", "author"]


def _is_editor(user):
    return _role_name(user) == "editor"


def _is_admin(user):
    return user.is_authenticated and (user.is_superuser or _role_name(user) == "admin")


def _parse_json_body(request):
    """Safely extracts dictionary items from incoming request bodies without crashing."""
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except (ValueError, SyntaxError):
        return {}


def _category_from_input(category_id=None, category_name=""):
    if category_id:
        return Category.objects.filter(id=category_id).first()

    category_name = (category_name or "").strip()
    if not category_name:
        return None

    slug = slugify(category_name)
    if not slug:
        return None

    category, _created = Category.objects.get_or_create(
        slug=slug,
        defaults={"name": category_name},
    )
    return category


# --- Category Endpoints ---

@require_GET
def list_categories(request):
    categories = list(Category.objects.all().values("id", "name", "slug"))
    return JsonResponse({"results": categories})


@login_required
@require_POST
def create_category(request):
    if not (_is_reporter(request.user) or _is_editor(request.user) or _is_admin(request.user)):
        return HttpResponseForbidden("Only reporters, editors, or admins can create categories.")
        
    payload = _parse_json_body(request)
    name = payload.get("name", "").strip()
    if not name:
        return HttpResponseBadRequest("Category name is required.")

    slug = slugify(name)
    if not slug:
        return HttpResponseBadRequest("Category name must contain letters or numbers.")

    category, created = Category.objects.get_or_create(slug=slug, defaults={"name": name})
    return JsonResponse(
        {"id": category.id, "name": category.name, "slug": category.slug},
        status=201 if created else 200
    )


# --- Content Feeds ---

@require_GET
def trending_articles(request):
    articles = Article.objects.filter(status=Article.Status.PUBLISHED).annotate(
        view_count=Count('views')
    ).order_by('-view_count')[:10]
    
    # Materialize query structure to array matching test structures
    results = list(articles.values("id", "title", "published_at", "view_count", "category__name", "category__slug"))
    return JsonResponse({"results": results, "categories": results})


@require_GET
def list_published_articles(request):
    articles = list(Article.objects.filter(status=Article.Status.PUBLISHED).values("id", "title", "published_at"))
    return JsonResponse({"results": articles})


@require_GET
def search_articles(request):
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    
    articles = Article.objects.filter(status=Article.Status.PUBLISHED)
    if query:
        articles = articles.filter(title__icontains=query)
    if category_slug:
        articles = articles.filter(category__slug=category_slug)
        
    return JsonResponse(
        {
            "query": query,
            "category": category_slug,
            "results": list(articles.values("id", "title", "published_at", "category__name", "category__slug")),
        }
    )


@require_GET
def article_detail(request, article_id):
    article = Article.objects.filter(id=article_id, status=Article.Status.PUBLISHED).first()
    if not article:
        return JsonResponse({"detail": "Article not found."}, status=404)

    # STRICT REQUIREMENT: Only log view counts for registered, authenticated users
    if request.user.is_authenticated:
        # get_or_create prevents duplicate count logs when refreshing or reloading
        ArticleView.objects.get_or_create(
            article=article, 
            user=request.user
        )

    comments = list(
        article.comments.select_related("user").values("id", "user_id", "content", "created_at")
    )
    
    # Calculate unique view count dynamically
    total_unique_views = article.views.count()

    return JsonResponse(
        {
            "id": article.id,
            "title": article.title,
            "body": article.body,
            "image": article.image.url if article.image else None,
            "author_name": article.author_name or (f"{article.author.first_name} {article.author.last_name}".strip() if article.author else ""),
            "published_at": article.published_at,
            "view_count": total_unique_views,  # Unique count passed to frontend
            "comments": comments,
        }
    )

# --- Content Creation / Workflow Endpoints ---

@login_required
@require_POST
def create_article(request):
    if not _is_reporter(request.user):
        return HttpResponseForbidden("Only reporters can create article drafts.")

    if request.content_type == "application/json":
        payload = _parse_json_body(request)
        title = payload.get("title", "").strip()
        body = payload.get("body", "").strip()
        author_name = payload.get("author_name", "").strip()
        category_id = payload.get("category_id")
        category_name = payload.get("category_name") or payload.get("category")
        image = None
    else:
        title = request.POST.get("title", "").strip()
        body = request.POST.get("body", "").strip()
        author_name = request.POST.get("author_name", "").strip()
        category_id = request.POST.get("category_id")
        category_name = request.POST.get("category_name") or request.POST.get("category")
        image = request.FILES.get("image")

    if not title or not body:
        return HttpResponseBadRequest("Both title and body are required.")

    category = _category_from_input(category_id=category_id, category_name=category_name)

    article = Article.objects.create(
        title=title,
        body=body,
        image=image,
        author=request.user,
        author_name=author_name or f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email,
        category=category,
        status=Article.Status.DRAFT,
    )
    return JsonResponse({"id": article.id, "status": article.status}, status=201)


@login_required
@require_POST
def update_article(request, article_id):
    if not _is_reporter(request.user):
        return HttpResponseForbidden("Only reporters can edit articles.")
        
    article = Article.objects.filter(id=article_id, author=request.user).first()
    if not article:
        return JsonResponse({"detail": "Article not found."}, status=404)
        
    if article.status not in [Article.Status.DRAFT, Article.Status.REJECTED]:
        return HttpResponseBadRequest("Only draft or rejected articles can be edited.")
        
    if request.content_type == "application/json":
        payload = _parse_json_body(request)
        title = payload.get("title", article.title).strip()
        body = payload.get("body", article.body).strip()
        author_name = payload.get("author_name", article.author_name).strip()
        category_id = payload.get("category_id")
        category_name = payload.get("category_name") or payload.get("category")
        image = article.image
    else:
        title = request.POST.get("title", article.title).strip()
        body = request.POST.get("body", article.body).strip()
        author_name = request.POST.get("author_name", article.author_name).strip()
        category_id = request.POST.get("category_id")
        category_name = request.POST.get("category_name") or request.POST.get("category")
        if "image" in request.FILES:
            image = request.FILES.get("image")
        elif "image" in request.POST and not request.POST.get("image"):
            image = None
        else:
            image = article.image
    
    if not title or not body:
        return HttpResponseBadRequest("Both title and body are required.")
        
    article.title = title
    article.body = body
    article.author_name = author_name
    article.image = image
    
    if category_id is not None:
        article.category = _category_from_input(category_id=category_id) if str(category_id).strip() else None
    elif category_name is not None:
        article.category = _category_from_input(category_name=category_name)
        
    if article.status == Article.Status.REJECTED:
        article.status = Article.Status.DRAFT
        article.review_note = ""

    article.save()
    return JsonResponse({"id": article.id, "status": article.status})


@login_required
@require_POST
def submit_article(request, article_id):
    article = Article.objects.filter(id=article_id).first()
    if not article:
        return JsonResponse({"detail": "Article not found."}, status=404)
    if article.author_id != request.user.id:
        return HttpResponseForbidden("Only the reporter who created this draft can submit it.")
    if article.status != Article.Status.DRAFT:
        return HttpResponseBadRequest("Only draft articles can be submitted.")

    article.submit_for_review()
    return JsonResponse({"id": article.id, "status": article.status})


@login_required
@require_POST
def review_article(request, article_id):
    if not _is_editor(request.user) and not _is_admin(request.user):
        return HttpResponseForbidden("Only editors or admins can review articles.")

    article = Article.objects.filter(id=article_id).first()
    if not article:
        return JsonResponse({"detail": "Article not found."}, status=404)
    if article.status != Article.Status.PENDING_REVIEW:
        return HttpResponseBadRequest("Only pending-review articles can be reviewed.")

    payload = _parse_json_body(request)
    action = payload.get("action")
    note = payload.get("note", "").strip()

    if action == "approve":
        article.approve(request.user)
    elif action == "reject":
        article.reject(request.user, note=note)
    else:
        return HttpResponseBadRequest("Action must be either 'approve' or 'reject'.")
        
    return JsonResponse({"id": article.id, "status": article.status})


# --- Missing Explicit Deletion Enforcement Target Endpoint ---

@csrf_exempt
@login_required
@require_http_methods(["POST", "DELETE"])
def delete_article(request, article_id):
    """Enforces the rules: Authors can delete their own work, Editors can clean up toxic entries."""
    article = get_object_or_404(Article, id=article_id)
    user = request.user
    
    is_owner = (article.author_id == user.id)
    
    if is_owner and _is_reporter(user):
        article.delete()
        return JsonResponse({"message": "Draft successfully deleted by author."})
        
    if _is_editor(user) or _is_admin(user):
        article.delete()
        return JsonResponse({"message": "Article removed from portal ecosystem by editorial team."})
        
    return HttpResponseForbidden("You do not have administrative clearance to delete this record.")


# --- User Interactions (Comments, Likes, Bookmarks) ---

@require_GET
def list_article_comments(request, article_id):
    article = Article.objects.filter(id=article_id, status=Article.Status.PUBLISHED).first()
    if not article:
        return JsonResponse({"detail": "Article not found."}, status=404)
    comments = list(article.comments.select_related("user").values("id", "user_id", "content", "created_at"))
    return JsonResponse({"results": comments})


@login_required
@require_POST
def add_comment(request, article_id):
    article = Article.objects.filter(id=article_id, status=Article.Status.PUBLISHED).first()
    if not article:
        return JsonResponse({"detail": "Article not found."}, status=404)
        
    payload = _parse_json_body(request)
    content = payload.get("content", "").strip()
    if not content:
        return HttpResponseBadRequest("Comment content is required.")
        
    comment = Comment.objects.create(article=article, user=request.user, content=content)
    return JsonResponse({"id": comment.id}, status=201)

@login_required
@require_POST
def react_to_article(request, article_id):
    article = Article.objects.filter(id=article_id, status=Article.Status.PUBLISHED).first()
    if not article:
        return JsonResponse({"detail": "Article not found."}, status=404)

    payload = _parse_json_body(request)
    reaction_name = payload.get("reaction", "like").strip() or "like"
    
    # update_or_create ensures a single user only has ONE active reaction per article
    reaction, created = Reaction.objects.update_or_create(
        article=article,
        user=request.user,
        defaults={"reaction": reaction_name}
    )
    return JsonResponse({"id": reaction.id, "reaction": reaction.reaction})


@login_required
@require_POST
def bookmark_article(request, article_id):
    article = Article.objects.filter(id=article_id, status=Article.Status.PUBLISHED).first()
    if not article:
        return JsonResponse({"detail": "Article not found."}, status=404)
        
    # Toggle behavior: If it exists, remove it (unbookmark). If not, create it.
    bookmark_queryset = Bookmark.objects.filter(article=article, user=request.user)
    if bookmark_queryset.exists():
        bookmark_queryset.delete()
        return JsonResponse({"message": "Bookmark removed."}, status=200)
    else:
        bookmark = Bookmark.objects.create(article=article, user=request.user)
        return JsonResponse({"id": bookmark.id, "message": "Bookmarked successfully."}, status=201)

# --- Dashboards & Pipelines ---

@login_required
@require_GET
def admin_activity_dashboard(request):
    if not _is_admin(request.user):
        return HttpResponseForbidden("Only admins can view activity data.")

    return JsonResponse(
        {
            "article_counts": {
                "draft": Article.objects.filter(status=Article.Status.DRAFT).count(),
                "pending": Article.objects.filter(status=Article.Status.PENDING_REVIEW).count(),
                "published": Article.objects.filter(status=Article.Status.PUBLISHED).count(),
                "rejected": Article.objects.filter(status=Article.Status.REJECTED).count(),
            },
            "engagement_counts": {
                "comments": Comment.objects.count(),
                "reactions": Reaction.objects.count(),
                "bookmarks": Bookmark.objects.count(),
                "views": ArticleView.objects.count(),
            },
            "categories": list(Category.objects.order_by("name").values("id", "name", "slug")),
            "recent_articles": list(
                Article.objects.order_by("-updated_at")
                .values(
                    "id", "title", "status", "category_id",
                    "category__name", "category__slug", "author_id",
                    "reviewer_id", "submitted_at", "reviewed_at", "published_at"
                )[:20]
            ),
        }
    )


@login_required
@require_GET
def list_reporter_articles(request):
    if not _is_reporter(request.user):
        return HttpResponseForbidden("Only reporters can view their articles.")
    
    articles = list(Article.objects.filter(author=request.user).order_by("-updated_at").values(
        "id", "title", "status", "submitted_at", "reviewed_at", "published_at", "review_note"
    ))
    return JsonResponse({"results": articles})


@login_required
@require_GET
def list_pending_articles(request):
    if not _is_editor(request.user) and not _is_admin(request.user):
        return HttpResponseForbidden("Only editors or admins can view pending articles.")
        
    articles = list(Article.objects.filter(status=Article.Status.PENDING_REVIEW).order_by("submitted_at").values(
        "id", "title", "author__username", "submitted_at"
    ))
    return JsonResponse({"results": articles})