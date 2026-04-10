from django.db import migrations


def populate_stream_key(apps, schema_editor):
    Key = apps.get_model('ffstream', 'Key')
    Key.objects.filter(stream_key__isnull=True).update(stream_key=schema_editor.connection.ops.quote_name('id'))


def populate_stream_key_sql(apps, schema_editor):
    schema_editor.execute(
        "UPDATE ffstream_key SET stream_key = id WHERE stream_key IS NULL"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('ffstream', '0013_key_add_stream_key'),
    ]

    operations = [
        migrations.RunPython(populate_stream_key_sql, migrations.RunPython.noop),
    ]
