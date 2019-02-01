# Generated by Django 2.1.2 on 2018-10-06 04:00

import datetime
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ('ffdonations', '0018_auto_20181005_0159'),
    ]

    operations = [
        migrations.CreateModel(
            name='AddressTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigAutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('addressLine1', models.CharField(default='Address Line 1', max_length=8192, null=True)),
                ('addressLine2', models.CharField(default='Address Line 2', max_length=8192, null=True)),
                ('city', models.CharField(default='City', max_length=8192, null=True)),
                ('region', models.CharField(default='Region', max_length=8192, null=True)),
                ('postalCode', models.BigIntegerField(default='Postal Code', null=True)),
                ('country', models.CharField(default='Country', max_length=8192, null=True)),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
            ],
        ),
        migrations.CreateModel(
            name='CampaignTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigIntegerField(primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=8192, null=True, unique=True, verbose_name='Name')),
                ('slug', models.CharField(max_length=8192, null=True, unique=True, verbose_name='Slug')),
                ('url', models.URLField(max_length=8192, null=True, unique=True, verbose_name='URL')),
                ('startsAt', models.DateTimeField(null=True, verbose_name='Starts At')),
                ('endsAt', models.DateTimeField(null=True, verbose_name='Ends At')),
                ('description', models.CharField(max_length=8192, null=True, unique=True, verbose_name='Description')),
                ('goal', models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Goal Amount')),
                ('fundraiserGoalAmount', models.DecimalField(decimal_places=2, max_digits=50, null=True,
                                                             verbose_name='Fundraiser Goal Amount')),
                ('originalGoalAmount',
                 models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Origional Goal Amount')),
                ('amountRaised',
                 models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Amount Raised')),
                ('supportingAmountRaised', models.DecimalField(decimal_places=2, max_digits=50, null=True,
                                                               verbose_name='Supporting Amount Raised')),
                ('totalAmountRaised',
                 models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Total Amount Raised')),
                ('supportable', models.NullBooleanField(verbose_name='Is Supportable')),
                ('status', models.CharField(max_length=8192, null=True, verbose_name='Status')),
                ('startsOn', models.DateTimeField(null=True, verbose_name='Starts On')),
                ('endsOn', models.DateTimeField(null=True, verbose_name='Ends On')),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
                ('subtype', models.CharField(default='CampaignResult', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='CauseTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigIntegerField(primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=8192, null=True, verbose_name='Name')),
                ('legalName', models.CharField(max_length=8192, null=True, verbose_name='Legal Name')),
                ('slug', models.CharField(max_length=8192, null=True, verbose_name='Slug')),
                ('currency', models.CharField(max_length=8192, null=True, verbose_name='Currency')),
                ('about', models.CharField(max_length=8192, null=True, verbose_name='About')),
                ('video', models.URLField(max_length=8192, null=True, verbose_name='Name')),
                ('contactEmail', models.EmailField(max_length=8192, null=True, verbose_name='Contact Email')),
                ('paypalEmail', models.EmailField(max_length=8192, null=True, verbose_name='Paypal Email')),
                ('paypalCurrencyCode',
                 models.CharField(max_length=8192, null=True, verbose_name='Paypal Currency Code')),
                ('status', models.CharField(max_length=8192, null=True, verbose_name='Status')),
                ('stripeConnected', models.NullBooleanField(verbose_name='Stripe Connected')),
                ('mailchimpConnected', models.NullBooleanField(verbose_name='Mail Chimp Connected')),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
                ('address', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                              to='ffdonations.AddressTiltifyModel', verbose_name='Address')),
            ],
        ),
        migrations.CreateModel(
            name='ColorTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigAutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('highlight', models.CharField(default='Hightlight Color', max_length=8192, null=True)),
                ('background', models.CharField(default='Background Color', max_length=8192, null=True)),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
            ],
        ),
        migrations.CreateModel(
            name='DonationTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigIntegerField(primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Amount')),
                ('name', models.CharField(max_length=8192, null=True, verbose_name='Name')),
                ('comment', models.CharField(max_length=1048576, null=True, verbose_name='Comment')),
                ('completedAt', models.DateTimeField(null=True, verbose_name='Completed At')),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
            ],
        ),
        migrations.CreateModel(
            name='EventTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigIntegerField(primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='LiveStreamTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigIntegerField(primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.CharField(max_length=8192, null=True, verbose_name='Channel')),
                ('stream_type', models.CharField(max_length=8192, null=True, verbose_name='Type')),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
            ],
        ),
        migrations.CreateModel(
            name='MediaTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigAutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('src', models.URLField(max_length=8192, null=True, verbose_name='Source URL')),
                ('alt', models.CharField(default='', max_length=8192, null=True, verbose_name='Alternate Text')),
                ('width', models.IntegerField(null=True, verbose_name='Width (px)')),
                ('height', models.IntegerField(null=True, verbose_name='Height (px)')),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
                ('subtype', models.CharField(default='MediaResult', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='RewardTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigIntegerField(primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Name', max_length=8192, null=True)),
                ('description', models.CharField(default='Description', max_length=1048576, null=True)),
                ('amount', models.IntegerField(null=True, verbose_name='Amount')),
                ('kind', models.CharField(default='Kind', max_length=8192, null=True)),
                ('quantity', models.IntegerField(null=True, verbose_name='Quantity')),
                ('remaining', models.IntegerField(null=True, verbose_name='Remaining')),
                ('fairMarketValue',
                 models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Fair Market Value')),
                ('currency', models.CharField(default='Currency', max_length=8192, null=True)),
                ('shippingAddressRequired', models.NullBooleanField(verbose_name='Is Active')),
                ('shippingNote', models.CharField(default='Description', max_length=1048576, null=True)),
                ('active', models.NullBooleanField(verbose_name='Is Active')),
                ('startsAt', models.DateTimeField(null=True, verbose_name='Starts At')),
                ('createdAt', models.DateTimeField(null=True, verbose_name='Created At')),
                ('updatedAt', models.DateTimeField(null=True, verbose_name='Updated At')),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
                ('image', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                            to='ffdonations.MediaTiltifyModel', verbose_name='Image')),
            ],
        ),
        migrations.CreateModel(
            name='SettingsTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigAutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('headerIntro', models.CharField(default='Intro', max_length=8192, null=True)),
                ('headerTitle', models.CharField(default='Title', max_length=8192, null=True)),
                ('footerCopyright', models.CharField(default='Copyright', max_length=8192, null=True)),
                ('findOutMoreLink', models.URLField(max_length=8192, null=True, verbose_name='Find Out More')),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
                ('colors', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                             to='ffdonations.ColorTiltifyModel', verbose_name='Colors')),
            ],
        ),
        migrations.CreateModel(
            name='SocailTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigAutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('twitter', models.CharField(default='Twitter', max_length=8192, null=True)),
                ('twitch', models.CharField(default='Twitch', max_length=8192, null=True)),
                ('youtube', models.CharField(default='Youtube', max_length=8192, null=True)),
                ('facebook', models.CharField(default='Facebook', max_length=8192, null=True)),
                ('instagram', models.CharField(default='Instagram', max_length=8192, null=True)),
                ('website', models.CharField(default='Website', max_length=8192, null=True)),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
            ],
        ),
        migrations.CreateModel(
            name='TeamTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigIntegerField(primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=8192, null=True, unique=True, verbose_name='Name')),
                ('slug', models.CharField(max_length=8192, null=True, unique=True, verbose_name='Slug')),
                ('url', models.CharField(max_length=8192, null=True, unique=True, verbose_name='URL')),
                ('bio', models.CharField(max_length=1048576, verbose_name='Bio')),
                ('inviteOnly', models.NullBooleanField(verbose_name='Is Invite Only Team')),
                ('disbanded', models.NullBooleanField(verbose_name='Is Disbanded')),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
                ('subtype', models.CharField(default='TeamResult', max_length=255)),
                ('avatar', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                             to='ffdonations.MediaTiltifyModel', verbose_name='Avatar')),
            ],
        ),
        migrations.CreateModel(
            name='UserTiltifyModel',
            fields=[
                ('guid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='GUID')),
                ('last_updated', models.DateTimeField(auto_now=True, verbose_name='Date Record Last Fetched')),
                ('id', models.BigIntegerField(primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=8192, null=True, unique=True, verbose_name='Username')),
                ('slug', models.CharField(max_length=8192, null=True, unique=True, verbose_name='Slug')),
                ('url', models.URLField(max_length=8192, null=True, unique=True, verbose_name='URL')),
                ('raw',
                 django.contrib.postgres.fields.jsonb.JSONField(default=dict, null=True, verbose_name='Raw Data')),
                ('avatar', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                             to='ffdonations.MediaTiltifyModel', verbose_name='Avatar')),
            ],
        ),
        migrations.AlterField(
            model_name='donationmodel',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=50, null=True,
                                      verbose_name='Donation Amount'),
        ),
        migrations.AlterField(
            model_name='donationmodel',
            name='created',
            field=models.DateTimeField(default=datetime.datetime.utcnow, null=True, verbose_name='Created At'),
        ),
        migrations.AlterField(
            model_name='donationmodel',
            name='displayName',
            field=models.CharField(default='', max_length=8192, null=True, verbose_name='Donor Name'),
        ),
        migrations.AlterField(
            model_name='donationmodel',
            name='message',
            field=models.CharField(default='', max_length=1048576, null=True, verbose_name='Message'),
        ),
        migrations.AlterField(
            model_name='participantmodel',
            name='fundraisingGoal',
            field=models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Fundraising Goal'),
        ),
        migrations.AlterField(
            model_name='participantmodel',
            name='sumDonations',
            field=models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Donations Total'),
        ),
        migrations.AlterField(
            model_name='participantmodel',
            name='sumPledges',
            field=models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Pledges Total'),
        ),
        migrations.AlterField(
            model_name='teammodel',
            name='fundraisingGoal',
            field=models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Fundraising Goal'),
        ),
        migrations.AlterField(
            model_name='teammodel',
            name='name',
            field=models.CharField(max_length=8192, null=True, verbose_name='Team Name'),
        ),
        migrations.AlterField(
            model_name='teammodel',
            name='sumDonations',
            field=models.DecimalField(decimal_places=2, max_digits=50, null=True, verbose_name='Donations Total'),
        ),
        migrations.AddField(
            model_name='donationtiltifymodel',
            name='reward',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                    to='ffdonations.RewardTiltifyModel', verbose_name='Reward'),
        ),
        migrations.AddField(
            model_name='causetiltifymodel',
            name='banner',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='banner',
                                    to='ffdonations.MediaTiltifyModel', verbose_name='Banner'),
        ),
        migrations.AddField(
            model_name='causetiltifymodel',
            name='image',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='image',
                                    to='ffdonations.MediaTiltifyModel', verbose_name='Image'),
        ),
        migrations.AddField(
            model_name='causetiltifymodel',
            name='logo',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='logo',
                                    to='ffdonations.MediaTiltifyModel', verbose_name='Logo'),
        ),
        migrations.AddField(
            model_name='causetiltifymodel',
            name='settings',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                    to='ffdonations.SettingsTiltifyModel', verbose_name='Settings'),
        ),
        migrations.AddField(
            model_name='causetiltifymodel',
            name='social',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                    to='ffdonations.SocailTiltifyModel', verbose_name='Social'),
        ),
        migrations.AddField(
            model_name='campaigntiltifymodel',
            name='avatar',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='avatar',
                                    to='ffdonations.MediaTiltifyModel', verbose_name='Avatar'),
        ),
        migrations.AddField(
            model_name='campaigntiltifymodel',
            name='cause',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                    to='ffdonations.CauseTiltifyModel', verbose_name='Cause'),
        ),
        migrations.AddField(
            model_name='campaigntiltifymodel',
            name='fundraisingEvent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                    to='ffdonations.EventTiltifyModel', verbose_name='Fundraising Event'),
        ),
        migrations.AddField(
            model_name='campaigntiltifymodel',
            name='livestream',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                    to='ffdonations.LiveStreamTiltifyModel', verbose_name='Live Stream'),
        ),
        migrations.AddField(
            model_name='campaigntiltifymodel',
            name='team',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                    to='ffdonations.TeamTiltifyModel', verbose_name='Team'),
        ),
        migrations.AddField(
            model_name='campaigntiltifymodel',
            name='thumbnail',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='thumbnail',
                                    to='ffdonations.MediaTiltifyModel', verbose_name='Thumbnail'),
        ),
        migrations.AddField(
            model_name='campaigntiltifymodel',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING,
                                    to='ffdonations.UserTiltifyModel', verbose_name='user'),
        ),
    ]
