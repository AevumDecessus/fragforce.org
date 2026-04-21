from datetime import datetime, timezone as dt_timezone

from django.contrib.auth.models import User
from django.test import TestCase

from eventer.admin import SUPERSTREAM_ROLES
from eventer.models import Event, EventPeriod, EventRole


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
        self.assertRedirects(response, f'/admin/eventer/event/{self.event.pk}/change/', fetch_redirect_response=False)
        self.assertEqual(EventPeriod.objects.filter(event=self.event).count(), 1)
        period = EventPeriod.objects.get(event=self.event)
        self.assertEqual(period.start.hour, 12)  # 8am EDT (UTC-4) = 12:00 UTC

    def test_post_creates_event_period_est(self):
        # January 10 2025 is in EST (UTC-5) - 8am EST = 13:00 UTC
        response = self.client.post(self._url(), {
            'start': '2025-01-10T08:00',
            'duration': '40',
        })
        self.assertRedirects(response, f'/admin/eventer/event/{self.event.pk}/change/', fetch_redirect_response=False)
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
        self.assertRedirects(response, f'/admin/eventer/event/{pacific_event.pk}/change/', fetch_redirect_response=False)
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
        self.assertRedirects(response, f'/admin/eventer/event/{utc_event.pk}/change/', fetch_redirect_response=False)
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
        from datetime import datetime, timezone as dt_timezone, timedelta
        start = datetime(2025, 4, 4, 12, 0, tzinfo=dt_timezone.utc)
        EventPeriod.objects.create(event=self.event, start=start, stop=start + timedelta(hours=40))
        response = self.client.get(self._url())
        self.assertContains(response, 'already has 1 period')
