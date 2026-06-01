import os
import random
import requests
import base64
from pathlib import Path
from dotenv import load_dotenv

# incarcam variabilele din .env (acelasi fisier ca Django)
load_dotenv(Path(__file__).resolve().parent / '.env')

LASTFM_API_KEY = os.environ['LASTFM_API_KEY']
SPOTIFY_ID     = os.environ['SPOTIFY_CLIENT_ID']
SPOTIFY_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']

# mapeaza tag-ul intern la termenul de cautare pe Last.fm
TAG_MAP = {
    "sad":      "sad songs",
    "chillout": "chillout",
    "happy":    "happy music",
}


def get_lastfm_tracks(tag: str, context: str = None, excluded: set = None) -> list:
    if excluded is None:
        excluded = set()

    base_tag = TAG_MAP.get(tag, tag)

    # combinam starea cu contextul muzical daca exista (ex: "sad rock")
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
        "limit":       300,
        "autocorrect": 1,
    }
    try:
        data   = requests.get(url, params=params, timeout=10).json()
        tracks = data.get("tracks", {}).get("track", [])

        # daca tag-ul combinat nu returneaza nimic, incercam doar starea
        if not tracks and context:
            params["tag"] = base_tag
            tracks = requests.get(url, params=params, timeout=10).json().get("tracks", {}).get("track", [])

        # fallback la pop daca tot nu gasim nimic
        if not tracks:
            params["tag"] = "pop"
            tracks = requests.get(url, params=params, timeout=10).json().get("tracks", {}).get("track", [])
        if isinstance(tracks, dict):
            tracks = [tracks]

        # eliminam piesele pe care utilizatorul le-a mai primit
        fresh_tracks = [t for t in tracks if t.get("name") not in excluded]

        # daca a primit deja toate piesele, ignoram excluderea
        if len(fresh_tracks) < 5:
            fresh_tracks = tracks

        # luam primele 20 cele mai populare si alegem 5 aleatoriu
        popular_fresh_pool = fresh_tracks[:20]
        return random.sample(popular_fresh_pool, min(5, len(popular_fresh_pool)))
    except Exception:
        return []


from concurrent.futures import ThreadPoolExecutor

def _check_track_mood(track: dict, expected_mood: str) -> dict:
    """Verifica daca o piesa are tag-ul de stare asteptat pe Last.fm."""
    try:
        url = "https://ws.audioscrobbler.com/2.0/"
        params = {
            "method":      "track.getInfo",
            "artist":      track["artist"]["name"],
            "track":       track["name"],
            "api_key":     LASTFM_API_KEY,
            "format":      "json",
            "autocorrect": 1
        }
        data      = requests.get(url, params=params, timeout=5).json()
        tags_data = data.get("track", {}).get("toptags", {}).get("tag", [])
        if isinstance(tags_data, dict):
            tags_data = [tags_data]

        tags   = [t.get("name", "").lower() for t in tags_data]
        target = TAG_MAP.get(expected_mood, expected_mood)

        # returnam piesa daca starea se regaseste in tag-urile ei
        if any(target in t for t in tags) or any(expected_mood in t for t in tags):
            return track
    except Exception:
        pass
    return None


def get_artist_tracks_by_mood(artist: str, mood_tag: str, excluded: set = None) -> list:
    """Returneaza piese ale unui artist filtrate dupa starea curenta."""
    if excluded is None:
        excluded = set()

    url    = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "method":      "artist.getTopTracks",
        "artist":      artist,
        "api_key":     LASTFM_API_KEY,
        "format":      "json",
        "limit":       50,
        "autocorrect": 1,
    }
    try:
        data   = requests.get(url, params=params, timeout=10).json()
        tracks = data.get("toptracks", {}).get("track", [])
        if isinstance(tracks, dict):
            tracks = [tracks]

        fresh_tracks = [t for t in tracks if t.get("name") not in excluded]

        # verificam tag-urile fiecarei piese in paralel pentru viteza
        matched_tracks = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(_check_track_mood, t, mood_tag) for t in fresh_tracks]
            for future in futures:
                result = future.result()
                if result:
                    matched_tracks.append(result)
                    # ne oprim dupa 10 rezultate, avem nevoie doar de 5
                    if len(matched_tracks) >= 10:
                        break

        # daca nu gasim suficiente piese cu starea potrivita, luam top-ul general
        if len(matched_tracks) < 5:
            return random.sample(fresh_tracks, min(5, len(fresh_tracks)))

        return random.sample(matched_tracks, min(5, len(matched_tracks)))
    except Exception:
        return []


