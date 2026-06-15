from django.core.management.base import BaseCommand
from rewards.models import Reward


class Command(BaseCommand):
    help = 'Delete all rewards from the catalog'

    def handle(self, *args, **options):
        count, _ = Reward.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} reward(s) from catalog.'))
