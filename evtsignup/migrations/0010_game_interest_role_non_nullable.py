from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('eventer', '0011_event_signup_flags'),
        ('evtsignup', '0009_game_interest_default_role_to_participant'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gameinterestuserevent',
            name='role',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='eventer.eventrole',
            ),
        ),
    ]
