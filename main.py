import sys
import requests
import base64
from analyzer import get_sentiment_score

# Forteaza UTF-8 pentru terminal Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Cheile tale ramase neschimbate
LASTFM_API_KEY = "95711c703010c8da32826ad534adc6b8"
SPOTIFY_ID = "1ca7f51e164b48e2bb2107c20bf915fd"
SPOTIFY_SECRET = "5ccf48475bcc48f4b449c9fe140f3dd7"

def get_spotify_token():
    auth_b64 = base64.b64encode(f"{SPOTIFY_ID}:{SPOTIFY_SECRET}".encode()).decode()
    url = "https://accounts.spotify.com/api/token"
    res = requests.post(url, headers={"Authorization": f"Basic {auth_b64}"}, data={"grant_type": "client_credentials"})
    return res.json().get("access_token")

def get_spotify_link(token, t_name, a_name):
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": f"track:{t_name} artist:{a_name}", "type": "track", "limit": 1}
    try:
        res = requests.get(url, headers=headers, params=params)
        items = res.json().get("tracks", {}).get("items", [])
        return items[0]["external_urls"]["spotify"] if items else "Link indisponibil"
    except Exception as e:
        print("Eroare link Spotify:", e)
        return "Eroare link"

def get_lastfm_tracks(tag):
    # Folosim HTTPS si forta bruta pentru tag-uri
    url = "https://ws.audioscrobbler.com/2.0/"
    
    # Last.fm prefera uneori tag-uri compuse pentru stari
    tag_fix = {
        "sad": "sad songs",
        "chillout": "chillout",
        "happy": "happy music"
    }
    
    params = {
        "method": "tag.gettoptracks",
        "tag": tag_fix.get(tag, tag),
        "api_key": LASTFM_API_KEY,
        "format": "json",
        "limit": 10, # Cerem 10 ca sa fim siguri ca avem de unde alege
        "autocorrect": 1
    }
    
    try:
        res = requests.get(url, params=params)
        data = res.json()
        
        # API-ul Last.fm returneaza cheia "tracks", nu "toptracks"
        tracks = data.get("tracks", {}).get("track", [])
        
        if not tracks:
            # Daca tag-ul principal nu merge, incercam "pop" ca fallback
            params["tag"] = "pop"
            res = requests.get(url, params=params)
            tracks = res.json().get("tracks", {}).get("track", [])
            
        if isinstance(tracks, dict): tracks = [tracks]
        return tracks[:5] # Returnam doar 5
    except Exception as e:
        print("Eroare Last.fm:", e)
        return []

def ruleaza():
    print("\n=== MOODIFY v3.0 - LIVE DATA ===")
    user_text = input("\nCum te simti astazi? ")
    if not user_text: return

    # 1. Scor corectat
    scor = get_sentiment_score(user_text)
    print(f"Scor detectat: {scor}")

    # 2. Mapare Mood
    if scor <= 0.44: tag = "sad"
    elif scor <= 0.70: tag = "chillout"
    else: tag = "happy"
    print(f"Starea determinata: {tag.upper()}")

    # 3. Last.fm (Fara piese de rezerva manuale, doar API live)
    print(f"Contactez Last.fm pentru '{tag}'...")
    piese = get_lastfm_tracks(tag)
    
    if not piese:
        print("Eroare: Nu s-au putut prelua date live. Verifica net-ul.")
        return

    # 4. Spotify
    token = get_spotify_token()
    print("\n--- RECOMANDARI REALE (LIVE) ---")
    for p in piese:
        nume = p.get("name")
        artist = p.get("artist", {}).get("name")
        link = get_spotify_link(token, nume, artist)
        print(f"[*] {nume} - {artist}")
        print(f"    -> {link}\n")

if __name__ == "__main__":
    ruleaza()