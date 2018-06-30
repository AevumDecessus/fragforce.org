from ffsfdc.models import *
import datetime


def common_org(request):
    return dict(
        all_events=Event.objects.order_by('event_start_date').all(),
        upcoming_events=Event.objects.filter(event_start_date__gte=datetime.datetime.now()).order_by(
            'event_start_date').all(),
        past_events=Event.objects.filter(event_start_date__lt=datetime.datetime.now()).order_by(
            '-event_start_date').all(),
        accounts=Account.objects.order_by('name').all(),
    )