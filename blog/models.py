import re
from django.db import models
from django.utils import timezone


def slugify_tr(text):
    tr_map = str.maketrans("çğışöüÇĞİŞÖÜ", "cgisouCGISOU")
    text = text.translate(tr_map).lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text.strip())
    return text


class BlogTopic(models.Model):
    topic = models.CharField(max_length=255, verbose_name="Konu")
    scheduled_date = models.DateField(verbose_name="Yayın Tarihi")
    is_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Blog Konusu"
        verbose_name_plural = "Blog Konuları"
        ordering = ["scheduled_date"]

    def __str__(self):
        return f"{self.topic} ({self.scheduled_date})"


class BlogPost(models.Model):
    title = models.CharField(max_length=255, verbose_name="Başlık")
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    content = models.TextField(verbose_name="İçerik")
    cover_image = models.ImageField(upload_to="blog/", blank=True, null=True)
    is_published = models.BooleanField(default=False, verbose_name="Yayında")
    ai_generated = models.BooleanField(default=False, verbose_name="AI Tarafından Oluşturuldu")
    topic = models.ForeignKey(BlogTopic, null=True, blank=True, on_delete=models.SET_NULL)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Blog Yazısı"
        verbose_name_plural = "Blog Yazıları"
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify_tr(self.title)
            slug = base
            n = 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
