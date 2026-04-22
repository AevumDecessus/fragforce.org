from datetime import datetime, timezone as dt_timezone
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from social_core.exceptions import AuthForbidden

from eventer.models import Event, EventPeriod, EventRole, EventSignupSlot
from evtsignup.models import EventInterest, EventAvailabilityInterest
from evtsignup.pipeline import require_discord_guild
from evtsignup.utils import parse_fundraising_url


def _dt(year, month, day, hour=0):
    return datetime(year, month, day, hour, tzinfo=dt_timezone.utc)


def _seed_roles():
    for slug, name in [
        ('participant', 'Participant'),
        ('streamer', 'Streamer'),
        ('moderator', 'Moderator'),
        ('tech-manager', 'Tech Manager'),
    ]:
        EventRole.objects.get_or_create(slug=slug, defaults={'name': name, 'description': ''})


def _make_event(signups_open=True, edits_open=True, locked=False, with_slots=True):
    event = Event.objects.create(
        name='Test Superstream', slug='test-superstream', description='A test event',
        timezone='America/New_York',
        signups_open=signups_open, edits_open=edits_open, locked=locked,
    )
    EventPeriod.objects.create(
        event=event,
        start=_dt(2025, 4, 4, 12),
        stop=_dt(2025, 4, 5, 4),
    )
    if with_slots:
        _seed_roles()
        participant_role = EventRole.objects.get(slug='participant')
        streamer_role = EventRole.objects.get(slug='streamer')
        slot = EventSignupSlot.objects.create(
            event=event,
            start=_dt(2025, 4, 4, 12),
            stop=_dt(2025, 4, 4, 15),
            label='Friday 8am - 11am',
        )
        slot.roles.set([participant_role, streamer_role])
    return event


class SignupViewGetTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', 'tester@example.com', 'pass')
        self.client.login(username='tester', password='pass')

    def test_unauthenticated_redirects_to_login(self):
        self.client.logout()
        event = _make_event()
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/signup/test-superstream/', response['Location'])

    def test_locked_shows_locked_message(self):
        event = _make_event(locked=True)
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'locked')
        self.assertTrue(response.context['locked'])

    def test_no_slots_shows_signups_closed(self):
        event = _make_event(with_slots=False)
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['signups_closed'])

    def test_signups_not_open_shows_signups_closed(self):
        event = _make_event(signups_open=False)
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['signups_closed'])

    def test_existing_signup_edits_not_open_shows_edits_closed(self):
        event = _make_event(signups_open=False, edits_open=False)
        EventInterest.objects.create(user=self.user, event=event, acknowledged=True)
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['edits_closed'])

    def test_open_event_renders_form(self):
        event = _make_event()
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign Up')
        self.assertFalse(response.context.get('locked'))
        self.assertFalse(response.context.get('signups_closed'))

    def test_existing_signup_prepopulates_display_name(self):
        event = _make_event()
        EventInterest.objects.create(
            user=self.user, event=event, acknowledged=True,
            display_name='My Name', preferences='they/them',
        )
        response = self.client.get(f'/signup/{event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Name')
        self.assertContains(response, 'they/them')


class SignupViewPostTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', 'tester@example.com', 'pass')
        self.client.login(username='tester', password='pass')
        self.event = _make_event()
        self.slot = EventSignupSlot.objects.filter(event=self.event).first()

    def _url(self):
        return f'/signup/{self.event.slug}/'

    def _post(self, extra=None):
        data = {
            'display_name': 'Test User',
            'preferences': '',
            'acknowledged': '1',
            'participant_slots': [str(self.slot.pk)],
        }
        if extra:
            data.update(extra)
        return self.client.post(self._url(), data)

    def test_no_acknowledgement_returns_error(self):
        response = self.client.post(self._url(), {
            'display_name': 'Test User',
            'preferences': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['errors'])
        self.assertContains(response, 'acknowledge')

    def test_no_acknowledgement_preserves_display_name(self):
        response = self.client.post(self._url(), {
            'display_name': 'My Name',
            'preferences': 'they/them',
        })
        self.assertContains(response, 'My Name')
        self.assertContains(response, 'they/them')

    def test_valid_post_creates_event_interest(self):
        self._post()
        self.assertTrue(EventInterest.objects.filter(user=self.user, event=self.event).exists())

    def test_valid_post_redirects(self):
        response = self._post()
        self.assertRedirects(response, self._url(), fetch_redirect_response=False)

    def test_valid_post_shows_received_message(self):
        self._post()
        response = self.client.get(self._url())
        msgs = list(response.context['messages'])
        self.assertEqual(len(msgs), 1)
        self.assertIn('received', str(msgs[0]))

    def test_update_post_shows_updated_message(self):
        self._post()
        self.client.get(self._url())  # consume the first message
        self._post()  # update
        response = self.client.get(self._url())
        msgs = list(response.context['messages'])
        self.assertEqual(len(msgs), 1)
        self.assertIn('updated', str(msgs[0]))

    def test_valid_post_expands_slot_to_hourly_rows(self):
        self._post()
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        # slot is 12:00-15:00 UTC = 3 hours
        hours = EventAvailabilityInterest.objects.filter(event_interest=interest)
        self.assertEqual(hours.count(), 3)
        self.assertTrue(all(h.as_participant for h in hours))
        self.assertFalse(any(h.as_streamer for h in hours))

    def test_valid_post_sets_streamer_flag_on_streamer_slots(self):
        self._post({'streamer_slots': [str(self.slot.pk)], 'participant_slots': []})
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        hours = EventAvailabilityInterest.objects.filter(event_interest=interest)
        self.assertTrue(all(h.as_streamer for h in hours))
        self.assertFalse(any(h.as_participant for h in hours))

    def test_valid_post_same_slot_both_roles_sets_both_flags(self):
        self._post({'participant_slots': [str(self.slot.pk)], 'streamer_slots': [str(self.slot.pk)]})
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        hours = EventAvailabilityInterest.objects.filter(event_interest=interest)
        self.assertTrue(all(h.as_participant for h in hours))
        self.assertTrue(all(h.as_streamer for h in hours))

    def test_resubmit_replaces_hourly_rows(self):
        self._post()
        self._post({'participant_slots': []})
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertEqual(EventAvailabilityInterest.objects.filter(event_interest=interest).count(), 0)

    def test_invalid_slot_id_ignored(self):
        self.client.post(self._url(), {
            'display_name': 'Test',
            'acknowledged': '1',
            'participant_slots': ['99999'],
        })
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertEqual(EventAvailabilityInterest.objects.filter(event_interest=interest).count(), 0)

    def test_slot_from_different_event_ignored(self):
        other_event = Event.objects.create(
            name='Other Event', slug='other-event', description='',
            signups_open=True, edits_open=True,
        )
        other_slot = EventSignupSlot.objects.create(
            event=other_event, start=_dt(2025, 4, 4, 12), stop=_dt(2025, 4, 4, 15),
            label='Friday 8am - 11am',
        )
        self.client.post(self._url(), {
            'display_name': 'Test',
            'acknowledged': '1',
            'participant_slots': [str(other_slot.pk)],
        })
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertEqual(EventAvailabilityInterest.objects.filter(event_interest=interest).count(), 0)


class SignupViewGameSelectionTest(TestCase):
    def setUp(self):
        from eventer.models import Game
        self.user = User.objects.create_user('tester', 'tester@example.com', 'pass')
        self.client.login(username='tester', password='pass')
        self.event = _make_event()
        self.slot = EventSignupSlot.objects.filter(event=self.event).first()
        self.game = Game.objects.create(
            name='Test Game', slug='test-game', status='approved', suggested=True,
            igdb_id=12345,
        )

    def _url(self):
        return f'/signup/{self.event.slug}/'

    def test_game_selection_creates_game_interest_rows(self):
        from evtsignup.models import GameInterestUserEvent
        self.client.post(self._url(), {
            'acknowledged': '1',
            'participant_games': [str(self.game.pk)],
        })
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertTrue(GameInterestUserEvent.objects.filter(event_interest=interest, game=self.game).exists())

    def test_resubmit_replaces_game_selections(self):
        from evtsignup.models import GameInterestUserEvent
        self.client.post(self._url(), {
            'acknowledged': '1',
            'participant_games': [str(self.game.pk)],
        })
        self.client.post(self._url(), {'acknowledged': '1'})
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertEqual(GameInterestUserEvent.objects.filter(event_interest=interest).count(), 0)

    def test_fundraising_url_saved(self):
        self.client.post(self._url(), {
            'acknowledged': '1',
            'fundraising_url': 'https://www.extra-life.org/participants/511438',
        })
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertEqual(interest.fundraising_url, 'https://www.extra-life.org/participants/511438')

    def test_fundraising_url_blank_stored_as_null(self):
        self.client.post(self._url(), {'acknowledged': '1', 'fundraising_url': ''})
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        self.assertIsNone(interest.fundraising_url)


class SignupViewPrefillTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', 'tester@example.com', 'pass')
        self.client.login(username='tester', password='pass')
        self.event = _make_event()
        self.slot = EventSignupSlot.objects.filter(event=self.event).first()

    def _url(self):
        return f'/signup/{self.event.slug}/'

    def test_reedit_preselects_previously_chosen_slots(self):
        # Submit with a slot selected
        self.client.post(self._url(), {
            'acknowledged': '1',
            'participant_slots': [str(self.slot.pk)],
        })
        # Re-open form - slot should be pre-checked
        response = self.client.get(self._url())
        self.assertIn(self.slot.pk, response.context['selected_slot_ids']['participant'])

    def test_reedit_does_not_preselect_unselected_slots(self):
        self.client.post(self._url(), {'acknowledged': '1'})
        response = self.client.get(self._url())
        self.assertNotIn(self.slot.pk, response.context['selected_slot_ids']['participant'])


class GroupSlotsByDayTest(TestCase):
    def setUp(self):
        import zoneinfo
        self.tz = zoneinfo.ZoneInfo('America/New_York')
        self.event = Event.objects.create(
            name='Day Test', slug='day-test', description='',
            timezone='America/New_York',
        )

    def test_slots_on_same_day_grouped_together(self):
        from evtsignup.views import _group_slots_by_day
        # Both slots start on Friday Apr 4 in ET (12 UTC and 15 UTC = 8am and 11am EDT)
        EventSignupSlot.objects.create(event=self.event, start=_dt(2025, 4, 4, 12), stop=_dt(2025, 4, 4, 15), label='8am')
        EventSignupSlot.objects.create(event=self.event, start=_dt(2025, 4, 4, 15), stop=_dt(2025, 4, 4, 18), label='11am')
        groups = _group_slots_by_day(EventSignupSlot.objects.filter(event=self.event).order_by('start'), self.tz)
        self.assertEqual(len(groups), 1)
        _, slots = groups[0]
        self.assertEqual(len(slots), 2)

    def test_slots_crossing_midnight_split_into_two_days(self):
        from evtsignup.views import _group_slots_by_day
        # Friday 11pm EDT = Saturday 03:00 UTC; Saturday 2am EDT = Saturday 06:00 UTC
        EventSignupSlot.objects.create(event=self.event, start=_dt(2025, 4, 4, 23), stop=_dt(2025, 4, 5, 2), label='Fri late')
        EventSignupSlot.objects.create(event=self.event, start=_dt(2025, 4, 5, 6), stop=_dt(2025, 4, 5, 9), label='Sat early')
        groups = _group_slots_by_day(EventSignupSlot.objects.filter(event=self.event).order_by('start'), self.tz)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0][0], 'Friday, April 4')
        self.assertEqual(groups[1][0], 'Saturday, April 5')

    def test_day_label_format(self):
        from evtsignup.views import _group_slots_by_day
        EventSignupSlot.objects.create(event=self.event, start=_dt(2025, 4, 4, 12), stop=_dt(2025, 4, 4, 15), label='8am')
        groups = _group_slots_by_day(EventSignupSlot.objects.filter(event=self.event), self.tz)
        self.assertEqual(groups[0][0], 'Friday, April 4')

    def test_empty_queryset_returns_empty_list(self):
        from evtsignup.views import _group_slots_by_day
        groups = _group_slots_by_day(EventSignupSlot.objects.none(), self.tz)
        self.assertEqual(groups, [])


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
