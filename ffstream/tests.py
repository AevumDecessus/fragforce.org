from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ffstream.models import Key


class MyKeysViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streamer', password='pass')
        self.other_user = User.objects.create_user(username='other', password='pass')
        self.key = Key.objects.create(id='secret-key-1', name='streamer', owner=self.user)
        self.other_key = Key.objects.create(id='secret-key-2', name='other', owner=self.other_user)

    def test_redirects_unauthenticated_users(self):
        response = self.client.get(reverse('my-keys'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/discord/', response['Location'])

    def test_shows_own_keys(self):
        self.client.login(username='streamer', password='pass')
        response = self.client.get(reverse('my-keys'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'secret-key-1')

    def test_does_not_show_other_users_keys(self):
        self.client.login(username='streamer', password='pass')
        response = self.client.get(reverse('my-keys'))
        self.assertNotContains(response, 'secret-key-2')

    def test_shows_empty_state_when_no_keys(self):
        User.objects.create_user(username='nokeys', password='pass')
        self.client.login(username='nokeys', password='pass')
        response = self.client.get(reverse('my-keys'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "don't have any stream keys")


class LogoutViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='streamer', password='pass')

    def test_logout_redirects_to_home(self):
        self.client.login(username='streamer', password='pass')
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, '/')

    def test_logout_ends_session(self):
        self.client.login(username='streamer', password='pass')
        self.client.get(reverse('logout'))
        response = self.client.get(reverse('my-keys'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/discord/', response['Location'])
