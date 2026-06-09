"""Unit and integration tests for the accounts app."""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta, date

from accounts.models import User, UserProfile, PointTransaction, DailyReward, EmailVerificationToken


class UserCreationTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='securepass123',
            efootball_id='EF_12345',
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertFalse(user.is_email_verified)
        self.assertFalse(user.check_password('wrongpass'))
        self.assertTrue(user.check_password('securepass123'))

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='adminpass123',
            efootball_id='EF_ADMIN',
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_email_verified)

    def test_profile_auto_created(self):
        user = User.objects.create_user(
            email='profile@example.com',
            username='profileuser',
            password='pass123456',
            efootball_id='EF_PROFILE',
        )
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.points_balance, 0)
        self.assertEqual(user.profile.level, UserProfile.LEVEL_BRONZE)

    def test_username_unique(self):
        User.objects.create_user(email='a@a.com', username='dupuser', password='pass123456', efootball_id='EF_1')
        with self.assertRaises(Exception):
            User.objects.create_user(email='b@b.com', username='dupuser', password='pass123456', efootball_id='EF_2')

    def test_efootball_id_unique(self):
        User.objects.create_user(email='c@c.com', username='u1', password='pass123456', efootball_id='SAME_ID')
        with self.assertRaises(Exception):
            User.objects.create_user(email='d@d.com', username='u2', password='pass123456', efootball_id='SAME_ID')


class PointSystemTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='points@example.com',
            username='pointsuser',
            password='pass123456',
            efootball_id='EF_POINTS',
        )
        self.user.is_email_verified = True
        self.user.save()
        self.profile = self.user.profile

    def test_add_points(self):
        self.profile.add_points(50, 'Test credit')
        self.assertEqual(self.profile.points_balance, 50)
        self.assertEqual(self.profile.total_points_earned, 50)
        tx = PointTransaction.objects.filter(user=self.user).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.points, 50)
        self.assertEqual(tx.transaction_type, PointTransaction.TYPE_CREDIT)

    def test_deduct_points(self):
        self.profile.add_points(100, 'Initial')
        self.profile.deduct_points(40, 'Purchase')
        self.assertEqual(self.profile.points_balance, 60)

    def test_deduct_insufficient_raises(self):
        with self.assertRaises(ValueError):
            self.profile.deduct_points(100, 'Overspend')

    def test_level_upgrade(self):
        self.profile.add_points(500, 'Level test')
        self.assertEqual(self.profile.level, UserProfile.LEVEL_SILVER)

    def test_level_gold(self):
        self.profile.add_points(1500, 'Level gold')
        self.assertEqual(self.profile.level, UserProfile.LEVEL_GOLD)


class LevelProgressTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='level@example.com', username='leveluser',
            password='pass123456', efootball_id='EF_LEVEL',
        )

    def test_bronze_level_info(self):
        info = self.user.profile.get_level_display_info()
        self.assertEqual(info['current'], 'bronze')
        self.assertEqual(info['next'], 'silver')
        self.assertGreaterEqual(info['progress'], 0)

    def test_diamond_no_next(self):
        self.user.profile.add_points(15000, 'Diamond')
        info = self.user.profile.get_level_display_info()
        self.assertEqual(info['current'], 'diamond')
        self.assertIsNone(info['next'])
        self.assertEqual(info['progress'], 100)


class AuthViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='auth@example.com',
            username='authuser',
            password='testpass123',
            efootball_id='EF_AUTH',
        )

    def test_register_page_loads(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newplayer',
            'email': 'new@example.com',
            'efootball_id': 'EF_NEW',
            'password': 'strongpass123',
            'confirm_password': 'strongpass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())

    def test_register_duplicate_email(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'another',
            'email': 'auth@example.com',
            'efootball_id': 'EF_OTHER',
            'password': 'strongpass123',
            'confirm_password': 'strongpass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'existe déjà')

    def test_login_with_email(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'auth@example.com',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_with_username(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'authuser',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, 302)

    def test_login_wrong_password(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'auth@example.com',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)


class EmailVerificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='verify@example.com',
            username='verifyuser',
            password='testpass123',
            efootball_id='EF_VERIFY',
        )

    def test_verify_email_valid_token(self):
        token = EmailVerificationToken.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        # Delete any existing token created by signal
        EmailVerificationToken.objects.filter(user=self.user).exclude(pk=token.pk).delete()
        response = self.client.get(reverse('accounts:verify_email', kwargs={'token': token.token}))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_verify_email_expired_token(self):
        token = EmailVerificationToken.objects.create(
            user=self.user,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        response = self.client.get(reverse('accounts:verify_email', kwargs={'token': token.token}))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)


class DailyRewardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='daily@example.com',
            username='dailyuser',
            password='testpass123',
            efootball_id='EF_DAILY',
        )
        self.user.is_email_verified = True
        self.user.save()
        self.client.login(username='daily@example.com', password='testpass123')

    def test_claim_daily_reward(self):
        response = self.client.post(reverse('accounts:claim_daily_reward'))
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points_balance, 10)
        self.assertTrue(DailyReward.objects.filter(user=self.user, date=date.today()).exists())

    def test_cannot_claim_twice(self):
        self.client.post(reverse('accounts:claim_daily_reward'))
        self.client.post(reverse('accounts:claim_daily_reward'))
        self.assertEqual(DailyReward.objects.filter(user=self.user, date=date.today()).count(), 1)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points_balance, 10)
