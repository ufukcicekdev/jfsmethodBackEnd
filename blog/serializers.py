from rest_framework import serializers
from .models import BlogPost, BlogTopic


class BlogTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogTopic
        fields = "__all__"


class BlogPostListSerializer(serializers.ModelSerializer):
    excerpt = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = [
            "id", "title", "slug", "cover_image", "is_published",
            "ai_generated", "published_at", "created_at", "view_count", "excerpt",
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
    class Meta:
        model = BlogPost
        fields = "__all__"


class BlogPostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPost
        fields = [
            "title", "content", "cover_image", "is_published", "topic",
        ]
