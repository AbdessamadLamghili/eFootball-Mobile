import random
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

from .models import User, UserProfile, EmailVerificationToken, PasswordResetToken, PasswordResetCode, EmailVerificationCode, DailyReward, PointTransaction, AccountVerificationRequest
from .forms import (
    RegisterForm, LoginForm, PasswordResetRequestForm,
    PasswordResetCodeForm, PasswordResetConfirmForm, EmailVerifyCodeForm, ProfileUpdateForm, AvatarUpdateForm,
)
from .emails import send_password_reset_code_email, send_email_verification_code_email
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
                    message="Votre compte a été créé. Confirmez votre email avec le code envoyé.",
                    notification_type=Notification.TYPE_INFO,
                )
            except Exception:
                pass

            # Send email verification code (skipped when EMAIL_VERIFICATION_REQUIRED=False)
            if settings.EMAIL_VERIFICATION_REQUIRED:
                EmailVerificationCode.objects.filter(user=user, is_used=False).update(is_used=True)
                code_obj = EmailVerificationCode.objects.create(
                    user=user,
                    code=str(random.randint(100000, 999999)),
                    expires_at=timezone.now() + timedelta(minutes=15),
                )
                try:
                    send_email_verification_code_email(user, code_obj.code)
                except Exception:
                    pass
                request.session['email_verify_code_id'] = code_obj.pk
                messages.info(request, 'Un code de vérification a été envoyé à votre email. Valable 15 minutes.')
                return redirect('accounts:email_verify')
            else:
                user.is_email_confirmed = True
                user.save(update_fields=['is_email_confirmed'])
                messages.success(request, 'Compte créé ! Vous pouvez maintenant vous connecter.')
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
            if settings.EMAIL_VERIFICATION_REQUIRED and not user.is_email_confirmed:
                # Block login — send a fresh code and redirect to verification
                EmailVerificationCode.objects.filter(user=user, is_used=False).update(is_used=True)
                code_obj = EmailVerificationCode.objects.create(
                    user=user,
                    code=str(random.randint(100000, 999999)),
                    expires_at=timezone.now() + timedelta(minutes=15),
                )
                try:
                    send_email_verification_code_email(user, code_obj.code)
                except Exception:
                    pass
                request.session['email_verify_code_id'] = code_obj.pk
                request.session['unconfirmed_login_user_id'] = str(user.pk)
                messages.warning(request, 'Veuillez confirmer votre adresse email. Un nouveau code a été envoyé.')
                return redirect('accounts:email_verify')
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


class EmailVerifyCodeView(View):
    template_name = 'accounts/email_verify.html'

    def _get_or_redirect(self, request):
        """Return (code_obj, None) or (None, redirect_response)."""
        code_id = request.session.get('email_verify_code_id')
        if not code_id:
            return None, redirect('accounts:login')
        try:
            return EmailVerificationCode.objects.select_related('user').get(pk=code_id), None
        except EmailVerificationCode.DoesNotExist:
            request.session.pop('email_verify_code_id', None)
            request.session.pop('unconfirmed_login_user_id', None)
            return None, redirect('accounts:login')

    def get(self, request):
        code_obj, redir = self._get_or_redirect(request)
        if redir:
            return redir
        return render(request, self.template_name, {
            'form': EmailVerifyCodeForm(),
            'masked_email': _mask_email(code_obj.user.email),
        })

    @method_decorator(ratelimit(key='ip', rate='10/h', block=True))
    def post(self, request):
        code_obj, redir = self._get_or_redirect(request)
        if redir:
            return redir

        form = EmailVerifyCodeForm(request.POST)
        masked_email = _mask_email(code_obj.user.email)

        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'masked_email': masked_email})

        entered_code = form.cleaned_data['code']

        if not code_obj.is_valid():
            messages.error(request, 'Ce code a expiré ou n\'est plus valide. Demandez un nouveau code.')
            return render(request, self.template_name, {
                'form': form,
                'masked_email': masked_email,
                'show_resend': True,
            })

        if entered_code != code_obj.code:
            code_obj.increment_attempts()
            remaining = max(0, EmailVerificationCode.MAX_ATTEMPTS - code_obj.attempts)
            if remaining == 0:
                messages.error(request, 'Trop de tentatives incorrectes. Demandez un nouveau code.')
                return render(request, self.template_name, {
                    'form': EmailVerifyCodeForm(),
                    'masked_email': masked_email,
                    'show_resend': True,
                })
            messages.error(request, f'Code incorrect. {remaining} tentative(s) restante(s).')
            return render(request, self.template_name, {'form': form, 'masked_email': masked_email})

        # Code correct — confirm email
        user = code_obj.user
        user.is_email_confirmed = True
        user.save(update_fields=['is_email_confirmed'])
        code_obj.is_used = True
        code_obj.save(update_fields=['is_used'])

        request.session.pop('email_verify_code_id', None)
        unconfirmed_user_id = request.session.pop('unconfirmed_login_user_id', None)

        try:
            Notification.objects.create(
                user=user,
                title='Email confirmé !',
                message='Votre adresse email a été confirmée. Votre compte est en attente de validation par un administrateur.',
                notification_type=Notification.TYPE_SUCCESS,
            )
        except Exception:
            pass

        if unconfirmed_user_id:
            # Came from blocked login — log the user in now
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Email confirmé ! Bienvenue.')
            return redirect(reverse('dashboard:user_dashboard'))

        messages.success(request, 'Email confirmé ! Vous pouvez maintenant vous connecter.')
        return redirect('accounts:login')


