from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/users/<uuid:pk>/', views.admin_user_detail, name='admin_user_detail'),
    path('admin-panel/users/<uuid:pk>/action/', views.admin_user_action, name='admin_user_action'),
    path('admin-panel/redemptions/', views.admin_redemptions, name='admin_redemptions'),
    path('admin-panel/redemptions/<int:pk>/action/', views.admin_redemption_action, name='admin_redemption_action'),
    # Exchange management
    path('admin-panel/exchanges/', views.admin_exchanges, name='admin_exchanges'),
    path('admin-panel/exchanges/<int:pk>/action/', views.admin_exchange_action, name='admin_exchange_action'),
    # Mission management
    path('admin-panel/missions/', views.admin_missions, name='admin_missions'),
    path('admin-panel/missions/add/', views.admin_mission_add, name='admin_mission_add'),
    path('admin-panel/missions/<int:pk>/edit/', views.admin_mission_edit, name='admin_mission_edit'),
    path('admin-panel/missions/<int:pk>/delete/', views.admin_mission_delete, name='admin_mission_delete'),
    path('admin-panel/missions/<int:pk>/toggle/', views.admin_mission_toggle, name='admin_mission_toggle'),
    # Mission request management
    path('admin-panel/mission-requests/', views.admin_mission_requests, name='admin_mission_requests'),
    path('admin-panel/mission-requests/<int:pk>/action/', views.admin_mission_request_action, name='admin_mission_request_action'),
    path('admin-panel/verifications/', views.admin_verifications, name='admin_verifications'),
    path('admin-panel/verifications/set-method/', views.admin_set_verification_method, name='admin_set_verification_method'),
    path('admin-panel/verifications/<int:pk>/set-code/', views.admin_set_verification_code, name='admin_set_verification_code'),
    path('admin-panel/verifications/<int:pk>/action/', views.admin_verification_action, name='admin_verification_action'),
]
