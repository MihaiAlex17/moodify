"""
evaluate.py — Script de evaluare a clasificatorului de stari Moodify

Ruleaza: python evaluate.py
Genereaza un raport cu acuratetea modelului pe un set de fraze de test in romana.

Frazele sunt etichetate manual si impartite in 3 categorii:
  - SAD      (scor asteptat <= 0.44)
  - CHILLOUT (scor asteptat intre 0.44 si 0.70)
  - HAPPY    (scor asteptat > 0.70)
"""

import sys
from analyzer import get_sentiment_score

# fortam UTF-8 pe Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ---------------------------------------------------------------------------
# Set de date de test (fraze in romana, etichetate manual)
# ---------------------------------------------------------------------------

TEST_DATA = [
    # SAD — fraze cu continut negativ clar
    ("ma simt oribil, totul merge prost",            "SAD"),
    ("nu ma simt deloc bine, sunt deprimat",         "SAD"),
    ("am pierdut tot ce aveam, sunt distrus",        "SAD"),
    ("plang in fiecare seara si nu stiu de ce",      "SAD"),
    ("ma simt singur si abandonat",                  "SAD"),
    ("sunt epuizat, nu mai am putere de nimic",      "SAD"),
    ("totul e negru in jurul meu",                   "SAD"),
    ("mi-e dor de cineva care nu mai e",             "SAD"),
    ("am dat gres la examen, ma simt un ratat",      "SAD"),
    ("nu am chef de nimic, vreau sa stau in pat",    "SAD"),
    ("sunt trist si nu stiu de ce",                  "SAD"),
    ("ma simt ignorat de toata lumea",               "SAD"),

    # CHILLOUT — fraze neutre sau de relaxare
    ("ziua a fost ok, nici bine nici rau",           "CHILLOUT"),
    ("ma descurc, merge asa si asa",                 "CHILLOUT"),
    ("sunt relaxat, ascult muzica si ma odihnesc",   "CHILLOUT"),
    ("nu am planuri speciale, o zi normala",         "CHILLOUT"),
    ("citesc o carte si beau cafea",                 "CHILLOUT"),
    ("ma plimb incet, nu ma grabesc nicaieri",       "CHILLOUT"),
    ("totul e linistit azi, e bine asa",             "CHILLOUT"),
    ("nu e nicio problema, ma simt ok",              "CHILLOUT"),
    ("azi am lucrat putin si m-am relaxat",          "CHILLOUT"),
    ("ma uit la un film, nimic special",             "CHILLOUT"),
    ("o zi obisnuita, fara evenimente",              "CHILLOUT"),
    ("sunt calm si echilibrat",                      "CHILLOUT"),

    # HAPPY — fraze cu continut pozitiv clar
    ("sunt fericit, totul merge perfect!",           "HAPPY"),
    ("totul e perfect, sunt pe val!",                "HAPPY"),
    ("am luat nota maxima, sunt super fericit",      "HAPPY"),
    ("m-am casatorit azi, e cea mai frumoasa zi",    "HAPPY"),
    ("am primit o veste extraordinara!",             "HAPPY"),
    ("azi am ras mult, a fost o zi minunata",        "HAPPY"),
    ("sunt plin de energie, gata de actiune",        "HAPPY"),
    ("am reusit proiectul, sunt mandru de mine",     "HAPPY"),
    ("ma simt fantastic, nimic nu ma poate opri",    "HAPPY"),
    ("am petrecut cu prietenii, a fost super",       "HAPPY"),
    ("totul imi merge bine in ultima vreme",         "HAPPY"),
    ("sunt incantat, abia astept ziua de maine",     "HAPPY"),
]


def get_label(score: float) -> str:
    """Converteste scorul numeric in eticheta de stare."""
    if score <= 0.44:
        return "SAD"
    elif score <= 0.70:
        return "CHILLOUT"
    else:
        return "HAPPY"


def run_evaluation():
    print("=" * 60)
    print("  EVALUARE CLASIFICATOR MOODIFY")
    print("=" * 60)
    print(f"  Total fraze de test: {len(TEST_DATA)}")
    print(f"  SAD: {sum(1 for _, l in TEST_DATA if l == 'SAD')}")
    print(f"  CHILLOUT: {sum(1 for _, l in TEST_DATA if l == 'CHILLOUT')}")
    print(f"  HAPPY: {sum(1 for _, l in TEST_DATA if l == 'HAPPY')}")
    print("=" * 60)
    print()

    results = []
    correct = 0
    errors_by_class = {"SAD": 0, "CHILLOUT": 0, "HAPPY": 0}
    total_by_class  = {"SAD": 0, "CHILLOUT": 0, "HAPPY": 0}

    for i, (phrase, expected) in enumerate(TEST_DATA, 1):
        score    = get_sentiment_score(phrase)
        detected = get_label(score)
        ok       = detected == expected

        if ok:
            correct += 1
        else:
            errors_by_class[expected] += 1
        total_by_class[expected] += 1

        results.append((phrase, expected, detected, score, ok))
        status = "OK" if ok else "GRESIT"
        print(f"  [{i:02d}] {status:6s} | scor={score:.2f} | asteptat={expected:8s} | detectat={detected}")

    # ---------------------------------------------------------------------------
    # Raport final
    # ---------------------------------------------------------------------------
    print()
    print("=" * 60)
    print("  RAPORT FINAL")
    print("=" * 60)

    total    = len(TEST_DATA)
    accuracy = correct / total * 100

    print(f"\n  Acuratete generala: {correct}/{total} = {accuracy:.1f}%\n")

    print("  Acuratete pe categorii:")
    for cls in ["SAD", "CHILLOUT", "HAPPY"]:
        cls_total   = total_by_class[cls]
        cls_correct = cls_total - errors_by_class[cls]
        cls_acc     = cls_correct / cls_total * 100 if cls_total > 0 else 0
        print(f"    {cls:8s}: {cls_correct}/{cls_total} = {cls_acc:.1f}%")

    print()
    print("  Fraze clasificate gresit:")
    wrong = [(p, e, d, s) for p, e, d, s, ok in results if not ok]
    if wrong:
        for phrase, expected, detected, score in wrong:
            print(f"    - \"{phrase}\"")
            print(f"      asteptat={expected}, detectat={detected}, scor={score:.2f}")
    else:
        print("    Nicio fraza gresita!")

    print()
    print("=" * 60)
    print(f"  Concluzie: modelul XLM-RoBERTa (zero-shot, romana)")
    print(f"  a clasificat corect {accuracy:.1f}% din frazele de test.")
    print("=" * 60)

    return accuracy


if __name__ == "__main__":
    run_evaluation()
