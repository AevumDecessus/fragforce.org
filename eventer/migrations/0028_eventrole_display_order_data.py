from django.db import migrations

DISPLAY_ORDERS = {
    'streamer': 10,
    'participant': 20,
    'moderator': 30,
    'tech-manager': 40,
}


def set_display_orders(apps, schema_editor):
    EventRole = apps.get_model('eventer', 'EventRole')
    for slug, order in DISPLAY_ORDERS.items():
        updated = EventRole.objects.filter(slug=slug).update(display_order=order)
        if updated != 1:
            raise ValueError(f"Expected to update 1 EventRole(slug={slug!r}), got {updated}. Run eventer migration 0024 first.")


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0027_eventrole_display_order'),
    ]

    operations = [
        migrations.RunPython(set_display_orders, migrations.RunPython.noop),
    ]
