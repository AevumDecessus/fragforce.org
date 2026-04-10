from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ffstream', '0014_key_populate_stream_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='key',
            name='stream_key',
            field=models.CharField(blank=True, max_length=255, unique=True, verbose_name='Stream Key'),
        ),
    ]
