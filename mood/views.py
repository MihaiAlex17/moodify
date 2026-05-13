from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.views import PasswordResetConfirmView
from django.core import signing
from django.core.mail import send_mail
from django.conf import settings

from .forms import RegisterForm
from .models import MoodSession, Recommendation, TrackCache
from .services import get_lastfm_tracks, get_spotify_token, get_spotify_link
from analyzer import get_sentiment_score

# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """Redirects to login with a success message instead of the complete page."""
    template_name = 'mood/password_reset_confirm.html'
    success_url   = '/login/'

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Parola a fost schimbată cu succes! Te poți autentifica acum cu noua parolă.'
        )
        return response

def register_view(request):
    if request.user.is_authenticated:
        return redirect('mood_input')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Create inactive user until email is verified
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # Signed token valid for 24 h
            token      = signing.dumps({'user_id': user.id}, salt='email-verify')
            verify_url = request.build_absolute_uri(f'/verify/{token}/')

            send_mail(
                subject='Confirmă adresa de email — Moodify',
                message=(
                    f'Salut {user.username},\n\n'
                    f'Click pe linkul de mai jos pentru a confirma contul Moodify:\n\n'
                    f'{verify_url}\n\n'
                    f'Linkul este valabil 24 de ore.\n\n'
                    f'Dacă nu tu ai creat acest cont, ignoră acest email.\n\n'
                    f'— Echipa Moodify'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            return render(request, 'mood/verify_sent.html', {'email': user.email})
    else:
        form = RegisterForm()

    return render(request, 'mood/register.html', {'form': form})


def verify_email(request, token):
    try:
        data = signing.loads(token, salt='email-verify', max_age=86400)  # 24 h
        user = User.objects.get(id=data['user_id'])

        if not user.is_active:
            user.is_active = True
            user.save()

        # Log the user in directly after verification
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        return render(request, 'mood/verify_success.html', {'user': user})

    except signing.SignatureExpired:
        return render(request, 'mood/verify_failed.html', {
            'reason': 'Linkul a expirat (valabil 24 h). Înregistrează-te din nou.'
        })
    except (signing.BadSignature, User.DoesNotExist):
        return render(request, 'mood/verify_failed.html', {
            'reason': 'Link invalid sau corupt.'
        })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('mood_input')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user     = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('mood_input')
        else:
            # Give a helpful message if account exists but isn't verified
            try:
                unverified = User.objects.get(username__iexact=username)
                if not unverified.is_active and unverified.check_password(password):
                    error = 'Contul tău nu este activat. Verifică email-ul pentru linkul de confirmare.'
                else:
                    error = 'Username sau parolă incorecte.'
            except User.DoesNotExist:
                error = 'Username sau parolă incorecte.'

    return render(request, 'mood/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


# ---------------------------------------------------------------------------
# Main app views
# ---------------------------------------------------------------------------

@login_required
def mood_input(request):
    if request.method == 'POST':
        text = request.POST.get('mood_text', '').strip()
        if not text:
            return render(request, 'mood/mood.html', {'error': 'Scrie ceva despre starea ta.'})

        score = get_sentiment_score(text)
        if score <= 0.44:
            tag = 'sad'
        elif score <= 0.70:
            tag = 'chillout'
        else:
            tag = 'happy'

        session = MoodSession.objects.create(
            user=request.user,
            user_input=text,
            score=score,
            mood_tag=tag,
        )

        tracks = get_lastfm_tracks(tag)
        token  = get_spotify_token()

        for i, p in enumerate(tracks, 1):
            name   = p.get('name', '')
            artist = p.get('artist', {}).get('name', '')

            cached = TrackCache.objects.filter(track_name=name, artist_name=artist).first()
            if cached:
                spotify_url = cached.spotify_url
            else:
                spotify_url = get_spotify_link(token, name, artist)
                TrackCache.objects.get_or_create(
                    track_name=name,
                    artist_name=artist,
                    defaults={'spotify_url': spotify_url},
                )

            Recommendation.objects.create(
                session=session,
                track_name=name,
                artist_name=artist,
                spotify_url=spotify_url,
                rank=i,
            )

        return redirect('results', session_id=session.id)

    return render(request, 'mood/mood.html')


@login_required
def results(request, session_id):
    session = get_object_or_404(MoodSession, id=session_id, user=request.user)
    tracks  = session.recommendations.all()
    return render(request, 'mood/results.html', {'session': session, 'tracks': tracks})


@login_required
def history(request):
    sessions = (
        MoodSession.objects
        .filter(user=request.user)
        .prefetch_related('recommendations')
    )
    return render(request, 'mood/history.html', {'sessions': sessions})
