# -*- coding: utf-8 -*-
"""Lassen sich den kommenden Arzneimitteln ihre Studien zuordnen?

Wunsch des Herausgebers vom 22.10.2026: die kommenden Arzneimittel mit
Indikationsgebiet UND den dazugehoerigen Studien auf einem Zeitstrahl.

Die Studien liegen bereits vor - jeder Hub fuehrt sein `studien-archiv.json`
mit allen je gezeigten PubMed-Arbeiten. Die Frage ist allein, ob sich eine
Arbeit einem Wirkstoff **mechanisch** zuordnen laesst. Wenn nicht, ist der
Zeitstrahl eine Zusage, die die Daten nicht einloesen.

Gesucht wird der INN im Titel und in der deutschen Zusammenfassung. Das ist
streng: Eine Zulassungsstudie nennt den Wirkstoff fast immer im Titel
("Daraxonrasib in Metastatic Pancreatic Cancer"), eine Uebersichtsarbeit
ueber die Stoffklasse nicht. Genau das soll der Unterschied sein - wir
wollen die Studie ZUM Mittel, nicht die Studie zum Thema.
"""
import collections
import datetime as dt
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline_quelle import liste_holen, spalte  # noqa: E402

# Sieht absichtlich AUS dem Repo heraus: Geprueft werden die
# studien-archiv.json aller fuenfzehn Portale, und die liegen als
# Schwesterordner daneben. Abgeleitet aus dem eigenen Ort.
HUBS = pathlib.Path(__file__).resolve().parents[3]
heute = dt.date.today()

# ---------------------------------------------------- die Archive einsammeln
archive = {}
gesamt = 0
for ordner in sorted(HUBS.glob("*-portal")):
    datei = ordner / "studien-archiv.json"
    if not datei.exists():
        continue
    try:
        daten = json.loads(datei.read_text(encoding="utf-8"))
    except ValueError:
        continue
    liste = daten if isinstance(daten, list) else daten.get("studien", [])
    archive[ordner.name.replace("-portal", "")] = liste
    gesamt += len(liste)

print(f"{len(archive)} Archive, {gesamt} Studieneintraege zusammen.")
print("  " + ", ".join(f"{k} {len(v)}" for k, v in
                       sorted(archive.items(), key=lambda x: -len(x[1]))[:8]))

# Welche Felder traegt ein Eintrag? Nicht raten - nachsehen.
beispiel = next(iter(next(iter(archive.values()))))
print(f"\nFelder eines Eintrags: {sorted(beispiel)}")

# ------------------------------------------------- die Wirkstoffe der Pipeline
kopf, satz, _ = liste_holen(heute.year, heute.month)
k_inn = spalte(kopf, "non-proprietary")
k_gen = spalte(kopf, "generic")
k_ind = spalte(kopf, "indication")
k_start = spalte(kopf, "start of evaluation")
neu = [z for z in satz if str(z.get(k_gen, "")).strip().upper() != "Y"]
print(f"\n{len(neu)} neue Wirkstoffe in EU-Pruefung.\n")


def suchbegriffe(inn: str) -> list[str]:
    """Der INN, zerlegt. Kombinationen liefern mehrere Begriffe; das
    englische End-e faellt im Deutschen weg, deshalb wird der Stamm gesucht."""
    raus = []
    for t in re.split(r"[/,;+]+", str(inn or "")):
        t = t.strip().lower()
        if len(t) < 6:
            continue
        stamm = t[:-1] if t.endswith("e") else t
        raus.append(stamm)
    return raus


def text_von(s: dict) -> str:
    teile = [str(s.get(f, "") or "") for f in
             ("title", "titel", "sum", "zusammenfassung", "result", "ergebnis",
              "titel_original")]
    return " ".join(teile).lower()


# Einmal alle Archivtexte vorbereiten - 4.000 Eintraege mal 57 Wirkstoffe
# waeren sonst 230.000 Volltextsuchen.
alle_studien = []
for hub, liste in archive.items():
    for s in liste:
        alle_studien.append((hub, s, text_von(s)))

treffer = collections.Counter()
beispiele = []
for z in neu:
    inn = str(z.get(k_inn, ""))
    begriffe = suchbegriffe(inn)
    if not begriffe:
        continue
    gefunden = [(hub, s) for hub, s, text in alle_studien
                if any(b in text for b in begriffe)]
    if gefunden:
        treffer[inn] = len(gefunden)
        if len(beispiele) < 10:
            beispiele.append((inn, z.get(k_ind, ""), gefunden[:2]))

mit = len(treffer)
print("=" * 74)
print(f"Wirkstoffe mit mindestens einer Studie im Bestand: {mit} von {len(neu)} "
      f"({100*mit//max(len(neu),1)} %)")
print("=" * 74)
if treffer:
    print(f"Studien je Wirkstoff: im Mittel "
          f"{sum(treffer.values())/len(treffer):.1f}, "
          f"hoechstens {max(treffer.values())}\n")
for inn, indikation, stud in beispiele:
    print(f"  {inn[:30]:<31} {str(indikation)[:46]}")
    for hub, s in stud:
        titel = (s.get("title") or s.get("titel") or
                 s.get("titel_original") or "")
        print(f"      [{hub}] {str(titel)[:84]}")
    print()

print("=" * 74)
print("Was der Zeitstrahl braucht - und was fehlt")
print("=" * 74)
# Verfahrensbeginn: liegt vor. Erwartetes Gutachten: rechnerisch.
beginn = [z.get(k_start) for z in neu if z.get(k_start)]
if beginn:
    aeltest = min(str(b)[:10] for b in beginn)
    juengst = max(str(b)[:10] for b in beginn)
    print(f"  Verfahrensbeginn vorhanden:   {len(beginn)} von {len(neu)}")
    print(f"  Spanne:                       {aeltest} bis {juengst}")
print(f"  Indikationstext vorhanden:    "
      f"{sum(1 for z in neu if z.get(k_ind))} von {len(neu)}")
print("  Erwartetes Gutachtendatum:    FEHLT - die EMA nennt kein Zieldatum.")
print("    Aus dem Verfahrensbeginn laesst es sich nur SCHAETZEN; gemessen")
print("    lagen 89 % der heutigen Gutachten sechs Monate vorher in der Liste.")
