"""Tests for missions system."""
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from missions.models import Mission, MissionCompletion


def make_user(email='m@m.com', username='muser', efootball_id=None):
    user = User.objects.create_user(
        email=email, username=username, password='testpass123', efootball_id=efootball_id,
    )
    user.is_email_verified = True
    user.save()
    return user


class MissionModelTest(TestCase):
    def setUp(self):
        self.user = make_user()
        self.mission = Mission.objects.create(
            title='Test Mission',
            description='Do something',
            reward_points=50,
            mission_code=Mission.CODE_CUSTOM,
        )

    def test_not_completed_initially(self):
        self.assertFalse(self.mission.is_completed_by(self.user))

    def test_completed_after_completion(self):
        MissionCompletion.objects.create(
            user=self.user,
            mission=self.mission,
            points_earned=50,
        )
        self.assertTrue(self.mission.is_completed_by(self.user))


class MissionViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user()
        self.client.login(username='m@m.com', password='testpass123')
        self.mission = Mission.objects.create(
            title='View Mission',
            description='Complete me',
            reward_points=30,
            mission_code=Mission.CODE_CUSTOM,
            validation_type=Mission.VALIDATION_AUTO,
        )

    def test_mission_list_view(self):
        response = self.client.get(reverse('missions:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'View Mission')

    def test_submit_auto_mission(self):
        response = self.client.post(reverse('missions:submit', kwargs={'pk': self.mission.pk}))
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points_balance, 30)
        self.assertTrue(MissionCompletion.objects.filter(user=self.user, mission=self.mission).exists())

    def test_cannot_complete_twice(self):
        self.client.post(reverse('missions:submit', kwargs={'pk': self.mission.pk}))
        self.client.post(reverse('missions:submit', kwargs={'pk': self.mission.pk}))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points_balance, 30)
