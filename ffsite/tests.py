from django.test import TestCase
from django.urls import reverse


class LoginErrorViewTest(TestCase):
    def test_returns_200(self):
        response = self.client.get(reverse('login-error'))
        self.assertEqual(response.status_code, 200)

    def test_contains_discord_invite_link(self):
        response = self.client.get(reverse('login-error'))
        self.assertContains(response, 'discord.gg/fragforce')
