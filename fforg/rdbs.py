from django.conf import settings

from .redisdb import HttpCacheDB, TimersDB

# Timers
r_timers = TimersDB(settings.REDIS_URL_TIMERS)

# HTTP conditional GET cache (ETags, Last-Modified)
r_http_cache = HttpCacheDB(settings.REDIS_URL_TIMERS)
