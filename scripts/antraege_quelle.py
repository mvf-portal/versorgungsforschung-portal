# -*- coding: utf-8 -*-
"""Fuenfte Stufe: Arzneimittel, die bei der EMA in der Pruefung sind.

Die EMA veroeffentlicht **monatlich** eine Excel-Liste aller laufenden
Verfahren zur Neuzulassung:

    https://www.ema.europa.eu/en/documents/report/
    applications-new-human-medicines-under-evaluation-<monat>-<jahr>_en.xlsx

Das ist die einzige offene Pipeline der EU, und sie ist **amtlich** - kein
Hersteller, der ankuendigt, sondern ein Verfahren, das laeuft.
Herstellerpipelines scheiden als Quelle aus: Hunderte Unternehmen, jede
Seite anders gebaut, keine Schnittstelle, und jede ist Werbung in eigener
Sache.

Wie viel Vorsprung (gemessen 22.10.2026 ueber den INN)
------------------------------------------------------
Anteil der damals aktuellen CHMP-Gutachten, die in einer aelteren Liste
schon standen:

    vor  3 Monaten  78 %        vor 12 Monaten  50 %
    vor  6 Monaten  89 %        vor 15 Monaten  17 %
    vor  9 Monaten  82 %        vor 18 Monaten   3 %

Die bis dahin frueheste Stufe ("Empfohlen") liegt rund **zwei** Monate vor
der Zulassung. Diese liegt **acht bis vierzehn** Monate davor.

Zwei Felder entscheiden ueber die Brauchbarkeit
-----------------------------------------------
- **`Generic, hybrid or Biosimilar`.** 35 der 92 Antraege waren das, und ein
  Generikum ist keine Nachricht. Ohne diesen Filter bestuende die halbe
  Stufe aus Abatacept-Nachbauten.
- **`EMA Prod. Number`.** Der Schluessel zur Medicines-Tabelle, aus der die
  Stufen 1 und 2 kommen. Damit **wandert** ein Eintrag von "in Pruefung"
  nach "empfohlen" und "zugelassen", statt dreimal als Neuigkeit zu
  erscheinen. Es gibt die Spalte erst seit Oktober 2025.

Was diese Stufe NICHT sagt
--------------------------
**Kein Zieldatum.** Die EMA nennt keines, und aus dem Verfahrensbeginn liesse
es sich nur schaetzen. Eine geschaetzte Zahl, die wie eine Zusage aussieht,
waere genau die Art Aussage, die dieser Radar sonst vermeidet - ein Leser
nimmt "Zulassung erwartet 03/2027" nicht als Schaetzung. Die Seite zeigt
deshalb ein **Band** mit der gemessenen Spanne, keinen Punkt.

Und: Ein laufendes Verfahren kann **zurueckgezogen oder abgelehnt** werden.
In der Medicines-Tabelle standen am 22.10.2026 268 zurueckgezogene Antraege
und 65 abgelehnte. Der Text auf der Seite muss das sagen.
"""
from __future__ import annotations

import datetime as dt
import io
import pathlib
import re
import sys

import openpyxl

HIER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import zulassungen_themen as themen  # noqa: E402

VORLAGE = ("https://www.ema.europa.eu/en/documents/report/"
           "applications-new-human-medicines-under-evaluation-{}-{}_en.xlsx")
MONATE = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]

# Die Seite, auf der alle Monatslisten stehen - als Beleg fuer den Leser.
QUELLSEITE = ("https://www.ema.europa.eu/en/medicines/"
              "medicines-human-use-under-evaluation")

# Gemessene Spanne zwischen Verfahrensbeginn und Gutachten. Daraus baut die
# Seite ihr Band. Keine Zusage, sondern eine Beobachtung an 28 Gutachten.
SPANNE_MONATE = (9, 14)


def spalte(kopf: list[str], teil: str) -> str:
    """Die Spalte, deren Name `teil` enthaelt - mit Ansage, wenn es sie nicht
    gibt. Die EMA hat die Kopfzeile seit 2021 zweimal erweitert; ein stilles
    `None` waere eine leere Stufe ohne Fehlermeldung."""
    for k in kopf:
        if k and teil.lower() in k.lower():
            return k
    raise SystemExit(
        f"Spalte mit '{teil}' fehlt in der EMA-Antragsliste. Vorhanden: "
        + ", ".join(k for k in kopf if k))


def _lesen(roh: bytes) -> tuple[list[str], list[dict]]:
    mappe = openpyxl.load_workbook(io.BytesIO(roh), read_only=True, data_only=True)
    blatt = mappe[mappe.sheetnames[0]]
    zeilen = list(blatt.iter_rows(values_only=True))
    mappe.close()
    # Die Kopfzeile ist die erste mit mehr als drei gefuellten Feldern. Fest
    # verdrahtet waere das eine Zeitbombe - dieselbe Vorsicht wie bei der
    # Medicines-Tabelle, deren Vorspann neun Zeilen lang ist.
    kopf_i = next(i for i, z in enumerate(zeilen)
                  if sum(1 for w in z if w not in (None, "")) > 3)
    kopf = [str(w).strip() if w else "" for w in zeilen[kopf_i]]
    satz = []
    for z in zeilen[kopf_i + 1:]:
        if not z or not any(z):
            continue
        satz.append({k: w for k, w in zip(kopf, z) if k})
    return kopf, satz


