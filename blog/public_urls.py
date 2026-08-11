from django.urls import path
from .views import PublicBlogListView, PublicBlogDetailView, PublicBlogCategoryListView

urlpatterns = [
    path("", PublicBlogListView.as_view(), name="public-blog-list"),
    path("categories/", PublicBlogCategoryListView.as_view(), name="public-blog-categories"),
    path("<slug:slug>/", PublicBlogDetailView.as_view(), name="public-blog-detail"),
]
