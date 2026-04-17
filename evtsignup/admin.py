# Register your models here.
from django.contrib import admin

from evtsignup.models import EventAvailabilityInterest, EventInterest, EventRoleInterest, \
    GameInterestUser, GameInterestUserEvent, InterestLevel, SalesforceEventUser, StreamSuggestion


@admin.register(EventAvailabilityInterest)
class EventAvailabilityInterestAdmin(admin.ModelAdmin):
    pass


@admin.register(EventInterest)
class EventInterestAdmin(admin.ModelAdmin):
    pass


@admin.register(EventRoleInterest)
class EventRoleInterestAdmin(admin.ModelAdmin):
    pass


@admin.register(GameInterestUser)
class GameInterestUserAdmin(admin.ModelAdmin):
    pass


@admin.register(GameInterestUserEvent)
class GameInterestUserEventAdmin(admin.ModelAdmin):
    pass


@admin.register(InterestLevel)
class InterestLevelAdmin(admin.ModelAdmin):
    pass


@admin.register(SalesforceEventUser)
class SalesforceEventUserAdmin(admin.ModelAdmin):
    pass


@admin.register(StreamSuggestion)
class StreamSuggestionAdmin(admin.ModelAdmin):
    pass
