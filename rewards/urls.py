from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('', views.reward_catalog, name='catalog'),
    path('<int:pk>/', views.reward_detail, name='detail'),
    path('<int:pk>/redeem/', views.redeem_reward, name='redeem'),
    path('my-redemptions/', views.my_redemptions, name='my_redemptions'),
]