class EmailVerifyResendView(View):

    @method_decorator(ratelimit(key='ip', rate='3/h', block=True))
    def post(self, request):
        user = None

        code_id = request.session.get('email_verify_code_id')
        if code_id:
            try:
                old_code = EmailVerificationCode.objects.select_related('user').get(pk=code_id)
                user = old_code.user
            except EmailVerificationCode.DoesNotExist:
                pass

        if not user:
            user_id = request.session.get('unconfirmed_login_user_id')
            if user_id:
                try:
                    user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    pass

        if not user:
            messages.error(request, 'Session expirée. Recommencez.')
            return redirect('accounts:login')

        EmailVerificationCode.objects.filter(user=user, is_used=False).update(is_used=True)
        code_obj = EmailVerificationCode.objects.create(
            user=user,
            code=str(random.randint(100000, 999999)),
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        try:
            send_email_verification_code_email(user, code_obj.code)
        except Exception:
            pass
        request.session['email_verify_code_id'] = code_obj.pk
        messages.success(request, 'Un nouveau code a été envoyé à votre email. Valable 15 minutes.')
        return redirect('accounts:email_verify')


class PasswordResetRequestView(View):
    template_name = 'accounts/password_reset_request.html'

    def get(self, request):
        return render(request, self.template_name, {'form': PasswordResetRequestForm()})

    @method_decorator(ratelimit(key='ip', rate='5/h', block=True))
    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.get(email__iexact=email)
            # Invalider les anciens codes non utilisés
            PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)
            code_obj = PasswordResetCode.objects.create(
                user=user,
                code=str(random.randint(100000, 999999)),
                expires_at=timezone.now() + timedelta(minutes=15),
            )
            try:
                send_password_reset_code_email(user, code_obj.code)
            except Exception:
                pass
            request.session['pwd_reset_code_id'] = code_obj.pk
            messages.success(request, f'Un code à 6 chiffres a été envoyé à {email}. Valable 15 minutes.')
            return redirect('accounts:password_reset_verify')
        return render(request, self.template_name, {'form': form})


class PasswordResetVerifyView(View):
    template_name = 'accounts/password_reset_verify.html'

    def get(self, request):
        if 'pwd_reset_code_id' not in request.session:
            return redirect('accounts:password_reset')
        return render(request, self.template_name, {'form': PasswordResetCodeForm()})

    @method_decorator(ratelimit(key='ip', rate='10/h', block=True))
    def post(self, request):
        code_id = request.session.get('pwd_reset_code_id')
        if not code_id:
            messages.error(request, 'Session expirée. Recommencez la procédure.')
            return redirect('accounts:password_reset')

        try:
            code_obj = PasswordResetCode.objects.get(pk=code_id)
        except PasswordResetCode.DoesNotExist:
            messages.error(request, 'Session invalide. Recommencez.')
            return redirect('accounts:password_reset')

        if not code_obj.is_valid():
            del request.session['pwd_reset_code_id']
            if code_obj.attempts >= PasswordResetCode.MAX_ATTEMPTS:
                messages.error(request, 'Trop de tentatives incorrectes. Faites une nouvelle demande.')
            else:
                messages.error(request, 'Ce code a expiré. Faites une nouvelle demande.')
            return redirect('accounts:password_reset')

        form = PasswordResetCodeForm(request.POST)
        if form.is_valid():
            entered = form.cleaned_data['code']
            if entered == code_obj.code:
                request.session['pwd_reset_verified_id'] = code_obj.pk
                del request.session['pwd_reset_code_id']
                return redirect('accounts:password_reset_new')
            else:
                code_obj.increment_attempts()
                remaining = PasswordResetCode.MAX_ATTEMPTS - code_obj.attempts
                if remaining <= 0:
                    messages.error(request, 'Trop de tentatives. Faites une nouvelle demande.')
                    del request.session['pwd_reset_code_id']
                    return redirect('accounts:password_reset')
                messages.error(request, f'Code incorrect. Il vous reste {remaining} tentative(s).')
        return render(request, self.template_name, {'form': form})


