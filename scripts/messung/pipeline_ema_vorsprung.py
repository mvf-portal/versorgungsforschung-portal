# -*- coding: utf-8 -*-
"""Wie weit reicht die EMA-Pipeline wirklich - und wie viel davon taugt?

Die erste Messung (pipeline_ema.py) ergab bei 15 und 18 Monaten null Treffer.
Das war **mein Messfehler**, nicht der Befund: Die Spalte "EMA Prod. Number"
gibt es erst seit Oktober 2025, und aeltere Listen haben sie nicht - mein
Abgleich suchte also eine Spalte, die dort gar nicht steht. Hier wird
ueber den INN abgeglichen, den jede Liste seit 2021 fuehrt.

Zweite Frage, die ueber den Nutzen entscheidet: Wie viele der laufenden
Antraege sind **berichtenswert**? Ein Generikum oder ein Biosimilar ist keine
Nachricht - und davon ist in dieser Liste reichlich.
"""
import collections
import datetime as dt
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import zulassungen  # noqa: E402
import zulassungen_themen as themen  # noqa: E402
from pipeline_quelle import MONATE, liste_holen  # noqa: E402


def inn_satz(satz, kopf_inn):
    """Die INN einer Liste, klein und ohne Beiwerk."""
    raus = set()
    for z in satz:
        wert = str(z.get(kopf_inn, "") or "").strip().lower()
        if wert:
            # Kombinationen stehen mit Schraegstrich oder Komma da.
            for t in re.split(r"[/,;]+", wert):
                t = t.strip()
                if len(t) >= 5:
                    raus.add(t)
    return raus


heute = dt.date.today()
tabelle = zulassungen.tabelle_lesen(zulassungen.hol(zulassungen.EMA_URL))
gutachten = [z for z in tabelle
             if str(z["kategorie"]).strip().lower() == "human"
             and str(z["status"]).strip() == "Opinion"
             and zulassungen.datum(z["gutachten_am"])]
# Die INN der heutigen Gutachten, nach derselben Regel zerlegt.
ziel = {}
for g in gutachten:
    wert = str(g["inn"] or g["wirkstoff"] or "").strip().lower()
    teile = {t.strip() for t in re.split(r"[/,;]+", wert) if len(t.strip()) >= 5}
    if teile:
        ziel[str(g["name"])] = teile
print(f"{len(ziel)} der {len(gutachten)} Gutachten haben einen brauchbaren INN.\n")

print("=" * 74)
print("Vorsprung, ueber den INN gemessen (gilt auch fuer alte Listen)")
print("=" * 74)
for zurueck in (3, 6, 9, 12, 15, 18, 24):
    monat = heute.month - zurueck
    jahr = heute.year + (monat - 1) // 12
    monat = (monat - 1) % 12 + 1
    try:
        kopf, alt, _ = liste_holen(jahr, monat)
    except Exception as fehler:                        # noqa: BLE001
        print(f"  vor {zurueck:>2} Monaten: nicht abrufbar ({str(fehler)[:46]})")
        continue
    kopf_inn = next(k for k in kopf if k and "non-proprietary" in k.lower())
    drin = inn_satz(alt, kopf_inn)
    gefunden = sum(1 for teile in ziel.values() if teile & drin)
    print(f"  vor {zurueck:>2} Monaten ({MONATE[monat-1][:3]} {jahr}): "
          f"{len(alt):>3} Antraege · {gefunden:>2} von {len(ziel)} der heutigen "
          f"Gutachten schon dabei ({100*gefunden//max(len(ziel),1)} %)")

print("\n" + "=" * 74)
print("Wie viel von der heutigen Liste waere berichtenswert?")
print("=" * 74)
kopf, satz, _ = liste_holen(heute.year, heute.month)
k_inn = next(k for k in kopf if k and "non-proprietary" in k.lower())
k_gen = next(k for k in kopf if k and "generic" in k.lower())
k_ind = next(k for k in kopf if k and "indication" in k.lower())
k_start = next(k for k in kopf if k and "start of evaluation" in k.lower())

generisch = [z for z in satz if str(z.get(k_gen, "")).strip().upper() == "Y"]
neu = [z for z in satz if str(z.get(k_gen, "")).strip().upper() != "Y"]
print(f"  Antraege insgesamt            {len(satz)}")
print(f"  davon Generika/Biosimilars    {len(generisch)}  <- keine Nachricht")
print(f"  neue Wirkstoffe/Biologika     {len(neu)}")

# Zuordnung zu den Hubs - ueber den Indikationstext, wie bei der FDA-Stufe.
# Der Text ist hier kein Beipackzettel, sondern ein Einzeiler ("Treatment of
# presbyopia in adults"), also ohne das Wort "indicated". Geprueft wird
# deshalb der ganze Text, aber der Diagnostik-Filter bleibt.
zuordnung = collections.Counter()
ohne = 0
for z in neu:
    text = str(z.get(k_ind, "") or "")
    if themen.DIAGNOSTIK.search(text):
        hubs = []
    else:
        hubs = [slug for slug, (_, muster) in themen.GEBAUT.items()
                if any(m.search(text) for m in muster)]
    if hubs:
        for h in hubs:
            zuordnung[h] += 1
    else:
        ohne += 1
print(f"\n  einem Hub zuzuordnen          {len(neu) - ohne} von {len(neu)} "
      f"({100*(len(neu)-ohne)//max(len(neu),1)} %)")
for h, n in zuordnung.most_common():
    print(f"      {themen.name_von(h):<34} {n}")
print(f"      (keinem Hub)                       {ohne}")

print("\nDie zehn juengsten neuen Wirkstoffe in der Pruefung:")
neu.sort(key=lambda z: str(z.get(k_start, "")), reverse=True)
for z in neu[:10]:
    beginn = str(z.get(k_start, ""))[:10]
    print(f"  {beginn}  {str(z.get(k_inn,''))[:26]:<27} "
          f"{str(z.get(k_ind,''))[:60]}")
