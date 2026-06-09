from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import User, UserProfile, EmailVerificationToken
from .emails import send_verification_email


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if created and not instance.is_staff:
        token = EmailVerificationToken.objects.create(
            user=instance,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        send_verification_email(instance, token)
