from django.db import migrations


def set_show_stream_commands(apps, schema_editor):
    EventRole = apps.get_model('eventer', 'EventRole')
    EventRole.objects.filter(slug='streamer').update(show_stream_commands=True)


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0035_eventrole_show_stream_commands'),
    ]

    operations = [
        migrations.RunPython(set_show_stream_commands, migrations.RunPython.noop),
    ]
