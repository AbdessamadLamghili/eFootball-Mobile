from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification

from .forms import AddParticipantForm, LeagueCreateForm, MatchResultForm, RejectResultForm
from .models import League, LeagueLog, LeagueParticipant, LeagueStanding, Match, MatchResult
from .utils import generate_round_robin


def staff_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, "Accès réservé aux administrateurs.")
            return redirect('leagues:league_list')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def league_list(request):
    leagues = League.objects.prefetch_related('participants').all()
    user_league_ids = set(
        LeagueParticipant.objects.filter(user=request.user).values_list('league_id', flat=True)
    )

    context = {
        'leagues': leagues,
        'user_league_ids': user_league_ids,
        'active_count': leagues.filter(status=League.STATUS_ACTIVE).count(),
        'setup_count': leagues.filter(status=League.STATUS_SETUP).count(),
        'closed_count': leagues.filter(status=League.STATUS_CLOSED).count(),
    }
    return render(request, 'leagues/league_list.html', context)


@staff_required
def league_create(request):
    if request.method == 'POST':
        form = LeagueCreateForm(request.POST, request.FILES)
        if form.is_valid():
            league = form.save(commit=False)
            league.created_by = request.user
            league.save()
            LeagueLog.objects.create(
                league=league,
                action=LeagueLog.ACTION_CREATED,
                description=f"Ligue « {league.name} » créée par {request.user.username}.",
                performed_by=request.user,
            )
            messages.success(request, f"Ligue « {league.name} » créée avec succès.")
            return redirect('leagues:league_detail', pk=league.pk)
    else:
        form = LeagueCreateForm()
    return render(request, 'leagues/league_create.html', {'form': form})


@login_required
def league_detail(request, pk):
    league = get_object_or_404(League, pk=pk)

    is_participant = league.participants.filter(user=request.user).exists()

    # Standings + forme (5 derniers résultats par participant)
    standings_list = list(league.get_standings_ordered())
    form_data = {}
    if league.is_active or league.is_closed:
        for m in league.matches.filter(status=Match.STATUS_VALIDATED).order_by('id'):
            h, a = m.home_participant_id, m.away_participant_id
            if m.home_score > m.away_score:
                form_data.setdefault(h, []).append('W')
                form_data.setdefault(a, []).append('L')
            elif m.home_score < m.away_score:
                form_data.setdefault(h, []).append('L')
                form_data.setdefault(a, []).append('W')
            else:
                form_data.setdefault(h, []).append('D')
                form_data.setdefault(a, []).append('D')
    for s in standings_list:
        s.form = form_data.get(s.participant_id, [])[-5:]

    matches_qs = league.matches.select_related(
        'home_participant__user', 'away_participant__user'
    ).prefetch_related('result')
    matches_by_round = {}
    for match in matches_qs:
        matches_by_round.setdefault(match.round_number, []).append(match)
    matches_by_round = dict(sorted(matches_by_round.items()))

    total_matches = league.matches.count()
    validated_count = league.matches.filter(status=Match.STATUS_VALIDATED).count()

    participants = league.participants.select_related('user', 'standing').all()

    user_participant = participants.filter(user=request.user).first()

    # Prochain match du joueur courant
    next_match = None
    if user_participant:
        next_match = league.matches.filter(
            status__in=[Match.STATUS_PENDING, Match.STATUS_REJECTED],
        ).filter(
            Q(home_participant=user_participant) | Q(away_participant=user_participant)
        ).select_related('home_participant__user', 'away_participant__user').first()

    pending_results = None
    if request.user.is_staff:
        pending_results = list(
            league.matches.filter(status=Match.STATUS_SUBMITTED).select_related(
                'home_participant__user',
                'away_participant__user',
                'result__submitted_by',
            )
        )

    add_form = AddParticipantForm(league) if (request.user.is_staff and league.is_setup) else None

    logs = league.logs.select_related('performed_by').all()[:100] if request.user.is_staff else []

    context = {
        'league': league,
        'standings': standings_list,
        'matches_by_round': matches_by_round,
        'total_matches': total_matches,
        'validated_count': validated_count,
        'participants': participants,
        'is_participant': is_participant,
        'user_participant': user_participant,
        'next_match': next_match,
        'pending_results': pending_results,
        'pending_count': len(pending_results) if pending_results else 0,
        'add_form': add_form,
        'logs': logs,
    }
    return render(request, 'leagues/league_detail.html', context)