def get_spotify_token() -> str:
    """Obtine un token de acces Spotify prin client credentials flow."""
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
    """Cauta o piesa pe Spotify si returneaza URL-ul sau string gol daca nu o gaseste."""
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


def search_lastfm_track(query: str) -> list:
    """Cauta piese pe Last.fm dupa un text partial. Folosit pentru autocomplete."""
    url    = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "method":  "track.search",
        "track":   query,
        "api_key": LASTFM_API_KEY,
        "format":  "json",
        "limit":   8,
    }
    try:
        data    = requests.get(url, params=params, timeout=8).json()
        matches = data.get("results", {}).get("trackmatches", {}).get("track", [])
        if isinstance(matches, dict):
            matches = [matches]
        return [{"name": t.get("name", ""), "artist": t.get("artist", "")} for t in matches]
    except Exception:
        return []


def get_similar_tracks(track: str, artist: str) -> list:
    """
    Returneaza pana la 8 piese similare folosind Last.fm track.getSimilar.
    Daca nu gaseste destule, cade pe top-ul artistului ca fallback.
    """
    url   = "https://ws.audioscrobbler.com/2.0/"
    token = get_spotify_token()

    def _resolve(raw_tracks, limit=8) -> list:
        """Transforma lista bruta Last.fm in formatul nostru de raspuns."""
        results = []
        for i, t in enumerate(raw_tracks[:limit], 1):
            name = t.get("name", "")
            art  = (
                t.get("artist", {}).get("name", "")
                if isinstance(t.get("artist"), dict)
                else t.get("artist", "")
            )
            sp_url = get_spotify_link(token, name, art)
            results.append({
                "rank":        i,
                "track_name":  name,
                "artist_name": art,
                "spotify_url": sp_url,
                "is_fallback": False,
            })
        return results

    # incercam mai intai track.getSimilar
    try:
        params = {
            "method":      "track.getSimilar",
            "track":       track,
            "artist":      artist,
            "api_key":     LASTFM_API_KEY,
            "format":      "json",
            "limit":       10,
            "autocorrect": 1,
        }
        data   = requests.get(url, params=params, timeout=10).json()
        tracks = data.get("similartracks", {}).get("track", [])
        if isinstance(tracks, dict):
            tracks = [tracks]

        if len(tracks) >= 3:
            return _resolve(tracks)
    except Exception:
        tracks = []

    # fallback: alte piese ale aceluiasi artist
    try:
        params = {
            "method":      "artist.getTopTracks",
            "artist":      artist,
            "api_key":     LASTFM_API_KEY,
            "format":      "json",
            "limit":       20,
            "autocorrect": 1,
        }
        data       = requests.get(url, params=params, timeout=10).json()
        top_tracks = data.get("toptracks", {}).get("track", [])
        if isinstance(top_tracks, dict):
            top_tracks = [top_tracks]

        # scoatem piesa de start din lista
        seed_lower = track.lower()
        filtered   = [t for t in top_tracks if t.get("name", "").lower() != seed_lower]

        result = _resolve(filtered, limit=8)
        # marcam ca fallback ca sa afisam un mesaj diferit in UI
        for r in result:
            r["is_fallback"] = True
        return result
    except Exception:
        return []
