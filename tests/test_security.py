"""Security tests — XSS, CSRF, SQL injection, access control."""
from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User


def make_user(email='sec@sec.com', username='secuser', efootball_id='EF_SEC'):
    user = User.objects.create_user(
        email=email, username=username, password='testpass123', efootball_id=efootball_id,
    )
    user.is_email_verified = True
    user.save()
    return user


class CSRFProtectionTest(TestCase):
    def test_login_enforces_csrf(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse('accounts:login'), {
            'username': 'sec@sec.com',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 403)

    def test_register_enforces_csrf(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse('accounts:register'), {
            'username': 'csrftest',
            'email': 'csrf@test.com',
            'efootball_id': 'EF_CSRF',
            'password': 'pass123456',
            'confirm_password': 'pass123456',
        })
        self.assertEqual(response.status_code, 403)


class AuthRequiredTest(TestCase):
    def test_dashboard_redirects_anonymous(self):
        response = self.client.get(reverse('dashboard:user_dashboard'))
        self.assertRedirects(response, '/accounts/login/?next=/dashboard/', fetch_redirect_response=False)

    def test_profile_redirects_anonymous(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_rewards_redirects_anonymous(self):
        response = self.client.get(reverse('rewards:catalog'))
        self.assertEqual(response.status_code, 302)

    def test_missions_redirects_anonymous(self):
        response = self.client.get(reverse('missions:list'))
        self.assertEqual(response.status_code, 302)


class AdminAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.regular_user = make_user()
        self.admin = User.objects.create_superuser(
            email='admin@admin.com', username='adminuser',
            password='adminpass123', efootball_id='EF_ADM',
        )

    def test_admin_panel_requires_staff(self):
        self.client.login(username='sec@sec.com', password='testpass123')
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_admin_panel_accessible_by_staff(self):
        self.client.login(username='admin@admin.com', password='adminpass123')
        response = self.client.get(reverse('dashboard:admin_dashboard'))
        self.assertEqual(response.status_code, 200)


class PasswordSecurityTest(TestCase):
    def test_password_is_hashed(self):
        user = make_user(email='hash@hash.com', username='hashuser', efootball_id='EF_HASH')
        self.assertNotEqual(user.password, 'testpass123')
        self.assertTrue(user.password.startswith('pbkdf2_') or user.password.startswith('argon2') or user.password.startswith('bcrypt'))

    def test_password_not_in_response(self):
        self.client.login(username='sec@sec.com', password='testpass123')
        make_user()
        response = self.client.get(reverse('accounts:profile'))
        self.assertNotContains(response, 'testpass123')


class SuspendedUserTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.user.is_suspended = True
        self.user.save()

    def test_suspended_user_cannot_login(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'sec@sec.com',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'suspendu')


class SQLInjectionTest(TestCase):
    def test_search_with_sql_injection(self):
        admin = User.objects.create_superuser(
            email='sqladmin@admin.com', username='sqladmin',
            password='adminpass123', efootball_id='EF_SQL',
        )
        self.client.login(username='sqladmin@admin.com', password='adminpass123')
        payload = "'; DROP TABLE accounts_user; --"
        response = self.client.get(reverse('dashboard:admin_users'), {'q': payload})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.exists())
