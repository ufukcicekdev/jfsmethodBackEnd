from django.urls import path
from .views import PublicBlogListView, PublicBlogDetailView

urlpatterns = [
    path("", PublicBlogListView.as_view(), name="public-blog-list"),
    path("<slug:slug>/", PublicBlogDetailView.as_view(), name="public-blog-detail"),
]
