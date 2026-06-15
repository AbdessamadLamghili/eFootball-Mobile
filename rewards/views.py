from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.conf import settings

from .models import Reward, RedemptionRequest, RedemptionStatusHistory, ExchangeRequest
from notifications.models import Notification
from logs.models import ActivityLog
from accounts.views import _get_client_ip
from accounts.models import PointTransaction


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

    profile.deduct_points(reward.points_cost, f'Demande récompense : {reward.name}', PointTransaction.CAT_EXCHANGE)
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


# ─── Exchange views ────────────────────────────────────────────────────────────

@login_required
def exchange_page(request):
    """Show user's exchange history and the exchange form."""
    user = request.user
    profile = user.profile
    exchanges = ExchangeRequest.objects.filter(user=user).order_by('-created_at')
    paginator = Paginator(exchanges, 10)
    page = paginator.get_page(request.GET.get('page', 1))

    min_points = ExchangeRequest.MIN_EXCHANGE_POINTS
    can_exchange = profile.points_balance >= min_points
    coins_preview = ExchangeRequest.calculate_coins(profile.points_balance // min_points * min_points)

    return render(request, 'rewards/exchange.html', {
        'page': page,
        'profile': profile,
        'min_points': min_points,
        'can_exchange': can_exchange,
        'exchange_rate': ExchangeRequest.EXCHANGE_RATE,
        'coins_preview': coins_preview,
    })


@login_required
@transaction.atomic
def create_exchange(request):
    """Process a points-to-coins exchange request."""
    if request.method != 'POST':
        return redirect('rewards:exchange')

    user = request.user
    if not user.can_redeem:
        messages.warning(request, 'Vous devez vérifier votre email pour effectuer un échange.')
        return redirect('rewards:exchange')

    profile = user.profile
    min_points = ExchangeRequest.MIN_EXCHANGE_POINTS

    if profile.points_balance < min_points:
        messages.error(request, f'Vous avez besoin d\'au moins {min_points} points pour effectuer un échange.')
        return redirect('rewards:exchange')

    # Exchange in multiples of MIN_EXCHANGE_POINTS
    max_exchangeable = (profile.points_balance // min_points) * min_points
    points_to_exchange = min_points  # always exchange one block at a time
    coins = ExchangeRequest.calculate_coins(points_to_exchange)

    profile.deduct_points(
        points_to_exchange,
        f'Échange : {points_to_exchange} pts → {coins} Coins eFootball',
        PointTransaction.CAT_EXCHANGE,
    )

    exchange = ExchangeRequest.objects.create(
        user=user,
        points_used=points_to_exchange,
        coins_requested=coins,
        status=ExchangeRequest.STATUS_PENDING,
    )

    Notification.objects.create(
        user=user,
        title='Demande d\'échange envoyée',
        message=f'Votre demande #{exchange.request_number} ({coins} Coins) est en cours de traitement. Délai : jusqu\'à 48h.',
        notification_type=Notification.TYPE_INFO,
    )

    ActivityLog.objects.create(
        user=user,
        action=ActivityLog.ACTION_REWARD_REQUEST,
        description=f'Échange de points : {points_to_exchange} pts → {coins} Coins',
        ip_address=_get_client_ip(request),
    )

    messages.success(
        request,
        f'Votre demande a été envoyée. Veuillez patienter jusqu\'à 48 heures. '
        f'Les Coins seront ajoutés à votre compte eFootball après vérification.'
    )
    return redirect('rewards:exchange')
