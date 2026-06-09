from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta, date

from accounts.models import User, UserProfile, PointTransaction
from rewards.models import Reward, RedemptionRequest, RedemptionStatusHistory
from missions.models import Mission, MissionCompletion
from notifications.models import Notification
from logs.models import ActivityLog
from accounts.emails import send_reward_accepted_email, send_reward_rejected_email


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

    active_missions = Mission.objects.filter(is_active=True)[:6]
    missions_with_status = [
        {'mission': m, 'completed': m.is_completed_by(user)}
        for m in active_missions
    ]

    recent_transactions = user.point_transactions.all()[:5]
    recent_redemptions = user.redemptions.select_related('reward').all()[:5]
    recent_notifications = user.notifications.filter(is_read=False)[:5]

    pending_redemptions_count = user.redemptions.filter(
        status=RedemptionRequest.STATUS_PENDING
    ).count()

    context = {
        'profile': profile,
        'level_info': level_info,
        'already_claimed_today': already_claimed_today,
        'missions_with_status': missions_with_status,
        'recent_transactions': recent_transactions,
        'recent_redemptions': recent_redemptions,
        'recent_notifications': recent_notifications,
        'pending_redemptions_count': pending_redemptions_count,
    }
    return render(request, 'dashboard/user_dashboard.html', context)


def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    # Stats
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True, is_suspended=False).count()
    verified_users = User.objects.filter(is_email_verified=True).count()
    pending_redemptions = RedemptionRequest.objects.filter(status=RedemptionRequest.STATUS_PENDING).count()
    total_points_distributed = PointTransaction.objects.filter(
        transaction_type=PointTransaction.TYPE_CREDIT
    ).aggregate(total=Sum('points'))['total'] or 0
    delivered_rewards = RedemptionRequest.objects.filter(
        status=RedemptionRequest.STATUS_DELIVERED
    ).count()

    # Recent registrations (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()

    # Daily registrations for chart (last 14 days)
    registrations_data = []
    for i in range(13, -1, -1):
        day = timezone.now().date() - timedelta(days=i)
        count = User.objects.filter(date_joined__date=day).count()
        registrations_data.append({'date': str(day), 'count': count})

    # Pending redemptions list
    pending_list = RedemptionRequest.objects.filter(
        status=RedemptionRequest.STATUS_PENDING
    ).select_related('user', 'reward').order_by('-created_at')[:10]

    # Recent logs
    recent_logs = ActivityLog.objects.select_related('user').all()[:15]

    # Top users by points
    top_users = UserProfile.objects.select_related('user').order_by('-points_balance')[:10]

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'verified_users': verified_users,
        'pending_redemptions': pending_redemptions,
        'total_points_distributed': total_points_distributed,
        'delivered_rewards': delivered_rewards,
        'new_users_week': new_users_week,
        'registrations_data': registrations_data,
        'pending_list': pending_list,
        'recent_logs': recent_logs,
        'top_users': top_users,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def admin_users(request):
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

    from django.core.paginator import Paginator
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
    return render(request, 'dashboard/admin_user_detail.html', {
        'target_user': user,
        'profile': profile,
        'logs': logs,
        'transactions': transactions,
        'redemptions': redemptions,
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
    redemptions = RedemptionRequest.objects.select_related('user', 'reward').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        redemptions = redemptions.filter(status=status_filter)

    from django.core.paginator import Paginator
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
        redemption.status = RedemptionRequest.STATUS_REJECTED
        redemption.admin_note = note
        redemption.save()
        RedemptionStatusHistory.objects.create(
            redemption=redemption, old_status=old_status,
            new_status=redemption.status, changed_by=request.user, note=note,
        )
        redemption.user.profile.add_points(redemption.points_spent, f'Remboursement : {redemption.reward.name}')
        Notification.objects.create(
            user=redemption.user,
            title='Récompense refusée',
            message=f'"{redemption.reward.name}" a été refusée. Points remboursés.',
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
