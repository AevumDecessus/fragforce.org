from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from social_core.exceptions import AuthForbidden

from evtsignup.pipeline import require_discord_guild


def _make_backend(name='discord'):
    backend = MagicMock()
    backend.name = name
    return backend


class RequireDiscordGuildTest(TestCase):
    @override_settings(DISCORD_REQUIRED_GUILD_ID='164136635762606081')
    def test_passes_when_user_in_guild(self):
        backend = _make_backend()
        guilds = [{'id': '164136635762606081'}, {'id': '999'}]
        with patch('evtsignup.pipeline.requests.get') as mock_get:
            mock_get.return_value.json.return_value = guilds
            result = require_discord_guild(backend, {'access_token': 'token'})
        self.assertIsNone(result)

    @override_settings(DISCORD_REQUIRED_GUILD_ID='164136635762606081')
    def test_raises_when_user_not_in_guild(self):
        backend = _make_backend()
        guilds = [{'id': '999'}]
        with patch('evtsignup.pipeline.requests.get') as mock_get:
            mock_get.return_value.json.return_value = guilds
            with self.assertRaises(AuthForbidden):
                require_discord_guild(backend, {'access_token': 'token'})

    def test_passes_when_no_guild_id_configured(self):
        backend = _make_backend()
        with self.settings(DISCORD_REQUIRED_GUILD_ID=''):
            result = require_discord_guild(backend, {'access_token': 'token'})
        self.assertIsNone(result)

    def test_skips_non_discord_backends(self):
        backend = _make_backend(name='google-oauth2')
        result = require_discord_guild(backend, {'access_token': 'token'})
        self.assertIsNone(result)

    @override_settings(DISCORD_REQUIRED_GUILD_ID='164136635762606081')
    def test_raises_when_guilds_response_is_not_a_list(self):
        backend = _make_backend()
        with patch('evtsignup.pipeline.requests.get') as mock_get:
            mock_get.return_value.json.return_value = {'error': 'unauthorized'}
            with self.assertRaises(AuthForbidden):
                require_discord_guild(backend, {'access_token': 'token'})
