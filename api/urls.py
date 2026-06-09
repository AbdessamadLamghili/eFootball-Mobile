from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from . import views

app_name = 'api'

urlpatterns = [
    # Auth / JWT
    path('auth/register/', views.RegisterAPIView.as_view(), name='register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Profile
    path('profile/', views.ProfileAPIView.as_view(), name='profile'),
    path('profile/transactions/', views.PointTransactionListAPIView.as_view(), name='transactions'),
    path('dashboard/', views.dashboard_summary, name='dashboard'),

    # Rewards
    path('rewards/', views.RewardListAPIView.as_view(), name='reward_list'),
    path('rewards/<int:pk>/', views.RewardDetailAPIView.as_view(), name='reward_detail'),
    path('rewards/<int:pk>/redeem/', views.RedeemRewardAPIView.as_view(), name='redeem'),
    path('rewards/my-redemptions/', views.MyRedemptionsAPIView.as_view(), name='my_redemptions'),

    # Missions
    path('missions/', views.MissionListAPIView.as_view(), name='mission_list'),

    # Notifications
    path('notifications/', views.NotificationListAPIView.as_view(), name='notification_list'),
    path('notifications/<int:pk>/read/', views.MarkNotificationReadAPIView.as_view(), name='notification_read'),
    path('notifications/mark-all-read/', views.MarkAllNotificationsReadAPIView.as_view(), name='notifications_read_all'),
]
