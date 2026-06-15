from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # UserProfile.save() assigns a random default_avatar automatically
        UserProfile.objects.get_or_create(user=instance)
