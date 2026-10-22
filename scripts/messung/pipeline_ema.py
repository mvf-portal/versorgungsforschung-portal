# -*- coding: utf-8 -*-
"""Die EMA-Liste der laufenden Antraege - taugt sie als fuenfte Stufe?

Die EMA veroeffentlicht **monatlich** eine Excel-Liste aller Antraege auf
Neuzulassung, die beim CHMP in der Pruefung sind:

    .../documents/report/applications-new-human-medicines-under-evaluation-
    <monat>-<jahr>_en.xlsx

Das ist die einzige offene Pipeline der EU, und sie ist amtlich - keine
Herstellerankuendigung. Gemessen wird dreierlei:

  1. **Was steht drin?** Spalten, Zeilen, und ob ein Anwendungsgebiet dabei
     ist - ohne das gibt es keine Zuordnung zu den Hubs.
  2. **Wie viel Vorsprung?** Wie lange liegt der Verfahrensbeginn vor dem
     Gutachten? Dafuer werden die Mittel, die heute im Gutachtenstand oder
     zugelassen sind, in alten Monatslisten gesucht.
  3. **Laesst sich der Eintrag spaeter wiedererkennen?** Wenn ja, kann ein
     Eintrag von der Stufe "in Pruefung" in "empfohlen" und "zugelassen"
     wandern, statt dreimal als Neuigkeit zu erscheinen.
"""
import collections
import datetime as dt
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import openpyxl  # noqa: E402

import zulassungen  # noqa: E402

VORLAGE = ("https://www.ema.europa.eu/en/documents/report/"
           "applications-new-human-medicines-under-evaluation-{}-{}_en.xlsx")
MONATE = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def liste_holen(jahr: int, monat: int):
    adresse = VORLAGE.format(MONATE[monat - 1], jahr)
    roh = zulassungen.hol(adresse)
    mappe = openpyxl.load_workbook(io.BytesIO(roh), read_only=True, data_only=True)
    blatt = mappe[mappe.sheetnames[0]]
    zeilen = list(blatt.iter_rows(values_only=True))
    mappe.close()
    # Die Kopfzeile ist die erste Zeile mit mehr als drei gefuellten Feldern -
    # fest verdrahtet waere das eine Zeitbombe, wie bei der Medicines-Tabelle.
    kopf_i = next(i for i, z in enumerate(zeilen)
                  if sum(1 for w in z if w not in (None, "")) > 3)
    kopf = [str(w).strip() if w else "" for w in zeilen[kopf_i]]
    satz = []
    for z in zeilen[kopf_i + 1:]:
        if not z or not any(z):
            continue
        satz.append({k: w for k, w in zip(kopf, z) if k})
    return kopf, satz, adresse


heute = dt.date.today()
print("=" * 74)
print("1. Was steht in der aktuellen Liste?")
print("=" * 74)
kopf, satz, adresse = liste_holen(heute.year, heute.month)
print(f"{adresse.rsplit('/', 1)[1]}\n{len(satz)} laufende Antraege\n")
print("Spalten:")
for k in kopf:
    if not k:
        continue
    gefuellt = sum(1 for z in satz if z.get(k) not in (None, ""))
    print(f"  {k[:46]:<47} {gefuellt:>4} von {len(satz)} gefuellt")

print("\nDrei Beispiele:")
for z in satz[:3]:
    for k in kopf:
        if k and z.get(k) not in (None, ""):
            print(f"    {k[:28]:<29} {str(z[k])[:76]}")
    print()

print("=" * 74)
print("2. Wie viel Vorsprung gegenueber dem Gutachten?")
print("=" * 74)
# Die Mittel, die HEUTE im Gutachtenstand sind, in alten Monatslisten suchen.
tabelle = zulassungen.tabelle_lesen(zulassungen.hol(zulassungen.EMA_URL))
gutachten = [z for z in tabelle
             if str(z["kategorie"]).strip().lower() == "human"
             and str(z["status"]).strip() == "Opinion"
             and zulassungen.datum(z["gutachten_am"])]
print(f"{len(gutachten)} Mittel stehen heute im Gutachtenstand.\n")

# Spalte mit der Produktnummer finden - der Schluessel zwischen beiden Quellen.
nummernspalte = next((k for k in kopf if k and "prod" in k.lower()
                      and "num" in k.lower()), None)
print(f"Produktnummer-Spalte: {nummernspalte or '(keine gefunden)'}")

treffer = []
for zurueck in (3, 6, 9, 12, 15, 18):
    monat = heute.month - zurueck
    jahr = heute.year + (monat - 1) // 12
    monat = (monat - 1) % 12 + 1
    try:
        _, alt, _ = liste_holen(jahr, monat)
    except Exception as fehler:                        # noqa: BLE001
        print(f"  {MONATE[monat-1]} {jahr}: nicht abrufbar ({str(fehler)[:50]})")
        continue
    if nummernspalte:
        drin = {str(z.get(nummernspalte, "")).strip() for z in alt}
        gefunden = sum(1 for g in gutachten
                       if str(g["nummer"]).strip() in drin)
    else:
        drin = {str(z.get(kopf[0], "")).strip().lower() for z in alt}
        gefunden = sum(1 for g in gutachten
                       if str(g["inn"] or "").strip().lower() in drin)
    treffer.append((zurueck, len(alt), gefunden))
    print(f"  vor {zurueck:>2} Monaten ({MONATE[monat-1]} {jahr}): "
          f"{len(alt):>3} Antraege, davon {gefunden:>2} von {len(gutachten)} "
          "der heutigen Gutachten schon dabei")

print("\n" + "=" * 74)
print("3. Was folgt daraus")
print("=" * 74)
if treffer:
    bester = max(treffer, key=lambda t: t[2])
    print(f"Die fruehste Liste, in der die heutigen Gutachten auftauchen, liegt")
    print(f"{bester[0]} Monate zurueck ({bester[2]} von {len(gutachten)}).")
print("Zum Vergleich: Die heutige Stufe 'Empfohlen' liegt rund 2 Monate vor")
print("der Zulassung.")
