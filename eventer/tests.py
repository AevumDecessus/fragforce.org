import zoneinfo
from datetime import datetime, timezone as dt_timezone, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from eventer.admin import SUPERSTREAM_ROLES
from eventer.models import Event, EventPeriod, EventRole, EventSignupSlotConfig, EventSignupSlot, HOUR_SECONDS
from eventer.schedule import SINGLE_ASSIGNMENT_ROLES, MULTI_ASSIGNMENT_ROLES
from eventer.slot_generator import _format_label, _variable_block_hours, generate_slots


def dt(year, month, day, hour=0, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=dt_timezone.utc)


class EventStartEndTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name='Test Event', slug='test-event', description='')

    def test_start_returns_none_with_no_periods(self):
        self.assertIsNone(self.event.start)

    def test_end_returns_none_with_no_periods(self):
        self.assertIsNone(self.event.end)

    def test_start_returns_period_start_for_single_period(self):
        start = dt(2025, 4, 4, 8)
        stop = dt(2025, 4, 6)
        EventPeriod.objects.create(event=self.event, start=start, stop=stop)

        self.assertEqual(self.event.start, start)

    def test_end_returns_period_stop_for_single_period(self):
        start = dt(2025, 4, 4, 8)
        stop = dt(2025, 4, 6)
        EventPeriod.objects.create(event=self.event, start=start, stop=stop)

        self.assertEqual(self.event.end, stop)

    def test_start_returns_earliest_with_multiple_periods(self):
        early = dt(2025, 4, 4, 8)
        late = dt(2025, 4, 5, 8)
        EventPeriod.objects.create(event=self.event, start=late, stop=dt(2025, 4, 5, 20))
        EventPeriod.objects.create(event=self.event, start=early, stop=dt(2025, 4, 4, 20))

        self.assertEqual(self.event.start, early)

    def test_end_returns_latest_with_multiple_periods(self):
        early_stop = dt(2025, 4, 4, 20)
        late_stop = dt(2025, 4, 6)
        EventPeriod.objects.create(event=self.event, start=dt(2025, 4, 4, 8), stop=early_stop)
        EventPeriod.objects.create(event=self.event, start=dt(2025, 4, 5, 8), stop=late_stop)

        self.assertEqual(self.event.end, late_stop)


class SeedSuperstreamRolesViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')

    def _url(self):
        return '/admin/eventer/eventrole/seed-superstream/'

    def test_creates_all_roles_when_none_exist(self):
        response = self.client.post(self._url())
        self.assertRedirects(response, '/admin/eventer/eventrole/', fetch_redirect_response=False)
        self.assertEqual(EventRole.objects.count(), len(SUPERSTREAM_ROLES))
        slugs = set(EventRole.objects.values_list('slug', flat=True))
        self.assertEqual(slugs, {r['slug'] for r in SUPERSTREAM_ROLES})

    def test_idempotent_when_roles_already_exist(self):
        for role in SUPERSTREAM_ROLES:
            EventRole.objects.create(name=role['name'], slug=role['slug'], description=role['description'])
        self.client.post(self._url())
        self.assertEqual(EventRole.objects.count(), len(SUPERSTREAM_ROLES))

    def test_creates_only_missing_roles(self):
        EventRole.objects.create(name='Participant', slug='participant', description='')
        EventRole.objects.create(name='Streamer', slug='streamer', description='')
        self.client.post(self._url())
        self.assertEqual(EventRole.objects.count(), len(SUPERSTREAM_ROLES))

    def test_get_also_seeds_and_redirects(self):
        response = self.client.get(self._url())
        self.assertRedirects(response, '/admin/eventer/eventrole/', fetch_redirect_response=False)
        self.assertEqual(EventRole.objects.count(), len(SUPERSTREAM_ROLES))


class SetupSuperstreamViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event = Event.objects.create(name='Test Event', slug='test-event', description='')

    def _url(self):
        return f'/admin/eventer/event/{self.event.pk}/setup-superstream/'

    def test_get_renders_form(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Superstream Period')

    def test_post_creates_event_period_edt(self):
        # April 4 2025 is in EDT (UTC-4) - 8am EDT = 12:00 UTC
        response = self.client.post(self._url(), {
            'start': '2025-04-04T08:00',
            'duration': '40',
        })
        self.assertRedirects(response, f'/admin/eventer/event/{self.event.pk}/generate-slots/', fetch_redirect_response=False)
        self.assertEqual(EventPeriod.objects.filter(event=self.event).count(), 1)
        period = EventPeriod.objects.get(event=self.event)
        self.assertEqual(period.start.hour, 12)  # 8am EDT (UTC-4) = 12:00 UTC

    def test_post_creates_event_period_est(self):
        # January 10 2025 is in EST (UTC-5) - 8am EST = 13:00 UTC
        response = self.client.post(self._url(), {
            'start': '2025-01-10T08:00',
            'duration': '40',
        })
        self.assertRedirects(response, f'/admin/eventer/event/{self.event.pk}/generate-slots/', fetch_redirect_response=False)
        period = EventPeriod.objects.get(event=self.event)
        self.assertEqual(period.start.hour, 13)  # 8am EST (UTC-5) = 13:00 UTC

    def test_post_creates_event_period_pacific_timezone(self):
        # Event in Pacific time - April 4 2025 is PDT (UTC-7) - 8am PDT = 15:00 UTC
        pacific_event = Event.objects.create(
            name='Pacific Event', slug='pacific-event', description='',
            timezone='America/Los_Angeles'
        )
        response = self.client.post(
            f'/admin/eventer/event/{pacific_event.pk}/setup-superstream/',
            {'start': '2025-04-04T08:00', 'duration': '40'},
        )
        self.assertRedirects(response, f'/admin/eventer/event/{pacific_event.pk}/generate-slots/', fetch_redirect_response=False)
        period = EventPeriod.objects.get(event=pacific_event)
        self.assertEqual(period.start.hour, 15)  # 8am PDT (UTC-7) = 15:00 UTC

    def test_post_creates_event_period_utc_timezone(self):
        # Event in UTC - 8am UTC = 8:00 UTC, no DST
        utc_event = Event.objects.create(
            name='UTC Event', slug='utc-event', description='',
            timezone='UTC'
        )
        response = self.client.post(
            f'/admin/eventer/event/{utc_event.pk}/setup-superstream/',
            {'start': '2025-04-04T08:00', 'duration': '40'},
        )
        self.assertRedirects(response, f'/admin/eventer/event/{utc_event.pk}/generate-slots/', fetch_redirect_response=False)
        period = EventPeriod.objects.get(event=utc_event)
        self.assertEqual(period.start.hour, 8)  # 8am UTC = 8:00 UTC

    def test_post_with_invalid_duration_shows_error(self):
        response = self.client.post(self._url(), {
            'start': '2025-04-04T08:00',
            'duration': '-1',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Duration must be at least 1 hour')
        self.assertEqual(EventPeriod.objects.filter(event=self.event).count(), 0)

    def test_get_shows_existing_periods(self):
        start = datetime(2025, 4, 4, 12, 0, tzinfo=dt_timezone.utc)
        EventPeriod.objects.create(event=self.event, start=start, stop=start + timedelta(hours=40))
        response = self.client.get(self._url())
        self.assertContains(response, 'already has 1 period')


def _local(year, month, day, hour, tz_name='America/New_York'):
    tz = zoneinfo.ZoneInfo(tz_name)
    return datetime(year, month, day, hour, tzinfo=dt_timezone.utc).astimezone(tz)


def _seed_roles():
    for slug, name in [
        ('participant', 'Participant'),
        ('streamer', 'Streamer'),
        ('moderator', 'Moderator'),
        ('tech-manager', 'Tech Manager'),
    ]:
        EventRole.objects.get_or_create(slug=slug, defaults={'name': name, 'description': ''})


class FormatLabelTest(TestCase):
    def test_same_day(self):
        # Fri Apr 4 2025: 12 UTC = 8am EDT, 15 UTC = 11am EDT
        self.assertEqual(_format_label(_local(2025, 4, 4, 12), _local(2025, 4, 4, 15)), 'Friday 8am - 11am')

    def test_crosses_midnight(self):
        # Fri 11pm EDT = Sat 3 UTC, Sat 2am EDT = Sat 6 UTC
        self.assertEqual(
            _format_label(_local(2025, 4, 5, 3), _local(2025, 4, 5, 6)),
            'Friday 11pm - Saturday 2am'
        )


class VariableBlockHoursTest(TestCase):
    def setUp(self):
        self.event = Event.objects.create(name='Test', slug='test', description='')
        self.config = EventSignupSlotConfig.objects.create(event=self.event)

    def test_standard_block_outside_prime(self):
        # 8am EDT = 12 UTC - outside prime time (2pm-9pm ET)
        local = _local(2025, 4, 4, 12)
        self.assertEqual(_variable_block_hours(local, self.config), self.config.standard_block_hours)

    def test_prime_block_during_prime(self):
        # 3pm EDT = 19 UTC - inside prime time
        local = _local(2025, 4, 4, 19)
        self.assertEqual(_variable_block_hours(local, self.config), self.config.prime_block_hours)

    def test_prime_start_boundary(self):
        # 2pm EDT = 18 UTC - at prime_time_start, should be prime
        local = _local(2025, 4, 4, 18)
        self.assertEqual(_variable_block_hours(local, self.config), self.config.prime_block_hours)

    def test_prime_end_boundary(self):
        # 9pm EDT = 01 UTC next day - at prime_time_end, should be standard
        local = _local(2025, 4, 5, 1)
        self.assertEqual(_variable_block_hours(local, self.config), self.config.standard_block_hours)


class GenerateSlotsTest(TestCase):
    def setUp(self):
        _seed_roles()
        self.event = Event.objects.create(
            name='Test Superstream', slug='test-superstream', description='',
            timezone='America/New_York',
        )
        # 40hr event: Fri Apr 4 8am EDT (12 UTC) → Sun Apr 6 12am EDT (04 UTC)
        EventPeriod.objects.create(
            event=self.event,
            start=datetime(2025, 4, 4, 12, 0, tzinfo=dt_timezone.utc),
            stop=datetime(2025, 4, 6, 4, 0, tzinfo=dt_timezone.utc),
        )

    def _config(self):
        config, _ = EventSignupSlotConfig.objects.get_or_create(event=self.event)
        return config

    def test_raises_without_periods(self):
        event = Event.objects.create(name='No Period', slug='no-period', description='')
        with self.assertRaises(ValueError):
            generate_slots(event)

    def test_raises_without_roles(self):
        EventRole.objects.all().delete()
        with self.assertRaises(ValueError):
            generate_slots(self.event)

    def test_creates_slots(self):
        result = generate_slots(self.event)
        self.assertGreater(result['created'], 0)
        self.assertEqual(result['deleted'], 0)
        # Some skipped is expected when grids share slot boundaries
        self.assertGreaterEqual(result['skipped'], 0)

    def test_participant_and_streamer_share_slots(self):
        generate_slots(self.event)
        participant = EventRole.objects.get(slug='participant')
        streamer = EventRole.objects.get(slug='streamer')
        p_slots = set(EventSignupSlot.objects.filter(event=self.event, roles=participant).values_list('id', flat=True))
        s_slots = set(EventSignupSlot.objects.filter(event=self.event, roles=streamer).values_list('id', flat=True))
        self.assertEqual(p_slots, s_slots)

    def test_tech_has_uniform_management_block_size(self):
        generate_slots(self.event)
        config = self._config()
        tech = EventRole.objects.get(slug='tech-manager')
        slots = list(EventSignupSlot.objects.filter(event=self.event, roles=tech).order_by('start'))
        for slot in slots[:-1]:  # last slot may be absorbed
            duration_hrs = (slot.stop - slot.start).total_seconds() / HOUR_SECONDS
            self.assertEqual(duration_hrs, config.management_block_hours, f"Tech slot {slot.label} should be {config.management_block_hours}hr")

    def test_moderator_first_block_matches_config(self):
        generate_slots(self.event)
        config = self._config()
        moderator = EventRole.objects.get(slug='moderator')
        first_slot = EventSignupSlot.objects.filter(event=self.event, roles=moderator).order_by('start').first()
        duration_hrs = (first_slot.stop - first_slot.start).total_seconds() / HOUR_SECONDS
        self.assertEqual(duration_hrs, config.mod_first_block_hours)

    def test_prime_time_slots_use_prime_block_hours(self):
        generate_slots(self.event)
        config = self._config()
        tz = zoneinfo.ZoneInfo(self.event.timezone)
        participant = EventRole.objects.get(slug='participant')
        for slot in EventSignupSlot.objects.filter(event=self.event, roles=participant):
            local_start = slot.start.astimezone(tz)
            t = local_start.time()
            if config.prime_time_start <= t < config.prime_time_end:
                duration_hrs = (slot.stop - slot.start).total_seconds() / HOUR_SECONDS
                self.assertEqual(duration_hrs, config.prime_block_hours, f"Prime-time slot {slot.label} should be {config.prime_block_hours}hr")

    def test_non_prime_slots_use_standard_block_hours(self):
        generate_slots(self.event)
        config = self._config()
        tz = zoneinfo.ZoneInfo(self.event.timezone)
        participant = EventRole.objects.get(slug='participant')
        slots = list(EventSignupSlot.objects.filter(event=self.event, roles=participant).order_by('start'))
        for slot in slots[:-1]:  # skip last slot (may be absorbed)
            local_start = slot.start.astimezone(tz)
            t = local_start.time()
            if not (config.prime_time_start <= t < config.prime_time_end):
                duration_hrs = (slot.stop - slot.start).total_seconds() / HOUR_SECONDS
                self.assertEqual(duration_hrs, config.standard_block_hours, f"Non-prime slot {slot.label} should be {config.standard_block_hours}hr")

    def test_no_stub_slots_shorter_than_min(self):
        generate_slots(self.event)
        config = self._config()
        min_hours = max(config.prime_block_hours, 2)
        for slot in EventSignupSlot.objects.filter(event=self.event):
            duration_hrs = (slot.stop - slot.start).total_seconds() / HOUR_SECONDS
            self.assertGreaterEqual(duration_hrs, min_hours, f"Slot {slot.label} is too short: {duration_hrs}hr")

    def test_replace_deletes_existing_and_regenerates(self):
        generate_slots(self.event)
        first_count = EventSignupSlot.objects.filter(event=self.event).count()
        result = generate_slots(self.event, replace=True)
        self.assertGreater(result['deleted'], 0)
        self.assertEqual(EventSignupSlot.objects.filter(event=self.event).count(), first_count)

    def test_idempotent_without_replace(self):
        generate_slots(self.event)
        first_count = EventSignupSlot.objects.filter(event=self.event).count()
        result = generate_slots(self.event, replace=False)
        self.assertEqual(result['created'], 0)
        self.assertEqual(EventSignupSlot.objects.filter(event=self.event).count(), first_count)


class EventAdminListTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event_with_period = Event.objects.create(
            name='Scheduled Event', slug='scheduled-event', description='',
            timezone='America/New_York',
        )
        EventPeriod.objects.create(
            event=self.event_with_period,
            start=datetime(2025, 4, 4, 12, 0, tzinfo=dt_timezone.utc),
            stop=datetime(2025, 4, 6, 4, 0, tzinfo=dt_timezone.utc),
        )
        self.event_no_period = Event.objects.create(
            name='Unscheduled Event', slug='unscheduled-event', description='',
        )

    def _url(self):
        return '/admin/eventer/event/'

    def test_has_period_filter_returns_scheduled_events(self):
        response = self.client.get(self._url(), {'has_period': 'yes'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Scheduled Event')
        self.assertNotContains(response, 'Unscheduled Event')

    def test_no_period_filter_returns_unscheduled_events(self):
        response = self.client.get(self._url(), {'has_period': 'no'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Unscheduled Event')
        self.assertNotContains(response, 'Scheduled Event')

    def test_event_start_shows_dash_when_no_period(self):
        response = self.client.get(self._url())
        self.assertContains(response, 'Unscheduled Event')
        # The event_start column should show '-' for events with no period
        self.assertContains(response, '<td class="field-event_start">-</td>')

    def test_event_start_shows_local_time_when_period_exists(self):
        response = self.client.get(self._url())
        # 12:00 UTC on April 4 2025 = 8am EDT
        self.assertContains(response, '2025-04-04 08:00 EDT')


class EventAdminCreateFlowTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')

    def test_create_event_redirects_to_slot_config_add(self):
        response = self.client.post('/admin/eventer/event/add/', {
            'name': 'New Event',
            'slug': 'new-event',
            'description': 'A new event',
            'timezone': 'America/New_York',
            'signups_open': False,
            'edits_open': False,
            'locked': False,
            '_save': '1',
        })
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(slug='new-event')
        self.assertIn(f'eventsignupslotconfig/add/?event={event.pk}', response['Location'])

    def test_create_slot_config_redirects_to_setup_superstream(self):
        event = Event.objects.create(name='Flow Event', slug='flow-event', description='')
        response = self.client.post('/admin/eventer/eventsignupslotconfig/add/', {
            'event': event.pk,
            'standard_block_hours': 3,
            'prime_block_hours': 2,
            'prime_time_start': '14:00:00',
            'prime_time_end': '21:00:00',
            'management_block_hours': 6,
            'mod_first_block_hours': 3,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'event/{event.pk}/setup-superstream/', response['Location'])

    def test_setup_superstream_redirects_to_generate_slots(self):
        event = Event.objects.create(name='Flow Event 2', slug='flow-event-2', description='')
        response = self.client.post(
            f'/admin/eventer/event/{event.pk}/setup-superstream/',
            {'start': '2025-04-04T08:00', 'duration': '40'},
        )
        self.assertRedirects(
            response,
            f'/admin/eventer/event/{event.pk}/generate-slots/',
            fetch_redirect_response=False,
        )


class EventListViewTest(TestCase):
    def setUp(self):
        self.now = datetime(2025, 4, 4, 12, 0, tzinfo=dt_timezone.utc)

    def _make_event(self, name, slug, public=True, stop_offset_hours=48):
        event = Event.objects.create(name=name, slug=slug, description='A test event', public=public)
        EventPeriod.objects.create(
            event=event,
            start=self.now,
            stop=self.now + timedelta(hours=stop_offset_hours),
        )
        return event

    def test_lists_public_upcoming_events(self):
        from unittest.mock import patch
        self._make_event('Public Event', 'public-event')
        with patch('django.utils.timezone.now', return_value=self.now):
            response = self.client.get('/events/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Event')

    def test_excludes_non_public_events(self):
        from unittest.mock import patch
        self._make_event('Private Event', 'private-event', public=False)
        with patch('django.utils.timezone.now', return_value=self.now):
            response = self.client.get('/events/')
        self.assertNotContains(response, 'Private Event')

    def test_excludes_past_events(self):
        from unittest.mock import patch
        self._make_event('Past Event', 'past-event', stop_offset_hours=-1)
        future = self.now + timedelta(hours=2)
        with patch('django.utils.timezone.now', return_value=future):
            response = self.client.get('/events/')
        self.assertNotContains(response, 'Past Event')

    def test_empty_state_shown_when_no_events(self):
        from unittest.mock import patch
        with patch('django.utils.timezone.now', return_value=self.now):
            response = self.client.get('/events/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No upcoming events')


class EventDetailViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('tester', 'tester@example.com', 'pass')
        self.event = Event.objects.create(
            name='Detail Event', slug='detail-event', description='An event',
            public=True, signups_open=True, edits_open=True,
        )
        EventPeriod.objects.create(
            event=self.event,
            start=datetime(2025, 4, 4, 12, tzinfo=dt_timezone.utc),
            stop=datetime(2025, 4, 6, 4, tzinfo=dt_timezone.utc),
        )

    def test_detail_returns_200(self):
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detail Event')

    def test_non_public_event_detail_still_accessible(self):
        self.event.public = False
        self.event.save()
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertEqual(response.status_code, 200)

    def test_404_for_unknown_slug(self):
        response = self.client.get('/events/does-not-exist/')
        self.assertEqual(response.status_code, 404)

    def test_signup_link_shown_when_signups_open_and_no_existing_signup(self):
        self.client.login(username='tester', password='pass')
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertTrue(response.context['show_signup_link'])
        self.assertFalse(response.context['show_edit_link'])

    def test_edit_link_shown_when_edits_open_and_existing_signup(self):
        from evtsignup.models import EventInterest
        self.client.login(username='tester', password='pass')
        EventInterest.objects.create(user=self.user, event=self.event, acknowledged=True)
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertFalse(response.context['show_signup_link'])
        self.assertTrue(response.context['show_edit_link'])

    def test_no_links_when_locked(self):
        self.event.locked = True
        self.event.save()
        self.client.login(username='tester', password='pass')
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertFalse(response.context['show_signup_link'])
        self.assertFalse(response.context['show_edit_link'])

    def test_no_signup_link_when_signups_closed(self):
        self.event.signups_open = False
        self.event.save()
        self.client.login(username='tester', password='pass')
        response = self.client.get(f'/events/{self.event.slug}/')
        self.assertFalse(response.context['show_signup_link'])


def _make_schedule_event():
    """
    Create a test event with periods, roles, and signup slots for schedule tests.
    Returns (event, slot, streamer_role) - uses streamer as the primary test role
    since participant is a multi-assignment role (EventScheduleMultiAssignment).
    """
    event = Event.objects.create(
        name='Schedule Test', slug='schedule-test', description='',
        timezone='America/New_York',
    )
    EventPeriod.objects.create(
        event=event,
        start=dt(2025, 4, 4, 12),
        stop=dt(2025, 4, 4, 18),
    )
    for slug, name in [('participant', 'Participant'), ('streamer', 'Streamer'),
                       ('moderator', 'Moderator'), ('tech-manager', 'Tech Manager')]:
        EventRole.objects.get_or_create(slug=slug, defaults={'name': name, 'description': ''})
    streamer_role = EventRole.objects.get(slug='streamer')
    participant_role = EventRole.objects.get(slug='participant')
    slot = EventSignupSlot.objects.create(
        event=event,
        start=dt(2025, 4, 4, 12),
        stop=dt(2025, 4, 4, 15),
        label='Friday 8am - 11am',
    )
    slot.roles.set([streamer_role, participant_role])
    return event, slot, streamer_role


class AvailabilitySummaryViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event, self.slot, self.role = _make_schedule_event()

    def _url(self):
        return f'/admin/eventer/event/{self.event.pk}/availability/'

    def test_returns_200(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    def test_shows_no_data_message_when_no_periods(self):
        event = Event.objects.create(name='No Period', slug='no-period', description='')
        response = self.client.get(f'/admin/eventer/event/{event.pk}/availability/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['rows'], [])

    def test_grid_has_correct_number_of_rows(self):
        response = self.client.get(self._url())
        # 6 hours (12:00-18:00 UTC)
        self.assertEqual(len(response.context['rows']), 6)

    def test_role_headers_present(self):
        response = self.client.get(self._url())
        labels = [h['label'] for h in response.context['role_headers']]
        for _, _, label in SINGLE_ASSIGNMENT_ROLES:
            self.assertIn(label, labels)
        for _, _, label in MULTI_ASSIGNMENT_ROLES:
            self.assertNotIn(label, labels)


class BuildScheduleViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event, self.slot, self.role = _make_schedule_event()

    def _url(self):
        return f'/admin/eventer/event/{self.event.pk}/build-schedule/'

    def test_get_returns_200(self):
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)

    def test_post_creates_schedule_slots(self):
        from eventer.models import EventScheduleAssignment
        streamer_role = EventRole.objects.get(slug='streamer')
        user = User.objects.create_user('streamer', 'streamer@example.com', 'pass')
        response = self.client.post(self._url(), {
            f'assign_{self.slot.pk}_streamer': str(user.pk),
        })
        self.assertRedirects(response, self._url(), fetch_redirect_response=False)
        self.assertTrue(EventScheduleAssignment.objects.filter(
            event=self.event, slot=self.slot, role=streamer_role, user=user
        ).exists())

    def test_post_creates_multi_assignments(self):
        from eventer.models import EventScheduleMultiAssignment
        participant_role = EventRole.objects.get(slug='participant')
        user1 = User.objects.create_user('p1', 'p1@example.com', 'pass')
        user2 = User.objects.create_user('p2', 'p2@example.com', 'pass')
        self.client.post(self._url(), {
            f'assign_{self.slot.pk}_participant': [str(user1.pk), str(user2.pk)],
        })
        self.assertEqual(
            EventScheduleMultiAssignment.objects.filter(event=self.event, slot=self.slot, role=participant_role).count(),
            2
        )

    def test_post_replaces_existing_assignments(self):
        from eventer.models import EventScheduleAssignment
        streamer_role = EventRole.objects.get(slug='streamer')
        user1 = User.objects.create_user('user1', 'u1@example.com', 'pass')
        user2 = User.objects.create_user('user2', 'u2@example.com', 'pass')
        EventScheduleAssignment.objects.create(event=self.event, slot=self.slot, role=streamer_role, user=user1)
        self.client.post(self._url(), {
            f'assign_{self.slot.pk}_streamer': str(user2.pk),
        })
        assignment = EventScheduleAssignment.objects.get(event=self.event, slot=self.slot, role=streamer_role)
        self.assertEqual(assignment.user, user2)

    def test_post_clears_unsubmitted_slots(self):
        from eventer.models import EventScheduleAssignment
        streamer_role = EventRole.objects.get(slug='streamer')
        user = User.objects.create_user('user1', 'u1@example.com', 'pass')
        EventScheduleAssignment.objects.create(event=self.event, slot=self.slot, role=streamer_role, user=user)
        # POST with no assignments - should clear all
        self.client.post(self._url(), {})
        self.assertEqual(EventScheduleAssignment.objects.filter(event=self.event).count(), 0)


class AssignSlotViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event, self.slot, self.role = _make_schedule_event()
        self.user = User.objects.create_user('streamer', 'streamer@example.com', 'pass')

    def _url(self):
        return f'/admin/eventer/event/{self.event.pk}/assign-slot/'

    def test_assigns_user_to_slot(self):
        from eventer.models import EventScheduleAssignment
        self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': 'streamer',
            'user_id': self.user.pk,
        })
        self.assertTrue(EventScheduleAssignment.objects.filter(
            slot=self.slot, role=self.role, user=self.user
        ).exists())

    def test_clears_assignment_when_no_user(self):
        from eventer.models import EventScheduleAssignment
        EventScheduleAssignment.objects.create(event=self.event, slot=self.slot, role=self.role, user=self.user)
        self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': 'streamer',
            'user_id': '',
        })
        self.assertFalse(EventScheduleAssignment.objects.filter(slot=self.slot, role=self.role).exists())

    def test_get_redirects_to_availability(self):
        response = self.client.get(self._url())
        self.assertRedirects(response,
            f'/admin/eventer/event/{self.event.pk}/availability/',
            fetch_redirect_response=False)


class AddAvailabilityViewTest(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.login(username='admin', password='pass')
        self.event, self.slot, self.role = _make_schedule_event()
        self.user = User.objects.create_user('newcomer', 'newcomer@example.com', 'pass')

    def _url(self):
        return f'/admin/eventer/event/{self.event.pk}/add-availability/'

    def test_get_renders_form(self):
        response = self.client.get(
            self._url(), {'slot': self.slot.pk, 'role': 'streamer'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Friday 8am - 11am')

    def test_post_creates_event_interest(self):
        from evtsignup.models import EventInterest
        self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': 'streamer',
            'user': self.user.pk,
        })
        self.assertTrue(EventInterest.objects.filter(user=self.user, event=self.event).exists())

    def test_post_creates_availability_rows(self):
        from evtsignup.models import EventAvailabilityInterest, EventInterest
        self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': 'streamer',
            'user': self.user.pk,
        })
        interest = EventInterest.objects.get(user=self.user, event=self.event)
        hours = EventAvailabilityInterest.objects.filter(event_interest=interest, as_streamer=True)
        self.assertEqual(hours.count(), 3)  # 12:00, 13:00, 14:00 UTC

    def test_post_creates_schedule_slot(self):
        from eventer.models import EventScheduleAssignment
        self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': 'streamer',
            'user': self.user.pk,
        })
        self.assertTrue(EventScheduleAssignment.objects.filter(
            event=self.event, slot=self.slot, role=self.role, user=self.user
        ).exists())

    def test_post_redirects_to_availability(self):
        response = self.client.post(self._url(), {
            'slot_pk': self.slot.pk,
            'role_slug': 'streamer',
            'user': self.user.pk,
        })
        self.assertRedirects(response,
            f'/admin/eventer/event/{self.event.pk}/availability/',
            fetch_redirect_response=False)


class GameCoverUrlTest(TestCase):
    def test_cover_url_returns_big_url(self):
        from eventer.models import Game
        game = Game(name='Test', igdb_id=1, igdb_cover_hash='abc123')
        self.assertEqual(game.cover_url, '//images.igdb.com/igdb/image/upload/t_cover_big/abc123.jpg')

    def test_cover_url_thumb_returns_thumb_url(self):
        from eventer.models import Game
        game = Game(name='Test', igdb_id=1, igdb_cover_hash='abc123')
        self.assertEqual(game.cover_url_thumb, '//images.igdb.com/igdb/image/upload/t_thumb/abc123.jpg')

    def test_cover_url_none_when_no_hash(self):
        from eventer.models import Game
        game = Game(name='Test', igdb_id=1, igdb_cover_hash=None)
        self.assertIsNone(game.cover_url)
        self.assertIsNone(game.cover_url_thumb)


class ParseIgdbGameTest(TestCase):
    def test_parses_basic_fields(self):
        from eventer.igdb import parse_igdb_game
        data = {
            'id': 1234,
            'name': 'Going Medieval',
            'slug': 'going-medieval',
            'url': 'https://www.igdb.com/games/going-medieval',
            'summary': 'A colony builder.',
            'cover': {'image_id': 'hash001'},
            'category': 0,
        }
        result = parse_igdb_game(data)
        self.assertEqual(result['name'], 'Going Medieval')
        self.assertEqual(result['igdb_slug'], 'going-medieval')
        self.assertEqual(result['igdb_url'], 'https://www.igdb.com/games/going-medieval')
        self.assertEqual(result['igdb_cover_hash'], 'hash001')
        self.assertEqual(result['summary'], 'A colony builder.')
        self.assertEqual(result['igdb_category'], 0)
        self.assertIsNone(result['first_release_date'])
        self.assertIsNone(result['multiplayer_max'])

    def test_parses_release_date(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X', 'first_release_date': 1609459200}  # 2021-01-01 UTC
        result = parse_igdb_game(data)
        from datetime import date
        self.assertEqual(result['first_release_date'], date(2021, 1, 1))

    def test_handles_missing_cover(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X'}
        result = parse_igdb_game(data)
        self.assertIsNone(result['igdb_cover_hash'])

    def test_handles_empty_slug(self):
        from eventer.igdb import parse_igdb_game
        data = {'id': 1, 'name': 'X', 'slug': ''}
        result = parse_igdb_game(data)
        self.assertIsNone(result['igdb_slug'])


class IGDBClientTest(TestCase):
    def test_credentials_configured_true_when_set(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='abc', IGDB_CLIENT_SECRET='def'):
            self.assertTrue(IGDBClient.credentials_configured())

    def test_credentials_configured_false_when_empty(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='', IGDB_CLIENT_SECRET=''):
            self.assertFalse(IGDBClient.credentials_configured())

    def test_credentials_configured_false_when_partial(self):
        from eventer.igdb import IGDBClient
        with self.settings(IGDB_CLIENT_ID='abc', IGDB_CLIENT_SECRET=''):
            self.assertFalse(IGDBClient.credentials_configured())

    def test_credentials_valid_returns_true_on_success(self):
        from unittest.mock import patch
        from eventer.igdb import IGDBClient
        client = IGDBClient()
        with patch.object(client, '_get_token', return_value='token'):
            self.assertTrue(client.credentials_valid())

    def test_credentials_valid_returns_false_on_401(self):
        from unittest.mock import patch
        from eventer.igdb import IGDBClient, IGDBError
        client = IGDBClient()
        with patch.object(client, '_get_token', side_effect=IGDBError('bad', status_code=401)):
            self.assertFalse(client.credentials_valid())

    def test_credentials_valid_returns_false_on_403(self):
        from unittest.mock import patch
        from eventer.igdb import IGDBClient, IGDBError
        client = IGDBClient()
        with patch.object(client, '_get_token', side_effect=IGDBError('forbidden', status_code=403)):
            self.assertFalse(client.credentials_valid())

    def test_credentials_valid_reraises_non_auth_errors(self):
        from unittest.mock import patch
        from eventer.igdb import IGDBClient, IGDBError
        client = IGDBClient()
        with patch.object(client, '_get_token', side_effect=IGDBError('timeout')):
            with self.assertRaises(IGDBError):
                client.credentials_valid()

    def test_rate_limit_retries_and_succeeds(self):
        from unittest.mock import patch, MagicMock
        from eventer.igdb import IGDBClient
        client = IGDBClient()
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.headers = {'Retry-After': '0'}
        success = MagicMock()
        success.status_code = 200
        success.ok = True
        success.json.return_value = [{'id': 1, 'name': 'X'}]
        with patch.object(client, '_get_token', return_value='token'), \
             patch.object(client, '_do_request', side_effect=[rate_limited, success]), \
             patch('eventer.igdb.time.sleep') as mock_sleep, \
             self.settings(IGDB_RATE_LIMIT_RETRIES=3, IGDB_RATE_LIMIT_RETRY_AFTER=1.0):
            result = client._request('games', 'fields id,name;')
        self.assertEqual(result, [{'id': 1, 'name': 'X'}])
        mock_sleep.assert_called_once_with(0.0)

    def test_rate_limit_raises_after_max_retries(self):
        from unittest.mock import patch, MagicMock
        from eventer.igdb import IGDBClient, IGDBError
        client = IGDBClient()
        rate_limited = MagicMock()
        rate_limited.status_code = 429
        rate_limited.ok = False
        rate_limited.headers = {'Retry-After': '0'}
        rate_limited.text = 'Too Many Requests'
        with patch.object(client, '_get_token', return_value='token'), \
             patch.object(client, '_do_request', return_value=rate_limited), \
             patch('eventer.igdb.time.sleep'), \
             self.settings(IGDB_RATE_LIMIT_RETRIES=2, IGDB_RATE_LIMIT_RETRY_AFTER=0):
            with self.assertRaises(IGDBError) as cm:
                client._request('games', 'fields id;')
        self.assertEqual(cm.exception.status_code, 429)


class SyncGameFromIgdbTest(TestCase):
    def _mock_data(self):
        return {
            'id': 9999,
            'name': 'Mock Game',
            'slug': 'mock-game',
            'url': 'https://www.igdb.com/games/mock-game',
            'summary': 'A mock game.',
            'cover': {'image_id': 'mockhash'},
            'category': 0,
            'first_release_date': 1609459200,
        }

    def test_creates_game(self):
        from unittest.mock import patch, MagicMock
        from eventer.igdb import sync_game_from_igdb, IGDBClient
        mock_client = MagicMock(spec=IGDBClient)
        mock_client.fetch_game.return_value = self._mock_data()
        with patch('eventer.igdb.IGDBClient', return_value=mock_client):
            game, created = sync_game_from_igdb(9999)
        self.assertTrue(created)
        self.assertEqual(game.name, 'Mock Game')
        self.assertEqual(game.igdb_id, 9999)
        self.assertEqual(game.igdb_cover_hash, 'mockhash')

    def test_updates_existing_game(self):
        from unittest.mock import patch, MagicMock
        from eventer.igdb import sync_game_from_igdb, IGDBClient
        from eventer.models import Game
        Game.objects.create(name='Old Name', igdb_id=9999)
        mock_client = MagicMock(spec=IGDBClient)
        mock_client.fetch_game.return_value = {**self._mock_data(), 'name': 'Updated Name'}
        with patch('eventer.igdb.IGDBClient', return_value=mock_client):
            game, created = sync_game_from_igdb(9999)
        self.assertFalse(created)
        self.assertEqual(game.name, 'Updated Name')

    def test_raises_on_not_found(self):
        from unittest.mock import patch, MagicMock
        from eventer.igdb import sync_game_from_igdb, IGDBClient
        mock_client = MagicMock(spec=IGDBClient)
        mock_client.fetch_game.return_value = None
        with patch('eventer.igdb.IGDBClient', return_value=mock_client):
            with self.assertRaises(ValueError):
                sync_game_from_igdb(9999)
