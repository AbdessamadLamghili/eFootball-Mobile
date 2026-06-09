from django.core.management.base import BaseCommand
from missions.models import Mission
from rewards.models import Reward


MISSIONS = [
    # Quotidiennes
    dict(title="Connexion quotidienne", description="Connectez-vous sur la plateforme aujourd'hui.", reward_points=10, mission_type=Mission.TYPE_DAILY, icon="calendar-check"),
    dict(title="Partager votre score", description="Partagez votre score eFootball du jour sur le forum.", reward_points=15, mission_type=Mission.TYPE_DAILY, icon="share-alt"),
    dict(title="Jouer 3 matchs", description="Disputez au moins 3 matchs eFootball aujourd'hui.", reward_points=20, mission_type=Mission.TYPE_DAILY, icon="futbol"),
    dict(title="Gagner un match", description="Remportez au moins une victoire en match en ligne.", reward_points=25, mission_type=Mission.TYPE_DAILY, icon="trophy"),
    # Hebdomadaires
    dict(title="Gagner 5 matchs cette semaine", description="Remportez 5 matchs en ligne au cours de la semaine.", reward_points=80, mission_type=Mission.TYPE_WEEKLY, icon="star"),
    dict(title="Streak de 7 jours", description="Connectez-vous 7 jours d'affilée pour obtenir votre bonus de streak.", reward_points=50, mission_type=Mission.TYPE_WEEKLY, icon="fire"),
    dict(title="Atteindre le top 100", description="Entrez dans le top 100 du classement hebdomadaire eFootball.", reward_points=150, mission_type=Mission.TYPE_WEEKLY, icon="medal"),
    dict(title="Inviter un ami", description="Invitez un ami à rejoindre eFootball Rewards cette semaine.", reward_points=60, mission_type=Mission.TYPE_WEEKLY, icon="user-plus"),
    # Permanentes
    dict(title="Première inscription", description="Créez votre compte sur eFootball Rewards.", reward_points=50, mission_type=Mission.TYPE_PERMANENT, icon="user-check"),
    dict(title="Vérifier son email", description="Vérifiez votre adresse email pour activer votre compte.", reward_points=30, mission_type=Mission.TYPE_PERMANENT, icon="envelope-check"),
    dict(title="Atteindre le niveau Argent", description="Accumulez 500 points pour passer au niveau Argent.", reward_points=100, mission_type=Mission.TYPE_PERMANENT, icon="medal"),
    dict(title="Atteindre le niveau Or", description="Accumulez 1 500 points pour passer au niveau Or.", reward_points=200, mission_type=Mission.TYPE_PERMANENT, icon="trophy"),
    dict(title="Streak de 30 jours", description="Connectez-vous 30 jours consécutifs pour le grand bonus.", reward_points=300, mission_type=Mission.TYPE_PERMANENT, icon="crown"),
    dict(title="Premier échange", description="Réclamez votre première récompense dans le catalogue.", reward_points=75, mission_type=Mission.TYPE_PERMANENT, icon="gift"),
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
    help = 'Seed initial missions and rewards'

    def handle(self, *args, **options):
        created_m = 0
        for data in MISSIONS:
            _, created = Mission.objects.get_or_create(title=data['title'], defaults=data)
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
