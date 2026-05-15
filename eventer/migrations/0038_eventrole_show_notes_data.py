from django.db import migrations


def set_show_notes(apps, schema_editor):
    EventRole = apps.get_model('eventer', 'EventRole')
    updated = EventRole.objects.filter(slug__in=['participant', 'streamer']).update(show_notes=True)
    if updated != 2:
        raise ValueError(f"Expected to update 2 EventRoles (participant, streamer), got {updated}. Run eventer migration 0024 first.")


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0037_eventrole_show_notes'),
    ]

    operations = [
        migrations.RunPython(set_show_notes, migrations.RunPython.noop),
    ]
