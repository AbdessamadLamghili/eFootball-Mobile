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
]
