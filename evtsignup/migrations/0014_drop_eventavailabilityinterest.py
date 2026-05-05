from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('evtsignup', '0013_migrate_availability_data'),
    ]

    operations = [
        migrations.DeleteModel(
            name='EventAvailabilityInterest',
        ),
    ]
