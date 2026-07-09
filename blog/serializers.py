from rest_framework import serializers
from .models import BlogPost, BlogTopic


class BlogTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogTopic
        fields = "__all__"


class BlogPostListSerializer(serializers.ModelSerializer):
    excerpt = serializers.SerializerMethodField()

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
