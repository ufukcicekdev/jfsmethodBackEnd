from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_patientprofile_admin_notes"),
    ]
    operations = [
        migrations.AddField(
            model_name="packageplan",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="package_images/"),
        ),
    ]
