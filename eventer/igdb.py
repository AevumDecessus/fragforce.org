"""
IGDB API client using Twitch OAuth2 client credentials.

Credentials are read from settings.IGDB_CLIENT_ID / IGDB_CLIENT_SECRET.
Bearer tokens are cached in Django's cache until 60 seconds before expiry.

Usage:
    if not IGDBClient.credentials_configured():
        return
    client = IGDBClient()
    if not client.credentials_valid():
        return
    game = client.fetch_game(115555)
"""
import logging
import time
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

IGDB_API_BASE = 'https://api.igdb.com/v4'
TWITCH_TOKEN_URL = 'https://id.twitch.tv/oauth2/token'
TOKEN_EXPIRY_BUFFER = 60  # seconds before expiry to refresh


class IGDBError(Exception):
    """Raised when the IGDB API returns an error response."""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class IGDBClient:
    """
    Client for the IGDB API.

    Check credentials_configured() before instantiating.
    Call credentials_valid() after instantiating to verify the credentials
    actually work before running bulk operations.
    """

    @classmethod
    def credentials_configured(cls):
        """True if both IGDB_CLIENT_ID and IGDB_CLIENT_SECRET are set in settings."""
        return bool(settings.IGDB_CLIENT_ID and settings.IGDB_CLIENT_SECRET)

    def __init__(self):
        self._client_id = settings.IGDB_CLIENT_ID
        self._client_secret = settings.IGDB_CLIENT_SECRET
        self._token_cache_key = f'igdb_bearer_token_{self._client_id}'

    def credentials_valid(self):
        """
        Attempt to fetch a bearer token to verify credentials work.
        Returns True if successful, False if credentials are rejected.
        Raises IGDBError on unexpected errors (network, server errors, etc).
        """
        try:
            self._get_token()
            return True
        except IGDBError as e:
            if e.status_code in (400, 401, 403):
                return False
            raise

    def _get_token(self):
        """Return a valid bearer token, fetching a new one from Twitch if needed."""
        token = cache.get(self._token_cache_key)
        if token:
            return token

        try:
            resp = requests.post(TWITCH_TOKEN_URL, params={
                'client_id': self._client_id,
                'client_secret': self._client_secret,
                'grant_type': 'client_credentials',
            }, timeout=10)
        except requests.exceptions.Timeout:
            raise IGDBError('Timed out fetching IGDB token from Twitch')
        except requests.exceptions.RequestException as e:
            raise IGDBError(f'Network error fetching IGDB token: {e}')

        if not resp.ok:
            raise IGDBError(
                f'Twitch token request failed ({resp.status_code}): {resp.text}',
                status_code=resp.status_code,
            )

        data = resp.json()
        token = data['access_token']
        ttl = max(data.get('expires_in', 3600) - TOKEN_EXPIRY_BUFFER, 1)
        cache.set(self._token_cache_key, token, ttl)
        return token

    def _do_request(self, endpoint, body, token):
        """Make a single POST to an IGDB endpoint. Returns the response object."""
        try:
            return requests.post(
                f'{IGDB_API_BASE}/{endpoint}',
                headers={
                    'Client-ID': self._client_id,
                    'Authorization': f'Bearer {token}',
                },
                data=body,
                timeout=10,
            )
        except requests.exceptions.Timeout:
            raise IGDBError(f'Timed out calling IGDB endpoint: {endpoint}')
        except requests.exceptions.RequestException as e:
            raise IGDBError(f'Network error calling IGDB: {e}')

    def _request(self, endpoint, body):
        """
        POST to an IGDB endpoint. Returns parsed JSON.
        Retries once on 401 (token expiry).
        Retries up to IGDB_RATE_LIMIT_RETRIES times on 429 with backoff.
        """
        token = self._get_token()
        resp = self._do_request(endpoint, body, token)

        if resp.status_code == 401:
            # Token may have expired between cache fetch and request - clear and retry once
            cache.delete(self._token_cache_key)
            token = self._get_token()
            resp = self._do_request(endpoint, body, token)

        max_retries = getattr(settings, 'IGDB_RATE_LIMIT_RETRIES', 3)
        default_retry_after = getattr(settings, 'IGDB_RATE_LIMIT_RETRY_AFTER', 1.0)
        for attempt in range(max_retries):
            if resp.status_code != 429:
                break
            retry_after = float(resp.headers.get('Retry-After', default_retry_after))
            log.warning('IGDB rate limited on %s - waiting %.1fs (attempt %d/%d)',
                        endpoint, retry_after, attempt + 1, max_retries)
            time.sleep(retry_after)
            resp = self._do_request(endpoint, body, token)

        if not resp.ok:
            raise IGDBError(
                f'IGDB request to {endpoint} failed ({resp.status_code}): {resp.text}',
                status_code=resp.status_code,
            )

        return resp.json()

    def fetch_game(self, igdb_id):
        """
        Fetch a single game from IGDB by numeric ID.
        Returns a dict or None if not found.
        """
        results = self._request('games', (
            f'fields id,name,slug,url,summary,cover.image_id,'
            f'first_release_date,category,multiplayer_modes.onlinecoop;'
            f'where id = {igdb_id};'
            f'limit 1;'
        ))
        return results[0] if results else None

    def search_games(self, query, limit=10):
        """
        Search IGDB for games by name.
        Filters to main games and standalone expansions (categories 0 and 4).
        Returns a list of game dicts.
        """
        safe_query = query.replace('\\', '\\\\').replace('"', '\\"')
        return self._request('games', (
            f'fields id,name,slug,url,summary,cover.image_id,first_release_date,category;'
            f'search "{safe_query}";'
            f'where category = (0,4);'
            f'limit {limit};'
        ))


def parse_igdb_game(data):
    """
    Convert raw IGDB game data dict into kwargs suitable for Game.objects.update_or_create().
    Returns a dict of field values.
    """
    release_date = None
    if data.get('first_release_date'):
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
    Raises ValueError if the game is not found on IGDB.
    Raises IGDBError on API errors.
    """
    from eventer.models import Game

    client = IGDBClient()
    data = client.fetch_game(igdb_id)
    if not data:
        raise ValueError(f'IGDB game {igdb_id} not found')

    defaults = parse_igdb_game(data)
    game, created = Game.objects.update_or_create(
        igdb_id=igdb_id,
        defaults=defaults,
    )
    log.info('%s game %s (igdb_id=%s)', 'Created' if created else 'Updated', game.name, igdb_id)
    return game, created
