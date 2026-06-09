from django.db import models
from django.conf import settings
from django.utils import timezone


class Mission(models.Model):
    TYPE_DAILY = 'daily'
    TYPE_WEEKLY = 'weekly'
    TYPE_PERMANENT = 'permanent'
    TYPE_CHOICES = [
        (TYPE_DAILY, 'Quotidienne'),
        (TYPE_WEEKLY, 'Hebdomadaire'),
        (TYPE_PERMANENT, 'Permanente'),
    ]

    title = models.CharField(max_length=100, verbose_name='Titre')
    description = models.TextField(verbose_name='Description')
    reward_points = models.PositiveIntegerField(verbose_name='Points de récompense')
    mission_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_PERMANENT)
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    icon = models.CharField(max_length=50, default='trophy', verbose_name='Icône (Font Awesome)')

    class Meta:
        verbose_name = 'Mission'
        verbose_name_plural = 'Missions'
        ordering = ['mission_type', '-reward_points']

    def __str__(self):
        return f"[{self.get_mission_type_display()}] {self.title}"

    def is_completed_by(self, user):
        from django.utils import timezone
        qs = MissionCompletion.objects.filter(user=user, mission=self)
        if self.mission_type == self.TYPE_DAILY:
            return qs.filter(completed_at__date=timezone.now().date()).exists()
        if self.mission_type == self.TYPE_WEEKLY:
            week_start = timezone.now().date() - timezone.timedelta(days=timezone.now().weekday())
            return qs.filter(completed_at__date__gte=week_start).exists()
        return qs.exists()


class MissionCompletion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mission_completions'
    )
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='completions')
    points_earned = models.PositiveIntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Complétion de mission'
        verbose_name_plural = 'Complétions de missions'
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.username} — {self.mission.title}"
