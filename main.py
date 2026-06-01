import sys
import os
import requests
import base64
from pathlib import Path
from dotenv import load_dotenv
from analyzer import get_sentiment_score

# forteaza UTF-8 pentru terminal Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# incarcam cheile din .env
load_dotenv(Path(__file__).resolve().parent / '.env')

LASTFM_API_KEY = os.environ['LASTFM_API_KEY']
SPOTIFY_ID     = os.environ['SPOTIFY_CLIENT_ID']
SPOTIFY_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']


def get_spotify_token():
    auth_b64 = base64.b64encode(f"{SPOTIFY_ID}:{SPOTIFY_SECRET}".encode()).decode()
    url = "https://accounts.spotify.com/api/token"
    res = requests.post(url, headers={"Authorization": f"Basic {auth_b64}"}, data={"grant_type": "client_credentials"})
    return res.json().get("access_token")


def get_spotify_link(token, t_name, a_name):
    url     = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}
    params  = {"q": f"track:{t_name} artist:{a_name}", "type": "track", "limit": 1}
    try:
        res   = requests.get(url, headers=headers, params=params)
        items = res.json().get("tracks", {}).get("items", [])
        return items[0]["external_urls"]["spotify"] if items else "Link indisponibil"
    except Exception as e:
        print("Eroare link Spotify:", e)
        return "Eroare link"


def get_lastfm_tracks(tag):
    url = "https://ws.audioscrobbler.com/2.0/"

    # Last.fm prefera tag-uri compuse pentru anumite stari
    tag_fix = {
        "sad":      "sad songs",
        "chillout": "chillout",
        "happy":    "happy music"
    }

    params = {
        "method":      "tag.gettoptracks",
        "tag":         tag_fix.get(tag, tag),
        "api_key":     LASTFM_API_KEY,
        "format":      "json",
        "limit":       10,
        "autocorrect": 1
    }

    try:
        res    = requests.get(url, params=params)
        data   = res.json()
        tracks = data.get("tracks", {}).get("track", [])

        if not tracks:
            # fallback la pop daca tag-ul nu returneaza nimic
            params["tag"] = "pop"
            res    = requests.get(url, params=params)
            tracks = res.json().get("tracks", {}).get("track", [])

        if isinstance(tracks, dict):
            tracks = [tracks]
        return tracks[:5]
    except Exception as e:
        print("Eroare Last.fm:", e)
        return []


def ruleaza():
    print("\n=== MOODIFY - LIVE DATA ===")
    user_text = input("\nCum te simti astazi? ")
    if not user_text:
        return

    scor = get_sentiment_score(user_text)
    print(f"Scor detectat: {scor}")

    if scor <= 0.44:
        tag = "sad"
    elif scor <= 0.70:
        tag = "chillout"
    else:
        tag = "happy"
    print(f"Starea determinata: {tag.upper()}")

    print(f"Contactez Last.fm pentru '{tag}'...")
    piese = get_lastfm_tracks(tag)

    if not piese:
        print("Eroare: Nu s-au putut prelua date live. Verifica conexiunea.")
        return

    token = get_spotify_token()
    print("\n--- RECOMANDARI (LIVE) ---")
    for p in piese:
        nume   = p.get("name")
        artist = p.get("artist", {}).get("name")
        link   = get_spotify_link(token, nume, artist)
        print(f"[*] {nume} - {artist}")
        print(f"    -> {link}\n")


if __name__ == "__main__":
    ruleaza()