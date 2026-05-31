import json
import random
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.views import PasswordResetConfirmView
from django.core import signing
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .forms import RegisterForm
from .models import MoodSession, Recommendation, TrackCache, TrackFeedback, UserPreferences
from .services import (
    get_lastfm_tracks, get_artist_tracks_by_mood,
    get_spotify_token, get_spotify_link,
    search_lastfm_track, get_similar_tracks,
)
from analyzer import get_sentiment_score, get_context_tag

# ---------------------------------------------------------------------------
# Genre catalogue (shared between preferences page and recommendations)
# ---------------------------------------------------------------------------

AVAILABLE_GENRES = [
    {"id": "rock",        "label": "Rock",        "emoji": "🎸"},
    {"id": "pop",         "label": "Pop",         "emoji": "🎵"},
    {"id": "hip hop",     "label": "Hip Hop",     "emoji": "🎤"},
    {"id": "jazz",        "label": "Jazz",        "emoji": "🎷"},
    {"id": "electronic",  "label": "Electronic",  "emoji": "🎧"},
    {"id": "classical",   "label": "Clasică",     "emoji": "🎻"},
    {"id": "lo-fi",       "label": "Lo-Fi",       "emoji": "🌙"},
    {"id": "acoustic",    "label": "Acustic",     "emoji": "🪕"},
    {"id": "metal",       "label": "Metal",       "emoji": "🤘"},
    {"id": "indie",       "label": "Indie",       "emoji": "🌿"},
    {"id": "rnb",         "label": "R\u0026B",         "emoji": "💜"},
    {"id": "soul",        "label": "Soul",        "emoji": "✨"},
    {"id": "country",     "label": "Country",     "emoji": "🤠"},
    {"id": "reggae",      "label": "Reggae",      "emoji": "🌴"},
    {"id": "blues",       "label": "Blues",       "emoji": "🎺"},
    {"id": "folk",        "label": "Folk",        "emoji": "🪕"},
    {"id": "punk",        "label": "Punk",        "emoji": "⚡"},
    {"id": "alternative", "label": "Alternative", "emoji": "🎭"},
    {"id": "dance",       "label": "Dance",       "emoji": "💃"},
    {"id": "ambient",     "label": "Ambient",     "emoji": "🌊"},
    {"id": "latin",       "label": "Latin",       "emoji": "🕺"},
    {"id": "trap",        "label": "Trap",        "emoji": "🔊"},
    {"id": "workout",     "label": "Workout",     "emoji": "💪"},
    {"id": "sleep",       "label": "Sleep",       "emoji": "😴"},
    {"id": "party",       "label": "Party",       "emoji": "🎉"},
]

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
                if '@' in username:
                    unverified = User.objects.get(email__iexact=username)
                else:
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
        req_artist = request.POST.get('artist', '').strip()
        
        if not text:
            return render(request, 'mood/mood.html', {'error': 'Scrie ceva despre starea ta.'})

        score = get_sentiment_score(text)
        if score <= 0.44:
            tag = 'sad'
        elif score <= 0.70:
            tag = 'chillout'
        else:
            tag = 'happy'

        context_t = get_context_tag(text)

        # Fall back to a random user genre preference if AI found nothing
        if not context_t:
            try:
                prefs = request.user.preferences
                if prefs.genres:
                    context_t = random.choice(prefs.genres)
            except UserPreferences.DoesNotExist:
                pass

        session = MoodSession.objects.create(
            user=request.user,
            user_input=text,
            score=score,
            mood_tag=tag,
            context_tag=context_t,
            artist_requested=req_artist if req_artist else None,
        )

        # Get all track names the user has ever received to avoid duplicates
        past_recommendations = Recommendation.objects.filter(session__user=request.user)
        excluded_track_names = set(past_recommendations.values_list('track_name', flat=True))

        if req_artist:
            tracks = get_artist_tracks_by_mood(req_artist, tag, excluded=excluded_track_names)
        else:
            tracks = get_lastfm_tracks(tag, context=context_t, excluded=excluded_track_names)
            
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

    # Build a dict of {recommendation_id: liked (True/False/None)}
    user_feedback = {
        fb.recommendation_id: fb.liked
        for fb in TrackFeedback.objects.filter(
            user=request.user,
            recommendation__in=tracks,
        )
    }

    return render(request, 'mood/results.html', {
        'session':       session,
        'tracks':        tracks,
        'user_feedback': user_feedback,
    })


@login_required
def history(request):
    sessions = (
        MoodSession.objects
        .filter(user=request.user)
        .prefetch_related('recommendations')
    )

    # All track IDs the user has rated, for the history view
    all_rec_ids = Recommendation.objects.filter(session__user=request.user).values_list('id', flat=True)
    user_feedback = {
        fb.recommendation_id: fb.liked
        for fb in TrackFeedback.objects.filter(user=request.user, recommendation_id__in=all_rec_ids)
    }

    return render(request, 'mood/history.html', {
        'sessions':      sessions,
        'user_feedback': user_feedback,
    })


