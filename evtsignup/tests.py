from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from social_core.exceptions import AuthForbidden

from evtsignup.pipeline import require_discord_guild
from evtsignup.utils import parse_fundraising_url


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


class ParseFundraisingUrlTest(TestCase):
    # --- Empty cases ---

    def test_empty_string(self):
        r = parse_fundraising_url('')
        self.assertEqual(r.type, 'empty')
        self.assertEqual(r.id_or_slug, '')

    def test_none(self):
        r = parse_fundraising_url(None)
        self.assertEqual(r.type, 'empty')

    def test_whitespace_only(self):
        r = parse_fundraising_url('   ')
        self.assertEqual(r.type, 'empty')

    # --- Modern participant URLs ---

    def test_numeric_participant_id(self):
        r = parse_fundraising_url('https://www.extra-life.org/participants/511438')
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '511438')
        self.assertTrue(r.is_participant)
        self.assertTrue(r.is_extralife)

    def test_vanity_participant_slug(self):
        r = parse_fundraising_url('https://www.extra-life.org/participants/aevumdecessus')
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, 'aevumdecessus')

    def test_participant_url_without_www(self):
        r = parse_fundraising_url('https://extra-life.org/participants/511438')
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '511438')

    def test_participant_url_with_trailing_slash(self):
        r = parse_fundraising_url('https://www.extra-life.org/participants/511438/')
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '511438')

    def test_participant_url_with_fragment(self):
        r = parse_fundraising_url('https://www.extra-life.org/participants/511438#donate')
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '511438')

    # --- Modern team URLs ---

    def test_team_vanity_slug(self):
        r = parse_fundraising_url('https://www.extra-life.org/teams/fragforce-dcm')
        self.assertEqual(r.type, 'team')
        self.assertEqual(r.id_or_slug, 'fragforce-dcm')
        self.assertTrue(r.is_team)
        self.assertTrue(r.is_extralife)

    def test_team_numeric_id(self):
        r = parse_fundraising_url('https://www.extra-life.org/teams/68980')
        self.assertEqual(r.type, 'team')
        self.assertEqual(r.id_or_slug, '68980')

    # --- Legacy cfm URLs ---

    def test_legacy_participant_cfm(self):
        r = parse_fundraising_url(
            'https://www.extra-life.org/index.cfm?fuseaction=donorDrive.participant&participantID=511438'
        )
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '511438')

    def test_legacy_participant_cfm_portal_home_fuseaction(self):
        # Seen in practice - fuseaction=portal.home but participantID present
        r = parse_fundraising_url(
            'https://www.extra-life.org/index.cfm?fuseaction=portal.home&participantID=514130'
        )
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '514130')

    def test_legacy_team_cfm(self):
        r = parse_fundraising_url(
            'https://www.extra-life.org/index.cfm?fuseaction=donorDrive.team&teamID=68980'
        )
        self.assertEqual(r.type, 'team')
        self.assertEqual(r.id_or_slug, '68980')

    def test_legacy_donordrive_domain(self):
        r = parse_fundraising_url(
            'https://www.donordrive.com/index.cfm?fuseaction=donorDrive.participant&participantID=533595'
        )
        self.assertEqual(r.type, 'participant')
        self.assertEqual(r.id_or_slug, '533595')

    # --- Non-EL / other URLs ---

    def test_tiltify_url(self):
        r = parse_fundraising_url('https://tiltify.com/+fragforce/')
        self.assertEqual(r.type, 'other')
        self.assertFalse(r.is_extralife)

    def test_hospital_charity_url(self):
        r = parse_fundraising_url('http://chfou.convio.net/goto/Montscot832')
        self.assertEqual(r.type, 'other')

    def test_shortlink_url(self):
        r = parse_fundraising_url('https://el.pvcp.co')
        self.assertEqual(r.type, 'other')

    def test_not_yet_signed_up_text(self):
        r = parse_fundraising_url('I have not signed up yet')
        self.assertEqual(r.type, 'other')

    def test_bare_text(self):
        r = parse_fundraising_url('some random text')
        self.assertEqual(r.type, 'other')

    # --- raw_url always preserved ---

    def test_raw_url_preserved_for_participant(self):
        url = 'https://www.extra-life.org/participants/511438'
        r = parse_fundraising_url(url)
        self.assertEqual(r.raw_url, url)

    def test_raw_url_preserved_for_other(self):
        url = 'https://tiltify.com/+fragforce/'
        r = parse_fundraising_url(url)
        self.assertEqual(r.raw_url, url)
