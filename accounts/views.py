from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import UpdateView
from django_ratelimit.decorators import ratelimit
from datetime import timedelta, date

from .models import User, UserProfile, EmailVerificationToken, PasswordResetToken, DailyReward
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
            user = form.save()
            ActivityLog.objects.create(
                user=user,
                action=ActivityLog.ACTION_REGISTER,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            Notification.objects.create(
                user=user,
                title='Bienvenue sur eFootball Rewards !',
                message='Votre compte a été créé. Vérifiez votre email pour l\'activer.',
                notification_type=Notification.TYPE_INFO,
            )
            messages.success(
                request,
                'Compte créé ! Vérifiez votre email pour l\'activer.'
            )
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
            ActivityLog.objects.create(
                user=user,
                action=ActivityLog.ACTION_LOGIN,
                ip_address=_get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            next_url = request.GET.get('next', 'dashboard:home')
            return redirect(next_url)
        return render(request, self.template_name, {'form': form})


@login_required
def logout_view(request):
    if request.method == 'POST':
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityLog.ACTION_LOGOUT,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
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
    messages.success(request, 'Email vérifié ! Votre compte est maintenant actif.')
    return redirect('accounts:login')


class PasswordResetRequestView(View):
    template_name = 'accounts/password_reset_request.html'

    @method_decorator(ratelimit(key='ip', rate='3/m', block=True))
    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email__iexact=email)
            PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
            token = PasswordResetToken.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(hours=1),
            )
            send_password_reset_email(user, token)
            messages.success(request, 'Un email de réinitialisation a été envoyé.')
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
    profile = request.user.profile
    transactions = request.user.point_transactions.all()[:20]
    daily_rewards = request.user.daily_rewards.all()[:10]
    redemptions = request.user.redemptions.select_related('reward').all()[:10]
    level_info = profile.get_level_display_info()
    context = {
        'profile': profile,
        'transactions': transactions,
        'daily_rewards': daily_rewards,
        'redemptions': redemptions,
        'level_info': level_info,
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
        messages.info(request, 'Vous avez déjà réclamé votre récompense quotidienne aujourd\'hui.')
        return redirect('dashboard:home')

    # Streak logic
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
    profile.add_points(base_points, 'Connexion quotidienne')
    if bonus_points:
        profile.add_points(bonus_points, f'Bonus streak {streak} jours')

    DailyReward.objects.create(
        user=user,
        date=today,
        points_earned=total_points,
        streak_day=streak,
        bonus_points=bonus_points,
    )

    Notification.objects.create(
        user=user,
        title='Récompense quotidienne réclamée !',
        message=f'+{base_points} points gagnés. Streak : {streak} jours. {streak_message}',
        notification_type=Notification.TYPE_POINTS,
    )

    messages.success(request, f'+{base_points} points ! Streak : {streak} jour(s). {streak_message}')
    return redirect('dashboard:home')


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
