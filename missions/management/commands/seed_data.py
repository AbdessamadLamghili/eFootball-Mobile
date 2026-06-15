from django.core.management.base import BaseCommand
from missions.models import Mission
from rewards.models import Reward


MISSIONS = [
    dict(
        title="Suivre Instagram officiel",
        description="Suivez notre compte Instagram officiel et cliquez sur « J'ai suivi » pour valider la mission. Un administrateur vérifiera votre demande.",
        reward_points=100,
        mission_code=Mission.CODE_INSTAGRAM,
        validation_type=Mission.VALIDATION_MANUAL,
        icon="instagram",
        link="https://instagram.com/efootball",
    ),
    dict(
        title="Compléter le profil",
        description="Ajoutez un avatar, renseignez votre eFootball ID et complétez votre profil pour obtenir vos points. Validation automatique.",
        reward_points=100,
        mission_code=Mission.CODE_PROFILE,
        validation_type=Mission.VALIDATION_AUTO,
        icon="user-check",
    ),
    dict(
        title="Visiter le site 3 jours consécutifs",
        description="Connectez-vous et réclamez votre récompense quotidienne 3 jours de suite. Validation automatique après votre 3ème connexion consécutive.",
        reward_points=150,
        mission_code=Mission.CODE_STREAK_3,
        validation_type=Mission.VALIDATION_AUTO,
        icon="calendar-check",
    ),
    dict(
        title="Visiter le site 7 jours consécutifs",
        description="Connectez-vous et réclamez votre récompense quotidienne 7 jours de suite. Validation automatique après votre 7ème connexion consécutive.",
        reward_points=250,
        mission_code=Mission.CODE_STREAK_7,
        validation_type=Mission.VALIDATION_AUTO,
        icon="fire",
    ),
    dict(
        title="Inviter des amis",
        description="Partagez votre code d'invitation. Gagnez 50 points par ami qui crée un compte et vérifie son email. Maximum 10 invitations par mois.",
        reward_points=50,
        mission_code=Mission.CODE_INVITE,
        validation_type=Mission.VALIDATION_AUTO,
        icon="user-plus",
        max_monthly_completions=10,
    ),
    dict(
        title="Toutes les missions terminées",
        description="Terminez toutes les missions actives pour recevoir ce bonus spécial. Validation automatique.",
        reward_points=300,
        mission_code=Mission.CODE_ALL,
        validation_type=Mission.VALIDATION_AUTO,
        icon="crown",
    ),
]

REWARDS = [
    dict(name="100 GP eFootball", description="100 GP (Game Points) utilisables dans eFootball Mobile.", points_cost=200, category=Reward.CATEGORY_INGAME, quantity_available=-1),
    dict(name="500 GP eFootball", description="500 GP pour débloquer des joueurs ou des packs.", points_cost=800, category=Reward.CATEGORY_INGAME, quantity_available=-1),
    dict(name="1 000 GP eFootball", description="1 000 GP — Pack de joueurs premium.", points_cost=1500, category=Reward.CATEGORY_INGAME, quantity_available=-1),
    dict(name="Pack Épique x1", description="Un pack de joueurs épiques aléatoires pour votre équipe.", points_cost=500, category=Reward.CATEGORY_INGAME, quantity_available=50),
    dict(name="Pack Légende x1", description="Un pack de joueurs légendaires pour booster votre équipe.", points_cost=1200, category=Reward.CATEGORY_INGAME, quantity_available=20),
    dict(name="Carte cadeau 5€", description="Carte cadeau Google Play ou App Store de 5€.", points_cost=2000, category=Reward.CATEGORY_GIFT, quantity_available=10),
    dict(name="Carte cadeau 10€", description="Carte cadeau Google Play ou App Store de 10€.", points_cost=3500, category=Reward.CATEGORY_GIFT, quantity_available=5),
    dict(name="Pass Premium 30 jours", description="Abonnement Premium eFootball pour 30 jours — accès exclusif.", points_cost=3000, category=Reward.CATEGORY_PREMIUM, quantity_available=15),
]


class Command(BaseCommand):
    help = 'Seed real missions and rewards (replaces any fictional data)'

    def add_arguments(self, parser):
        parser.add_argument('--clear-missions', action='store_true', help='Delete all existing missions first')

    def handle(self, *args, **options):
        if options['clear_missions']:
            Mission.objects.all().delete()
            self.stdout.write(self.style.WARNING('[seed_data] Missions existantes supprimées.'))

        created_m = 0
        for data in MISSIONS:
            _, created = Mission.objects.get_or_create(
                mission_code=data['mission_code'],
                defaults=data,
            )
            if created:
                created_m += 1

        created_r = 0
        for data in REWARDS:
            _, created = Reward.objects.get_or_create(name=data['name'], defaults=data)
            if created:
                created_r += 1

        self.stdout.write(self.style.SUCCESS(
            f'[seed_data] {created_m} missions créées, {created_r} récompenses créées.'
        ))
