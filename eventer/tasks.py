import logging
import time

from celery import shared_task
from django.conf import settings

log = logging.getLogger(__name__)


@shared_task
def sync_all_igdb_games():
    """Re-fetch all existing Game records from IGDB to refresh metadata. Skips if credentials not configured."""
    from eventer.igdb import IGDBClient, IGDBError, sync_game_from_igdb
    from eventer.models import Game

    if not IGDBClient.credentials_configured():
        log.info('sync_all_igdb_games: IGDB credentials not configured, skipping')
        return

    igdb_ids = list(Game.objects.values_list('igdb_id', flat=True))
    log.info('sync_all_igdb_games: syncing %d games', len(igdb_ids))

    delay = getattr(settings, 'IGDB_BULK_SYNC_DELAY', 0.5)
    updated, errors = 0, 0
    for igdb_id in igdb_ids:
        try:
            sync_game_from_igdb(igdb_id)
            updated += 1
        except IGDBError as e:
            log.warning('sync_all_igdb_games: failed to sync igdb_id=%s: %s', igdb_id, e)
            errors += 1
        except ValueError as e:
            log.warning('sync_all_igdb_games: igdb_id=%s not found on IGDB: %s', igdb_id, e)
            errors += 1
        if delay > 0:
            time.sleep(delay)

    log.info('sync_all_igdb_games: done — %d updated, %d errors', updated, errors)
