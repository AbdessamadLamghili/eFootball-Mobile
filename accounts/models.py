import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.conf import settings


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
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(unique=True)
    efootball_id = models.CharField(max_length=50, unique=True, verbose_name='eFootball ID')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'efootball_id']

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
    points_balance = models.PositiveIntegerField(default=0)
    total_points_earned = models.PositiveIntegerField(default=0)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_BRONZE)
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_daily_reward = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Profil utilisateur'
        verbose_name_plural = 'Profils utilisateurs'

    def __str__(self):
        return f"Profil de {self.user.username}"

    def add_points(self, points, reason=''):
        self.points_balance += points
        self.total_points_earned += points
        self.update_level()
        self.save()
        PointTransaction.objects.create(
            user=self.user,
            points=points,
            transaction_type=PointTransaction.TYPE_CREDIT,
            reason=reason,
            balance_after=self.points_balance,
        )

    def deduct_points(self, points, reason=''):
        if self.points_balance < points:
            raise ValueError('Solde de points insuffisant')
        self.points_balance -= points
        self.save()
        PointTransaction.objects.create(
            user=self.user,
            points=points,
            transaction_type=PointTransaction.TYPE_DEBIT,
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
        return '/static/images/default-avatar.png'


class PointTransaction(models.Model):
    TYPE_CREDIT = 'credit'
    TYPE_DEBIT = 'debit'
    TYPE_CHOICES = [
        (TYPE_CREDIT, 'Crédit'),
        (TYPE_DEBIT, 'Débit'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions')
    points = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
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
