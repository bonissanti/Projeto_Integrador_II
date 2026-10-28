from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class EnsureAdminCommandTests(TestCase):
    def test_creates_default_superuser(self):
        call_command("ensure_admin")

        user = get_user_model().objects.get(username="admin")
        self.assertEqual(user.email, "admin@example.com")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("12345"))

    def test_does_not_create_default_when_a_superuser_already_exists(self):
        User = get_user_model()
        existing = User.objects.create_superuser(
            username="tati",
            email="tati@example.com",
            password="unique-existing-password",
        )

        call_command("ensure_admin")

        self.assertEqual(User.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.username, "tati")
        self.assertTrue(existing.check_password("unique-existing-password"))

    def test_is_idempotent(self):
        call_command("ensure_admin")
        call_command("ensure_admin")

        self.assertEqual(get_user_model().objects.count(), 1)
