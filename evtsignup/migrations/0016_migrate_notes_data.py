from django.db import migrations


def migrate_notes(apps, schema_editor):
    EventInterest = apps.get_model('evtsignup', 'EventInterest')
    EventInterestNote = apps.get_model('evtsignup', 'EventInterestNote')
    EventRole = apps.get_model('eventer', 'EventRole')

    participant = EventRole.objects.filter(slug='participant').first()
    streamer = EventRole.objects.filter(slug='streamer').first()

    rows = []
    for interest in EventInterest.objects.exclude(participant_notes='', streamer_notes='').iterator():
        if participant and interest.participant_notes:
            rows.append(EventInterestNote(event_interest=interest, role=participant, notes=interest.participant_notes))
        if streamer and interest.streamer_notes:
            rows.append(EventInterestNote(event_interest=interest, role=streamer, notes=interest.streamer_notes))

    EventInterestNote.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('evtsignup', '0015_eventinterestnote'),
    ]

    operations = [
        migrations.RunPython(migrate_notes, migrations.RunPython.noop),
    ]
