from django.db import migrations


def seed_slot_groups(apps, schema_editor):
    EventSlotGroup = apps.get_model('eventer', 'EventSlotGroup')
    EventSlotGroupMembership = apps.get_model('eventer', 'EventSlotGroupMembership')
    EventRole = apps.get_model('eventer', 'EventRole')

    # Prime-time group: participant + streamer, variable block sizing, no offset
    prime, _ = EventSlotGroup.objects.get_or_create(
        name='Prime Time',
        defaults={'use_prime_time': True, 'block_hours': None},
    )
    for slug in ('participant', 'streamer'):
        role = EventRole.objects.filter(slug=slug).first()
        if role:
            EventSlotGroupMembership.objects.get_or_create(group=prime, role=role, defaults={'first_block_hours': None})

    # Tech group: uniform management blocks, no offset
    tech_group, _ = EventSlotGroup.objects.get_or_create(
        name='Tech',
        defaults={'use_prime_time': False, 'block_hours': None},
    )
    tech_role = EventRole.objects.filter(slug='tech-manager').first()
    if tech_role:
        EventSlotGroupMembership.objects.get_or_create(group=tech_group, role=tech_role, defaults={'first_block_hours': None})

    # Moderator group: uniform management blocks, first block offset to stagger from tech
    mod_group, _ = EventSlotGroup.objects.get_or_create(
        name='Moderator',
        defaults={'use_prime_time': False, 'block_hours': None},
    )
    mod_role = EventRole.objects.filter(slug='moderator').first()
    if mod_role:
        EventSlotGroupMembership.objects.get_or_create(group=mod_group, role=mod_role, defaults={'first_block_hours': 3})


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0033_slot_groups'),
    ]

    operations = [
        migrations.RunPython(seed_slot_groups, migrations.RunPython.noop),
    ]
