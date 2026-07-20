from django.db import migrations


def seed_roles(apps, schema_editor):
    Role = apps.get_model("user", "Role")
    for role_name in ("Admin", "Editor", "Staff", "Reporter", "User"):
        Role.objects.get_or_create(role_name=role_name)


class Migration(migrations.Migration):
    dependencies = [("user", "0008_user_email_notifications")]

    operations = [migrations.RunPython(seed_roles, migrations.RunPython.noop)]
