"""Tests for rewards and redemption system."""
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from rewards.models import Reward, RedemptionRequest


def make_user(email='r@r.com', username='rewarduser', efootball_id='EF_R', verified=True):
    user = User.objects.create_user(
        email=email, username=username, password='testpass123', efootball_id=efootball_id,
    )
    user.is_email_verified = verified
    user.save()
    return user


def make_reward(name='Test Reward', points=100, quantity=-1, active=True):
    return Reward.objects.create(
        name=name,
        description='A test reward',
        points_cost=points,
        quantity_available=quantity,
        is_active=active,
    )


class RewardModelTest(TestCase):
    def test_unlimited_reward_is_available(self):
        r = make_reward(quantity=-1)
        self.assertTrue(r.is_available)

    def test_inactive_reward_not_available(self):
        r = make_reward(active=False)
        self.assertFalse(r.is_available)

    def test_zero_quantity_not_available(self):
        r = make_reward(quantity=0)
        self.assertFalse(r.is_available)

    def test_decrement_quantity(self):
        r = make_reward(quantity=5)
        r.decrement_quantity()
        r.refresh_from_db()
        self.assertEqual(r.quantity_available, 4)

    def test_decrement_unlimited_no_change(self):
        r = make_reward(quantity=-1)
        r.decrement_quantity()
        r.refresh_from_db()
        self.assertEqual(r.quantity_available, -1)


class RedemptionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.user.profile.add_points(500, 'Initial')
        self.reward = make_reward(points=100)
        self.client.login(username='r@r.com', password='testpass123')

    def test_redeem_success(self):
        response = self.client.post(reverse('rewards:redeem', kwargs={'pk': self.reward.pk}))
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points_balance, 400)
        self.assertTrue(RedemptionRequest.objects.filter(user=self.user, reward=self.reward).exists())

    def test_redeem_insufficient_points(self):
        self.reward.points_cost = 1000
        self.reward.save()
        response = self.client.post(reverse('rewards:redeem', kwargs={'pk': self.reward.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(RedemptionRequest.objects.filter(user=self.user, reward=self.reward).exists())

    def test_redeem_unverified_email(self):
        user2 = make_user(email='unv@test.com', username='unvuser', efootball_id='EF_UNV', verified=False)
        user2.profile.add_points(500, 'Initial')
        client2 = Client()
        client2.login(username='unv@test.com', password='testpass123')
        response = client2.post(reverse('rewards:redeem', kwargs={'pk': self.reward.pk}))
        self.assertFalse(RedemptionRequest.objects.filter(user=user2).exists())

    def test_redeem_inactive_reward(self):
        inactive = make_reward(name='Inactive', active=False)
        response = self.client.post(reverse('rewards:redeem', kwargs={'pk': inactive.pk}))
        self.assertFalse(RedemptionRequest.objects.filter(user=self.user, reward=inactive).exists())

    def test_catalog_view(self):
        response = self.client.get(reverse('rewards:catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Reward')

    def test_my_redemptions_view(self):
        response = self.client.get(reverse('rewards:my_redemptions'))
        self.assertEqual(response.status_code, 200)
