from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def _send_email(subject, template_name, context, recipient_email):
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
    )
    email.attach_alternative(html_content, 'text/html')
    email.send(fail_silently=False)


def send_verification_email(user, token):
    verification_url = f"{settings.SITE_URL}/accounts/verify-email/{token.token}/"
    _send_email(
        subject=f'[{settings.SITE_NAME}] Vérifiez votre adresse email',
        template_name='emails/verify_email.html',
        context={
            'user': user,
            'verification_url': verification_url,
            'site_name': settings.SITE_NAME,
        },
        recipient_email=user.email,
    )


def send_password_reset_email(user, token):
    reset_url = f"{settings.SITE_URL}/accounts/password-reset/confirm/{token.token}/"
    _send_email(
        subject=f'[{settings.SITE_NAME}] Réinitialisation de votre mot de passe',
        template_name='emails/password_reset.html',
        context={
            'user': user,
            'reset_url': reset_url,
            'site_name': settings.SITE_NAME,
        },
        recipient_email=user.email,
    )


def send_reward_accepted_email(user, redemption):
    _send_email(
        subject=f'[{settings.SITE_NAME}] Votre demande de récompense a été acceptée',
        template_name='emails/reward_accepted.html',
        context={
            'user': user,
            'redemption': redemption,
            'site_name': settings.SITE_NAME,
        },
        recipient_email=user.email,
    )


def send_reward_rejected_email(user, redemption):
    _send_email(
        subject=f'[{settings.SITE_NAME}] Votre demande de récompense a été refusée',
        template_name='emails/reward_rejected.html',
        context={
            'user': user,
            'redemption': redemption,
            'site_name': settings.SITE_NAME,
        },
        recipient_email=user.email,
    )
