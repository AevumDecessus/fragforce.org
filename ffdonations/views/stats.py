from django.http import JsonResponse
from django.views.decorators.cache import cache_page

from django.conf import settings


@cache_page(settings.VIEW_DONATIONS_STATS_CACHE)
def v_tracked_donations_stats(request):
    from ..ctx import donations
    return JsonResponse(donations(request=request))
