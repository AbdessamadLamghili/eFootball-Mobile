import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class Reward(models.Model):
    CATEGORY_INGAME = 'ingame'
    CATEGORY_GIFT = 'gift'
    CATEGORY_PREMIUM = 'premium'
    CATEGORY_CHOICES = [
        (CATEGORY_INGAME, 'In-Game'),
        (CATEGORY_GIFT, 'Carte cadeau'),
        (CATEGORY_PREMIUM, 'Premium'),
    ]

    name = models.CharField(max_length=100, verbose_name='Nom')
    description = models.TextField(verbose_name='Description')
    image = models.ImageField(upload_to='rewards/', null=True, blank=True, verbose_name='Image')
    points_cost = models.PositiveIntegerField(verbose_name='Coût en points')
    quantity_available = models.IntegerField(
        default=-1, verbose_name='Quantité disponible',
        help_text='-1 = illimitée'
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_INGAME)
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Récompense'
        verbose_name_plural = 'Récompenses'
        ordering = ['points_cost']

    def __str__(self):
        return self.name

    @property
    def is_available(self):
        return self.is_active and (self.quantity_available == -1 or self.quantity_available > 0)

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return '/static/images/default-reward.png'

    def decrement_quantity(self):
        if self.quantity_available > 0:
            self.quantity_available -= 1
            self.save(update_fields=['quantity_available'])


class RedemptionRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_DELIVERED = 'delivered'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_ACCEPTED, 'Acceptée'),
        (STATUS_REJECTED, 'Refusée'),
        (STATUS_DELIVERED, 'Livrée'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='redemptions'
    )
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE, related_name='redemptions')
    points_spent = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_note = models.TextField(blank=True, verbose_name='Note admin')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Demande de récompense'
        verbose_name_plural = 'Demandes de récompenses'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.reward.name} ({self.get_status_display()})"


class RedemptionStatusHistory(models.Model):
    redemption = models.ForeignKey(RedemptionRequest, on_delete=models.CASCADE, related_name='history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='status_changes'
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historique statut demande'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.redemption} : {self.old_status} → {self.new_status}"


def generate_exchange_number():
    prefix = "EX"
    suffix = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{suffix}"


class ExchangeRequest(models.Model):
    """User request to exchange points for eFootball Coins."""
    STATUS_PENDING = 'pending'
    STATUS_VALIDATED = 'validated'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_VALIDATED, 'Validé'),
        (STATUS_REJECTED, 'Refusé'),
    ]

    EXCHANGE_RATE = 10        # 10 points = 1 coin
    MIN_EXCHANGE_POINTS = 1000  # minimum 1000 points per exchange

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exchange_requests'
    )
    request_number = models.CharField(max_length=20, unique=True, blank=True)
    points_used = models.PositiveIntegerField(verbose_name='Points utilisés')
    coins_requested = models.PositiveIntegerField(verbose_name='Coins demandés')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    rejection_reason = models.TextField(blank=True, verbose_name='Raison du refus')
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_exchanges'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Demande d\'échange'
        verbose_name_plural = 'Demandes d\'échange'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_number} — {self.user.username} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = generate_exchange_number()
        super().save(*args, **kwargs)

    @classmethod
    def calculate_coins(cls, points):
        return points // cls.EXCHANGE_RATE
