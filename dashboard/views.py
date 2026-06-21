from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta, date
from django import forms as django_forms

from accounts.models import User, UserProfile, PointTransaction
from rewards.models import Reward, RedemptionRequest, RedemptionStatusHistory, ExchangeRequest
from missions.models import Mission, MissionCompletion, MissionRequest
from notifications.models import Notification
from logs.models import ActivityLog
from accounts.emails import send_reward_accepted_email, send_reward_rejected_email
from accounts.models import PointTransaction as PT


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard:user_dashboard')
    return render(request, 'dashboard/landing.html')


@login_required
def user_dashboard(request):
    user = request.user
    profile = user.profile
    level_info = profile.get_level_display_info()

    today = date.today()
    already_claimed_today = user.daily_rewards.filter(date=today).exists()

    active_missions = Mission.objects.filter(is_active=True)
    missions_with_status = []
    for m in active_missions:
        pending_req = m.get_pending_request(user) if m.is_manual else None
        missions_with_status.append({
            'mission': m,
            'completed': m.is_completed_by(user),
            'pending_request': pending_req,
        })

    recent_transactions = user.point_transactions.all()[:5]
    recent_redemptions = user.redemptions.select_related('reward').all()[:5]
    recent_exchanges = ExchangeRequest.objects.filter(user=user)[:3]
    recent_notifications = user.notifications.filter(is_read=False)[:5]
    pending_exchanges_count = ExchangeRequest.objects.filter(user=user, status=ExchangeRequest.STATUS_PENDING).count()

    min_points = ExchangeRequest.MIN_EXCHANGE_POINTS
    can_exchange = profile.points_balance >= min_points

    invited_count = User.objects.filter(profile__invited_by=user, is_email_verified=True).count()

    context = {
        'profile': profile,
        'level_info': level_info,
        'already_claimed_today': already_claimed_today,
        'missions_with_status': missions_with_status,
        'recent_transactions': recent_transactions,
        'recent_redemptions': recent_redemptions,
        'recent_exchanges': recent_exchanges,
        'recent_notifications': recent_notifications,
        'pending_exchanges_count': pending_exchanges_count,
        'can_exchange': can_exchange,
        'min_points': min_points,
        'invited_count': invited_count,
    }
    return render(request, 'dashboard/user_dashboard.html', context)


def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True, is_suspended=False).count()
    verified_users = User.objects.filter(is_email_verified=True).count()
    pending_redemptions = RedemptionRequest.objects.filter(status=RedemptionRequest.STATUS_PENDING).count()
    pending_exchanges = ExchangeRequest.objects.filter(status=ExchangeRequest.STATUS_PENDING).count()
    pending_mission_requests = MissionRequest.objects.filter(status=MissionRequest.STATUS_PENDING).count()
    total_points_distributed = PointTransaction.objects.filter(
        transaction_type=PointTransaction.TYPE_CREDIT
    ).aggregate(total=Sum('points'))['total'] or 0
    delivered_rewards = RedemptionRequest.objects.filter(status=RedemptionRequest.STATUS_DELIVERED).count()

    week_ago = timezone.now() - timedelta(days=7)
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()

    registrations_data = []
    for i in range(13, -1, -1):
        day = timezone.now().date() - timedelta(days=i)
        count = User.objects.filter(date_joined__date=day).count()
        registrations_data.append({'date': str(day), 'count': count})

    pending_list = RedemptionRequest.objects.filter(
        status=RedemptionRequest.STATUS_PENDING
    ).select_related('user', 'reward').order_by('-created_at')[:10]
    pending_exchange_list = ExchangeRequest.objects.filter(
        status=ExchangeRequest.STATUS_PENDING
    ).select_related('user').order_by('-created_at')[:5]
    recent_logs = ActivityLog.objects.select_related('user').all()[:15]
    top_users = UserProfile.objects.select_related('user').order_by('-points_balance')[:10]

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'verified_users': verified_users,
        'pending_redemptions': pending_redemptions,
        'pending_exchanges': pending_exchanges,
        'pending_mission_requests': pending_mission_requests,
        'total_points_distributed': total_points_distributed,
        'delivered_rewards': delivered_rewards,
        'new_users_week': new_users_week,
        'registrations_data': registrations_data,
        'pending_list': pending_list,
        'pending_exchange_list': pending_exchange_list,
        'recent_logs': recent_logs,
        'top_users': top_users,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def admin_users(request):
    from django.core.paginator import Paginator
    users = User.objects.select_related('profile').order_by('-date_joined')
    search = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(efootball_id__icontains=search)
        )
    if status_filter == 'verified':
        users = users.filter(is_email_verified=True)
    elif status_filter == 'unverified':
        users = users.filter(is_email_verified=False)
    elif status_filter == 'suspended':
        users = users.filter(is_suspended=True)

    paginator = Paginator(users, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'dashboard/admin_users.html', {
        'page': page,
        'search': search,
        'status_filter': status_filter,
    })


