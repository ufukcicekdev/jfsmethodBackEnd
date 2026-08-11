from rest_framework import serializers
from .models import BlogCategory, BlogPost, BlogTopic


class BlogCategorySerializer(serializers.ModelSerializer):
    post_count = serializers.SerializerMethodField()

    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug", "description", "sort_order", "is_active", "created_at", "post_count"]
        read_only_fields = ["id", "slug", "created_at", "post_count"]

    def get_post_count(self, obj):
        return obj.posts.count()


class BlogTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogTopic
        fields = "__all__"


class BlogPostListSerializer(serializers.ModelSerializer):
    excerpt = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "slug", "cover_image", "is_published",
            "ai_generated", "published_at", "created_at", "view_count", "excerpt",
            "category", "category_name",
        ]

    def get_excerpt(self, obj):
        import re
        text = re.sub(r"<[^>]+>", " ", obj.content or "")
        text = re.sub(r"\s+", " ", text).strip()
        return text[:200]

    def get_cover_image(self, obj):
        if obj.cover_image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        import re
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', obj.content or "")
        if match:
            return match.group(1)
        return None


class BlogPostDetailSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = "__all__"

    def get_cover_image(self, obj):
        if obj.cover_image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.cover_image.url)
            return obj.cover_image.url
        import re
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', obj.content or "")
        if match:
            return match.group(1)
        return None


class BlogPostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = [
            "title", "content", "cover_image", "is_published", "topic", "category",
        ]
