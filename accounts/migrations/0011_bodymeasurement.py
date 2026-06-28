from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_packageplan_image"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BodyMeasurement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("label", models.CharField(blank=True, max_length=80, help_text="Ölçüm etiketi")),
                ("weight", models.FloatField(blank=True, null=True)),
                ("gogus", models.FloatField(blank=True, null=True)),
                ("omuz", models.FloatField(blank=True, null=True)),
                ("bel", models.FloatField(blank=True, null=True)),
                ("gobek", models.FloatField(blank=True, null=True)),
                ("alt_karin", models.FloatField(blank=True, null=True)),
                ("kalca", models.FloatField(blank=True, null=True)),
                ("basen", models.FloatField(blank=True, null=True)),
                ("sag_bacak", models.FloatField(blank=True, null=True)),
                ("sol_bacak", models.FloatField(blank=True, null=True)),
                ("sag_kol", models.FloatField(blank=True, null=True)),
                ("sol_kol", models.FloatField(blank=True, null=True)),
                ("yag_orani", models.FloatField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="body_measurements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "Vücut Ölçümü", "verbose_name_plural": "Vücut Ölçümleri", "ordering": ["-date"]},
        ),
    ]
