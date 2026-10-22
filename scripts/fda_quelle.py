# -*- coding: utf-8 -*-
"""Vierte Stufe des Radars: Erstzulassungen der US-Behoerde FDA.

Zwei Quellen, beide offen und ohne Schluessel:

  **openFDA `drug/drugsfda.json`** nennt Antrag, Handelsname, Wirkstoff,
  Zulassungsdatum und Antragsklasse. Sie nennt **kein Therapiegebiet**: Von 32
  Erstzulassungen der letzten 180 Tage trug am 22.10.2026 genau **eine** einen
  Stoffklassen-Code (`pharm_class_epc`). Ohne Anwendungsgebiet ist eine
  Zuordnung zu den Hubs unmoeglich - und die Zuordnung ist der Zweck.

  **DailyMed der National Library of Medicine** liefert den Beipackzettel im
  Volltext (SPL) und damit den Abschnitt "INDICATIONS AND USAGE". Sie ist die
  Quelle, aus der openFDA sein eigenes Label-Verzeichnis speist - aber
  vollstaendiger: Am 22.10.2026 an denselben 32 Mitteln gemessen,

      openFDA  drug/label.json  : 15 mit Indikationstext
      DailyMed Services v2      : 25 mit Indikationstext
      DailyMed kennt das Mittel : 32

Zwei Klassen von Eintraegen
---------------------------
Daraus folgt der Zuschnitt dieser Stufe - die Entscheidung des Herausgebers
vom 22.10.2026:

  **A - mit Beipackzettel.** Ein Indikationstext liegt vor. Die Hub-Zuordnung
  steht damit auf einer Quelle, und der deutsche Satz ist gegen den Wirkstoff
  pruefbar. Diese Eintraege erscheinen in den Indikations-Hubs und in der
  Newsletter-Rubrik - wie die EMA-Stufen.

  **B - ohne Beipackzettel.** Das Label ist noch nicht eingestellt. Der
  Eintrag erscheint **nur** im Sammelordner "Alle", mit Name, Wirkstoff,
  Datum und dem Vermerk, dass der Beipackzettel folgt. **Kein Modellaufruf**:
  Ohne Indikation gibt es nichts zu uebersetzen und nichts zuzuordnen, und
  was das Modell dann bildet, waere geraten. Der Eintrag wandert von allein
  nach A, sobald DailyMed das Label fuehrt.

Warum nicht fda.gov
-------------------
Die Seite, die den Menschen die Liste der neuen Wirkstoffe zeigt
(`novel-drug-approvals-2026`), antwortet Maschinen mit 404 - ebenso
`accessdata.fda.gov` und selbst `robots.txt` (geprueft 22.10.2026). Nur
`api.fda.gov` antwortet. Die Adresse auf accessdata.fda.gov ist deshalb hier
**nur als Link fuer Leser** verwendet, nicht als Quelle; im Browser
aufgerufen zeigt sie den Antrag (am 22.10.2026 an NDA 221154 geprueft).

Was diese Stufe NICHT kann
--------------------------
Eine FDA-Zulassung ist **keine** europaeische. Sie sagt nichts ueber
Erstattung, nichts ueber Verfuegbarkeit in Deutschland und nichts ueber den
Stand bei der EMA. Der Satz auf der Seite muss das sagen; die Pruefung in
zulassungen.py erzwingt es.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

OPENFDA = "https://api.fda.gov/drug/drugsfda.json"
DAILYMED = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
# Fuer Leser, nicht fuer Maschinen - siehe Kopf dieser Datei.
DAF = ("https://www.accessdata.fda.gov/scripts/cder/daf/"
       "index.cfm?event=overview.process&ApplNo=")
DRUGINFO = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid="

UA = "MVF-Knowledge-Hubs/1.0 (https://knowledge-hubs.m-vf.de)"
VERSUCHE = 3
PAUSE = 3
# Hoeflichkeit gegenueber DailyMed: 32 Mittel heissen 64 Abrufe. Die NLM nennt
# keine Obergrenze, aber ein nachtlicher Lauf hat es nicht eilig.
TAKT = 0.3

# Der Abschnitt steht im SPL zweimal: einmal als Abschnitt, einmal in den
# "Highlights" am Kopf. Geschnitten wird bis zur naechsten Ueberschrift.
#
# **Die Schlussmarke muss grossgeschrieben sein.** Ueberschriften stehen im
# SPL in Versalien, Querverweise im Text dagegen gemischt: "[see Dosage and
# Administration (2.1)]". Ein Ausdruck ohne Ruecksicht auf die Schreibung
# schneidet dort - und zwar mitten im Indikationssatz. Am 22.10.2026 sind
# daran drei Zuordnungen gescheitert (ETCAMAH, JIDEYTRO, REVTORPYK): Der
# Text endete vor dem Wort "cancer", und die drei Mittel standen in keinem
# Hub. Kein Fehler, den man sieht - der Satz las sich vollstaendig.
ABSCHNITT = re.compile(
    r"INDICATIONS AND USAGE(.{40,4000}?)"
    r"(?:DOSAGE AND ADMINISTRATION|CONTRAINDICATIONS|DOSAGE FORMS|"
    r"WARNINGS AND PRECAUTIONS|ADVERSE REACTIONS)",
    re.S)


def hol(url: str, roh: bool = False):
    """Abgerissene Verbindungen wiederholen, abgelehnte nicht - wie in
    zulassungen.py. Ein 404 von DailyMed heisst: Das Mittel ist dort nicht
    gefuehrt, und beim zweiten Versuch ist es das auch nicht."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    letzter: Exception | None = None
    for versuch in range(VERSUCHE):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = r.read()
            return d if roh else json.loads(d)
        except urllib.error.HTTPError as fehler:
            if fehler.code in (404, 400):
                raise
            letzter = fehler
        except (urllib.error.URLError, TimeoutError) as fehler:
            letzter = fehler
        if versuch < VERSUCHE - 1:
            time.sleep(PAUSE * (versuch + 1))
    raise letzter if letzter else RuntimeError(url)


