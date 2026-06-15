from django.urls import path
from . import views

app_name = 'rewards'

urlpatterns = [
    path('exchange/', views.exchange_page, name='exchange'),
    path('exchange/create/', views.create_exchange, name='create_exchange'),
    path('my-redemptions/', views.my_redemptions, name='my_redemptions'),
    path('<int:pk>/', views.reward_detail, name='detail'),
    path('<int:pk>/redeem/', views.redeem_reward, name='redeem'),
]
