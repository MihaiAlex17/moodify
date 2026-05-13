from django.db import models
from django.contrib.auth.models import User


class MoodSession(models.Model):
    MOOD_CHOICES = [
        ('sad', 'Sad'),
        ('chillout', 'Chillout'),
        ('happy', 'Happy'),
    ]

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    user_input  = models.TextField()
    score            = models.FloatField()
    mood_tag         = models.CharField(max_length=20, choices=MOOD_CHOICES)
    context_tag      = models.CharField(max_length=50, blank=True, null=True)
    artist_requested = models.CharField(max_length=100, blank=True, null=True)
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
    rank        = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['rank']

    def __str__(self):
        return f"{self.rank}. {self.track_name} — {self.artist_name}"

    @property
    def has_spotify(self):
        return bool(self.spotify_url and self.spotify_url.startswith('http'))


class TrackCache(models.Model):
    track_name  = models.CharField(max_length=255)
    artist_name = models.CharField(max_length=255)
    spotify_url = models.URLField(max_length=500, blank=True)
    cached_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('track_name', 'artist_name')

    def __str__(self):
        return f"{self.track_name} — {self.artist_name}"
