"""
IGDB API client using Twitch OAuth2 client credentials.

Credentials are read from settings.IGDB_CLIENT_ID / IGDB_CLIENT_SECRET.
The bearer token is cached in Django's cache until 60 seconds before expiry.
"""
import logging

import requests
from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

IGDB_API_BASE = 'https://api.igdb.com/v4'
TWITCH_TOKEN_URL = 'https://id.twitch.tv/oauth2/token'
TOKEN_CACHE_KEY = 'igdb_bearer_token'
TOKEN_EXPIRY_BUFFER = 60  # seconds before expiry to refresh


def get_igdb_token():
    """Return a valid IGDB bearer token, fetching a new one if needed."""
    token = cache.get(TOKEN_CACHE_KEY)
    if token:
        return token

    resp = requests.post(TWITCH_TOKEN_URL, params={
        'client_id': settings.IGDB_CLIENT_ID,
        'client_secret': settings.IGDB_CLIENT_SECRET,
        'grant_type': 'client_credentials',
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    token = data['access_token']
    ttl = max(data.get('expires_in', 3600) - TOKEN_EXPIRY_BUFFER, 1)
    cache.set(TOKEN_CACHE_KEY, token, ttl)
    return token


def igdb_request(endpoint, body):
    """POST to an IGDB endpoint with the bearer token. Returns parsed JSON."""
    token = get_igdb_token()
    resp = requests.post(
        f'{IGDB_API_BASE}/{endpoint}',
        headers={
            'Client-ID': settings.IGDB_CLIENT_ID,
            'Authorization': f'Bearer {token}',
        },
        data=body,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_igdb_game(igdb_id):
    """
    Fetch a single game from IGDB by numeric ID.
    Returns a dict or None if not found.
    """
    results = igdb_request('games', (
        f'fields id,name,slug,url,summary,cover.image_id,'
        f'first_release_date,category,multiplayer_modes.onlinecoop;'
        f'where id = {igdb_id};'
        f'limit 1;'
    ))
    return results[0] if results else None


def search_igdb_games(query, limit=10):
    """
    Search IGDB for games by name.
    Returns a list of dicts with id, name, slug, cover, first_release_date, category.
    Filters to main games and standalone expansions (categories 0 and 4) by default.
    """
    results = igdb_request('games', (
        f'fields id,name,slug,url,summary,cover.image_id,first_release_date,category;'
        f'search "{query}";'
        f'where category = (0,4);'
        f'limit {limit};'
    ))
    return results


def parse_igdb_game(data):
    """
    Convert raw IGDB game data dict into kwargs suitable for Game.objects.update_or_create().
    Returns a dict of field values.
    """
    release_date = None
    if data.get('first_release_date'):
        from datetime import datetime, timezone
        release_date = datetime.fromtimestamp(
            data['first_release_date'], tz=timezone.utc
        ).date()

    multiplayer_max = None
    for mode in data.get('multiplayer_modes', []):
        if mode.get('onlinecoop'):
            multiplayer_max = max(multiplayer_max or 0, mode.get('onlinecoopmax', 2))
    if multiplayer_max == 0:
        multiplayer_max = None

    return {
        'name': data['name'],
        'igdb_slug': data.get('slug') or None,
        'igdb_url': data.get('url') or None,
        'igdb_cover_hash': (data.get('cover') or {}).get('image_id') or None,
        'summary': data.get('summary', ''),
        'first_release_date': release_date,
        'igdb_category': data.get('category'),
        'multiplayer_max': multiplayer_max,
    }


def sync_game_from_igdb(igdb_id):
    """
    Fetch game data from IGDB and upsert the local Game record.
    Creates the record if it doesn't exist, updates fields if it does.
    Returns (game, created).
    """
    from eventer.models import Game

    data = fetch_igdb_game(igdb_id)
    if not data:
        raise ValueError(f'IGDB game {igdb_id} not found')

    defaults = parse_igdb_game(data)

    game, created = Game.objects.update_or_create(
        igdb_id=igdb_id,
        defaults=defaults,
    )
    log.info('%s game %s (igdb_id=%s)', 'Created' if created else 'Updated', game.name, igdb_id)
    return game, created
