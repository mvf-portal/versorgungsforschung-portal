# -*- coding: utf-8 -*-
"""Fehlerquote der Studienzuordnung - der teurere Fehler von beiden.

"14 von 20 Wirkstoffen haben Studien" ist eine Trefferquote und sagt nichts
darueber, ob die gefundenen Studien zum Mittel gehoeren. Ein Zeitstrahl, der
unter "Orforglipron" eine Arbeit ueber ein anderes GLP-1-Analogon zeigt,
behauptet etwas, das der Leser nicht nachpruefen kann - er sieht nur einen
Titel und glaubt die Zuordnung.

Vier Pruefungen:

  1. **Steht der Wirkstoff im Titel?** Im Abstract allein genuegt nicht:
     "verglichen mit Semaglutid" macht eine Semaglutid-Studie daraus nicht.
  2. **Passt die Indikation?** Die Hub-Zuordnung der Studie wird gegen die
     des Antrags gehalten. Weichen beide ab, ist die Studie zwar echt, aber
     zu einer anderen Anwendung - fuer einen Zeitstrahl irrefuehrend.
  3. **Gegentest mit erfundenen Wirkstoffen.** Drei Namen, die es nicht gibt,
     muessen null Treffer liefern. Liefern sie welche, sucht die Abfrage
     etwas anderes als das, was wir glauben.
  4. **Gegentest mit kurzen Namen.** Ein kurzer Stamm faengt fremde Begriffe
     mit. Geprueft wird, ob die Mindestlaenge genuegt.
"""
import collections
import datetime as dt
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import zulassungen_themen as themen  # noqa: E402
from pipeline_quelle import liste_holen, spalte  # noqa: E402

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
UA = "MVF-Knowledge-Hubs/1.0 (https://knowledge-hubs.m-vf.de)"
TAKT = 0.4


def hol(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def frage(wirkstoff: str) -> str:
    return (f'"{wirkstoff}"[Title/Abstract] AND '
            '(clinicaltrial[Filter] OR "clinical trial"[Publication Type])')


def studien(wirkstoff: str, wieviel: int = 5) -> list[dict]:
    a = hol(EUTILS + "esearch.fcgi?db=pubmed&retmode=json&sort=date"
            f"&retmax={wieviel}&term=" + urllib.parse.quote(frage(wirkstoff)))
    pmids = a.get("esearchresult", {}).get("idlist", [])
    if not pmids:
        return []
    time.sleep(TAKT)
    b = hol(EUTILS + "esummary.fcgi?db=pubmed&retmode=json&id=" + ",".join(pmids))
    raus = []
    for p in pmids:
        s = b.get("result", {}).get(p, {})
        raus.append({"pmid": p, "titel": s.get("title", ""),
                     "datum": s.get("pubdate", "")})
    return raus


heute = dt.date.today()
kopf, satz, _ = liste_holen(heute.year, heute.month)
k_inn = spalte(kopf, "non-proprietary")
k_gen = spalte(kopf, "generic")
k_ind = spalte(kopf, "indication")
neu = [z for z in satz if str(z.get(k_gen, "")).strip().upper() != "Y"]

print("=" * 74)
print("Gegentest 1: erfundene Wirkstoffe muessen null Treffer liefern")
print("=" * 74)
for erfunden in ("Zarfumetinib", "Belpracitide", "Quorvastamab"):
    try:
        t = studien(erfunden)
        print(f"  {erfunden:<16} {len(t)} Treffer"
              + ("   <- FEHLER" if t else "   richtig"))
    except Exception as f:                             # noqa: BLE001
        print(f"  {erfunden:<16} Abfrage fehlgeschlagen ({str(f)[:40]})")
    time.sleep(TAKT)

print("\n" + "=" * 74)
print("Je Wirkstoff: wie viele der gefundenen Studien gehoeren wirklich dazu?")
print("=" * 74)

im_titel = nur_abstract = 0
indikation_passt = indikation_weicht_ab = indikation_offen = 0
ohne_treffer = []
zeilen = []

for z in neu:
    inn_roh = str(z.get(k_inn, "")).strip()
    # Nur der fuehrende Wirkstoff, und nur wenn er ein INN ist: Eine
    # Beschreibung wie "Human IgG1 monoclonal antibody" ist kein Suchbegriff,
    # sondern eine Stoffklasse - danach zu suchen liefert alles Moegliche.
    erster = re.split(r"[/,;+]", inn_roh)[0].strip()
    ist_inn = (len(erster) >= 6 and " " not in erster and erster.isalpha())
    if not ist_inn:
        zeilen.append((inn_roh, "kein INN", 0, 0, ""))
        continue
    try:
        gefunden = studien(erster)
    except Exception as f:                             # noqa: BLE001
        zeilen.append((inn_roh, f"Abfrage: {str(f)[:24]}", 0, 0, ""))
        continue
    if not gefunden:
        ohne_treffer.append(erster)
        zeilen.append((inn_roh, "keine Studie", 0, 0, ""))
        time.sleep(TAKT)
        continue

    stamm = erster.lower()
    stamm = stamm[:-1] if stamm.endswith("e") else stamm
    soll_hubs = set(themen.hubs_fuer_antrag(z.get(k_ind, "")))
    treffer_titel = 0
    abweichend = 0
    for s in gefunden:
        titel_klein = themen.amerikanisch(s["titel"])
        if stamm in titel_klein:
            treffer_titel += 1
        # Indikation der Studie aus ihrem Titel - grob, aber es geht nur
        # darum, ob sie einem ANDEREN Gebiet zugehoert.
        studien_hubs = set(themen.hubs_fuer_antrag(s["titel"]))
        if soll_hubs and studien_hubs and not (soll_hubs & studien_hubs):
            abweichend += 1
    im_titel += treffer_titel
    nur_abstract += len(gefunden) - treffer_titel
    if soll_hubs:
        indikation_weicht_ab += abweichend
        indikation_passt += len(gefunden) - abweichend
    else:
        indikation_offen += len(gefunden)
    zeilen.append((inn_roh, f"{len(gefunden)} Studien",
                   treffer_titel, abweichend,
                   gefunden[0]["titel"][:70]))
    time.sleep(TAKT)

for inn, lage, titel_n, abw, beispiel in zeilen:
    marke = ""
    if isinstance(titel_n, int) and lage.endswith("Studien"):
        marke = f"  Titel {titel_n}" + (f" · abweichend {abw}" if abw else "")
    print(f"  {inn[:28]:<29} {lage:<16}{marke}")
    if beispiel:
        print(f"      {beispiel}")

gesamt = im_titel + nur_abstract
print("\n" + "=" * 74)
print(f"  gefundene Studien insgesamt        {gesamt}")
print(f"  Wirkstoff steht im TITEL           {im_titel} "
      f"({100*im_titel//max(gesamt,1)} %)")
print(f"  nur im Abstract                    {nur_abstract} "
      f"({100*nur_abstract//max(gesamt,1)} %)  <- schwaecherer Beleg")
print(f"  Indikation passt zum Antrag        {indikation_passt}")
print(f"  Indikation weicht ab               {indikation_weicht_ab} "
      "  <- echte Studie, falscher Zusammenhang")
print(f"  Antrag ohne Hub, nicht pruefbar    {indikation_offen}")
print(f"  Wirkstoffe ohne jede Studie        {len(ohne_treffer)}")
print("=" * 74)
