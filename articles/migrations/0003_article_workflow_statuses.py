# Generated manually to preserve articles created with the original workflow.

from django.db import migrations, models


def migrate_pending_articles(apps, schema_editor):
    Article = apps.get_model("articles", "Article")
    Article.objects.filter(status="pending_review").update(status="submitted")


class Migration(migrations.Migration):
    dependencies = [("articles", "0002_alter_articleview_options_alter_bookmark_options_and_more")]

    operations = [
        migrations.RunPython(migrate_pending_articles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="article",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("submitted", "Submitted"),
                    ("under_review", "Under Review"),
                    ("approved", "Approved"),
                    ("published", "Published"),
                    ("rejected", "Rejected"),
                    ("archived", "Archived"),
                ],
                db_index=True,
                default="draft",
                max_length=20,
            ),
        ),
    ]
