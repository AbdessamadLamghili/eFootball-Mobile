from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_INFO = 'info'
    TYPE_SUCCESS = 'success'
    TYPE_ERROR = 'error'
    TYPE_WARNING = 'warning'
    TYPE_POINTS = 'points'

    TYPE_CHOICES = [
        (TYPE_INFO, 'Info'),
        (TYPE_SUCCESS, 'Succès'),
        (TYPE_ERROR, 'Erreur'),
        (TYPE_WARNING, 'Avertissement'),
        (TYPE_POINTS, 'Points'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=100)
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_INFO)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.title}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])

    @property
    def icon(self):
        icons = {
            self.TYPE_INFO: 'info-circle',
            self.TYPE_SUCCESS: 'check-circle',
            self.TYPE_ERROR: 'times-circle',
            self.TYPE_WARNING: 'exclamation-triangle',
            self.TYPE_POINTS: 'star',
        }
        return icons.get(self.notification_type, 'bell')
