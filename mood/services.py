import random
import requests
import base64

LASTFM_API_KEY = "95711c703010c8da32826ad534adc6b8"
SPOTIFY_ID     = "1ca7f51e164b48e2bb2107c20bf915fd"
SPOTIFY_SECRET = "5ccf48475bcc48f4b449c9fe140f3dd7"

TAG_MAP = {
    "sad":      "sad songs",
    "chillout": "chillout",
    "happy":    "happy music",
}


def get_lastfm_tracks(tag: str, context: str = None, excluded: set = None) -> list:
    if excluded is None:
        excluded = set()
        
    base_tag = TAG_MAP.get(tag, tag)
    if context:
        if tag == 'sad':
            query_tag = f"sad {context}"
        elif tag == 'chillout':
            query_tag = f"chill {context}"
        elif tag == 'happy':
            query_tag = f"happy {context}"
        else:
            query_tag = context
    else:
        query_tag = base_tag
        
    url    = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "method":      "tag.gettoptracks",
        "tag":         query_tag,
        "api_key":     LASTFM_API_KEY,
        "format":      "json",
        "limit":       300,  # Fetch a huge pool
        "autocorrect": 1,
    }
    try:
        data   = requests.get(url, params=params, timeout=10).json()
        tracks = data.get("tracks", {}).get("track", [])
        
        # If combined tag (e.g., "sad rock") returns nothing, fallback to just the mood ("sad songs")
        if not tracks and context:
            params["tag"] = base_tag
            tracks = requests.get(url, params=params, timeout=10).json().get("tracks", {}).get("track", [])
            
        if not tracks:
            params["tag"] = "pop"
            tracks = requests.get(url, params=params, timeout=10).json().get("tracks", {}).get("track", [])
        if isinstance(tracks, dict):
            tracks = [tracks]
            
        # Filter out tracks the user has already received
        fresh_tracks = [t for t in tracks if t.get("name") not in excluded]
        
        # Fallback just in case they somehow exhausted all 300 top tracks
        if len(fresh_tracks) < 5:
            fresh_tracks = tracks
            
        # Limit to the top 20 most popular fresh tracks to guarantee we don't pick obscure/weird songs
        popular_fresh_pool = fresh_tracks[:20]
            
        # Shuffle and pick 5 random completely fresh tracks from the popular pool
        return random.sample(popular_fresh_pool, min(5, len(popular_fresh_pool)))
    except Exception:
        return []


from concurrent.futures import ThreadPoolExecutor

def _check_track_mood(track: dict, expected_mood: str) -> dict:
    """Helper function to fetch tags for a single track and check if it matches the mood."""
    try:
        url = "https://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "track.getInfo",
            "artist": track["artist"]["name"],
            "track": track["name"],
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "autocorrect": 1
        }
        data = requests.get(url, params=params, timeout=5).json()
        tags_data = data.get("track", {}).get("toptags", {}).get("tag", [])
        if isinstance(tags_data, dict):
            tags_data = [tags_data]
            
        tags = [t.get("name", "").lower() for t in tags_data]
        
        # Check if the expected mood tag is in the track's tags
        target = TAG_MAP.get(expected_mood, expected_mood)
        if any(target in t for t in tags) or any(expected_mood in t for t in tags):
            return track
    except Exception:
        pass
    return None

def get_artist_tracks_by_mood(artist: str, mood_tag: str, excluded: set = None) -> list:
    """Fetches top tracks by an artist and filters them by mood (Option B)."""
    if excluded is None:
        excluded = set()
        
    url = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "artist.getTopTracks",
        "artist": artist,
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": 50,  # Fetch top 50 to have enough to filter
        "autocorrect": 1,
    }
    try:
        data = requests.get(url, params=params, timeout=10).json()
        tracks = data.get("toptracks", {}).get("track", [])
        if isinstance(tracks, dict):
            tracks = [tracks]
            
        # Filter out previously received tracks
        fresh_tracks = [t for t in tracks if t.get("name") not in excluded]
        
        matched_tracks = []
        # Use ThreadPoolExecutor to check tags for all fresh tracks concurrently (lightning fast)
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Map the helper function over the fresh tracks
            futures = [executor.submit(_check_track_mood, t, mood_tag) for t in fresh_tracks]
            for future in futures:
                result = future.result()
                if result:
                    matched_tracks.append(result)
                    # Once we find 10 matches, we can stop to save time, we only need 5
                    if len(matched_tracks) >= 10:
                        break
                        
        # If we didn't find enough matched tracks (e.g., no sad songs by this artist),
        # fallback to their top fresh tracks generally so we don't return an empty page.
        if len(matched_tracks) < 5:
            return random.sample(fresh_tracks, min(5, len(fresh_tracks)))
            
        return random.sample(matched_tracks, min(5, len(matched_tracks)))
    except Exception:
        return []


def get_spotify_token() -> str:
    auth_b64 = base64.b64encode(f"{SPOTIFY_ID}:{SPOTIFY_SECRET}".encode()).decode()
    try:
        res = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {auth_b64}"},
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
        return res.json().get("access_token", "")
    except Exception:
        return ""


def get_spotify_link(token: str, track: str, artist: str) -> str:
    if not token:
        return ""
    try:
        res   = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": f"track:{track} artist:{artist}", "type": "track", "limit": 1},
            timeout=10,
        )
        items = res.json().get("tracks", {}).get("items", [])
        return items[0]["external_urls"]["spotify"] if items else ""
    except Exception:
        return ""