def _iso(wert) -> str:
    if isinstance(wert, dt.datetime):
        return wert.date().isoformat()
    if isinstance(wert, dt.date):
        return wert.isoformat()
    s = str(wert or "")[:10]
    return s if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else ""


def ist_inn(name: str) -> bool:
    """Taugt der Name als Suchbegriff fuer die Literatur?

    Die Liste fuehrt neben echten INN auch Beschreibungen: "Human IgG1
    monoclonal antibody", "Bilayer engineered skin composite", "Lyme
    borreliosis vaccine (6-valent)". Das sind Stoffklassen, keine Namen -
    danach zu suchen liefert alles Moegliche. Am 22.10.2026 waren vier der
    57 Antraege so benannt.
    """
    n = str(name or "").strip()
    return len(n) >= 6 and " " not in n and n.isalpha()


def holen(warnungen: list[str], heute: dt.date | None = None,
          hol=None) -> tuple[list[dict], dict]:
    """Die laufenden Antraege auf Neuzulassung, den Hubs zugeordnet.

    `hol` ist die Abrufmethode (wird von zulassungen.py hereingereicht,
    damit es nur eine Stelle mit Wiederholungslogik gibt).
    """
    if hol is None:
        import zulassungen
        hol = zulassungen.hol
    heute = heute or dt.date.today()

    # Die Liste des laufenden Monats; erscheint sie noch nicht, die des
    # Vormonats. Die EMA stellt sie im Lauf des Monats ein, und ein Lauf am
    # Ersten soll nicht scheitern.
    roh = kopf = satz = None
    for zurueck in (0, 1):
        monat = heute.month - zurueck
        jahr = heute.year + (monat - 1) // 12
        monat = (monat - 1) % 12 + 1
        try:
            roh = hol(VORLAGE.format(MONATE[monat - 1], jahr))
            kopf, satz = _lesen(roh)
            stand = f"{MONATE[monat - 1]} {jahr}"
            break
        except Exception as fehler:                    # noqa: BLE001
            letzter = fehler
    if satz is None:
        warnungen.append("EMA-Antragsliste nicht abrufbar - fuenfte Stufe "
                         f"entfaellt ({str(letzter)[:80]})")
        return [], {"antrag_roh": 0, "antrag_gezeigt": 0}

    k_inn = spalte(kopf, "non-proprietary")
    k_gen = spalte(kopf, "generic")
    k_ind = spalte(kopf, "indication")
    k_start = spalte(kopf, "start of evaluation")
    k_nr = spalte(kopf, "prod")
    k_orphan = spalte(kopf, "orphan")
    k_prime = spalte(kopf, "prime")
    k_schnell = spalte(kopf, "accelerated")

    eintraege = []
    generisch = 0
    ohne_hub = 0
    for z in satz:
        if str(z.get(k_gen, "")).strip().upper() == "Y":
            generisch += 1
            continue
        inn = " ".join(str(z.get(k_inn, "") or "").split())
        indikation = " ".join(str(z.get(k_ind, "") or "").split())
        beginn = _iso(z.get(k_start))
        if not inn or not beginn:
            continue
        hubs = themen.hubs_fuer_antrag(indikation)
        if not hubs:
            ohne_hub += 1
        kennzeichen = []
        for name, feld in (("Orphan Drug", k_orphan), ("PRIME", k_prime),
                           ("beschleunigt", k_schnell)):
            if str(z.get(feld, "")).strip().upper() == "Y":
                kennzeichen.append(name)
        eintraege.append({
            "stufe": "antrag",
            "datum": beginn,
            "name": inn,
            "wirkstoff": inn,
            "gebiet_mesh": "",
            "atc": "",
            "inhaber": "",
            "kennzeichen": kennzeichen,
            "gutachten": "",
            "nummer": "EMA-" + str(z.get(k_nr, "") or "").strip(),
            "url": QUELLSEITE,
            "indikation_en": indikation,
            # `ohne-hub` ist kein Hub, sondern der Durchgang zur Rubrik
            # "Alle" - dieselbe Vorkehrung wie bei den FDA-Zulassungen ohne
            # Beipackzettel. Die Seite baut "Alle" aus den Gebietsgruppen,
            # und was in keiner steht, stuende nirgends. 26 der 57 Antraege
            # betrifft das: HIV, seltene Erkrankungen, Diagnostika.
            "hubs": hubs or ["ohne-hub"],
            "satz": "",
            # Fuer den Zeitstrahl und die Literatursuche.
            "suchbar": ist_inn(inn.split("/")[0].strip()),
        })

    eintraege.sort(key=lambda e: e["datum"], reverse=True)
    zahlen = {
        "antrag_roh": len(satz),
        "antrag_generisch": generisch,
        "antrag_gezeigt": len(eintraege),
        "antrag_ohne_hub": ohne_hub,
        "antrag_stand": stand,
    }
    if eintraege and generisch / max(len(satz), 1) > 0.7:
        warnungen.append(
            f"{generisch} von {len(satz)} Antraegen sind Generika "
            "- sonst rund 38 %. Spalte 'Generic, hybrid or Biosimilar' pruefen.")
    return eintraege, zahlen


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    w: list[str] = []
    liste, z = holen(w)
    print(z)
    for e in liste[:15]:
        print(f"  {e['datum']}  {e['name'][:28]:<29} "
              f"{','.join(e['hubs']) or '-':<22} {e['indikation_en'][:46]}")
    for x in w:
        print("  ! " + x)