@staff_required
def league_add_participant(request, pk):
    league = get_object_or_404(League, pk=pk)

    if not league.is_setup:
        messages.error(request, "Impossible d'ajouter des participants : la ligue est déjà démarrée.")
        return redirect('leagues:league_detail', pk=pk)

    form = AddParticipantForm(league, request.POST)
    if form.is_valid():
        user = form.cleaned_data['user']
        team_name = form.cleaned_data['team_name']
        participant = LeagueParticipant.objects.create(
            league=league,
            user=user,
            team_name=team_name,
            added_by=request.user,
        )
        LeagueStanding.objects.create(league=league, participant=participant)
        LeagueLog.objects.create(
            league=league,
            action=LeagueLog.ACTION_PARTICIPANT_ADDED,
            description=f"{user.username} ({team_name}) ajouté par {request.user.username}.",
            performed_by=request.user,
        )
        messages.success(request, f"{user.username} ajouté à la ligue.")
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)

    return redirect(reverse('leagues:league_detail', kwargs={'pk': pk}) + '?tab=participants')


@staff_required
def league_remove_participant(request, pk, participant_pk):
    league = get_object_or_404(League, pk=pk)
    participant = get_object_or_404(LeagueParticipant, pk=participant_pk, league=league)

    if not league.is_setup:
        messages.error(request, "Impossible de supprimer : la ligue est déjà démarrée.")
        return redirect('leagues:league_detail', pk=pk)

    username = participant.user.username
    team_name = participant.team_name
    participant.delete()

    LeagueLog.objects.create(
        league=league,
        action=LeagueLog.ACTION_PARTICIPANT_REMOVED,
        description=f"{username} ({team_name}) retiré par {request.user.username}.",
        performed_by=request.user,
    )
    messages.success(request, f"{username} retiré de la ligue.")
    return redirect(reverse('leagues:league_detail', kwargs={'pk': pk}) + '?tab=participants')


@staff_required
@transaction.atomic
def league_start(request, pk):
    league = get_object_or_404(League, pk=pk)

    if not league.is_setup:
        messages.error(request, "La ligue est déjà démarrée ou terminée.")
        return redirect('leagues:league_detail', pk=pk)

    participants = list(league.participants.all())
    if len(participants) < 2:
        messages.error(request, "Il faut au moins 2 participants pour démarrer la ligue.")
        return redirect('leagues:league_detail', pk=pk)

    rounds = generate_round_robin(participants, two_legs=league.two_legs)
    for round_num, round_matches in enumerate(rounds, start=1):
        for home, away in round_matches:
            Match.objects.create(
                league=league,
                home_participant=home,
                away_participant=away,
                round_number=round_num,
            )

    league.status = League.STATUS_ACTIVE
    league.started_at = timezone.now()
    league.save()

    total_matches = sum(len(r) for r in rounds)
    LeagueLog.objects.create(
        league=league,
        action=LeagueLog.ACTION_STARTED,
        description=(
            f"Ligue démarrée par {request.user.username}. "
            f"{len(participants)} participants, {len(rounds)} journées, "
            f"{total_matches} matchs générés."
        ),
        performed_by=request.user,
    )
    messages.success(request, f"Ligue démarrée ! {total_matches} matchs ont été générés.")
    return redirect('leagues:league_detail', pk=pk)


@login_required
def match_submit_result(request, pk, match_pk):
    league = get_object_or_404(League, pk=pk)
    match = get_object_or_404(Match, pk=match_pk, league=league)

    if not match.can_submit(request.user):
        messages.error(request, "Vous ne pouvez pas soumettre un résultat pour ce match.")
        return redirect('leagues:league_detail', pk=pk)

    if request.method == 'POST':
        form = MatchResultForm(request.POST, request.FILES)
        if form.is_valid():
            MatchResult.objects.filter(match=match).delete()

            result = form.save(commit=False)
            result.match = match
            result.submitted_by = request.user
            result.save()

            match.status = Match.STATUS_SUBMITTED
            match.save()

            LeagueLog.objects.create(
                league=league,
                action=LeagueLog.ACTION_RESULT_SUBMITTED,
                description=(
                    f"Résultat soumis par {request.user.username} : "
                    f"{match.home_participant.team_name} {result.home_score}–{result.away_score} "
                    f"{match.away_participant.team_name} (J{match.round_number})."
                ),
                performed_by=request.user,
            )
            messages.success(request, "Résultat soumis. En attente de validation par l'administrateur.")
            _notify_staff_result_submitted(match, request.user)
            return redirect('leagues:league_detail', pk=pk)
    else:
        form = MatchResultForm()

    return render(request, 'leagues/match_submit.html', {
        'league': league,
        'match': match,
        'form': form,
    })


