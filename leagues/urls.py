from django.urls import path

from . import views

app_name = 'leagues'

urlpatterns = [
    path('', views.league_list, name='league_list'),
    path('creer/', views.league_create, name='league_create'),
    path('<int:pk>/', views.league_detail, name='league_detail'),
    path('<int:pk>/ajouter/', views.league_add_participant, name='league_add_participant'),
    path('<int:pk>/retirer/<int:participant_pk>/', views.league_remove_participant, name='league_remove_participant'),
    path('<int:pk>/demarrer/', views.league_start, name='league_start'),
    path('<int:pk>/match/<int:match_pk>/soumettre/', views.match_submit_result, name='match_submit_result'),
    path('<int:pk>/match/<int:match_pk>/valider/', views.match_validate, name='match_validate'),
    path('<int:pk>/match/<int:match_pk>/refuser/', views.match_reject, name='match_reject'),
]
