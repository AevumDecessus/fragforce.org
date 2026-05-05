from django.db import migrations


def set_participant_multi_assign(apps, schema_editor):
    EventRole = apps.get_model('eventer', 'EventRole')
    EventRole.objects.filter(slug='participant').update(multi_assign=True)


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0025_eventrole_multi_assign'),
    ]

    operations = [
        migrations.RunPython(set_participant_multi_assign, migrations.RunPython.noop),
    ]
