import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'email@exemplu.com', 'autocomplete': 'email'}),
    )

    class Meta:
        model  = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()

        # validari de lungime si format
        if len(username) < 3:
            raise ValidationError('Username-ul trebuie sa aiba cel putin 3 caractere.')
        if len(username) > 20:
            raise ValidationError('Username-ul nu poate depasi 20 de caractere.')
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', username):
            raise ValidationError(
                'Username-ul poate contine doar litere, cifre, _ si -, '
                'si trebuie sa inceapa cu o litera.'
            )
        # verificam daca username-ul e deja folosit (case-insensitive)
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Acest username este deja folosit.')

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        # un singur cont per adresa de email
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Exista deja un cont cu aceasta adresa de email.')

        return email

    def save(self, commit=True):
        user       = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
