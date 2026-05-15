from django.db import migrations

ROLES = [
    {'name': 'Participant', 'slug': 'participant', 'description': 'Game participant - plays games with a streamer', 'color': '#417690'},
    {'name': 'Streamer', 'slug': 'streamer', 'description': 'Streams and leads a time slot', 'color': '#ff8000'},
    {'name': 'Moderator', 'slug': 'moderator', 'description': 'Moderates chat and provides streamer backup', 'color': '#8000ff'},
    {'name': 'Tech Manager', 'slug': 'tech-manager', 'description': 'Manages stream tech and coordinates handoffs', 'color': '#319320'},
]


def seed_roles(apps, schema_editor):
    EventRole = apps.get_model('eventer', 'EventRole')
    for role in ROLES:
        EventRole.objects.get_or_create(slug=role['slug'], defaults={
            'name': role['name'],
            'description': role['description'],
            'color': role['color'],
        })


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0023_game_multiplayer_max_override'),
    ]

    operations = [
        migrations.RunPython(seed_roles, migrations.RunPython.noop),
    ]
