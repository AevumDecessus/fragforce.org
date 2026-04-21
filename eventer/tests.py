from datetime import datetime, timezone as dt_timezone

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.cookie import CookieStorage
from django.test import RequestFactory, TestCase

from eventer.admin import EventAdmin, SUPERSTREAM_ROLES
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


class EnsureSuperstreamRolesActionTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = EventAdmin(Event, self.site)
        self.superuser = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.event = Event.objects.create(name='Test Event', slug='test-event', description='')

    def _make_request(self):
        request = self.factory.post('/')
        request.user = self.superuser
        request._messages = CookieStorage(request)
        return request

    def test_creates_all_roles_when_none_exist(self):
        self.admin.ensure_superstream_roles(self._make_request(), Event.objects.none())
        self.assertEqual(EventRole.objects.count(), len(SUPERSTREAM_ROLES))
        slugs = set(EventRole.objects.values_list('slug', flat=True))
        self.assertEqual(slugs, {r['slug'] for r in SUPERSTREAM_ROLES})

    def test_idempotent_when_roles_already_exist(self):
        for role in SUPERSTREAM_ROLES:
            EventRole.objects.create(name=role['name'], slug=role['slug'], description=role['description'])
        self.admin.ensure_superstream_roles(self._make_request(), Event.objects.none())
        self.assertEqual(EventRole.objects.count(), len(SUPERSTREAM_ROLES))

    def test_creates_only_missing_roles(self):
        EventRole.objects.create(name='Participant', slug='participant', description='')
        EventRole.objects.create(name='Streamer', slug='streamer', description='')
        self.admin.ensure_superstream_roles(self._make_request(), Event.objects.none())
        self.assertEqual(EventRole.objects.count(), len(SUPERSTREAM_ROLES))
