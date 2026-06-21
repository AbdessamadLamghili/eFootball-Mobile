from django.db import models
from django.db.models import F
from django.conf import settings
from django.utils import timezone


class League(models.Model):
    STATUS_SETUP = 'setup'
    STATUS_ACTIVE = 'active'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_SETUP, 'Configuration'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CLOSED, 'Terminée'),
    ]

    name = models.CharField(max_length=200, verbose_name='Nom')
    description = models.TextField(blank=True, verbose_name='Description')
    rules = models.TextField(blank=True, verbose_name='Règlement')
    season = models.CharField(max_length=50, blank=True, verbose_name='Saison')
    logo = models.ImageField(upload_to='leagues/logos/', null=True, blank=True, verbose_name='Logo')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_leagues',
        verbose_name='Créé par',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_SETUP, verbose_name='Statut'
    )
    two_legs = models.BooleanField(default=False, verbose_name='Aller-retour (2 manches)')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Démarrée le')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='Terminée le')
    champion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='league_championships',
        verbose_name='Champion',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ligue'
        verbose_name_plural = 'Ligues'

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def is_setup(self):
        return self.status == self.STATUS_SETUP

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE

    @property
    def is_closed(self):
        return self.status == self.STATUS_CLOSED

    def get_status_badge_class(self):
        return {
            self.STATUS_SETUP: 'badge-warning',
            self.STATUS_ACTIVE: 'badge-success',
            self.STATUS_CLOSED: 'badge-secondary',
        }.get(self.status, 'badge-secondary')

    def get_standings_ordered(self):
        return self.standings.select_related('participant__user').annotate(
            goal_diff=F('goals_for') - F('goals_against')
        ).order_by(
            '-points', '-goal_diff', '-goals_for', 'participant__team_name'
        )

    def check_and_close(self):
        """Auto-close the league when all matches are validated."""
        has_open = self.matches.filter(
            status__in=[Match.STATUS_PENDING, Match.STATUS_SUBMITTED, Match.STATUS_REJECTED]
        ).exists()
        if not has_open and self.matches.exists():
            self._close_league()

    def _close_league(self):
        standings = self.get_standings_ordered()
        if standings.exists():
            self.champion = standings.first().participant.user
        self.status = self.STATUS_CLOSED
        self.ended_at = timezone.now()
        self.save()
        LeagueLog.objects.create(
            league=self,
            action=LeagueLog.ACTION_CLOSED,
            description=(
                f"Ligue clôturée automatiquement. "
                f"Champion : {self.champion.username if self.champion else 'N/A'}"
            ),
        )


class LeagueParticipant(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='league_participations',
    )
    team_name = models.CharField(max_length=100, verbose_name="Nom de l'équipe")
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='added_league_participants',
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['league', 'user']]
        verbose_name = 'Participant'
        verbose_name_plural = 'Participants'

    def __str__(self):
        return f"{self.user.username} ({self.team_name})"


class Match(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_SUBMITTED = 'submitted'
    STATUS_VALIDATED = 'validated'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_SUBMITTED, 'Soumis'),
        (STATUS_VALIDATED, 'Validé'),
        (STATUS_REJECTED, 'Rejeté'),
    ]

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='matches')
    home_participant = models.ForeignKey(
        LeagueParticipant, on_delete=models.CASCADE, related_name='home_matches'
    )
    away_participant = models.ForeignKey(
        LeagueParticipant, on_delete=models.CASCADE, related_name='away_matches'
    )
    round_number = models.PositiveIntegerField(verbose_name='Journée')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    home_score = models.PositiveIntegerField(null=True, blank=True)
    away_score = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['round_number', 'id']
        verbose_name = 'Match'
        verbose_name_plural = 'Matchs'

    def __str__(self):
        return (
            f"J{self.round_number}: {self.home_participant.team_name} "
            f"vs {self.away_participant.team_name}"
        )

    def get_status_badge_class(self):
        return {
            self.STATUS_PENDING: 'badge-secondary',
            self.STATUS_SUBMITTED: 'badge-warning',
            self.STATUS_VALIDATED: 'badge-success',
            self.STATUS_REJECTED: 'badge-danger',
        }.get(self.status, 'badge-secondary')

    def is_participant(self, user):
        return (
            self.home_participant.user_id == user.pk
            or self.away_participant.user_id == user.pk
        )

    def can_submit(self, user):
        return (
            self.status in (self.STATUS_PENDING, self.STATUS_REJECTED)
            and self.is_participant(user)
        )

    @property
    def result_or_none(self):
        try:
            return self.result
        except MatchResult.DoesNotExist:
            return None