@login_required
@user_passes_test(is_admin)
def admin_user_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile = user.profile
    logs = user.activity_logs.all()[:20]
    transactions = user.point_transactions.all()[:20]
    redemptions = user.redemptions.select_related('reward').all()[:10]
    exchanges = ExchangeRequest.objects.filter(user=user).order_by('-created_at')[:10]
    return render(request, 'dashboard/admin_user_detail.html', {
        'target_user': user,
        'profile': profile,
        'logs': logs,
        'transactions': transactions,
        'redemptions': redemptions,
        'exchanges': exchanges,
    })


@login_required
@user_passes_test(is_admin)
def admin_user_action(request, pk):
    if request.method != 'POST':
        return redirect('dashboard:admin_users')
    user = get_object_or_404(User, pk=pk)
    action = request.POST.get('action')

    if action == 'suspend':
        user.is_suspended = True
        user.save()
        messages.success(request, f'Utilisateur {user.username} suspendu.')
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ACTION_ADMIN,
            description=f'Suspension de {user.username}',
        )
    elif action == 'reactivate':
        user.is_suspended = False
        user.save()
        messages.success(request, f'Utilisateur {user.username} réactivé.')
    elif action == 'delete':
        username = user.username
        user.delete()
        messages.success(request, f'Utilisateur {username} supprimé.')
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ACTION_ADMIN,
            description=f'Suppression de {username}',
        )
        return redirect('dashboard:admin_users')

    return redirect('dashboard:admin_user_detail', pk=pk)


