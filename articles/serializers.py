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
        fields = ['id', 'title', 'published_at', 'category_name', 'category_slug', 'status']


class ArticleDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    view_count = serializers.IntegerField(read_only=True)
    reactions_total = serializers.IntegerField(read_only=True)
    reactions_breakdown = serializers.DictField(read_only=True)
    user_has_reacted = serializers.CharField(read_only=True)
    comments = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'body', 'image', 'author_name', 'published_at',
            'tags', 'view_count', 'reactions_total', 'reactions_breakdown',
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
    # 🟢 Allow null or blank input types so multi-part form data doesn't trigger validation blockers
    category_id = serializers.CharField(write_only=True, required=False, allow_null=True, allow_blank=True)
    category_name = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'body', 'image', 'author_name', 'category_id', 'category_name', 'status']
        read_only_fields = ['status']

    def _assign_category(self, instance, category_id, category_name):
        # 🟢 Explicitly parse form data variations (integers vs strings vs empty text fields)
        parsed_id = None
        if category_id is not None and str(category_id).strip() != "":
            try:
                parsed_id = int(category_id)
            except ValueError:
                parsed_id = None

        if parsed_id:
            instance.category = Category.objects.filter(id=parsed_id).first()
        elif category_name and str(category_name).strip():
            name = str(category_name).strip()
            slug = slugify(name)
            if slug:
                category, _ = Category.objects.get_or_create(slug=slug, defaults={"name": name})
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