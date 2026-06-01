from transformers import pipeline, AutoTokenizer

print("Incarc modelul AI...")

# model XLM-RoBERTa antrenat pe clasificare zero-shot (XNLI)
# intelege texte in romana, inclusiv negatii si context
# use_fast=False evita dependinta de protobuf necesara pentru tokenizer-ul rapid
_tokenizer = AutoTokenizer.from_pretrained(
    "joeddav/xlm-roberta-large-xnli",
    use_fast=False
)
classifier = pipeline(
    "zero-shot-classification",
    model="joeddav/xlm-roberta-large-xnli",
    tokenizer=_tokenizer
)

# etichete de stare folosite la clasificare
# fiecare eticheta are o valoare fixa de valenta pe scala 0.1 - 0.9
MOOD_LABELS = [
    "extrem de trist",
    "trist",
    "neutru",
    "bine",
    "extrem de fericit",
]

VALENCE_ANCHORS = {
    "extrem de trist":   0.10,
    "trist":             0.28,
    "neutru":            0.50,
    "bine":              0.72,
    "extrem de fericit": 0.90,
}

def get_sentiment_score(text: str) -> float:
    """
    Returneaza un scor de valenta intre 0.1 (trist) si 0.9 (fericit).
    Scorul este media ponderata a ancorelor inmultite cu probabilitatile date de model.
    """
    result = classifier(text, candidate_labels=MOOD_LABELS)

    # calculam media ponderata: suma(probabilitate * valenta)
    score = sum(
        prob * VALENCE_ANCHORS[label]
        for label, prob in zip(result["labels"], result["scores"])
    )

    return round(score, 2)


# etichete de gen/context muzical folosite pentru a detecta preferinta din text
GENRE_LABELS = [
    "rock", "pop", "hip hop", "jazz", "electronic", "clasica", "lo-fi",
    "acustic", "metal", "relaxare", "sport", "petrecere", "somn"
]

def get_context_tag(text: str) -> str:
    """
    Incearca sa detecteze un gen muzical din textul utilizatorului.
    Returneaza un string (ex: 'rock') sau None daca nu e sigur.
    """
    # multi_label=True evalueaza fiecare eticheta independent, nu intre ele
    result = classifier(text, candidate_labels=GENRE_LABELS, multi_label=True)

    best_label = result["labels"][0]
    best_score = result["scores"][0]

    # acceptam eticheta doar daca probabilitatea depaseste 40%
    if best_score >= 0.40:
        # traducere in engleza pentru cautarea pe Last.fm
        translations = {
            "clasica":   "classical",
            "acustic":   "acoustic",
            "relaxare":  "relaxing",
            "sport":     "workout",
            "petrecere": "party",
            "somn":      "sleep",
        }
        return translations.get(best_label, best_label)

    return None


# bloc de test rulat doar direct (python analyzer.py), nu la import
if __name__ == "__main__":
    test_phrases = [
        ("ma simt oribil, totul merge prost", "SAD"),
        ("nu ma simt deloc bine", "SAD"),
        ("am pierdut tot ce aveam", "SAD"),
        ("ziua a fost ok, nici bine nici rau", "CHILL"),
        ("ma descurc, merge asa si asa", "CHILL"),
        ("sunt fericit azi, merge totul bine", "HAPPY"),
        ("totul e perfect, sunt pe val!", "HAPPY"),
    ]

    print("\n=== TEST CLASIFICATOR ===")
    for phrase, expected in test_phrases:
        scor = get_sentiment_score(phrase)
        if scor <= 0.44:
            detected = "SAD"
        elif scor <= 0.70:
            detected = "CHILL"
        else:
            detected = "HAPPY"
        ok = "OK" if detected == expected else "GRESIT"
        print(f"{ok} [{scor:.2f}] {detected:5s} | '{phrase}'")