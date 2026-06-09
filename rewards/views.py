from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction

from .models import Reward, RedemptionRequest, RedemptionStatusHistory
from notifications.models import Notification
from logs.models import ActivityLog
from accounts.views import _get_client_ip


@login_required
def reward_catalog(request):
    rewards = Reward.objects.filter(is_active=True).order_by('points_cost')
    category = request.GET.get('category')
    if category:
        rewards = rewards.filter(category=category)
    paginator = Paginator(rewards, 12)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'rewards/catalog.html', {
        'page': page,
        'category': category,
        'categories': Reward.CATEGORY_CHOICES,
        'user_points': request.user.profile.points_balance,
    })


@login_required
def reward_detail(request, pk):
    reward = get_object_or_404(Reward, pk=pk, is_active=True)
    return render(request, 'rewards/detail.html', {
        'reward': reward,
        'user_points': request.user.profile.points_balance,
        'can_afford': request.user.profile.points_balance >= reward.points_cost,
    })


@login_required
@transaction.atomic
def redeem_reward(request, pk):
    if request.method != 'POST':
        return redirect('rewards:catalog')

    reward = get_object_or_404(Reward, pk=pk, is_active=True)
    user = request.user

    if not user.can_redeem:
        messages.warning(request, 'Vous devez vérifier votre email pour demander des récompenses.')
        return redirect('rewards:catalog')

    if not reward.is_available:
        messages.error(request, 'Cette récompense n\'est plus disponible.')
        return redirect('rewards:catalog')

    profile = user.profile
    if profile.points_balance < reward.points_cost:
        messages.error(request, f'Solde insuffisant. Vous avez {profile.points_balance} points, il faut {reward.points_cost} points.')
        return redirect('rewards:detail', pk=pk)

    profile.deduct_points(reward.points_cost, f'Demande récompense : {reward.name}')
    redemption = RedemptionRequest.objects.create(
        user=user,
        reward=reward,
        points_spent=reward.points_cost,
        status=RedemptionRequest.STATUS_PENDING,
    )
    if reward.quantity_available > 0:
        reward.decrement_quantity()

    Notification.objects.create(
        user=user,
        title='Demande envoyée !',
        message=f'Votre demande pour "{reward.name}" est en cours de traitement.',
        notification_type=Notification.TYPE_INFO,
    )
    ActivityLog.objects.create(
        user=user,
        action=ActivityLog.ACTION_REWARD_REQUEST,
        description=f'Demande récompense : {reward.name}',
        ip_address=_get_client_ip(request),
    )

    messages.success(request, f'Demande envoyée pour "{reward.name}". Vous recevrez une réponse bientôt.')
    return redirect('rewards:my_redemptions')


@login_required
def my_redemptions(request):
    redemptions = RedemptionRequest.objects.filter(user=request.user).select_related('reward')
    status_filter = request.GET.get('status')
    if status_filter:
        redemptions = redemptions.filter(status=status_filter)
    paginator = Paginator(redemptions, 10)
    page = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'rewards/my_redemptions.html', {
        'page': page,
        'status_filter': status_filter,
        'status_choices': RedemptionRequest.STATUS_CHOICES,
    })
