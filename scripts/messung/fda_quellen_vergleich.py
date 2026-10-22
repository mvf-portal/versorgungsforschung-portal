# -*- coding: utf-8 -*-
"""Wo ist der Beipackzettel einer frischen FDA-Zulassung maschinell zu holen?

Drei Quellen an denselben Zulassungen gemessen:
  1. openFDA  drug/label.json          (der Weg, den ich vorher gemessen habe)
  2. DailyMed Services v2              (die Quelle, aus der openFDA gespeist wird)
  3. DailyMed SPL als XML je setid     (hat der Satz einen Indikationsabschnitt?)

Gefragt ist nicht, ob die Quelle existiert, sondern ob sie fuer die 42 Mittel
der letzten 180 Tage etwas liefert. Eine Datenbank, die alles von 2015 hat und
nichts von letzter Woche, hilft einem Radar nicht.
"""
import datetime as dt
import json
import re
import pathlib
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FENSTER_TAGE = 180
heute = dt.date.today()
von = heute - dt.timedelta(days=FENSTER_TAGE)


def hole(url, roh=False):
    req = urllib.request.Request(url, headers={"User-Agent": "MVF-Knowledge-Hubs/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        rohdaten = r.read()
    return rohdaten if roh else json.loads(rohdaten)


# ---------------------------------------------------------------- Zulassungen
suche = (
    f'submissions.submission_status_date:[{von:%Y%m%d}+TO+{heute:%Y%m%d}]'
    '+AND+submissions.submission_status:"AP"'
    '+AND+submissions.submission_class_code:"TYPE+1"'
)
url = f"https://api.fda.gov/drug/drugsfda.json?search={suche}&limit=1000"
antwort = hole(url)
print(f"openFDA drugsfda: {antwort['meta']['results']['total']} Datensaetze im Fenster "
      f"({von:%d.%m.%Y} bis {heute:%d.%m.%Y})\n")

zulassungen = []
for d in antwort["results"]:
    produkte = d.get("products") or []
    if not produkte:
        continue
    # Nur die Einreichung, die in unser Fenster faellt und eine Erstzulassung ist.
    treffer = None
    for s in d.get("submissions", []):
        if s.get("submission_status") != "AP":
            continue
        if s.get("submission_class_code") != "TYPE 1":
            continue
        datum = s.get("submission_status_date", "")
        if not (f"{von:%Y%m%d}" <= datum <= f"{heute:%Y%m%d}"):
            continue
        treffer = s
        break
    if not treffer:
        continue
    wirkstoffe = []
    for p in produkte:
        for w in p.get("active_ingredients") or []:
            if w.get("name"):
                wirkstoffe.append(w["name"].strip())
    zulassungen.append({
        "nummer": d.get("application_number", ""),
        "name": (produkte[0].get("brand_name") or "").strip(),
        "wirkstoff": "; ".join(dict.fromkeys(wirkstoffe)),
        "datum": treffer.get("submission_status_date", ""),
        "typ": d.get("sponsor_name", ""),
    })

zulassungen.sort(key=lambda e: e["datum"], reverse=True)
print(f"Erstzulassungen (TYPE 1) mit Handelsnamen: {len(zulassungen)}")
ohne_name = [e for e in zulassungen if not e["name"]]
print(f"  davon ohne Handelsnamen: {len(ohne_name)}\n")


# ------------------------------------------------- Quelle 1: openFDA drug/label
def openfda_label(e):
    """Hat openFDA einen Beipackzettel mit Indikationsabschnitt?"""
    for feld, wert in (("openfda.application_number", e["nummer"]),
                       ("openfda.brand_name", e["name"])):
        if not wert:
            continue
        q = urllib.parse.quote(f'{feld}:"{wert}"', safe=":")
        try:
            a = hole(f"https://api.fda.gov/drug/label.json?search={q}&limit=1")
        except Exception:
            continue
        for r in a.get("results", []):
            text = " ".join(r.get("indications_and_usage") or [])
            if text.strip():
                return len(text)
    return 0


# ------------------------------------------------------ Quelle 2+3: DailyMed v2
ABSCHNITT = re.compile(
    r"INDICATIONS AND USAGE(.{40,4000}?)(?:DOSAGE AND ADMINISTRATION|CONTRAINDICATIONS)",
    re.S | re.I)


def dailymed(e):
    """(Treffer in der Liste, Laenge des Indikationstexts im SPL)"""
    for wert in (e["name"], e["wirkstoff"].split(";")[0].strip()):
        if not wert:
            continue
        q = urllib.parse.quote(wert)
        try:
            a = hole(f"https://dailymed.nlm.nih.gov/dailymed/services/v2/"
                     f"spls.json?drug_name={q}&pagesize=5")
        except Exception:
            continue
        for r in a.get("data", []):
            setid = r.get("setid")
            if not setid:
                continue
            try:
                xml = hole("https://dailymed.nlm.nih.gov/dailymed/services/v2/"
                           f"spls/{setid}.xml", roh=True).decode("utf-8", "replace")
            except Exception:
                continue
            nur_text = " ".join(re.sub(r"<[^>]+>", " ", xml).split())
            m = ABSCHNITT.search(nur_text)
            if m and len(m.group(1).strip()) > 60:
                return True, len(m.group(1).strip()), r.get("published_date", "")
        return True, 0, ""   # in der Liste, aber kein brauchbarer Abschnitt
    return False, 0, ""


print("Je Zulassung geprueft (o = openFDA-Label, D = DailyMed-Satz, I = Indikationstext):\n")
zahl_openfda = zahl_dailymed = zahl_text = 0
for i, e in enumerate(zulassungen, 1):
    laenge_o = openfda_label(e)
    in_dm, laenge_i, veroeff = dailymed(e)
    zahl_openfda += bool(laenge_o)
    zahl_dailymed += bool(in_dm)
    zahl_text += bool(laenge_i)
    marken = ("o" if laenge_o else "-") + ("D" if in_dm else "-") + ("I" if laenge_i else "-")
    print(f"  {marken}  {e['datum']}  {e['name'][:26]:<26} {e['wirkstoff'][:30]:<30}"
          f" {('I=' + str(laenge_i)) if laenge_i else ''}")
    time.sleep(0.3)

n = len(zulassungen)
print(f"\n{'='*70}")
print(f"openFDA drug/label mit Indikationstext : {zahl_openfda:>3} von {n}")
print(f"DailyMed kennt das Mittel ueberhaupt   : {zahl_dailymed:>3} von {n}")
print(f"DailyMed mit lesbarem Indikationstext  : {zahl_text:>3} von {n}")
print("="*70)

with open(pathlib.Path(__file__).resolve().parent / "fda_messung.json", "w", encoding="utf-8") as f:
    json.dump(zulassungen, f, ensure_ascii=False, indent=1)
print("\nListe in fda_messung.json")
