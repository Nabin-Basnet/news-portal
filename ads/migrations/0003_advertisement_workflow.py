from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def preserve_currently_delivered_advertisements(apps, schema_editor):
    Advertisement = apps.get_model("ads", "Advertisement")
    now = timezone.now()
    Advertisement.objects.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now,
    ).update(status="published", published_at=now)


class Migration(migrations.Migration):
    dependencies = [
        ("ads", "0002_alter_advertisement_image"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="advertisement",
            name="creator",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="advertisements_created", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="advertisement",
            name="reviewer",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="advertisements_reviewed", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="advertisement",
            name="status",
            field=models.CharField(choices=[("draft", "Draft"), ("submitted", "Submitted"), ("under_review", "Under Review"), ("approved", "Approved"), ("published", "Published"), ("rejected", "Rejected"), ("archived", "Archived")], db_index=True, default="draft", max_length=20),
        ),
        migrations.AddField(model_name="advertisement", name="review_note", field=models.TextField(blank=True)),
        migrations.AddField(model_name="advertisement", name="submitted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="advertisement", name="reviewed_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="advertisement", name="published_at", field=models.DateTimeField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name="advertisement", name="updated_at", field=models.DateTimeField(auto_now=True, default=timezone.now), preserve_default=False),
        migrations.RunPython(preserve_currently_delivered_advertisements, migrations.RunPython.noop),
    ]
