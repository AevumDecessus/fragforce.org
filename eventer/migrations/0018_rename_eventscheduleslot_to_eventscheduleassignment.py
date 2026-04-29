import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0017_event_schedule_multi_assignment'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name='EventScheduleSlot',
            new_name='EventScheduleAssignment',
        ),
        # Update related_names to match the new model structure
        migrations.AlterField(
            model_name='eventscheduleassignment',
            name='event',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='schedule_assignments',
                to='eventer.event',
            ),
        ),
        migrations.AlterField(
            model_name='eventscheduleassignment',
            name='slot',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='schedule_slot_assignments',
                to='eventer.eventsignupslot',
            ),
        ),
    ]
