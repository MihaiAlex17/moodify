from django.db import models
from django.contrib.auth.models import User


class MoodSession(models.Model):
    MOOD_CHOICES = [
        ('sad', 'Sad'),
        ('chillout', 'Chillout'),
        ('happy', 'Happy'),
    ]

    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    user_input       = models.TextField()
    score            = models.FloatField()             # valoare 0.1 - 0.9
    mood_tag         = models.CharField(max_length=20, choices=MOOD_CHOICES)
    context_tag      = models.CharField(max_length=50, blank=True, null=True)   # gen detectat din text
    artist_requested = models.CharField(max_length=100, blank=True, null=True)  # artist completat de user
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.mood_tag} ({self.created_at:%d %b %Y})"


class Recommendation(models.Model):
    session     = models.ForeignKey(MoodSession, on_delete=models.CASCADE, related_name='recommendations')
    track_name  = models.CharField(max_length=255)
    artist_name = models.CharField(max_length=255)
    spotify_url = models.URLField(max_length=500, blank=True)
    rank        = models.PositiveSmallIntegerField()  # pozitia in lista (1-5)

    class Meta:
        ordering = ['rank']

    def __str__(self):
        return f"{self.rank}. {self.track_name} — {self.artist_name}"

    @property
    def has_spotify(self):
        # returneaza True daca piesa are un link Spotify valid
        return bool(self.spotify_url and self.spotify_url.startswith('http'))


class TrackCache(models.Model):
    """Stocheaza link-urile Spotify ca sa nu apelam API-ul de fiecare data."""
    track_name  = models.CharField(max_length=255)
    artist_name = models.CharField(max_length=255)
    spotify_url = models.URLField(max_length=500, blank=True)
    cached_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('track_name', 'artist_name')

    def __str__(self):
        return f"{self.track_name} — {self.artist_name}"


class TrackFeedback(models.Model):
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback')
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name='feedback')
    liked          = models.BooleanField()  # True = place, False = nu place
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recommendation')  # un singur vot per piesa per user

    def __str__(self):
        verdict = 'like' if self.liked else 'dislike'
        return f"{verdict} {self.user.username} -> {self.recommendation.track_name}"


class UserPreferences(models.Model):
    """Stocheaza genurile muzicale preferate ale utilizatorului."""
    user   = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    genres = models.JSONField(default=list, blank=True)  # ex: ["rock", "pop", "lo-fi"]

    def __str__(self):
        return f"{self.user.username} — preferinte ({len(self.genres)} genuri)"