@staff_required
@transaction.atomic
def match_validate(request, pk, match_pk):
    league = get_object_or_404(League, pk=pk)
    match = get_object_or_404(Match, pk=match_pk, league=league, status=Match.STATUS_SUBMITTED)
    result = get_object_or_404(MatchResult, match=match)

    result.validated_by = request.user
    result.validated_at = timezone.now()
    result.save()

    match.status = Match.STATUS_VALIDATED
    match.home_score = result.home_score
    match.away_score = result.away_score
    match.save()

    _update_standings(match, result.home_score, result.away_score)

    LeagueLog.objects.create(
        league=league,
        action=LeagueLog.ACTION_RESULT_VALIDATED,
        description=(
            f"Résultat validé par {request.user.username} : "
            f"{match.home_participant.team_name} {result.home_score}–{result.away_score} "
            f"{match.away_participant.team_name} (J{match.round_number})."
        ),
        performed_by=request.user,
    )

    # Refresh league to check closure
    league.refresh_from_db()
    league.check_and_close()

    _notify_result_validated(match, result)

    if league.is_closed:
        messages.success(request, "Résultat validé. La ligue est maintenant terminée !")
    else:
        messages.success(request, "Résultat validé et classement mis à jour.")

    return redirect(reverse('leagues:league_detail', kwargs={'pk': pk}) + '?tab=results')


@staff_required
def match_reject(request, pk, match_pk):
    league = get_object_or_404(League, pk=pk)
    match = get_object_or_404(Match, pk=match_pk, league=league, status=Match.STATUS_SUBMITTED)

    form = RejectResultForm(request.POST)
    if form.is_valid():
        reason = form.cleaned_data['rejection_reason']
        result = get_object_or_404(MatchResult, match=match)
        result.rejection_reason = reason
        result.save()

        match.status = Match.STATUS_REJECTED
        match.save()

        LeagueLog.objects.create(
            league=league,
            action=LeagueLog.ACTION_RESULT_REJECTED,
            description=(
                f"Résultat refusé par {request.user.username} : "
                f"{match.home_participant.team_name} vs {match.away_participant.team_name} "
                f"(J{match.round_number}). Motif : {reason}"
            ),
            performed_by=request.user,
        )
        _notify_result_rejected(match, result, reason)
        messages.warning(request, "Résultat refusé. Le joueur devra soumettre à nouveau.")
    else:
        messages.error(request, "Veuillez indiquer le motif du refus.")

    return redirect(reverse('leagues:league_detail', kwargs={'pk': pk}) + '?tab=results')


def _update_standings(match, home_score, away_score):
    home_st, _ = LeagueStanding.objects.get_or_create(
        participant=match.home_participant,
        defaults={'league': match.league},
    )
    away_st, _ = LeagueStanding.objects.get_or_create(
        participant=match.away_participant,
        defaults={'league': match.league},
    )

    home_st.played += 1
    away_st.played += 1
    home_st.goals_for += home_score
    home_st.goals_against += away_score
    away_st.goals_for += away_score
    away_st.goals_against += home_score

    if home_score > away_score:
        home_st.wins += 1
        home_st.points += 3
        away_st.losses += 1
    elif home_score < away_score:
        away_st.wins += 1
        away_st.points += 3
        home_st.losses += 1
    else:
        home_st.draws += 1
        home_st.points += 1
        away_st.draws += 1
        away_st.points += 1

    home_st.save()
    away_st.save()


def _notify_staff_result_submitted(match, submitter):
    User = get_user_model()
    staff_users = list(User.objects.filter(is_staff=True, is_active=True))
    if staff_users:
        Notification.objects.bulk_create([
            Notification(
                user=su,
                title="Résultat soumis",
                message=(
                    f"{submitter.username} a soumis un résultat : "
                    f"{match.home_participant.team_name} vs {match.away_participant.team_name} "
                    f"— Journée {match.round_number} ({match.league.name})."
                ),
                notification_type=Notification.TYPE_WARNING,
            )
            for su in staff_users
        ])


def _notify_result_validated(match, result):
    submitter = result.submitted_by
    score = f"{result.home_score}–{result.away_score}"
    Notification.objects.create(
        user=submitter,
        title="Résultat validé ✓",
        message=(
            f"Résultat validé : {match.home_participant.team_name} {score} "
            f"{match.away_participant.team_name} (Journée {match.round_number})."
        ),
        notification_type=Notification.TYPE_SUCCESS,
    )
    home_user = match.home_participant.user
    away_user = match.away_participant.user
    opponent = away_user if submitter.pk == home_user.pk else home_user
    if opponent.pk != submitter.pk:
        Notification.objects.create(
            user=opponent,
            title="Résultat officiel",
            message=(
                f"Résultat officiel : {match.home_participant.team_name} {score} "
                f"{match.away_participant.team_name} (Journée {match.round_number})."
            ),
            notification_type=Notification.TYPE_INFO,
        )


def _notify_result_rejected(match, result, reason):
    Notification.objects.create(
        user=result.submitted_by,
        title="Résultat refusé",
        message=(
            f"Résultat refusé : {match.home_participant.team_name} vs "
            f"{match.away_participant.team_name} (Journée {match.round_number}). "
            f"Motif : {reason}"
        ),
        notification_type=Notification.TYPE_ERROR,
    )
