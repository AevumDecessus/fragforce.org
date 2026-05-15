from django.db import migrations


def migrate_notes(apps, schema_editor):
    EventInterest = apps.get_model('evtsignup', 'EventInterest')
    EventInterestNote = apps.get_model('evtsignup', 'EventInterestNote')
    EventRole = apps.get_model('eventer', 'EventRole')

    slugs = ('participant', 'streamer')
    roles = {slug: EventRole.objects.filter(slug=slug).first() for slug in slugs}
    missing = [slug for slug, role in roles.items() if role is None]
    if missing:
        raise ValueError(
            f"Cannot migrate notes data: EventRole rows missing for slugs: {missing}. "
            "Run eventer migrations first."
        )

    rows = []
    # exclude() with two conditions is an AND - rows where BOTH are empty are skipped.
    # Rows where only one is set are included, which is correct.
    for interest in EventInterest.objects.exclude(participant_notes='', streamer_notes='').iterator():
        if interest.participant_notes:
            rows.append(EventInterestNote(event_interest=interest, role=roles['participant'], notes=interest.participant_notes))
        if interest.streamer_notes:
            rows.append(EventInterestNote(event_interest=interest, role=roles['streamer'], notes=interest.streamer_notes))

    EventInterestNote.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('evtsignup', '0015_eventinterestnote'),
    ]

    operations = [
        migrations.RunPython(migrate_notes, migrations.RunPython.noop),
    ]