@login_required
@user_passes_test(is_admin)
def admin_redemptions(request):
    from django.core.paginator import Paginator
    redemptions = RedemptionRequest.objects.select_related('user', 'reward').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        redemptions = redemptions.filter(status=status_filter)

    paginator = Paginator(redemptions, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'dashboard/admin_redemptions.html', {
        'page': page,
        'status_filter': status_filter,
        'status_choices': RedemptionRequest.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_admin)
def admin_redemption_action(request, pk):
    if request.method != 'POST':
        return redirect('dashboard:admin_redemptions')
    redemption = get_object_or_404(RedemptionRequest, pk=pk)
    action = request.POST.get('action')
    note = request.POST.get('note', '')
    old_status = redemption.status

    if action == 'accept' and redemption.status == RedemptionRequest.STATUS_PENDING:
        redemption.status = RedemptionRequest.STATUS_ACCEPTED
        redemption.admin_note = note
        redemption.save()
        RedemptionStatusHistory.objects.create(
            redemption=redemption, old_status=old_status,
            new_status=redemption.status, changed_by=request.user, note=note,
        )
        Notification.objects.create(
            user=redemption.user,
            title='Récompense acceptée !',
            message=f'"{redemption.reward.name}" a été acceptée.',
            notification_type=Notification.TYPE_SUCCESS,
        )
        send_reward_accepted_email(redemption.user, redemption)
        messages.success(request, 'Demande acceptée.')

    elif action == 'reject' and redemption.status == RedemptionRequest.STATUS_PENDING:
        if not note.strip():
            messages.error(request, 'La cause du refus est obligatoire.')
            return redirect('dashboard:admin_redemptions')
        redemption.status = RedemptionRequest.STATUS_REJECTED
        redemption.admin_note = note
        redemption.save()
        RedemptionStatusHistory.objects.create(
            redemption=redemption, old_status=old_status,
            new_status=redemption.status, changed_by=request.user, note=note,
        )
        redemption.user.profile.add_points(
            redemption.points_spent,
            f'Remboursement : {redemption.reward.name}',
            PointTransaction.CAT_REFUND,
        )
        Notification.objects.create(
            user=redemption.user,
            title='Récompense refusée',
            message=f'"{redemption.reward.name}" a été refusée. Raison : {note}. Points remboursés.',
            notification_type=Notification.TYPE_ERROR,
        )
        send_reward_rejected_email(redemption.user, redemption)
        messages.success(request, 'Demande refusée. Points remboursés.')

    elif action == 'deliver' and redemption.status == RedemptionRequest.STATUS_ACCEPTED:
        redemption.status = RedemptionRequest.STATUS_DELIVERED
        redemption.save()
        RedemptionStatusHistory.objects.create(
            redemption=redemption, old_status=old_status,
            new_status=redemption.status, changed_by=request.user, note=note,
        )
        messages.success(request, 'Marquée comme livrée.')

    return redirect('dashboard:admin_redemptions')


# ─── Exchange admin ────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_exchanges(request):
    from django.core.paginator import Paginator
    exchanges = ExchangeRequest.objects.select_related('user').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        exchanges = exchanges.filter(status=status_filter)

    paginator = Paginator(exchanges, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'dashboard/admin_exchanges.html', {
        'page': page,
        'status_filter': status_filter,
        'status_choices': ExchangeRequest.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_admin)
def admin_exchange_action(request, pk):
    from django.db import transaction as db_transaction
    if request.method != 'POST':
        return redirect('dashboard:admin_exchanges')
    exchange = get_object_or_404(ExchangeRequest, pk=pk)
    action = request.POST.get('action')
    rejection_reason = request.POST.get('rejection_reason', '').strip()

    with db_transaction.atomic():
        if action == 'validate' and exchange.status == ExchangeRequest.STATUS_PENDING:
            exchange.status = ExchangeRequest.STATUS_VALIDATED
            exchange.processed_by = request.user
            exchange.processed_at = timezone.now()
            exchange.save()
            Notification.objects.create(
                user=exchange.user,
                title='Échange traité avec succès !',
                message=f'Votre échange #{exchange.request_number} a été validé. '
                        f'{exchange.coins_requested} Coins ont été ajoutés à votre compte eFootball.',
                notification_type=Notification.TYPE_SUCCESS,
            )
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.ACTION_ADMIN,
                description=f'Échange validé #{exchange.request_number} pour {exchange.user.username}',
            )
            messages.success(request, f'Échange #{exchange.request_number} validé.')

        elif action == 'reject' and exchange.status == ExchangeRequest.STATUS_PENDING:
            if not rejection_reason:
                messages.error(request, 'La cause du refus est obligatoire.')
                return redirect('dashboard:admin_exchanges')
            exchange.status = ExchangeRequest.STATUS_REJECTED
            exchange.rejection_reason = rejection_reason
            exchange.processed_by = request.user
            exchange.processed_at = timezone.now()
            exchange.save()
            # Refund points
            exchange.user.profile.add_points(
                exchange.points_used,
                f'Remboursement échange #{exchange.request_number}',
                PointTransaction.CAT_REFUND,
            )
            Notification.objects.create(
                user=exchange.user,
                title='Demande d\'échange refusée',
                message=f'Votre demande #{exchange.request_number} a été refusée. '
                        f'Raison : {rejection_reason}. '
                        f'Vos {exchange.points_used} points ont été retournés sur votre compte.',
                notification_type=Notification.TYPE_ERROR,
            )
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.ACTION_ADMIN,
                description=f'Échange refusé #{exchange.request_number} — {rejection_reason}',
            )
            messages.success(request, f'Échange refusé. {exchange.points_used} points remboursés.')

    return redirect('dashboard:admin_exchanges')


# ─── Mission admin ─────────────────────────────────────────────────────────────

class MissionForm(django_forms.ModelForm):
    class Meta:
        model = Mission
        fields = ['title', 'description', 'reward_points', 'mission_code',
                  'validation_type', 'is_active', 'link', 'max_monthly_completions', 'icon']
        widgets = {
            'title': django_forms.TextInput(attrs={'class': 'form-control'}),
            'description': django_forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'reward_points': django_forms.NumberInput(attrs={'class': 'form-control'}),
            'mission_code': django_forms.Select(attrs={'class': 'form-select'}),
            'validation_type': django_forms.Select(attrs={'class': 'form-select'}),
            'is_active': django_forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'link': django_forms.URLInput(attrs={'class': 'form-control'}),
            'max_monthly_completions': django_forms.NumberInput(attrs={'class': 'form-control'}),
            'icon': django_forms.TextInput(attrs={'class': 'form-control'}),
        }


@login_required
@user_passes_test(is_admin)
def admin_missions(request):
    missions = Mission.objects.all().order_by('mission_code')
    return render(request, 'dashboard/admin_missions.html', {'missions': missions})


