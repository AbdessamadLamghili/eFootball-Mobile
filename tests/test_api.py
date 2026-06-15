"""API tests — JWT authentication and endpoints."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import User
from rewards.models import Reward
from missions.models import Mission
from notifications.models import Notification


def make_user(email='api@api.com', username='apiuser', efootball_id='EF_API', verified=True):
    user = User.objects.create_user(
        email=email, username=username, password='testpass123', efootball_id=efootball_id,
    )
    user.is_email_verified = verified
    user.save()
    return user


def get_tokens(client, email='api@api.com', password='testpass123'):
    response = client.post(reverse('api:token_obtain'), {'email': email, 'password': password})
    return response.data


class APIAuthTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()

    def test_obtain_token(self):
        response = self.client.post(reverse('api:token_obtain'), {
            'email': 'api@api.com',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_register_api(self):
        response = self.client.post(reverse('api:register'), {
            'email': 'newapi@api.com',
            'username': 'newapiuser',
            'efootball_id': 'EF_NEWAPI',
            'password': 'strongpass123',
            'confirm_password': 'strongpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='newapi@api.com').exists())

    def test_profile_requires_auth(self):
        response = self.client.get(reverse('api:profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_with_token(self):
        tokens = get_tokens(self.client)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.client.get(reverse('api:profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'apiuser')


class APIRewardsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        tokens = get_tokens(self.client)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.reward = Reward.objects.create(
            name='API Reward', description='Test', points_cost=50,
        )

    def test_list_rewards(self):
        response = self.client.get(reverse('api:reward_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['count'], 0)

    def test_reward_detail(self):
        response = self.client.get(reverse('api:reward_detail', kwargs={'pk': self.reward.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'API Reward')

    def test_redeem_reward_insufficient_points(self):
        response = self.client.post(reverse('api:redeem', kwargs={'pk': self.reward.pk}))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_redeem_reward_success(self):
        self.user.profile.add_points(200, 'Test')
        response = self.client.post(reverse('api:redeem', kwargs={'pk': self.reward.pk}))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points_balance, 150)


class APIMissionsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        tokens = get_tokens(self.client)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        Mission.objects.create(title='API Mission', description='Test', reward_points=20, mission_code=Mission.CODE_CUSTOM)

    def test_list_missions(self):
        response = self.client.get(reverse('api:mission_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['count'], 0)


class APINotificationsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        tokens = get_tokens(self.client)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        Notification.objects.create(
            user=self.user, title='Test Notif', message='Hello',
            notification_type=Notification.TYPE_INFO,
        )

    def test_list_notifications(self):
        response = self.client.get(reverse('api:notification_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['count'], 0)

    def test_mark_notification_read(self):
        notif = Notification.objects.filter(user=self.user).first()
        response = self.client.post(reverse('api:notification_read', kwargs={'pk': notif.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)


class APIDashboardTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        tokens = get_tokens(self.client)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_dashboard_summary(self):
        response = self.client.get(reverse('api:dashboard'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('points_balance', response.data)
        self.assertIn('level', response.data)
        self.assertIn('current_streak', response.data)
