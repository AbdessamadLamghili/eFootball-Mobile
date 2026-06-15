from django.db import models
from django.conf import settings
from django.utils import timezone


class Mission(models.Model):
    # Special mission codes with built-in behavior
    CODE_INSTAGRAM = 'instagram_follow'
    CODE_PROFILE = 'complete_profile'
    CODE_STREAK_3 = 'consecutive_3_days'
    CODE_STREAK_7 = 'consecutive_7_days'
    CODE_INVITE = 'invite_friends'
    CODE_ALL = 'all_missions'
    CODE_CUSTOM = 'custom'

    MISSION_CODE_CHOICES = [
        (CODE_INSTAGRAM, 'Suivre Instagram officiel'),
        (CODE_PROFILE, 'Compléter le profil'),
        (CODE_STREAK_3, 'Visiter 3 jours consécutifs'),
        (CODE_STREAK_7, 'Visiter 7 jours consécutifs'),
        (CODE_INVITE, 'Inviter des amis'),
        (CODE_ALL, 'Toutes les missions terminées'),
        (CODE_CUSTOM, 'Mission personnalisée'),
    ]

    VALIDATION_AUTO = 'automatic'
    VALIDATION_MANUAL = 'manual'
    VALIDATION_CHOICES = [
        (VALIDATION_AUTO, 'Automatique'),
        (VALIDATION_MANUAL, 'Manuelle'),
    ]

    title = models.CharField(max_length=100, verbose_name='Titre')
    description = models.TextField(verbose_name='Description')
    reward_points = models.PositiveIntegerField(verbose_name='Points de récompense')
    mission_code = models.CharField(
        max_length=30, choices=MISSION_CODE_CHOICES, default=CODE_CUSTOM,
        verbose_name='Code de mission'
    )
    validation_type = models.CharField(
        max_length=20, choices=VALIDATION_CHOICES, default=VALIDATION_AUTO,
        verbose_name='Type de validation'
    )
    is_active = models.BooleanField(default=True, verbose_name='Active')
    link = models.URLField(
        blank=True, null=True,
        verbose_name='Lien externe',
        help_text='URL pour les missions externes (ex: page Instagram)'
    )
    max_monthly_completions = models.PositiveIntegerField(
        default=0,
        verbose_name='Max complétions/mois',
        help_text='0 = une seule fois (permanente)'
    )
    icon = models.CharField(max_length=50, default='trophy', verbose_name='Icône (Font Awesome)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mission'
        verbose_name_plural = 'Missions'
        ordering = ['mission_code', '-reward_points']

    def __str__(self):
        return self.title

    def is_completed_by(self, user):
        """Returns True if user has already completed this mission (and cannot complete again)."""
        qs = MissionCompletion.objects.filter(user=user, mission=self)

        if self.mission_code == self.CODE_INVITE:
            # Invite mission can be completed multiple times (per invitation)
            # but here we just check if at least one completion exists
            return False  # always show as available (repeatable)

        if self.max_monthly_completions > 0:
            now = timezone.now()
            count = qs.filter(
                completed_at__year=now.year,
                completed_at__month=now.month,
            ).count()
            return count >= self.max_monthly_completions

        return qs.exists()

    def get_pending_request(self, user):
        """Returns pending MissionRequest for this user if any."""
        return MissionRequest.objects.filter(
            user=user, mission=self, status=MissionRequest.STATUS_PENDING
        ).first()

    def has_pending_request(self, user):
        return self.get_pending_request(user) is not None

    @property
    def is_manual(self):
        return self.validation_type == self.VALIDATION_MANUAL

    @property
    def is_repeatable(self):
        return self.mission_code == self.CODE_INVITE or self.max_monthly_completions > 0


class MissionRequest(models.Model):
    """Manual validation request submitted by user for manual missions."""
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_APPROVED, 'Approuvée'),
        (STATUS_REJECTED, 'Refusée'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mission_requests'
    )
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, related_name='requests')
    instagram_username = models.CharField(max_length=100, blank=True, verbose_name='Nom d\'utilisateur Instagram')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    rejection_reason = models.TextField(blank=True, verbose_name='Raison du refus')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_mission_requests'
    )

    class Meta:
        verbose_name = 'Demande de mission'
        verbose_name_plural = 'Demandes de missions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.mission.title} ({self.get_status_display()})"


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