@login_required
@user_passes_test(is_admin)
def admin_mission_add(request):
    if request.method == 'POST':
        form = MissionForm(request.POST)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.ACTION_ADMIN,
                description=f'Mission ajoutée : {form.cleaned_data["title"]}',
            )
            messages.success(request, 'Mission ajoutée.')
            return redirect('dashboard:admin_missions')
    else:
        form = MissionForm()
    return render(request, 'dashboard/admin_mission_form.html', {'form': form, 'action': 'Ajouter'})


@login_required
@user_passes_test(is_admin)
def admin_mission_edit(request, pk):
    mission = get_object_or_404(Mission, pk=pk)
    if request.method == 'POST':
        form = MissionForm(request.POST, instance=mission)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.ACTION_ADMIN,
                description=f'Mission modifiée : {mission.title}',
            )
            messages.success(request, 'Mission mise à jour.')
            return redirect('dashboard:admin_missions')
    else:
        form = MissionForm(instance=mission)
    return render(request, 'dashboard/admin_mission_form.html', {'form': form, 'action': 'Modifier', 'mission': mission})


@login_required
@user_passes_test(is_admin)
def admin_mission_delete(request, pk):
    if request.method != 'POST':
        return redirect('dashboard:admin_missions')
    mission = get_object_or_404(Mission, pk=pk)
    title = mission.title
    mission.delete()
    ActivityLog.objects.create(
        user=request.user,
        action=ActivityLog.ACTION_ADMIN,
        description=f'Mission supprimée : {title}',
    )
    messages.success(request, f'Mission "{title}" supprimée.')
    return redirect('dashboard:admin_missions')


@login_required
@user_passes_test(is_admin)
def admin_mission_toggle(request, pk):
    if request.method != 'POST':
        return redirect('dashboard:admin_missions')
    mission = get_object_or_404(Mission, pk=pk)
    mission.is_active = not mission.is_active
    mission.save(update_fields=['is_active'])
    state = 'activée' if mission.is_active else 'désactivée'
    messages.success(request, f'Mission "{mission.title}" {state}.')
    return redirect('dashboard:admin_missions')


# ─── Mission requests admin ────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_mission_requests(request):
    from django.core.paginator import Paginator
    requests_qs = MissionRequest.objects.select_related('user', 'mission').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)

    paginator = Paginator(requests_qs, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'dashboard/admin_mission_requests.html', {
        'page': page,
        'status_filter': status_filter,
        'status_choices': MissionRequest.STATUS_CHOICES,
    })


@login_required
@user_passes_test(is_admin)
def admin_mission_request_action(request, pk):
    if request.method != 'POST':
        return redirect('dashboard:admin_mission_requests')

    from accounts.models import PointTransaction
    from missions.views import _complete_mission
    mission_request = get_object_or_404(MissionRequest, pk=pk)
    action = request.POST.get('action')
    rejection_reason = request.POST.get('rejection_reason', '').strip()

    if action == 'approve' and mission_request.status == MissionRequest.STATUS_PENDING:
        if not mission_request.mission.is_completed_by(mission_request.user):
            _complete_mission(mission_request.user, mission_request.mission)
        mission_request.status = MissionRequest.STATUS_APPROVED
        mission_request.reviewed_by = request.user
        mission_request.reviewed_at = timezone.now()
        mission_request.save()
        Notification.objects.create(
            user=mission_request.user,
            title='Mission validée !',
            message=f'Votre demande pour "{mission_request.mission.title}" a été approuvée. +{mission_request.mission.reward_points} points.',
            notification_type=Notification.TYPE_SUCCESS,
        )
        messages.success(request, 'Mission approuvée. Points accordés.')

    elif action == 'reject' and mission_request.status == MissionRequest.STATUS_PENDING:
        if not rejection_reason:
            messages.error(request, 'La cause du refus est obligatoire.')
            return redirect('dashboard:admin_mission_requests')
        mission_request.status = MissionRequest.STATUS_REJECTED
        mission_request.rejection_reason = rejection_reason
        mission_request.reviewed_by = request.user
        mission_request.reviewed_at = timezone.now()
        mission_request.save()
        Notification.objects.create(
            user=mission_request.user,
            title='Mission refusée',
            message=f'Votre demande pour "{mission_request.mission.title}" a été refusée. Raison : {rejection_reason}.',
            notification_type=Notification.TYPE_ERROR,
        )
        messages.success(request, 'Mission refusée.')

    return redirect('dashboard:admin_mission_requests')


