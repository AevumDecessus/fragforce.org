# Register your models here.
from django.contrib import admin

from evtsignup.models import (
    EventAvailabilityInterest, EventInterest, GameInterestUserEvent,
    InterestLevel,
)


@admin.register(EventAvailabilityInterest)
class EventAvailabilityInterestAdmin(admin.ModelAdmin):
    pass


@admin.register(EventInterest)
class EventInterestAdmin(admin.ModelAdmin):
    pass


@admin.register(GameInterestUserEvent)
class GameInterestUserEventAdmin(admin.ModelAdmin):
    pass


@admin.register(InterestLevel)
class InterestLevelAdmin(admin.ModelAdmin):
    pass
