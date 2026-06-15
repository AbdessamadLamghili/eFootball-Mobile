from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, UserProfile


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'}),
        label='Mot de passe',
        min_length=8,
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmer le mot de passe'}),
        label='Confirmer le mot de passe',
    )
    invitation_code = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: EFOOT-4582 (optionnel)'}),
        label='Code d\'invitation',
        required=False,
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'efootball_id']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom d\'utilisateur'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Adresse email'}),
            'efootball_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre ID eFootball (optionnel)'}),
        }
        labels = {
            'username': 'Nom d\'utilisateur',
            'email': 'Adresse email',
            'efootball_id': 'eFootball ID',
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Ce nom d\'utilisateur est déjà pris.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Un compte avec cet email existe déjà.')
        return email

    def clean_efootball_id(self):
        efootball_id = self.cleaned_data.get('efootball_id')
        if not efootball_id:
            return efootball_id
        if User.objects.filter(efootball_id__iexact=efootball_id).exists():
            raise ValidationError('Cet eFootball ID est déjà utilisé.')
        return efootball_id

    def clean_invitation_code(self):
        code = self.cleaned_data.get('invitation_code', '').strip().upper()
        if not code:
            return ''
        if not UserProfile.objects.filter(invitation_code__iexact=code).exists():
            raise ValidationError('Code d\'invitation invalide.')
        return code

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise ValidationError('Les mots de passe ne correspondent pas.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email ou nom d\'utilisateur'}),
        label='Email ou nom d\'utilisateur',
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'}),
        label='Mot de passe',
    )
    remember_me = forms.BooleanField(required=False, label='Se souvenir de moi')


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Votre adresse email'}),
        label='Adresse email',
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Aucun compte associé à cet email.')
        return email


class PasswordResetConfirmForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nouveau mot de passe'}),
        label='Nouveau mot de passe',
        min_length=8,
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmer le mot de passe'}),
        label='Confirmer le mot de passe',
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise ValidationError('Les mots de passe ne correspondent pas.')
        return cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'efootball_id']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'efootball_id': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'username': 'Nom d\'utilisateur',
            'efootball_id': 'eFootball ID',
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ce nom d\'utilisateur est déjà pris.')
        return username

    def clean_efootball_id(self):
        efootball_id = self.cleaned_data.get('efootball_id')
        if not efootball_id:
            return efootball_id
        qs = User.objects.filter(efootball_id__iexact=efootball_id).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Cet eFootball ID est déjà utilisé.')
        return efootball_id


class AvatarUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
