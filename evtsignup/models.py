from django.contrib.postgres.fields import HStoreField
from django.db import models
from django_workflow_engine.executor import User


class SalesforceEventUser(models.Model):
    """ Created if a user maps to a SFID """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    salesforce_id = models.CharField(max_length=64, blank=False, db_index=True, null=False, unique=True)


class StreamSuggestion(models.Model):
    """ A user would like to stream a game """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    game = models.ForeignKey("eventer.Game", on_delete=models.CASCADE, blank=False, null=False)
    suggested_players = models.ManyToManyField(User, blank=True)
    min_players = models.PositiveSmallIntegerField(default=1, blank=False, null=False)
    max_players = models.PositiveSmallIntegerField(default=1, blank=False, null=False)
    ideal_players = models.PositiveSmallIntegerField(default=1, blank=False, null=False)
    flags = HStoreField(default=dict, blank=False, null=False)


class EventInterest(models.Model):
    """ A user has expressed interest in an event """
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    event = models.ForeignKey("eventer.Event", on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey("evtsignup.InterestLevel", on_delete=models.CASCADE, blank=False, null=False)

    # Display info from signup form
    display_name = models.CharField(max_length=255, blank=True)
    preferences = models.TextField(blank=True)  # pronouns, other info
    acknowledged = models.BooleanField(default=False)

    class Meta:
        unique_together = [
            ["user", "event"],
        ]


class InterestLevel(models.Model):
    """ Different levels/types of interest """
    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)
    rank = models.SmallIntegerField(default=0, blank=False, null=False)  # Above zero = good, below zero = never


class EventRoleInterest(models.Model):
    """ A User's interest level in a given role for a given event they're interested in """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    event_role = models.ForeignKey("eventer.EventRole", on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey("InterestLevel", on_delete=models.CASCADE, blank=False, null=False)

    # Fundraising (streamers)
    fundraising_url = models.URLField(null=True, blank=True)
    el_participant = models.ForeignKey(
        'ffdonations.ParticipantModel', null=True, blank=True, on_delete=models.SET_NULL
    )

    # Write-in game preferences
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [
            ["event_interest", "event_role"],
        ]


class GameInterestUser(models.Model):
    """ User's interest in a game overall """
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    game = models.ForeignKey('eventer.Game', on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey('InterestLevel', on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = [
            ["user", "game"],
        ]


class GameInterestUserEvent(models.Model):
    """ User's interest in a game for a particular event """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    game = models.ForeignKey('eventer.Game', on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey('InterestLevel', on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = [
            ["event_interest", "game"],
        ]


class EventAvailabilityInterest(models.Model):
    """ User's availability for a given time period for a specific role in an event """
    event_role_interest = models.ForeignKey("EventRoleInterest", on_delete=models.CASCADE, blank=True, null=True)
    interest_level = models.ForeignKey("InterestLevel", on_delete=models.CASCADE, blank=False, null=False)
    period_start = models.DateTimeField(null=False, blank=False)
    period_end = models.DateTimeField(null=False, blank=False)

    class Meta:
        unique_together = [
            ["event_role_interest", "period_start", "period_end"],
        ]
