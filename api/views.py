from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from rewards.models import Reward, RedemptionRequest
from missions.models import Mission
from notifications.models import Notification
from .serializers import (
    UserSerializer, RegisterSerializer, RewardSerializer,
    RedemptionRequestSerializer, MissionSerializer,
    NotificationSerializer, PointTransactionSerializer,
)


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Compte créé. Vérifiez votre email.',
        }, status=status.HTTP_201_CREATED)


class ProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


class RewardListAPIView(generics.ListAPIView):
    serializer_class = RewardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Reward.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


class RewardDetailAPIView(generics.RetrieveAPIView):
    serializer_class = RewardSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Reward.objects.filter(is_active=True)


class RedeemRewardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        user = request.user
        if not user.can_redeem:
            return Response({'error': 'Email non vérifié ou compte suspendu.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            reward = Reward.objects.get(pk=pk, is_active=True)
        except Reward.DoesNotExist:
            return Response({'error': 'Récompense introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if not reward.is_available:
            return Response({'error': 'Récompense non disponible.'}, status=status.HTTP_400_BAD_REQUEST)

        profile = user.profile
        if profile.points_balance < reward.points_cost:
            return Response({
                'error': f'Solde insuffisant. Vous avez {profile.points_balance} pts, il faut {reward.points_cost} pts.'
            }, status=status.HTTP_400_BAD_REQUEST)

        profile.deduct_points(reward.points_cost, f'Demande récompense : {reward.name}')
        redemption = RedemptionRequest.objects.create(
            user=user, reward=reward, points_spent=reward.points_cost,
        )
        if reward.quantity_available > 0:
            reward.decrement_quantity()

        return Response(
            RedemptionRequestSerializer(redemption, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


class MyRedemptionsAPIView(generics.ListAPIView):
    serializer_class = RedemptionRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RedemptionRequest.objects.filter(user=self.request.user).select_related('reward')


class MissionListAPIView(generics.ListAPIView):
    serializer_class = MissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Mission.objects.filter(is_active=True)
        mission_type = self.request.query_params.get('type')
        if mission_type:
            qs = qs.filter(mission_type=mission_type)
        return qs


class NotificationListAPIView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MarkNotificationReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        notif.mark_read()
        return Response({'status': 'ok'})


class MarkAllNotificationsReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.notifications.filter(is_read=False).update(is_read=True)
        return Response({'status': 'ok'})


class PointTransactionListAPIView(generics.ListAPIView):
    serializer_class = PointTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.point_transactions.all()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_summary(request):
    user = request.user
    profile = user.profile
    return Response({
        'username': user.username,
        'email': user.email,
        'efootball_id': user.efootball_id,
        'points_balance': profile.points_balance,
        'level': profile.level,
        'current_streak': profile.current_streak,
        'unread_notifications': user.notifications.filter(is_read=False).count(),
        'pending_redemptions': user.redemptions.filter(status=RedemptionRequest.STATUS_PENDING).count(),
    })
