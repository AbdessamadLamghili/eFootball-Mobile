from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.views import View
from django_ratelimit.decorators import ratelimit
from datetime import timedelta, date

from .models import User, UserProfile, EmailVerificationToken, PasswordResetToken, DailyReward, PointTransaction
from .forms import (
    RegisterForm, LoginForm, PasswordResetRequestForm,
    PasswordResetConfirmForm, ProfileUpdateForm, AvatarUpdateForm,
)
from .emails import send_password_reset_email
from notifications.models import Notification
from logs.models import ActivityLog
from django.conf import settings


class RegisterView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:home')
        return render(request, self.template_name, {'form': RegisterForm()})

    @method_decorator(ratelimit(key='ip', rate='5/m', block=True))
    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            invitation_code = form.cleaned_data.get('invitation_code', '')
            inviter_profile = None
            if invitation_code:
                try:
                    inviter_profile = UserProfile.objects.select_related('user').get(
                        invitation_code__iexact=invitation_code
                    )
                except UserProfile.DoesNotExist:
                    inviter_profile = None

            try:
                user = form.save()
            except Exception:
                messages.error(request, 'Une erreur est survenue lors de la création du compte. Réessayez.')
                return render(request, self.template_name, {'form': form})

            # Link invitation after user (and profile) are created
            if inviter_profile and inviter_profile.user != user:
                try:
                    profile = user.profile
                    profile.invited_by = inviter_profile.user
                    profile.save(update_fields=['invited_by'])
                except Exception:
                    pass

            try:
                ActivityLog.objects.create(
                    user=user,
                    action=ActivityLog.ACTION_REGISTER,
                    ip_address=_get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
            except Exception:
                pass

            try:
                Notification.objects.create(
                    user=user,
                    title='Bienvenue sur eFootball Rewards !',
                    message="Votre compte a été créé. Vérifiez votre email pour l'activer.",
                    notification_type=Notification.TYPE_INFO,
                )
            except Exception:
                pass

            messages.success(request, 'Compte créé ! Vérifiez votre email pour l\'activer.')
            return redirect('accounts:login')
        return render(request, self.template_name, {'form': form})


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard:home')
        return render(request, self.template_name, {'form': LoginForm()})

    @method_decorator(ratelimit(key='ip', rate='10/m', block=True))
    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_suspended:
                messages.error(request, 'Votre compte a été suspendu. Contactez le support.')
                return render(request, self.template_name, {'form': form})
            login(request, user)
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)

            try:
                ActivityLog.objects.create(
                    user=user,
                    action=ActivityLog.ACTION_LOGIN,
                    ip_address=_get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                )
            except Exception:
                pass

            # Auto-check streak-based missions after login
            _check_streak_missions_on_login(user)

            next_url = request.GET.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect(reverse('dashboard:user_dashboard'))
        return render(request, self.template_name, {'form': form})