# ─── Account Verification Admin ───────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_verifications(request):
    from accounts.models import AccountVerificationRequest
    verifications = AccountVerificationRequest.objects.select_related('user', 'user__profile').exclude(
        status=AccountVerificationRequest.STATUS_VERIFIED
    ).order_by('-created_at')
    history = AccountVerificationRequest.objects.filter(
        status=AccountVerificationRequest.STATUS_VERIFIED
    ).select_related('user').order_by('-updated_at')[:30]
    return render(request, 'dashboard/admin_verifications.html', {
        'verifications': verifications,
        'history': history,
    })


@login_required
@user_passes_test(is_admin)
def admin_set_request_method(request, pk):
    """Assign a verification method to a specific user's request."""
    from accounts.models import AccountVerificationRequest
    if request.method == 'POST':
        ver = get_object_or_404(AccountVerificationRequest, pk=pk)
        method = request.POST.get('method', '')
        valid = ['phone', 'admin_code', 'send_code']
        if method in valid:
            ver.method = method
            if ver.status == AccountVerificationRequest.STATUS_CODE_ENTERED:
                ver.status = AccountVerificationRequest.STATUS_PENDING
            ver.save(update_fields=['method', 'status'])
            labels = {'phone': 'Téléphone', 'admin_code': 'Code admin', 'send_code': 'Envoi automatique'}
            messages.success(request, f'Méthode "{labels[method]}" assignée à {ver.user.username}.')
            Notification.objects.create(
                user=ver.user,
                title='Méthode de vérification assignée',
                message='L\'administrateur a configuré votre méthode de vérification. Consultez la page de vérification.',
                notification_type=Notification.TYPE_INFO,
            )
        else:
            messages.error(request, 'Méthode invalide.')
    return redirect('dashboard:admin_verifications')


@login_required
@user_passes_test(is_admin)
def admin_set_verification_method(request):
    from accounts.models import VerificationSettings
    if request.method == 'POST':
        method = request.POST.get('method', '')
        valid = [VerificationSettings.METHOD_PHONE, VerificationSettings.METHOD_ADMIN_CODE, VerificationSettings.METHOD_SEND_CODE]
        if method in valid:
            vsettings = VerificationSettings.get_current()
            vsettings.method = method
            vsettings.updated_by = request.user
            vsettings.save()
            labels = dict(VerificationSettings.METHOD_CHOICES)
            messages.success(request, f'Méthode de vérification : {labels[method]}')
        else:
            messages.error(request, 'Méthode invalide.')
    return redirect('dashboard:admin_verifications')


@login_required
@user_passes_test(is_admin)
def admin_set_verification_code(request, pk):
    from accounts.models import AccountVerificationRequest
    if request.method == 'POST':
        ver = get_object_or_404(AccountVerificationRequest, pk=pk)
        code = request.POST.get('verification_code', '').strip()
        if code:
            ver.verification_code = code
            ver.save(update_fields=['verification_code'])
            messages.success(request, f'Code défini pour {ver.user.username}. Envoyez-le manuellement.')
        else:
            messages.error(request, 'Veuillez entrer un code.')
    return redirect('dashboard:admin_verifications')


@login_required
@user_passes_test(is_admin)
def admin_verification_action(request, pk):
    from accounts.models import AccountVerificationRequest
    from accounts.views import _award_invitation_points

    if request.method != 'POST':
        return redirect('dashboard:admin_verifications')

    ver_request = get_object_or_404(AccountVerificationRequest, pk=pk)
    action = request.POST.get('action')

    if action == 'verify':
        user = ver_request.user
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])
        ver_request.status = AccountVerificationRequest.STATUS_VERIFIED
        ver_request.save()
        try:
            _award_invitation_points(user)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('_award_invitation_points failed for user %s', user.pk)
        Notification.objects.create(
            user=user,
            title='Compte vérifié !',
            message='Votre compte a été vérifié par l\'administrateur. Vous pouvez maintenant gagner des points et compléter des missions.',
            notification_type=Notification.TYPE_SUCCESS,
        )
        messages.success(request, f'Compte de {user.username} vérifié avec succès.')

    elif action == 'reject':
        ver_request.status = AccountVerificationRequest.STATUS_REJECTED
        ver_request.save()
        Notification.objects.create(
            user=ver_request.user,
            title='Vérification refusée',
            message='Votre demande de vérification a été refusée. Contactez le support ou réessayez.',
            notification_type=Notification.TYPE_ERROR,
        )
        messages.warning(request, 'Demande de vérification refusée.')

    return redirect('dashboard:admin_verifications')
