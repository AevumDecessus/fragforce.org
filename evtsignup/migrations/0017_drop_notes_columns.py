from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('evtsignup', '0016_migrate_notes_data'),
    ]

    operations = [
        migrations.RemoveField(model_name='eventinterest', name='participant_notes'),
        migrations.RemoveField(model_name='eventinterest', name='streamer_notes'),
    ]
