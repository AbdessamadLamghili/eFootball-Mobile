from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

ADMIN_EMAIL = 'admin@efootball.com'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'Admin@eFootball2024!'


class Command(BaseCommand):
    help = 'Create the single site admin account (idempotent)'

    def handle(self, *args, **options):
        if User.objects.filter(email=ADMIN_EMAIL).exists():
            self.stdout.write(self.style.WARNING(f'Admin already exists: {ADMIN_EMAIL}'))
            return
        User.objects.create_superuser(
            email=ADMIN_EMAIL,
            username=ADMIN_USERNAME,
            password=ADMIN_PASSWORD,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Admin created — email: {ADMIN_EMAIL} / password: {ADMIN_PASSWORD}'
        ))
