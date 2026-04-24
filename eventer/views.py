from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_safe

from eventer.models import Event


def _signup_link_context(event, user):
    """Return show_signup_link and show_edit_link for an event given the current user."""
    if event.locked:
        return {'show_signup_link': False, 'show_edit_link': False}

    has_signup = (
        user.is_authenticated and
        event.eventinterest_set.filter(user=user).exists()
    )
    return {
        'show_signup_link': event.signups_open and not has_signup,
        'show_edit_link': event.edits_open and has_signup,
    }


@require_safe
def event_list(request):
    # Show events that are in progress or haven't ended yet
    now = timezone.now()
    events = (
        Event.objects
        .filter(eventperiod__isnull=False, eventperiod__stop__gte=now)
        .distinct()
        .prefetch_related('eventperiod_set')
        .order_by('eventperiod__start')
    )
    return render(request, 'eventer/event_list.html', {'events': events})


@require_safe
def event_detail(request, event_slug):
    event = get_object_or_404(Event, slug=event_slug)
    context = {
        'event': event,
        **_signup_link_context(event, request.user),
    }
    return render(request, 'eventer/event_detail.html', context)
