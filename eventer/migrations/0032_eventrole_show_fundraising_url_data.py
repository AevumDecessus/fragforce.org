from django.db import migrations


def set_show_fundraising_url(apps, schema_editor):
    EventRole = apps.get_model('eventer', 'EventRole')
    EventRole.objects.filter(slug='streamer').update(show_fundraising_url=True)


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0031_eventrole_show_fundraising_url'),
    ]

    operations = [
        migrations.RunPython(set_show_fundraising_url, migrations.RunPython.noop),
    ]