@login_required
def logout_view(request):
    if request.method == 'POST':
        try:
            ActivityLog.objects.create(
                user=request.user,
                action=ActivityLog.ACTION_LOGOUT,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        except Exception:
            pass
        logout(request)
        messages.info(request, 'Vous avez été déconnecté.')
    return redirect('accounts:login')


def verify_email(request, token):
    token_obj = get_object_or_404(EmailVerificationToken, token=token)
    if not token_obj.is_valid():
        messages.error(request, 'Ce lien de vérification a expiré.')
        return redirect('accounts:login')
    user = token_obj.user
    user.is_email_verified = True
    user.save()
    token_obj.delete()

    try:
        Notification.objects.create(
            user=user,
            title='Email vérifié !',
            message='Votre adresse email a été vérifiée. Vous pouvez maintenant gagner des points.',
            notification_type=Notification.TYPE_SUCCESS,
        )
        ActivityLog.objects.create(
            user=user,
            action=ActivityLog.ACTION_EMAIL_VERIFIED,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
    except Exception:
        pass

    # Award invitation reward to inviter now that email is verified
    _award_invitation_points(user)

    messages.success(request, 'Email vérifié ! Votre compte est maintenant actif.')
    return redirect('accounts:login')


class PasswordResetRequestView(View):
    template_name = 'accounts/password_reset_request.html'

    @method_decorator(ratelimit(key='ip', rate='3/m', block=True))
    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email__iexact=email)
                PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
                token = PasswordResetToken.objects.create(
                    user=user,
                    expires_at=timezone.now() + timedelta(hours=1),
                )
                send_password_reset_email(user, token)
            except Exception:
                pass
            messages.success(request, 'Si un compte existe pour cet email, un lien a été envoyé.')
            return redirect('accounts:login')
        return render(request, self.template_name, {'form': form})

    def get(self, request):
        return render(request, self.template_name, {'form': PasswordResetRequestForm()})


class PasswordResetConfirmView(View):
    template_name = 'accounts/password_reset_confirm.html'

    def get(self, request, token):
        token_obj = get_object_or_404(PasswordResetToken, token=token)
        if not token_obj.is_valid():
            messages.error(request, 'Ce lien de réinitialisation a expiré.')
            return redirect('accounts:password_reset')
        return render(request, self.template_name, {'form': PasswordResetConfirmForm(), 'token': token})

    def post(self, request, token):
        token_obj = get_object_or_404(PasswordResetToken, token=token)
        if not token_obj.is_valid():
            messages.error(request, 'Ce lien a expiré.')
            return redirect('accounts:password_reset')
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            user = token_obj.user
            user.set_password(form.cleaned_data['password'])
            user.save()
            token_obj.is_used = True
            token_obj.save()
            messages.success(request, 'Mot de passe réinitialisé avec succès. Vous pouvez vous connecter.')
            return redirect('accounts:login')
        return render(request, self.template_name, {'form': form, 'token': token})


@login_required
def profile_view(request):
    from rewards.models import ExchangeRequest
    profile = request.user.profile
    transactions = request.user.point_transactions.all()[:20]
    daily_rewards = request.user.daily_rewards.all()[:10]
    redemptions = request.user.redemptions.select_related('reward').all()[:10]
    exchange_requests = ExchangeRequest.objects.filter(user=request.user).order_by('-created_at')[:10]
    level_info = profile.get_level_display_info()
    invited_users = User.objects.filter(profile__invited_by=request.user).select_related('profile')
    context = {
        'profile': profile,
        'transactions': transactions,
        'daily_rewards': daily_rewards,
        'redemptions': redemptions,
        'exchange_requests': exchange_requests,
        'level_info': level_info,
        'invited_users': invited_users,
        'monthly_invitations': profile.get_monthly_invitation_count(),
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        avatar_form = AvatarUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid() and avatar_form.is_valid():
            form.save()
            avatar_form.save()
            # Auto-check profile completion mission
            _check_profile_mission(request.user)
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
        avatar_form = AvatarUpdateForm(instance=request.user.profile)
    return render(request, 'accounts/profile_edit.html', {
        'form': form,
        'avatar_form': avatar_form,
    })


@login_required
def claim_daily_reward(request):
    if request.method != 'POST':
        return redirect('dashboard:home')

    user = request.user
    if not user.can_earn_points:
        messages.warning(request, 'Vous devez vérifier votre email pour gagner des points.')
        return redirect('dashboard:home')

    profile = user.profile
    today = date.today()

    if DailyReward.objects.filter(user=user, date=today).exists():
        messages.info(request, "Vous avez déjà réclamé votre récompense quotidienne aujourd'hui.")
        return redirect('dashboard:home')

    yesterday = today - timedelta(days=1)
    had_yesterday = DailyReward.objects.filter(user=user, date=yesterday).exists()

    if had_yesterday:
        profile.current_streak += 1
    else:
        profile.current_streak = 1

    if profile.current_streak > profile.longest_streak:
        profile.longest_streak = profile.current_streak

    profile.last_daily_reward = today
    profile.save(update_fields=['current_streak', 'longest_streak', 'last_daily_reward'])

    base_points = settings.POINTS_DAILY_LOGIN
    bonus_points = 0
    streak_message = ''

    streak = profile.current_streak
    if streak == 30:
        bonus_points = settings.POINTS_STREAK_30
        streak_message = f'Streak 30 jours ! +{bonus_points} points bonus !'
    elif streak == 14:
        bonus_points = settings.POINTS_STREAK_14
        streak_message = f'Streak 14 jours ! +{bonus_points} points bonus !'
    elif streak == 7:
        bonus_points = settings.POINTS_STREAK_7
        streak_message = f'Streak 7 jours ! +{bonus_points} points bonus !'

    total_points = base_points + bonus_points
    profile.add_points(base_points, 'Connexion quotidienne', PointTransaction.CAT_DAILY)
    if bonus_points:
        profile.add_points(bonus_points, f'Bonus streak {streak} jours', PointTransaction.CAT_BONUS)

    DailyReward.objects.create(
        user=user,
        date=today,
        points_earned=total_points,
        streak_day=streak,
        bonus_points=bonus_points,
    )

    try:
        Notification.objects.create(
            user=user,
            title='Récompense quotidienne réclamée !',
            message=f'+{base_points} points gagnés. Streak : {streak} jours. {streak_message}',
            notification_type=Notification.TYPE_POINTS,
        )
    except Exception:
        pass

    messages.success(request, f'+{base_points} points ! Streak : {streak} jour(s). {streak_message}')
    return redirect('dashboard:home')


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _award_invitation_points(user):
    """Award points to inviter when invited user verifies their email."""
    try:
        profile = user.profile
        if not profile.invited_by:
            return
        inviter = profile.invited_by
        inviter_profile = inviter.profile
        if not inviter.can_earn_points:
            return
        if not inviter_profile.can_earn_invitation_reward():
            return

        points = settings.POINTS_INVITE_FRIEND
        inviter_profile.add_points(
            points,
            f'Invitation validée : {user.username}',
            PointTransaction.CAT_INVITATION,
        )
        Notification.objects.create(
            user=inviter,
            title='Invitation validée !',
            message=f'{user.username} a rejoint et vérifié son email. +{points} points.',
            notification_type=Notification.TYPE_POINTS,
        )
    except Exception:
        pass


def _check_profile_mission(user):
    """Auto-complete profile mission if all conditions are met."""
    if not user.can_earn_points:
        return
    if not user.is_profile_complete:
        return
    from missions.models import Mission, MissionCompletion
    try:
        mission = Mission.objects.get(mission_code=Mission.CODE_PROFILE, is_active=True)
    except Mission.DoesNotExist:
        return
    if MissionCompletion.objects.filter(user=user, mission=mission).exists():
        return
    MissionCompletion.objects.create(
        user=user, mission=mission, points_earned=mission.reward_points
    )
    user.profile.add_points(
        mission.reward_points,
        f'Mission : {mission.title}',
        PointTransaction.CAT_MISSION,
    )
    Notification.objects.create(
        user=user,
        title='Mission accomplie !',
        message=f'"{mission.title}" complétée ! +{mission.reward_points} points.',
        notification_type=Notification.TYPE_POINTS,
    )
    _check_all_missions(user)


def _check_streak_missions_on_login(user):
    """Check streak-based missions after login."""
    if not user.can_earn_points:
        return
    try:
        profile = user.profile
    except Exception:
        return

    from missions.models import Mission, MissionCompletion
    streak = profile.current_streak

    for code, threshold in [(Mission.CODE_STREAK_3, 3), (Mission.CODE_STREAK_7, 7)]:
        if streak < threshold:
            continue
        try:
            mission = Mission.objects.get(mission_code=code, is_active=True)
        except Mission.DoesNotExist:
            continue
        if MissionCompletion.objects.filter(user=user, mission=mission).exists():
            continue
        MissionCompletion.objects.create(
            user=user, mission=mission, points_earned=mission.reward_points
        )
        user.profile.add_points(
            mission.reward_points,
            f'Mission : {mission.title}',
            PointTransaction.CAT_MISSION,
        )
        Notification.objects.create(
            user=user,
            title='Mission accomplie !',
            message=f'"{mission.title}" complétée ! +{mission.reward_points} points.',
            notification_type=Notification.TYPE_POINTS,
        )
        _check_all_missions(user)


def _check_all_missions(user):
    """Check if user completed all active non-repeatable missions and award bonus."""
    from missions.models import Mission, MissionCompletion
    try:
        all_missions_mission = Mission.objects.get(mission_code=Mission.CODE_ALL, is_active=True)
    except Mission.DoesNotExist:
        return
    if MissionCompletion.objects.filter(user=user, mission=all_missions_mission).exists():
        return

    # Gather all active missions except CODE_ALL and CODE_INVITE
    active_missions = Mission.objects.filter(is_active=True).exclude(
        mission_code__in=[Mission.CODE_ALL, Mission.CODE_INVITE]
    )
    completed_ids = MissionCompletion.objects.filter(
        user=user, mission__in=active_missions
    ).values_list('mission_id', flat=True)

    if set(active_missions.values_list('id', flat=True)) <= set(completed_ids):
        MissionCompletion.objects.create(
            user=user,
            mission=all_missions_mission,
            points_earned=all_missions_mission.reward_points,
        )
        user.profile.add_points(
            all_missions_mission.reward_points,
            f'Mission : {all_missions_mission.title}',
            PointTransaction.CAT_MISSION,
        )
        Notification.objects.create(
            user=user,
            title='Toutes les missions terminées !',
            message=f'Félicitations ! Vous avez terminé toutes les missions. +{all_missions_mission.reward_points} points bonus.',
            notification_type=Notification.TYPE_POINTS,
        )
