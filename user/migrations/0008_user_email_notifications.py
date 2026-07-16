from django.db import migrations, models


def add_email_notifications_column_if_missing(apps, schema_editor):
    """Synchronize databases created before this migration was added."""
    User = apps.get_model('user', 'User')
    table_name = User._meta.db_table
    existing_columns = {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(), table_name
        )
    }

    if 'email_notifications' not in existing_columns:
        field = models.BooleanField(default=True)
        field.set_attributes_from_name('email_notifications')
        field.model = User
        schema_editor.add_field(User, field)


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0007_alter_user_managers'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='user',
                    name='email_notifications',
                    field=models.BooleanField(default=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    add_email_notifications_column_if_missing,
                    migrations.RunPython.noop,
                ),
            ],
        ),
    ]
