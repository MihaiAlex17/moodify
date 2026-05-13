from transformers import pipeline, AutoTokenizer

print("Incarc creierul AI...")

# Model XLM-RoBERTa antrenat pe inferenta lingvistica naturala (NLI / XNLI)
# Intelege propozitii intregi in romana, inclusiv negatii si context
# use_fast=False forteaza tokenizer-ul lent (pur Python / SentencePiece)
# evitand dependinta de protobuf pe care tokenizer-ul rapid o cere
_tokenizer = AutoTokenizer.from_pretrained(
    "joeddav/xlm-roberta-large-xnli",
    use_fast=False
)
classifier = pipeline(
    "zero-shot-classification",
    model="joeddav/xlm-roberta-large-xnli",
    tokenizer=_tokenizer
)

# Etichete de stare in romana — modelul calculeaza probabilitatile pentru fiecare
# Valorile de valenta sunt ancorele fixe pe scala 0.1 → 0.9
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
    Returneaza un scor de valenta intre 0.1 (foarte trist) si 0.9 (foarte fericit).

    Foloseste clasificare zero-shot: modelul primeste textul si etichetele de stare,
    si calculeaza o distributie de probabilitate peste ele.
    Scorul final este media ponderata a ancorelor de valenta.
    """
    result = classifier(text, candidate_labels=MOOD_LABELS)

    # result["labels"] si result["scores"] sunt sortate descrescator dupa scor
    score = sum(
        prob * VALENCE_ANCHORS[label]
        for label, prob in zip(result["labels"], result["scores"])
    )

    return round(score, 2)


# --- Test rapid la import (comenteaza daca nu vrei output la import) ---
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
        ok = "✓" if detected == expected else "✗"
        print(f"{ok} [{scor:.2f}] {detected:5s} | '{phrase}'")