from django.urls import path
from . import views

app_name = 'missions'

urlpatterns = [
    path('', views.mission_list, name='list'),
    path('<int:pk>/submit/', views.submit_mission, name='submit'),
]