def _erstzulassungen(fenster_tage: int, warnungen: list[str]) -> list[dict]:
    """Die Antraege, die im Fenster erstmals zugelassen wurden.

    **Die Suche von openFDA prueft die Bedingungen nicht an derselben
    Einreichung.** Ein Antrag mit einer alten Erstzulassung und einer frischen
    Aenderung erfuellt beide Klauseln - jede an einer anderen Einreichung -
    und kommt zurueck. Am 22.10.2026 lieferte die Suche 251 Datensaetze,
    von denen 32 wirklich eine Erstzulassung im Fenster trugen. Gefiltert
    wird deshalb hier noch einmal, Einreichung fuer Einreichung. Wer sich auf
    die Trefferzahl der Suche verlaesst, baut denselben Fehler wie mit dem
    Kommissionsbeschluss der EMA: Aenderungen als Neuigkeit.
    """
    heute = dt.date.today()
    von = heute - dt.timedelta(days=fenster_tage)
    suche = (f"submissions.submission_status_date:[{von:%Y%m%d}+TO+{heute:%Y%m%d}]"
             '+AND+submissions.submission_status:"AP"'
             '+AND+submissions.submission_class_code:"TYPE+1"')
    try:
        antwort = hol(f"{OPENFDA}?search={suche}&limit=1000")
    except Exception as fehler:                       # noqa: BLE001
        warnungen.append(f"openFDA nicht erreichbar - FDA-Stufe entfaellt "
                         f"({str(fehler)[:80]})")
        return []

    roh = antwort.get("results", [])
    gefunden = []
    for d in roh:
        produkte = d.get("products") or []
        if not produkte:
            continue
        treffer = None
        for s in d.get("submissions", []):
            if (s.get("submission_status") == "AP"
                    and s.get("submission_class_code") == "TYPE 1"
                    and f"{von:%Y%m%d}" <= str(s.get("submission_status_date", ""))
                    <= f"{heute:%Y%m%d}"):
                treffer = s
                break
        if not treffer:
            continue

        # **Der Handelsname steht in `products[].brand_name`.** Nicht in
        # `openfda.brand_name` - das Feld ist nur gefuellt, wenn die FDA den
        # Antrag mit ihrem Produktverzeichnis verknuepft hat, und das tut sie
        # bei frischen Zulassungen gerade nicht. Am 22.10.2026 waren es dort
        # 11 von 43, hier 32 von 32.
        name = (produkte[0].get("brand_name") or "").strip()
        wirkstoffe: list[str] = []
        for p in produkte:
            for w in p.get("active_ingredients") or []:
                if w.get("name"):
                    wirkstoffe.append(w["name"].strip())
        if not name:
            continue
        datum = str(treffer["submission_status_date"])
        nummer = str(d.get("application_number", "")).strip()
        gefunden.append({
            "nummer": nummer,
            "name": name,
            "wirkstoff": "; ".join(dict.fromkeys(wirkstoffe)),
            "iso": f"{datum[:4]}-{datum[4:6]}-{datum[6:8]}",
            "inhaber": str(d.get("sponsor_name", "")).strip(),
            "antrag": "BLA" if nummer.startswith("BLA") else "NDA",
            "daf": DAF + re.sub(r"\D", "", nummer),
        })
    # Ein Antrag kann mehrere Produkte tragen, aber nur einmal erstzugelassen
    # werden. Entdoppelt wird ueber die Antragsnummer.
    einmal: dict[str, dict] = {}
    for e in sorted(gefunden, key=lambda x: x["iso"], reverse=True):
        einmal.setdefault(e["nummer"], e)
    return list(einmal.values())


