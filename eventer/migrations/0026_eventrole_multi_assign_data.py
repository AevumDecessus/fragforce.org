from django.db import migrations


def set_participant_multi_assign(apps, schema_editor):
    EventRole = apps.get_model('eventer', 'EventRole')
    updated = EventRole.objects.filter(slug='participant').update(multi_assign=True)
    if updated != 1:
        raise ValueError(f"Expected to update 1 EventRole(slug='participant'), got {updated}. Run eventer migration 0024 first.")


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0025_eventrole_multi_assign'),
    ]

    operations = [
        migrations.RunPython(set_participant_multi_assign, migrations.RunPython.noop),
    ]