class PasswordResetNewPasswordView(View):
    template_name = 'accounts/password_reset_confirm.html'

    def _get_code_obj(self, request):
        verified_id = request.session.get('pwd_reset_verified_id')
        if not verified_id:
            return None
        try:
            code_obj = PasswordResetCode.objects.get(pk=verified_id, is_used=False)
            if timezone.now() > code_obj.expires_at:
                return None
            return code_obj
        except PasswordResetCode.DoesNotExist:
            return None

    def get(self, request):
        if not self._get_code_obj(request):
            messages.error(request, 'Session expirée. Recommencez la procédure.')
            return redirect('accounts:password_reset')
        return render(request, self.template_name, {'form': PasswordResetConfirmForm()})

    def post(self, request):
        code_obj = self._get_code_obj(request)
        if not code_obj:
            messages.error(request, 'Session expirée. Recommencez.')
            return redirect('accounts:password_reset')
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            user = code_obj.user
            user.set_password(form.cleaned_data['password'])
            user.save()
            code_obj.is_used = True
            code_obj.save(update_fields=['is_used'])
            del request.session['pwd_reset_verified_id']
            messages.success(request, 'Mot de passe modifié avec succès. Vous pouvez vous connecter.')
            return redirect('accounts:login')
        return render(request, self.template_name, {'form': form})


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


def _mask_email(email):
    parts = email.split('@')
    if len(parts) != 2:
        return email
    local, domain = parts
    masked_local = local[0] + '***' if len(local) > 1 else '***'
    domain_parts = domain.split('.')
    masked_domain = (domain_parts[0][0] + '***.' + '.'.join(domain_parts[1:])) if len(domain_parts) > 1 else domain
    return f'{masked_local}@{masked_domain}'


def _award_invitation_points(user):
    """Award points to inviter when invited user's account is verified."""
    profile = user.profile
    if not profile.invited_by:
        return

    inviter = profile.invited_by
    inviter_profile = inviter.profile

    # Already rewarded for this specific user
    if PointTransaction.objects.filter(
        user=inviter,
        category=PointTransaction.CAT_INVITATION,
        reason__icontains=user.username,
    ).exists():
        return

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
        message=f'{user.username} a rejoint et vérifié son compte. +{points} points.',
        notification_type=Notification.TYPE_POINTS,
    )


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


# ─── Account Verification Views ───────────────────────────────────────────────

@login_required
def verification_request_view(request):
    """User requests account verification — admin sends code manually by email."""
    user = request.user
    if user.is_email_verified:
        messages.info(request, 'Votre compte est déjà vérifié.')
        return redirect('dashboard:user_dashboard')

    # Check if there's already a pending/submitted request
    existing = AccountVerificationRequest.objects.filter(
        user=user
    ).exclude(status=AccountVerificationRequest.STATUS_REJECTED).order_by('-created_at').first()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'request' and (not existing or existing.status == AccountVerificationRequest.STATUS_REJECTED):
            req = AccountVerificationRequest.objects.create(user=user)
            req.generate_code()
            messages.success(
                request,
                'Votre demande a été envoyée. L\'admin vous enverra un code à 6 chiffres par email. '
                'Revenez ici pour saisir ce code.'
            )
            return redirect('accounts:verification_request')

        if action == 'submit_code' and existing and existing.status == AccountVerificationRequest.STATUS_PENDING:
            code = request.POST.get('code', '').strip()
            if not code:
                messages.error(request, 'Veuillez entrer le code reçu par email.')
            else:
                existing.entered_code = code
                existing.status = AccountVerificationRequest.STATUS_CODE_ENTERED
                existing.save()
                messages.success(
                    request,
                    'Code soumis. En attente de validation par l\'administrateur. '
                    'Votre compte sera activé dès que l\'admin valide votre demande.'
                )
            return redirect('accounts:verification_request')

        if action == 'new_request':
            # Allow user to restart the process
            if existing:
                existing.delete()
            req = AccountVerificationRequest.objects.create(user=user)
            req.generate_code()
            messages.success(request, 'Nouvelle demande de vérification envoyée.')
            return redirect('accounts:verification_request')

    return render(request, 'accounts/verification_request.html', {
        'existing_request': existing,
    })