@login_required
@require_POST
def feedback_view(request, recommendation_id):
    """Toggle 👍/👎 on a track. Returns JSON {liked: true|false|null}."""
    rec = get_object_or_404(Recommendation, id=recommendation_id, session__user=request.user)
    liked_value = request.POST.get('liked')          # 'true' or 'false'
    liked = liked_value == 'true'

    existing = TrackFeedback.objects.filter(user=request.user, recommendation=rec).first()

    if existing:
        if existing.liked == liked:
            # Same button clicked again → remove vote
            existing.delete()
            return JsonResponse({'liked': None})
        else:
            # Opposite button → switch
            existing.liked = liked
            existing.save()
            return JsonResponse({'liked': liked})
    else:
        TrackFeedback.objects.create(user=request.user, recommendation=rec, liked=liked)
        return JsonResponse({'liked': liked})


@login_required
def profile_view(request):
    sessions = MoodSession.objects.filter(user=request.user)

    total_sessions = sessions.count()

    # Calculate mood distribution
    distribution = sessions.values('mood_tag').annotate(count=Count('id')).order_by('-count')

    dominant_mood = None
    if distribution:
        dominant_mood = distribution[0]['mood_tag']

    # Serialize sessions chronologically for the Chart.js mood timeline
    chart_sessions = sessions.order_by('created_at')
    chart_data = json.dumps([
        {
            'date':    s.created_at.strftime('%d %b %Y, %H:%M'),
            'score':   round(s.score, 2),
            'mood':    s.mood_tag,
            'snippet': (s.user_input[:55] + '…') if len(s.user_input) > 55 else s.user_input,
        }
        for s in chart_sessions
    ])

    # Top liked artists (from 👍 feedback)
    from django.db.models import Q
    liked_artists = (
        TrackFeedback.objects
        .filter(user=request.user, liked=True)
        .values('recommendation__artist_name')
        .annotate(count=Count('id'))
        .order_by('-count')[:3]
    )

    # User genre preferences — resolve IDs to display labels
    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    genre_label_map = {g['id']: g['label'] for g in AVAILABLE_GENRES}
    liked_genres = [genre_label_map.get(gid, gid) for gid in (prefs.genres or [])]

    context = {
        'total_sessions': total_sessions,
        'dominant_mood':  dominant_mood,
        'distribution':   distribution,
        'chart_data':     chart_data,
        'liked_artists':  liked_artists,
        'liked_genres':   liked_genres,
    }

    return render(request, 'mood/profile.html', context)


# ---------------------------------------------------------------------------
# Sound-alike discovery views
# ---------------------------------------------------------------------------

@login_required
def search_view(request):
    """Render the song search / sound-alike discovery page."""
    return render(request, 'mood/search.html')


@login_required
def track_suggest_ajax(request):
    """AJAX autocomplete: return JSON list of tracks matching the query."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    results = search_lastfm_track(q)
    return JsonResponse(results, safe=False)


@login_required
def similar_tracks_ajax(request):
    """AJAX: given track + artist, return JSON list of similar tracks with Spotify links."""
    track  = request.GET.get('track',  '').strip()
    artist = request.GET.get('artist', '').strip()
    if not track or not artist:
        return JsonResponse({'error': 'Parametri lipsă.'}, status=400)
    tracks = get_similar_tracks(track, artist)
    return JsonResponse(tracks, safe=False)


# ---------------------------------------------------------------------------
# Genre Preferences
# ---------------------------------------------------------------------------

@login_required
def preferences_view(request):
    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    valid_ids = {g['id'] for g in AVAILABLE_GENRES}

    if request.method == 'POST':
        selected = request.POST.getlist('genres')
        prefs.genres = [g for g in selected if g in valid_ids]
        prefs.save()
        messages.success(request, 'Preferințele muzicale au fost salvate! 🎵')
        return redirect('preferences')

    return render(request, 'mood/preferences.html', {
        'prefs':            prefs,
        'available_genres': AVAILABLE_GENRES,
    })


# ---------------------------------------------------------------------------
# Delete Account
# ---------------------------------------------------------------------------

@login_required
@require_POST
def delete_account_view(request):
    password = request.POST.get('password', '')
    user     = request.user

    if not user.check_password(password):
        messages.error(request, 'Parolă incorectă. Contul nu a fost șters.')
        return redirect('profile')

    # Cascade deletes all related data automatically
    logout(request)
    user.delete()
    return render(request, 'mood/account_deleted.html')
