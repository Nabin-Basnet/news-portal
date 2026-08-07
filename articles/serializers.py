from rest_framework import serializers
from django.utils.text import slugify
from .models import Category, Tag, Article, Comment, Reaction, Bookmark


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['slug']


class RecursiveCommentSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return instance


class ArticleListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)

    class Meta:
        model = Article
        fields = ['id', 'slug', 'title', 'summary', 'published_at', 'category_name', 'category_slug', 'status']


class ArticleDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    view_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    reactions_total = serializers.IntegerField(read_only=True)
    bookmark_count = serializers.IntegerField(read_only=True)
    reactions_breakdown = serializers.DictField(read_only=True)
    user_has_reacted = serializers.CharField(read_only=True)
    comments = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'slug', 'title', 'summary', 'body', 'image', 'author_name', 'published_at',
            'tags', 'view_count', 'comment_count', 'reactions_total', 'bookmark_count', 'reactions_breakdown',
            'user_has_reacted', 'comments'
        ]

    def get_author_name(self, obj):
        if obj.author_name:
            return obj.author_name
        if obj.author:
            return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.email
        return ""

    def get_image(self, obj):
        return obj.image.url if obj.image else None

    def get_comments(self, obj):
        return self.context.get('comments_tree', [])


class ArticleWriteSerializer(serializers.ModelSerializer):
    category_id = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    category_name = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'summary', 'body', 'image', 'author_name', 'category_id', 'category_name', 'status']
        read_only_fields = ['status']

    def validate_title(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Title is required.")
        return value.strip()

    def validate_body(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError("Body is required.")
        return value.strip()

    def validate(self, attrs):
        category_id = attrs.get('category_id')
        category_name = attrs.get('category_name')

        if category_id in (None, '', 'null'):
            category_id = None

        if category_id is not None and str(category_id).strip() != '':
            try:
                int(str(category_id))
            except ValueError as exc:
                raise serializers.ValidationError({'category_id': 'Category ID must be an integer.'}) from exc

        if category_name and str(category_name).strip():
            slug = slugify(str(category_name).strip())
            if not Category.objects.filter(slug=slug).exists():
                raise serializers.ValidationError({'category_name': 'Category not found. Create it through the category API.'})

        return attrs

    def _assign_category(self, instance, category_id, category_name):
        # 🟢 Explicitly parse form data variations (integers vs strings vs empty text fields)
        parsed_id = None
        if category_id is not None and str(category_id).strip() != "":
            try:
                parsed_id = int(category_id)
            except ValueError:
                parsed_id = None

        if parsed_id:
            category = Category.objects.filter(id=parsed_id).first()
            if not category:
                raise serializers.ValidationError({"category_id": "Category not found."})
            instance.category = category
        elif category_name and str(category_name).strip():
            name = str(category_name).strip()
            category = Category.objects.filter(slug=slugify(name)).first()
            if not category:
                raise serializers.ValidationError({"category_name": "Category not found. Create it through the category API."})
            instance.category = category
        elif category_id == "" or category_id is None:
            # Clear field explicitly if user requests removal
            instance.category = None

    def create(self, validated_data):
        category_id = validated_data.pop('category_id', None)
        category_name = validated_data.pop('category_name', None)

        request = self.context.get('request')
        user = request.user if request else None

        if not validated_data.get('author_name') and user:
            validated_data['author_name'] = f"{user.first_name} {user.last_name}".strip() or user.email

        article = Article.objects.create(status=Article.Status.DRAFT, **validated_data)
        self._assign_category(article, category_id, category_name)
        article.save()
        return article

    def update(self, instance, validated_data):
        category_id = validated_data.pop('category_id', None)
        category_name = validated_data.pop('category_name', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        self._assign_category(instance, category_id, category_name)
        
        if instance.status == Article.Status.REJECTED:
            instance.status = Article.Status.DRAFT
            instance.review_note = ""

        instance.save()
        return instance


class AdminArticleListSerializer(serializers.ModelSerializer):
    """Read model and aggregate data required by the custom admin article list."""

    author = serializers.SerializerMethodField()
    category = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    featured = serializers.SerializerMethodField()
    view_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    reaction_count = serializers.IntegerField(read_only=True)
    bookmark_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Article
        fields = [
            "id", "title", "slug", "author", "category", "status", "featured",
            "created_at", "updated_at", "published_at", "view_count", "comment_count",
            "reaction_count", "bookmark_count",
        ]

    def get_author(self, obj):
        if not obj.author_id:
            return None
        return {
            "id": obj.author_id,
            "name": obj.author_name or obj.author.full_name or obj.author.email,
            "email": obj.author.email,
        }

    def get_featured(self, obj):
        # The Article model currently has no persisted featured flag.
        return False


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'content', 'parent', 'created_at']
        read_only_fields = ['id', 'created_at', 'parent']

    def validate_content(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Comment content is required.')
        return str(value).strip()


class ReactionSerializer(serializers.Serializer):
    reaction_type = serializers.ChoiceField(choices=[choice[0] for choice in Reaction.ReactionType.choices], required=True)