class MatchResult(models.Model):
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='result')
    home_score = models.PositiveIntegerField()
    away_score = models.PositiveIntegerField()
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_match_results',
    )
    screenshot = models.ImageField(upload_to='leagues/screenshots/', null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='validated_match_results',
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    # Second player's version (challenger submission)
    challenger_home_score = models.IntegerField(null=True, blank=True)
    challenger_away_score = models.IntegerField(null=True, blank=True)
    challenger_submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='challenger_match_results',
    )
    challenger_screenshot = models.ImageField(upload_to='leagues/screenshots/', null=True, blank=True)

    class Meta:
        verbose_name = 'Résultat'
        verbose_name_plural = 'Résultats'

    def __str__(self):
        return f"{self.match} → {self.home_score}–{self.away_score}"


class LeagueStanding(models.Model):
    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='standings')
    participant = models.OneToOneField(
        LeagueParticipant, on_delete=models.CASCADE, related_name='standing'
    )
    played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    goals_for = models.PositiveIntegerField(default=0)
    goals_against = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Classement'
        verbose_name_plural = 'Classements'

    @property
    def goal_difference(self):
        return self.goals_for - self.goals_against

    def __str__(self):
        return f"{self.participant} — {self.points} pts"


class LeagueLog(models.Model):
    ACTION_CREATED = 'league_created'
    ACTION_PARTICIPANT_ADDED = 'participant_added'
    ACTION_PARTICIPANT_REMOVED = 'participant_removed'
    ACTION_STARTED = 'league_started'
    ACTION_RESULT_SUBMITTED = 'result_submitted'
    ACTION_RESULT_VALIDATED = 'result_validated'
    ACTION_RESULT_REJECTED = 'result_rejected'
    ACTION_CLOSED = 'league_closed'

    ACTION_CHOICES = [
        (ACTION_CREATED, 'Ligue créée'),
        (ACTION_PARTICIPANT_ADDED, 'Participant ajouté'),
        (ACTION_PARTICIPANT_REMOVED, 'Participant supprimé'),
        (ACTION_STARTED, 'Ligue démarrée'),
        (ACTION_RESULT_SUBMITTED, 'Résultat soumis'),
        (ACTION_RESULT_VALIDATED, 'Résultat validé'),
        (ACTION_RESULT_REJECTED, 'Résultat rejeté'),
        (ACTION_CLOSED, 'Ligue clôturée'),
    ]

    ACTION_ICONS = {
        ACTION_CREATED: 'fa-plus-circle',
        ACTION_PARTICIPANT_ADDED: 'fa-user-plus',
        ACTION_PARTICIPANT_REMOVED: 'fa-user-minus',
        ACTION_STARTED: 'fa-play-circle',
        ACTION_RESULT_SUBMITTED: 'fa-upload',
        ACTION_RESULT_VALIDATED: 'fa-check-circle',
        ACTION_RESULT_REJECTED: 'fa-times-circle',
        ACTION_CLOSED: 'fa-trophy',
    }

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='league_log_actions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Journal'
        verbose_name_plural = 'Journal des ligues'

    def __str__(self):
        return f"[{self.league.name}] {self.get_action_display()}"

    def get_icon(self):
        return self.ACTION_ICONS.get(self.action, 'fa-info-circle')
