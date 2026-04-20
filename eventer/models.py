from django.contrib.postgres.fields import HStoreField
from django.db import models
from django_workflow_engine.executor import User


class Team(models.Model):
    """ A team or group of people who do events """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    team_info = HStoreField(default=dict, null=False)
    role = models.ForeignKey('TeamRole', on_delete=models.CASCADE, blank=False, null=False)
    description = models.TextField(default='', blank=False, null=False)


class TeamRole(models.Model):
    """ A role a user can have in a team """
    name = models.CharField(max_length=255, unique=True, blank=False, null=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)


class TeamMember(models.Model):
    """ Connect a User to a Role in a Team """
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, blank=False, null=False)
    role = models.ForeignKey(TeamRole, on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = [
            ["user", "team"],  # Basic overlap check
        ]


class EventRole(models.Model):
    """ A role a user can have on an event """
    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)


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
    flags = HStoreField(default=dict, blank=False, null=False, verbose_name="Flags")


class Event(models.Model):
    """ A gaming event """
    name = models.CharField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)

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

    @staticmethod
    def duration_f():
        """ Field value for duration (stop-start) """
        from django.db.models import F
        return F('stop') - F('start')
