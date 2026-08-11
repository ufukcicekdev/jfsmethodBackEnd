from django.urls import path
from .views import (
    PublicBlogListView,
    PublicBlogDetailView,
    PublicBlogCategoryListView,
    AdminBlogPostListView,
    AdminBlogPostDetailView,
    AdminBlogTopicListView,
    AdminBlogTopicDetailView,
    AdminBlogGenerateView,
    AdminBlogCategoryListView,
    AdminBlogCategoryDetailView,
)

public_urlpatterns = [
    path("", PublicBlogListView.as_view(), name="public-blog-list"),
    path("categories/", PublicBlogCategoryListView.as_view(), name="public-blog-categories"),
    path("<slug:slug>/", PublicBlogDetailView.as_view(), name="public-blog-detail"),
]

admin_urlpatterns = [
    path("posts/", AdminBlogPostListView.as_view(), name="admin-blog-posts"),
    path("posts/<int:pk>/", AdminBlogPostDetailView.as_view(), name="admin-blog-post-detail"),
    path("topics/", AdminBlogTopicListView.as_view(), name="admin-blog-topics"),
    path("topics/<int:pk>/", AdminBlogTopicDetailView.as_view(), name="admin-blog-topic-detail"),
    path("generate/", AdminBlogGenerateView.as_view(), name="admin-blog-generate"),
    path("categories/", AdminBlogCategoryListView.as_view(), name="admin-blog-categories"),
    path("categories/<int:pk>/", AdminBlogCategoryDetailView.as_view(), name="admin-blog-category-detail"),
]
