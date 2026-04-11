from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ffstream', '0012_alter_key_superstream'),
    ]

    operations = [
        migrations.AddField(
            model_name='key',
            name='stream_key',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Stream Key'),
        ),
    ]
