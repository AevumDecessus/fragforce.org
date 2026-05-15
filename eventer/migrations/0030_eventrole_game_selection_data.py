from django.db import migrations

GAME_SELECTION = {
    'participant': {'has_game_selection': True, 'game_min_players': 2},
    'streamer':    {'has_game_selection': True, 'game_min_players': None},
    'moderator':   {'has_game_selection': False, 'game_min_players': None},
    'tech-manager':{'has_game_selection': False, 'game_min_players': None},
}


def set_game_selection(apps, schema_editor):
    EventRole = apps.get_model('eventer', 'EventRole')
    for slug, values in GAME_SELECTION.items():
        updated = EventRole.objects.filter(slug=slug).update(**values)
        if updated != 1:
            raise ValueError(f"Expected to update 1 EventRole(slug={slug!r}), got {updated}. Run eventer migration 0024 first.")


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0029_eventrole_game_selection_fields'),
    ]

    operations = [
        migrations.RunPython(set_game_selection, migrations.RunPython.noop),
    ]
