from django import forms
from django.contrib.auth import get_user_model

from .models import League, MatchResult

User = get_user_model()


class LeagueCreateForm(forms.ModelForm):
    class Meta:
        model = League
        fields = ['name', 'description', 'season', 'rules', 'logo', 'two_legs']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Ligue des Champions — Saison 1',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description de la ligue...',
            }),
            'season': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : Saison 1 — 2024',
            }),
            'rules': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Règlement de la ligue (optionnel)...',
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }


class AddParticipantForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='Joueur',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Sélectionner un joueur...',
    )
    team_name = forms.CharField(
        max_length=100,
        label="Nom de l'équipe",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex : Real Madrid CF',
        }),
    )

    def __init__(self, league, *args, **kwargs):
        super().__init__(*args, **kwargs)
        existing_ids = league.participants.values_list('user_id', flat=True)
        self.fields['user'].queryset = (
            User.objects.filter(is_active=True)
            .exclude(id__in=existing_ids)
            .order_by('username')
        )


class MatchResultForm(forms.ModelForm):
    home_score = forms.IntegerField(
        min_value=0, max_value=99,
        label='Score domicile',
        widget=forms.NumberInput(attrs={
            'class': 'form-control score-input',
            'placeholder': '0',
        }),
    )
    away_score = forms.IntegerField(
        min_value=0, max_value=99,
        label='Score extérieur',
        widget=forms.NumberInput(attrs={
            'class': 'form-control score-input',
            'placeholder': '0',
        }),
    )
    screenshot = forms.ImageField(
        label="Capture d'écran",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
    )

    class Meta:
        model = MatchResult
        fields = ['home_score', 'away_score', 'screenshot']


class RejectResultForm(forms.Form):
    rejection_reason = forms.CharField(
        label='Motif du refus',
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Motif du refus...',
        }),
    )
