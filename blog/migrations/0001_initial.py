from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="BlogTopic",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("topic", models.CharField(max_length=255, verbose_name="Konu")),
                ("scheduled_date", models.DateField(verbose_name="Yayın Tarihi")),
                ("is_generated", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "Blog Konusu", "verbose_name_plural": "Blog Konuları", "ordering": ["scheduled_date"]},
        ),
        migrations.CreateModel(
            name="BlogPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="Başlık")),
                ("slug", models.SlugField(blank=True, max_length=280, unique=True)),
                ("content", models.TextField(verbose_name="İçerik")),
                ("cover_image", models.ImageField(blank=True, null=True, upload_to="blog/")),
                ("is_published", models.BooleanField(default=False, verbose_name="Yayında")),
                ("ai_generated", models.BooleanField(default=False, verbose_name="AI Tarafından Oluşturuldu")),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("view_count", models.PositiveIntegerField(default=0)),
                (
                    "topic",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="blog.blogtopic",
                    ),
                ),
            ],
            options={"verbose_name": "Blog Yazısı", "verbose_name_plural": "Blog Yazıları", "ordering": ["-published_at", "-created_at"]},
        ),
    ]
