from django.db import models
from django.conf import settings


class ActivityLog(models.Model):
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_REGISTER = 'register'
    ACTION_EMAIL_VERIFIED = 'email_verified'
    ACTION_REWARD_REQUEST = 'reward_request'
    ACTION_REWARD_ACCEPTED = 'reward_accepted'
    ACTION_REWARD_REJECTED = 'reward_rejected'
    ACTION_MISSION_COMPLETE = 'mission_complete'
    ACTION_DAILY_REWARD = 'daily_reward'
    ACTION_ADMIN = 'admin'
    ACTION_PASSWORD_RESET = 'password_reset'

    ACTION_CHOICES = [
        (ACTION_LOGIN, 'Connexion'),
        (ACTION_LOGOUT, 'Déconnexion'),
        (ACTION_REGISTER, 'Inscription'),
        (ACTION_EMAIL_VERIFIED, 'Email vérifié'),
        (ACTION_REWARD_REQUEST, 'Demande récompense'),
        (ACTION_REWARD_ACCEPTED, 'Récompense acceptée'),
        (ACTION_REWARD_REJECTED, 'Récompense refusée'),
        (ACTION_MISSION_COMPLETE, 'Mission complétée'),
        (ACTION_DAILY_REWARD, 'Récompense quotidienne'),
        (ACTION_ADMIN, 'Action admin'),
        (ACTION_PASSWORD_RESET, 'Réinitialisation mot de passe'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Journal d\'activité'
        verbose_name_plural = 'Journaux d\'activité'
        ordering = ['-created_at']

    def __str__(self):
        username = self.user.username if self.user else 'Anonyme'
        return f"{username} — {self.get_action_display()} — {self.created_at}"
