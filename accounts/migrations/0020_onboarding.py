import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0019_landing_content_models"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OnboardingQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.CharField(max_length=500)),
                ("question_type", models.CharField(
                    choices=[("text", "Açık Metin"), ("choice", "Çoktan Seçmeli"), ("scale", "Skala (1-10)"), ("multi", "Çoklu Seçim")],
                    default="text",
                    max_length=20,
                )),
                ("options", models.JSONField(blank=True, default=list)),
                ("is_required", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["sort_order", "created_at"]},
        ),
        migrations.CreateModel(
            name="OnboardingAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("answer", models.JSONField()),
                ("answered_at", models.DateTimeField(auto_now_add=True)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="accounts.onboardingquestion",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="onboarding_answers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"unique_together": {("user", "question")}},
        ),
        migrations.AddField(
            model_name="patientprofile",
            name="onboarding_completed",
            field=models.BooleanField(default=False),
        ),
    ]
