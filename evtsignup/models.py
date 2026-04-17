from django.db import models
from django_workflow_engine.executor import User


class SalesforceEventUser(models.Model):
    """ Created if a user maps to a SFID """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    salesforce_id = models.CharField(max_length=64, blank=False, db_index=True, null=False, unique=True)


class InterestLevel(models.Model):
    """ Different levels/types of interest """
    name = models.CharField(max_length=255, unique=True, db_index=True, null=False, blank=False)
    slug = models.SlugField(max_length=255, null=False, blank=False, db_index=True, unique=True)
    description = models.TextField(default='', blank=False, null=False)
    rank = models.SmallIntegerField(default=0, blank=False, null=False)  # Above zero = good, below zero = never


class EventInterest(models.Model):
    """ A user's signup for an event """
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    event = models.ForeignKey("eventer.Event", on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey("evtsignup.InterestLevel", on_delete=models.CASCADE, blank=False, null=False)

    # Display info from signup form
    display_name = models.CharField(max_length=255, blank=True)
    preferences = models.TextField(blank=True)  # pronouns, other info
    acknowledged = models.BooleanField(default=False)

    # Fundraising - for streamers
    fundraising_url = models.URLField(null=True, blank=True)
    el_participant = models.ForeignKey(
        'ffdonations.ParticipantModel', null=True, blank=True, on_delete=models.SET_NULL
    )

    # Write-in game preferences (freeform, not yet resolved to Game records)
    participant_notes = models.TextField(blank=True)
    streamer_notes = models.TextField(blank=True)

    class Meta:
        unique_together = [["user", "event"]]


class GameInterestUserEvent(models.Model):
    """ User's interest in a pre-selected game for a particular event """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    game = models.ForeignKey('eventer.Game', on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey('InterestLevel', on_delete=models.CASCADE, blank=False, null=False)

    class Meta:
        unique_together = [["event_interest", "game"]]


class EventAvailabilityInterest(models.Model):
    """ One record per available hour per user per event, indicating which roles they're available for.
    Form checkboxes (e.g. 'Friday 8pm-11pm') expand to one row per hour on save. """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    hour = models.DateTimeField(null=False, blank=False)  # UTC, start of the hour

    as_participant = models.BooleanField(default=False)
    as_streamer = models.BooleanField(default=False)
    as_moderator = models.BooleanField(default=False)
    as_tech = models.BooleanField(default=False)

    class Meta:
        unique_together = [["event_interest", "hour"]]
