import uuid
import random
import string
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.conf import settings

DEFAULT_AVATARS = [f'/static/images/avatars/default_{i}.svg' for i in range(1, 11)]


def get_random_default_avatar():
    return random.choice(DEFAULT_AVATARS)


def generate_invitation_code():
    number = random.randint(1000, 9999)
    code = f"EFOOT-{number}"
    while UserProfile.objects.filter(invitation_code=code).exists():
        number = random.randint(1000, 9999)
        code = f"EFOOT-{number}"
    return code


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'email est obligatoire')
        if not username:
            raise ValueError('Le nom d\'utilisateur est obligatoire')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_email_verified', True)
        extra_fields.setdefault('is_email_confirmed', True)
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    efootball_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name='eFootball ID')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_email_confirmed = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-date_joined']

    def __str__(self):
        return self.username

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    @property
    def can_earn_points(self):
        return self.is_email_verified and not self.is_suspended

    @property
    def can_redeem(self):
        return self.is_email_verified and not self.is_suspended

    @property
    def is_profile_complete(self):
        return bool(
            self.efootball_id
            and hasattr(self, 'profile')
            and self.profile.avatar
        )


class UserProfile(models.Model):
    LEVEL_BRONZE = 'bronze'
    LEVEL_SILVER = 'silver'
    LEVEL_GOLD = 'gold'
    LEVEL_PLATINUM = 'platinum'
    LEVEL_DIAMOND = 'diamond'

    LEVEL_CHOICES = [
        (LEVEL_BRONZE, 'Bronze'),
        (LEVEL_SILVER, 'Argent'),
        (LEVEL_GOLD, 'Or'),
        (LEVEL_PLATINUM, 'Platine'),
        (LEVEL_DIAMOND, 'Diamant'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    default_avatar = models.CharField(max_length=60, blank=True, default='')
    phone_number = models.CharField(max_length=30, blank=True, verbose_name='Numéro de téléphone')
    points_balance = models.PositiveIntegerField(default=0)
    total_points_earned = models.PositiveIntegerField(default=0)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_BRONZE)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_daily_reward = models.DateField(null=True, blank=True)
    invitation_code = models.CharField(max_length=20, unique=True, blank=True)
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invited_users'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profil utilisateur'
        verbose_name_plural = 'Profils utilisateurs'

    def __str__(self):
        return f"Profil de {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.invitation_code:
            self.invitation_code = generate_invitation_code()
        if not self.default_avatar:
            self.default_avatar = get_random_default_avatar()
        super().save(*args, **kwargs)

    def add_points(self, points, reason='', transaction_category=None):
        self.points_balance += points
        self.total_points_earned += points
        self.update_level()
        self.save()
        PointTransaction.objects.create(
            user=self.user,
            points=points,
            transaction_type=PointTransaction.TYPE_CREDIT,
            category=transaction_category or PointTransaction.CAT_BONUS,
            reason=reason,
            balance_after=self.points_balance,
        )

    def deduct_points(self, points, reason='', transaction_category=None):
        if self.points_balance < points:
            raise ValueError('Solde de points insuffisant')
        self.points_balance -= points
        self.save()
        PointTransaction.objects.create(
            user=self.user,
            points=points,
            transaction_type=PointTransaction.TYPE_DEBIT,
            category=transaction_category or PointTransaction.CAT_EXCHANGE,
            reason=reason,
            balance_after=self.points_balance,
        )

    def update_level(self):
        levels = settings.USER_LEVELS
        if self.total_points_earned >= levels['diamond']:
            self.level = self.LEVEL_DIAMOND
        elif self.total_points_earned >= levels['platinum']:
            self.level = self.LEVEL_PLATINUM
        elif self.total_points_earned >= levels['gold']:
            self.level = self.LEVEL_GOLD
        elif self.total_points_earned >= levels['silver']:
            self.level = self.LEVEL_SILVER
        else:
            self.level = self.LEVEL_BRONZE

    def get_level_display_info(self):
        levels = settings.USER_LEVELS
        level_order = ['bronze', 'silver', 'gold', 'platinum', 'diamond']
        current_index = level_order.index(self.level)
        if current_index < len(level_order) - 1:
            next_level = level_order[current_index + 1]
            next_threshold = levels[next_level]
            current_threshold = levels[self.level]
            progress = ((self.total_points_earned - current_threshold) /
                        (next_threshold - current_threshold)) * 100
            return {
                'current': self.level,
                'next': next_level,
                'progress': min(int(progress), 100),
                'points_needed': max(next_threshold - self.total_points_earned, 0),
            }
        return {
            'current': self.level,
            'next': None,
            'progress': 100,
            'points_needed': 0,
        }

    @property
    def avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return self.default_avatar or get_random_default_avatar()

    def get_monthly_invitation_count(self):
        from django.utils import timezone
        now = timezone.now()
        return self.user.point_transactions.filter(
            category=PointTransaction.CAT_INVITATION,
            transaction_type=PointTransaction.TYPE_CREDIT,
            created_at__year=now.year,
            created_at__month=now.month,
        ).count()

    def can_earn_invitation_reward(self):
        return self.get_monthly_invitation_count() < getattr(settings, 'MAX_MONTHLY_INVITATIONS', 10)


class PointTransaction(models.Model):
    TYPE_CREDIT = 'credit'
    TYPE_DEBIT = 'debit'
    TYPE_CHOICES = [
        (TYPE_CREDIT, 'Crédit'),
        (TYPE_DEBIT, 'Débit'),
    ]

    CAT_DAILY = 'daily_login'
    CAT_MISSION = 'mission'
    CAT_INVITATION = 'invitation'
    CAT_BONUS = 'bonus'
    CAT_EXCHANGE = 'exchange'
    CAT_REFUND = 'refund'
    CAT_CORRECTION = 'correction'

    CATEGORY_CHOICES = [
        (CAT_DAILY, 'Connexion quotidienne'),
        (CAT_MISSION, 'Mission complétée'),
        (CAT_INVITATION, 'Invitation'),
        (CAT_BONUS, 'Bonus'),
        (CAT_EXCHANGE, 'Échange'),
        (CAT_REFUND, 'Remboursement'),
        (CAT_CORRECTION, 'Correction administrateur'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions')
    points = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CAT_BONUS)
    reason = models.CharField(max_length=255)
    balance_after = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Transaction de points'
        verbose_name_plural = 'Transactions de points'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.transaction_type == self.TYPE_CREDIT else '-'
        return f"{self.user.username}: {sign}{self.points} pts — {self.reason}"


class EmailVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_token')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = 'Token vérification email'

    def is_valid(self):
        return timezone.now() <= self.expires_at

    def __str__(self):
        return f"Token pour {self.user.username}"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Token réinitialisation mot de passe'

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.expires_at

    def __str__(self):
        return f"Reset token pour {self.user.username}"


class PasswordResetCode(models.Model):
    MAX_ATTEMPTS = 5

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_codes')
    code = models.CharField(max_length=6)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Code réinitialisation mot de passe'
        ordering = ['-created_at']

    def is_valid(self):
        return (
            not self.is_used
            and self.attempts < self.MAX_ATTEMPTS
            and timezone.now() <= self.expires_at
        )

    def increment_attempts(self):
        self.attempts += 1
        self.save(update_fields=['attempts'])

    def __str__(self):
        return f"Code reset pour {self.user.username}"


class EmailVerificationCode(models.Model):
    MAX_ATTEMPTS = 5

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verify_codes')
    code = models.CharField(max_length=6)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Code vérification email'
        ordering = ['-created_at']

    def is_valid(self):
        return (
            not self.is_used
            and self.attempts < self.MAX_ATTEMPTS
            and timezone.now() <= self.expires_at
        )

    def increment_attempts(self):
        self.attempts += 1
        self.save(update_fields=['attempts'])

    def __str__(self):
        return f"Code vérification email pour {self.user.username}"


class DailyReward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_rewards')
    date = models.DateField()
    points_earned = models.PositiveIntegerField()
    streak_day = models.PositiveIntegerField(default=1)
    bonus_points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Récompense quotidienne'
        verbose_name_plural = 'Récompenses quotidiennes'
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} — {self.date} (+{self.points_earned} pts)"


class AccountVerificationRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_CODE_ENTERED = 'code_entered'
    STATUS_VERIFIED = 'verified'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_CODE_ENTERED, 'Code soumis'),
        (STATUS_VERIFIED, 'Vérifié'),
        (STATUS_REJECTED, 'Refusé'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_requests')
    verification_code = models.CharField(max_length=20, blank=True)
    entered_code = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    method = models.CharField(max_length=20, blank=True)
    phone_snapshot = models.CharField(max_length=30, blank=True)
    code_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Demande de vérification'
        verbose_name_plural = 'Demandes de vérification'
        ordering = ['-created_at']

    def __str__(self):
        return f"Vérification de {self.user.username} ({self.get_status_display()})"

    def generate_code(self):
        self.verification_code = str(random.randint(100000, 999999))
        self.save(update_fields=['verification_code'])


class VerificationSettings(models.Model):
    METHOD_PHONE = 'phone'
    METHOD_ADMIN_CODE = 'admin_code'
    METHOD_SEND_CODE = 'send_code'
    METHOD_CHOICES = [
        ('phone',      'Option 1 — Numéro de téléphone (vérification manuelle)'),
        ('admin_code', "Option 2 — Code saisi par l'administrateur"),
        ('send_code',  "Option 3 — Envoi automatique du code à l'utilisateur"),
    ]

    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='admin_code',
                              verbose_name='Méthode de vérification')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='verification_settings_updates',
    )

    class Meta:
        verbose_name = 'Configuration de vérification'

    def __str__(self):
        return f"Méthode : {self.get_method_display()}"

    @classmethod
    def get_current(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'method': 'admin_code'})
        return obj
