from django.db import migrations

SLUG_TO_FIELD = {
    'participant': 'as_participant',
    'streamer': 'as_streamer',
    'moderator': 'as_moderator',
    'tech-manager': 'as_tech',
}


def migrate_availability_data(apps, schema_editor):
    EventAvailabilityInterest = apps.get_model('evtsignup', 'EventAvailabilityInterest')
    EventAvailabilityHour = apps.get_model('evtsignup', 'EventAvailabilityHour')
    EventRole = apps.get_model('eventer', 'EventRole')

    roles = {slug: EventRole.objects.filter(slug=slug).first() for slug in SLUG_TO_FIELD}
    missing = [slug for slug, role in roles.items() if role is None]
    if missing:
        raise ValueError(f"Cannot migrate availability data: EventRole rows missing for slugs: {missing}. Run eventer migrations first.")

    batch = []
    for old in EventAvailabilityInterest.objects.select_related('event_interest').iterator():
        for slug, field in SLUG_TO_FIELD.items():
            if getattr(old, field):
                batch.append(EventAvailabilityHour(
                    event_interest=old.event_interest,
                    hour=old.hour,
                    role=roles[slug],
                ))
    EventAvailabilityHour.objects.bulk_create(batch, ignore_conflicts=True, batch_size=1000)


class Migration(migrations.Migration):

    dependencies = [
        ('evtsignup', '0012_eventavailabilityhour'),
    ]

    operations = [
        migrations.RunPython(migrate_availability_data, migrations.RunPython.noop),
    ]
