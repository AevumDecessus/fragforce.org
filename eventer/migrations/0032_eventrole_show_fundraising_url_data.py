from django.db import migrations


def set_show_fundraising_url(apps, schema_editor):
    EventRole = apps.get_model('eventer', 'EventRole')
    updated = EventRole.objects.filter(slug='streamer').update(show_fundraising_url=True)
    if updated != 1:
        raise ValueError(f"Expected to update 1 EventRole(slug='streamer'), got {updated}. Run eventer migration 0024 first.")


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0031_eventrole_show_fundraising_url'),
    ]

    operations = [
        migrations.RunPython(set_show_fundraising_url, migrations.RunPython.noop),
    ]
