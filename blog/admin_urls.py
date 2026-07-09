from django.urls import path
from .views import (
    AdminBlogPostListView,
    AdminBlogPostDetailView,
    AdminBlogTopicListView,
    AdminBlogTopicDetailView,
    AdminBlogGenerateView,
    AdminBlogImageUploadView,
)

urlpatterns = [
    path("posts/", AdminBlogPostListView.as_view(), name="admin-blog-posts"),
    path("posts/<int:pk>/", AdminBlogPostDetailView.as_view(), name="admin-blog-post-detail"),
    path("topics/", AdminBlogTopicListView.as_view(), name="admin-blog-topics"),
    path("topics/<int:pk>/", AdminBlogTopicDetailView.as_view(), name="admin-blog-topic-detail"),
    path("generate/", AdminBlogGenerateView.as_view(), name="admin-blog-generate"),
    path("upload-image/", AdminBlogImageUploadView.as_view(), name="admin-blog-image-upload"),
]