def _indikation(e: dict) -> tuple[str, str, str]:
    """(Indikationstext, SPL-Adresse, Veroeffentlichungsdatum) aus DailyMed.

    Gesucht wird erst nach dem Handelsnamen, dann nach dem fuehrenden
    Wirkstoff. Beides noetig: Ein frisches Label laeuft manchmal nur unter
    dem Wirkstoff, ein aelteres nur unter der Marke.
    """
    kandidaten = [e["name"]]
    erster = e["wirkstoff"].split(";")[0].strip()
    if erster:
        kandidaten.append(erster)
    for wert in kandidaten:
        try:
            liste = hol(f"{DAILYMED}/spls.json?drug_name="
                        f"{urllib.parse.quote(wert)}&pagesize=5")
        except Exception:                             # noqa: BLE001
            continue
        for satz in liste.get("data", []):
            setid = satz.get("setid")
            if not setid:
                continue
            try:
                xml = hol(f"{DAILYMED}/spls/{setid}.xml", roh=True)
            except Exception:                         # noqa: BLE001
                continue
            nur = " ".join(re.sub(r"<[^>]+>", " ", xml.decode("utf-8", "replace")).split())
            treffer = ABSCHNITT.search(nur)
            if treffer and len(treffer.group(1).strip()) > 60:
                return (treffer.group(1).strip()[:2500],
                        DRUGINFO + setid, satz.get("published_date", ""))
            time.sleep(TAKT)
    return "", "", ""


def holen(fenster_tage: int, warnungen: list[str]) -> tuple[list[dict], dict]:
    """Die FDA-Erstzulassungen des Fensters, je mit Indikationstext wenn es
    einen gibt. Die Zuordnung zu den Hubs macht der Aufrufer."""
    eintraege = _erstzulassungen(fenster_tage, warnungen)
    mit = 0
    for e in eintraege:
        text, spl, veroeff = _indikation(e)
        e["indikation_en"] = text
        e["spl"] = spl
        e["spl_stand"] = veroeff
        # Der Link zeigt auf den Beipackzettel, wo es einen gibt - das ist
        # die Seite, auf der ein Leser nachlesen kann. Sonst auf den Antrag
        # bei Drugs@FDA, der wenigstens Antragsteller und Datum belegt.
        e["url"] = spl or e["daf"]
        mit += bool(text)
        time.sleep(TAKT)
    zahlen = {
        "fda_roh": len(eintraege),
        "fda_mit_label": mit,
        "fda_ohne_label": len(eintraege) - mit,
    }
    if eintraege and mit / len(eintraege) < 0.4:
        # Unter 40 % stimmt etwas mit DailyMed nicht - am 22.10.2026 waren es
        # 25 von 32 (78 %). Keine Warnung bei wenigen Eintraegen: Im Januar
        # sind drei von vier ohne Label der Normalfall.
        warnungen.append(
            f"Nur {mit} von {len(eintraege)} FDA-Zulassungen mit Indikationstext "
            f"({100*mit//len(eintraege)} %) - sonst rund 78 %. DailyMed pruefen.")
    return eintraege, zahlen


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    w: list[str] = []
    liste, z = holen(180, w)
    print(json.dumps(z, indent=1))
    for x in sorted(liste, key=lambda y: y["iso"], reverse=True):
        marke = "A" if x["indikation_en"] else "B"
        print(f"  {marke}  {x['iso']}  {x['name'][:22]:<22} {x['wirkstoff'][:34]:<34} "
              f"{len(x['indikation_en']):>5}")
    for x in w:
        print("  ! " + x)
