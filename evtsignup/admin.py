# Register your models here.
from django.contrib import admin

from evtsignup.models import EventAvailabilityInterest, EventInterest, GameInterestUserEvent


@admin.register(EventAvailabilityInterest)
class EventAvailabilityInterestAdmin(admin.ModelAdmin):
    pass


@admin.register(EventInterest)
class EventInterestAdmin(admin.ModelAdmin):
    raw_id_fields = ['el_participant']


@admin.register(GameInterestUserEvent)
class GameInterestUserEventAdmin(admin.ModelAdmin):
    pass
