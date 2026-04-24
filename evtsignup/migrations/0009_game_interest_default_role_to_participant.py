from django.db import migrations


def default_roleless_to_participant(apps, schema_editor):
    GameInterestUserEvent = apps.get_model('evtsignup', 'GameInterestUserEvent')
    EventRole = apps.get_model('eventer', 'EventRole')
    participant_role = EventRole.objects.filter(slug='participant').first()
    if participant_role:
        GameInterestUserEvent.objects.filter(role__isnull=True).update(role=participant_role)


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0011_event_signup_flags'),
        ('evtsignup', '0008_game_interest_add_role_nullable'),
    ]

    operations = [
        migrations.RunPython(
            default_roleless_to_participant,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
