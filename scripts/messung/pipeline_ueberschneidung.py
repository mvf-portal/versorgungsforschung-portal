# -*- coding: utf-8 -*-
"""Wie viele EU-Antraege sind in den USA schon zugelassen?

Das ist die Frage, die ueber den Nutzen einer Pipeline-Stufe entscheidet.
Eine Liste laufender Antraege allein ist eine Ankuendigung. Interessant wird
sie, wenn daneben steht, dass dasselbe Mittel in den USA bereits auf dem
Markt ist - dann ist aus der Ankuendigung eine Aussage ueber den Abstand
zwischen zwei Zulassungssystemen geworden, und die hat kein anderes offenes
Angebot.

Abgeglichen wird ueber den Wirkstoff, nicht ueber den Handelsnamen: Die
Marken unterscheiden sich zwischen den Kontinenten (Lirafugratinib heisst in
den USA LYRFIGTU und hat in der EU noch gar keinen Namen).
"""
import datetime as dt
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline_quelle import liste_holen, spalte  # noqa: E402

WURZEL = pathlib.Path(__file__).resolve().parent.parent.parent
heute = dt.date.today()


def staemme(wert: str) -> set:
    """Wirkstoffnamen vergleichbar machen.

    Der deutsche und der englische INN unterscheiden sich am Ende ('Temozolomid'
    gegen 'temozolomide'), Salze haengen hinten dran ('Orforglipron
    hemicalcium'), und Kombinationen stehen mit Schraegstrich da. Genommen
    wird der erste Wortbestandteil jedes Teils, mindestens fuenf Zeichen -
    dieselbe Regel wie im Torwaechter.
    """
    raus = set()
    for t in re.split(r"[;,/()]+", str(wert or "").lower()):
        t = t.replace("-", " ").strip()
        if not t:
            continue
        wort = t.split()[0]
        if len(wort) >= 5:
            raus.add(wort)
            if wort.endswith("e"):
                raus.add(wort[:-1])
    return raus


kopf, satz, _ = liste_holen(heute.year, heute.month)
k_inn = next(k for k in kopf if k and "non-proprietary" in k.lower())
k_gen = next(k for k in kopf if k and "generic" in k.lower())
k_ind = next(k for k in kopf if k and "indication" in k.lower())
k_start = next(k for k in kopf if k and "start of evaluation" in k.lower())
neu = [z for z in satz if str(z.get(k_gen, "")).strip().upper() != "Y"]

daten = json.loads((WURZEL / "zulassungen.json").read_text(encoding="utf-8"))
fda = [e for e in daten["eintraege"] if str(e["stufe"]).startswith("fda")]
print(f"{len(neu)} neue Wirkstoffe in EU-Pruefung, "
      f"{len(fda)} FDA-Erstzulassungen der letzten 180 Tage.\n")

treffer = []
for z in neu:
    s = staemme(z.get(k_inn, ""))
    for f in fda:
        if s & staemme(f["wirkstoff"]):
            treffer.append((z, f))
            break

print("=" * 74)
print(f"In den USA bereits zugelassen, in der EU noch in Pruefung: "
      f"{len(treffer)} von {len(neu)}")
print("=" * 74)
for z, f in sorted(treffer, key=lambda t: t[1]["datum"], reverse=True):
    print(f"  {str(z.get(k_inn,''))[:26]:<27} EU-Pruefung seit "
          f"{str(z.get(k_start,''))[:10]}")
    print(f"  {'':27} USA zugelassen am {f['datum']} als {f['name']}")
    print(f"  {'':27} {str(z.get(k_ind,''))[:62]}")
    print()

if not treffer:
    print("  (keine)")
print("Hinweis: Das Fenster der FDA-Stufe ist 180 Tage. Mit einem laengeren")
print("Rueckblick faenden sich mehr - die Zahl hier ist eine Untergrenze.")
