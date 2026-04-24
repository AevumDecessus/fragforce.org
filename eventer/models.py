from datetime import time

from django.db import models
from django_workflow_engine.executor import User

HOUR_SECONDS = 3600

SUPERSTREAM_TIMEZONES = [
    ('US/Canada', [
        ('America/New_York', 'Eastern (ET)'),
        ('America/Chicago', 'Central (CT)'),
        ('America/Denver', 'Mountain (MT)'),
        ('America/Los_Angeles', 'Pacific (PT)'),
        ('America/Anchorage', 'Alaska (AKT)'),
        ('Pacific/Honolulu', 'Hawaii (HT)'),
    ]),
    ('Australia/NZ', [
        ('Australia/Sydney', 'Sydney/Melbourne (AEST)'),
        ('Australia/Brisbane', 'Brisbane (AEST no DST)'),
        ('Australia/Perth', 'Perth (AWST)'),
        ('Pacific/Auckland', 'Auckland (NZST)'),
    ]),
    ('Europe/UK', [
        ('Europe/London', 'London (GMT/BST)'),
        ('Europe/Paris', 'Central Europe (CET/CEST)'),
        ('Europe/Helsinki', 'Eastern Europe (EET/EEST)'),
    ]),
    ('Other', [
        ('UTC', 'UTC'),
        ('Asia/Singapore', 'Singapore (SGT)'),
        ('Asia/Tokyo', 'Japan (JST)'),
    ]),
]


class Team(models.Model):
    """ A team or group of people who do events """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    role = models.ForeignKey('TeamRole', on_delete=models.CASCADE, blank=False, null=False)
    description = models.TextField(default='', blank=False, null=False)

    def __str__(self):
        return self.name


class TeamRole(models.Model):
    """ A role a user can have in a team """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    """ Connect a User to a Role in a Team """
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, blank=False, null=False)
    role = models.ForeignKey(TeamRole, on_delete=models.CASCADE, blank=False, null=False)

    def __str__(self):
        return f'{self.user} - {self.team} ({self.role})'

    class Meta:
        unique_together = [
            ["user", "team"],  # Basic overlap check
        ]


class EventRole(models.Model):
    """ A role a user can have on an event """
    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)

    def __str__(self):
        return self.name


class Game(models.Model):
    """ An IGDB backed game """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected - not allowed on stream (e.g. banned on Twitch)'

    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False, verbose_name="Game name")
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True, verbose_name="Fragforce slug", help_text="Internal URL slug for this app")
    coordinator_notes = models.TextField(blank=True, verbose_name="Coordinator notes", help_text="Internal notes for coordinators, e.g. hardware requirements or known issues")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True, verbose_name="Status", help_text="Moderation status - rejected games cannot be selected on signup forms")
    suggested = models.BooleanField(default=False, db_index=True, verbose_name="Suggested game", help_text="Show this game on the signup form game selection list (only applies when status=approved)")
    igdb_id = models.PositiveIntegerField(unique=True, null=False, blank=False, verbose_name="IGDB ID", help_text="Numeric IGDB game ID, e.g. 115555")
    igdb_slug = models.SlugField(max_length=255, unique=True, null=True, blank=True, db_index=True, verbose_name="IGDB slug", help_text="IGDB URL slug, e.g. 'going-medieval'")
    igdb_url = models.URLField(null=True, blank=True, verbose_name="IGDB URL", help_text="Full IGDB game page URL")
    igdb_cover_hash = models.CharField(max_length=255, null=True, blank=True, verbose_name="IGDB cover hash", help_text="IGDB image hash - use //images.igdb.com/igdb/image/upload/t_{size}/{hash}.jpg")
    summary = models.TextField(blank=True, verbose_name="IGDB summary", help_text="Short game description from IGDB")
    multiplayer_max = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Max players", help_text="Maximum number of players; null=unknown, 1=single player only")

    def __str__(self):
        return self.name


class Event(models.Model):
    """ A gaming event """
    name = models.CharField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)
    timezone = models.CharField(max_length=64, default='America/New_York', blank=False, null=False,
                                choices=SUPERSTREAM_TIMEZONES,
                                help_text="Timezone for coordinator-facing display. Public schedule uses browser local time via the |localtime template filter.")
    public = models.BooleanField(default=False,
                               help_text="Show this event on the public events listing.")
    signups_open = models.BooleanField(default=False,
                                       help_text="Allow new signups. Has no effect when locked.")
    edits_open = models.BooleanField(default=False,
                                     help_text="Allow existing signups to be edited. Has no effect when locked.")
    locked = models.BooleanField(default=False,
                                 help_text="Lock the event - disables all signups and edits regardless of other flags.")

    @property
    def start(self):
        """ Earliest period start - the event's effective start time """
        period = self.eventperiod_set.order_by('start').first()
        return period.start if period else None

    @property
    def end(self):
        """ Latest period stop - the event's effective end time """
        period = self.eventperiod_set.order_by('stop').last()
        return period.stop if period else None

    def __str__(self):
        return self.name

    @classmethod
    def add_details(cls, fq=None):
        from django.db.models import Sum, F

        if fq is None:
            fq = cls.objects

        return fq.annotate(duration=Sum(F("event_period__stop") - F("event_period__start")))


class EventPeriod(models.Model):
    """ A start/stop time period for an event """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, blank=False, null=False)
    start = models.DateTimeField(null=False, blank=False)
    stop = models.DateTimeField(null=False, blank=False)

    def __str__(self):
        return f'{self.event} - {self.start} to {self.stop}'

    @staticmethod
    def duration_f():
        """ Field value for duration (stop-start) """
        from django.db.models import F
        return F('stop') - F('start')


class EventSignupSlotConfig(models.Model):
    """ Generator configuration for slot templates for an event """
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='slot_config')

    # Player/Streamer block sizes
    standard_block_hours = models.PositiveSmallIntegerField(
        default=3,
        help_text="Default slot block size in hours for participant/streamer grid",
    )
    prime_block_hours = models.PositiveSmallIntegerField(
        default=2,
        help_text="Slot block size during prime time hours",
    )
    prime_time_start = models.TimeField(
        default=time(14, 0),
        help_text="Start of prime time (in event timezone) - shorter blocks begin here",
    )
    prime_time_end = models.TimeField(
        default=time(21, 0),
        help_text="End of prime time (in event timezone) - shorter blocks end here",
    )

    # Management (Moderator/Tech) block sizes
    management_block_hours = models.PositiveSmallIntegerField(
        default=6,
        help_text="Block size in hours for moderator and tech manager slots",
    )
    mod_first_block_hours = models.PositiveSmallIntegerField(
        default=3,
        help_text="Length of the first moderator block - shorter than standard to stagger mod/tech changeovers",
    )

    def __str__(self):
        return f'Slot config for {self.event}'


class EventSignupSlot(models.Model):
    """ A single slot on the signup form, linked to one or more roles """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='signup_slots')
    roles = models.ManyToManyField(EventRole, blank=True, help_text="Roles this slot applies to")
    start = models.DateTimeField(help_text="Slot start time (UTC)")
    stop = models.DateTimeField(help_text="Slot end time (UTC)")
    label = models.CharField(max_length=255, help_text="Human-readable label shown on signup form")

    class Meta:
        ordering = ['start']
        unique_together = [['event', 'start', 'stop']]

    def __str__(self):
        return f'{self.event} - {self.label}'
