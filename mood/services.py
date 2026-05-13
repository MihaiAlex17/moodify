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


def get_lastfm_tracks(tag: str) -> list:
    url    = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "method":      "tag.gettoptracks",
        "tag":         TAG_MAP.get(tag, tag),
        "api_key":     LASTFM_API_KEY,
        "format":      "json",
        "limit":       10,
        "autocorrect": 1,
    }
    try:
        data   = requests.get(url, params=params, timeout=10).json()
        tracks = data.get("tracks", {}).get("track", [])
        if not tracks:
            params["tag"] = "pop"
            tracks = requests.get(url, params=params, timeout=10).json().get("tracks", {}).get("track", [])
        if isinstance(tracks, dict):
            tracks = [tracks]
        return tracks[:5]
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
