from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_patientnotification"),
    ]

    operations = [
        migrations.AddField(
            model_name="patientprofile",
            name="admin_notes",
            field=models.TextField(blank=True, help_text="Internal therapist notes about this patient"),
        ),
    ]
