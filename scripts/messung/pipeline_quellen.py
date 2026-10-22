# -*- coding: utf-8 -*-
"""Woran erkennt man, welche Arzneimittel DEMNAECHST kommen?

Frage des Herausgebers vom 22.10.2026. Der Radar zeigt heute vier Stufen,
die frueheste ist das CHMP-Gutachten - rund zwei Monate vor der Zulassung.
Geht es frueher, und mit welcher Quelle?

Gemessen wird in dieser Reihenfolge, billigste Quelle zuerst:

  1. **Die EMA-Tabelle, die wir ohnehin holen.** Welche Werte stehen im Feld
     "Medicine status"? Steht dort etwas vor dem Gutachten, kostet eine
     fuenfte Stufe nichts weiter als ein paar Zeilen.
  2. **ClinicalTrials.gov.** Zulassungsstudien mit Abschlussdatum - offene
     API, strukturiert. Wie viele Phase-3-Studien schliessen demnaechst ab,
     und nennen sie den Wirkstoff so, dass man ihn spaeter wiedererkennt?

Nicht gemessen, weil ohne Schnittstelle: die Pipeline-Seiten der Hersteller.
Jede sieht anders aus, es gibt Hunderte, und keine liefert maschinenlesbar.
"""
import collections
import datetime as dt
import io
import json
import pathlib
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import openpyxl  # noqa: E402

import zulassungen  # noqa: E402

print("=" * 72)
print("1. Die EMA-Tabelle, die wir ohnehin holen")
print("=" * 72)
roh = zulassungen.hol(zulassungen.EMA_URL)
satz = zulassungen.tabelle_lesen(roh)
human = [z for z in satz if str(z["kategorie"]).strip().lower() == "human"]
print(f"{len(satz)} Zeilen, davon {len(human)} Humanarzneimittel.\n")

zaehler = collections.Counter(str(z["status"] or "(leer)").strip() for z in human)
print('Werte im Feld "Medicine status":')
for wert, n in zaehler.most_common():
    print(f"  {wert:<34} {n:>5}")

# Gibt es Zeilen OHNE Zulassungsdatum und OHNE Gutachtendatum? Das waeren
# Antraege, die noch in der Pruefung stehen.
offen = [z for z in human
         if not zulassungen.datum(z["zulassung_am"])
         and not zulassungen.datum(z["gutachten_am"])]
print(f"\nOhne Zulassungs- UND ohne Gutachtendatum: {len(offen)}")
if offen:
    print("  Status dieser Zeilen:",
          dict(collections.Counter(str(z["status"] or "(leer)").strip()
                                   for z in offen)))
    for z in offen[:5]:
        print(f"    {str(z['name'])[:34]:<35} {str(z['status'])[:24]}")

print("\n" + "=" * 72)
print("2. ClinicalTrials.gov - Zulassungsstudien vor dem Abschluss")
print("=" * 72)

# Die offene API v2. Gefragt wird nach interventionellen Phase-3-Studien mit
# Arzneimitteln, deren primaerer Abschluss im naechsten Jahr liegt und die
# noch laufen.
heute = dt.date.today()
bis = heute + dt.timedelta(days=365)
felder = ["NCTId", "BriefTitle", "InterventionName", "Phase",
          "PrimaryCompletionDate", "OverallStatus", "LeadSponsorName",
          "Condition"]
adresse = (
    "https://clinicaltrials.gov/api/v2/studies"
    "?filter.overallStatus=RECRUITING|ACTIVE_NOT_RECRUITING"
    "&query.term=AREA[Phase]PHASE3 AND AREA[InterventionType]DRUG"
    f" AND AREA[PrimaryCompletionDate]RANGE[{heute:%Y-%m-%d},{bis:%Y-%m-%d}]"
    "&fields=" + ",".join(felder) +
    "&countTotal=true&pageSize=50"
)
req = urllib.request.Request(adresse.replace(" ", "%20"),
                             headers={"User-Agent": zulassungen.UA})
try:
    with urllib.request.urlopen(req, timeout=90) as r:
        antwort = json.loads(r.read())
except Exception as fehler:                            # noqa: BLE001
    print(f"  nicht erreichbar: {str(fehler)[:160]}")
    raise SystemExit(0)

gesamt = antwort.get("totalCount", 0)
studien = antwort.get("studies", [])
print(f"Phase-3-Arzneimittelstudien mit primaerem Abschluss bis "
      f"{bis:%d.%m.%Y}: {gesamt}")
print(f"(gelesen: {len(studien)})\n")

mit_wirkstoff = 0
for s in studien[:12]:
    p = s.get("protocolSection", {})
    kennung = p.get("identificationModule", {})
    stat = p.get("statusModule", {})
    arme = p.get("armsInterventionsModule", {}).get("interventions") or []
    namen = [i.get("name", "") for i in arme if i.get("type") == "DRUG"]
    abschluss = (stat.get("primaryCompletionDateStruct") or {}).get("date", "")
    leiter = (p.get("sponsorCollaboratorsModule", {})
                .get("leadSponsor", {}).get("name", ""))
    leiden = (p.get("conditionsModule", {}).get("conditions") or [])
    if namen:
        mit_wirkstoff += 1
    print(f"  {abschluss:<9} {', '.join(namen)[:34]:<35} "
          f"{', '.join(leiden)[:26]:<27} {leiter[:22]}")

print(f"\n  mit benanntem Wirkstoff: {mit_wirkstoff} von {len(studien[:12])}")
print("\nHinweis: Die Zahl oben ist die Grundgesamtheit, nicht die Menge, die")
print("ein Hub zeigen wuerde - darin steckt alles von der Erstzulassung bis")
print("zur Indikationserweiterung eines seit Jahrzehnten bekannten Mittels.")
