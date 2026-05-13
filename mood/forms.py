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

    # ── Username rules ──────────────────────────────────────────────────────
    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()

        if len(username) < 3:
            raise ValidationError('Username-ul trebuie să aibă cel puțin 3 caractere.')
        if len(username) > 20:
            raise ValidationError('Username-ul nu poate depăși 20 de caractere.')
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', username):
            raise ValidationError(
                'Username-ul poate conține doar litere, cifre, _ și -, '
                'și trebuie să înceapă cu o literă.'
            )
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Acest username este deja folosit.')

        return username

    # ── Email uniqueness ─────────────────────────────────────────────────────
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Există deja un cont cu această adresă de email.')

        return email

    def save(self, commit=True):
        user       = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
