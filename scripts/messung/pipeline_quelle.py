# -*- coding: utf-8 -*-
"""Die monatliche EMA-Liste der laufenden Antraege - nur das Holen.

Eigenes Modul, damit die Messskripte sie importieren koennen, ohne dass
dabei eine fremde Messung mitlaeuft: `pipeline_ema.py` ist ein Skript und
fuehrt beim Import seinen ganzen Rumpf aus. Am 22.10.2026 kam deshalb die
Ausgabe der einen Messung aus der anderen heraus.

Die Quelle
----------
    https://www.ema.europa.eu/en/documents/report/
    applications-new-human-medicines-under-evaluation-<monat>-<jahr>_en.xlsx

Monatlich, offen, amtlich. Zwoelf Spalten, alle gefuellt (gemessen am
22.10.2026 an der Oktoberliste): INN, Indikationstext, Stoffklasse,
EMA-Produktnummer, die Kennzeichen beschleunigt / Orphan / PRIME / OPEN,
**die Angabe Generikum-Hybrid-Biosimilar** und der Verfahrensbeginn.

Zwei Felder entscheiden ueber die Brauchbarkeit:

  - **`Generic, hybrid or Biosimilar`.** 35 der 92 Antraege sind das, und
    ein Generikum ist keine Nachricht. Ohne diesen Filter bestuende die
    Haelfte einer Pipeline-Stufe aus Abatacept-Nachbauten.
  - **`EMA Prod. Number`.** Der Schluessel zur Medicines-Tabelle, aus der
    die uebrigen Stufen kommen - damit wandert ein Eintrag von "in Pruefung"
    nach "empfohlen" und "zugelassen", statt dreimal als Neuigkeit zu
    erscheinen. **Es gibt die Spalte erst seit Oktober 2025**; aeltere
    Listen lassen sich nur ueber den INN abgleichen.
"""
from __future__ import annotations

import io
import pathlib
import sys

import openpyxl

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import zulassungen  # noqa: E402

VORLAGE = ("https://www.ema.europa.eu/en/documents/report/"
           "applications-new-human-medicines-under-evaluation-{}-{}_en.xlsx")
MONATE = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def liste_holen(jahr: int, monat: int) -> tuple[list[str], list[dict], str]:
    """(Spaltennamen, Zeilen als dict, Adresse)."""
    adresse = VORLAGE.format(MONATE[monat - 1], jahr)
    roh = zulassungen.hol(adresse)
    mappe = openpyxl.load_workbook(io.BytesIO(roh), read_only=True, data_only=True)
    blatt = mappe[mappe.sheetnames[0]]
    zeilen = list(blatt.iter_rows(values_only=True))
    mappe.close()
    # Die Kopfzeile ist die erste Zeile mit mehr als drei gefuellten Feldern.
    # Fest verdrahtet waere das eine Zeitbombe - dieselbe Vorsicht wie bei der
    # Medicines-Tabelle, deren Vorspann neun Zeilen lang ist.
    kopf_i = next(i for i, z in enumerate(zeilen)
                  if sum(1 for w in z if w not in (None, "")) > 3)
    kopf = [str(w).strip() if w else "" for w in zeilen[kopf_i]]
    satz = []
    for z in zeilen[kopf_i + 1:]:
        if not z or not any(z):
            continue
        satz.append({k: w for k, w in zip(kopf, z) if k})
    return kopf, satz, adresse


def spalte(kopf: list[str], teil: str) -> str:
    """Die Spalte, deren Name `teil` enthaelt - mit Ansage, wenn es sie nicht
    gibt. Die EMA hat die Kopfzeile seit 2021 zweimal erweitert; ein stilles
    `None` waere eine leere Stufe ohne Fehlermeldung."""
    for k in kopf:
        if k and teil.lower() in k.lower():
            return k
    raise SystemExit(
        f"Spalte mit '{teil}' fehlt in der EMA-Liste. Vorhanden: "
        + ", ".join(k for k in kopf if k))
