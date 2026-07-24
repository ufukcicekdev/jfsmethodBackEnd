import uuid

from django.db import migrations, models


def populate_ical_uid(apps, schema_editor):
    Appointment = apps.get_model("appointments", "Appointment")
    for appt in Appointment.objects.filter(ical_uid=""):
        appt.ical_uid = f"{uuid.uuid4()}@jfsmethod.com"
        appt.save(update_fields=["ical_uid"])


class Migration(migrations.Migration):
    dependencies = [
        ("appointments", "0010_slot_break"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="ical_uid",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.RunPython(populate_ical_uid, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="appointment",
            name="ical_uid",
            field=models.CharField(blank=True, max_length=100, unique=True),
        ),
    ]
