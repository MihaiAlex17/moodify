from django.contrib import admin
from .models import MoodSession, Recommendation, TrackCache


@admin.register(MoodSession)
class MoodSessionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'mood_tag', 'score', 'created_at']
    list_filter   = ['mood_tag', 'created_at']
    search_fields = ['user__username', 'user_input']


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ['rank', 'track_name', 'artist_name', 'session']


@admin.register(TrackCache)
class TrackCacheAdmin(admin.ModelAdmin):
    list_display = ['track_name', 'artist_name', 'cached_at']
