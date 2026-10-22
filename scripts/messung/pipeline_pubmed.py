# -*- coding: utf-8 -*-
"""Liefert PubMed die Zulassungsstudien, wenn man gezielt nach dem Wirkstoff fragt?

Die Hub-Archive tun es nicht: Nur 3 von 57 kommenden Wirkstoffen kamen darin
vor (pipeline_studien.py), und einer davon war ein Fehltreffer. Das ist kein
Mangel der Hubs - sie waehlen Versorgungsforschung aus, nicht
Zulassungsstudien. Ein Archiv von rund 370 Eintraegen je Hub kann die
Studienlage zu 57 einzelnen Molekuelen gar nicht enthalten.

Die Frage ist deshalb nicht, ob wir die Studien schon haben, sondern ob man
sie **gezielt** bekommt. Gefragt wird mit dem Wirkstoffnamen als
Substanzbegriff, eingegrenzt auf klinische Studien.
"""
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline_quelle import liste_holen, spalte  # noqa: E402

ESEARCH = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
           "?db=pubmed&retmode=json&retmax=5&sort=date&term=")
ESUMMARY = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            "?db=pubmed&retmode=json&id=")
UA = "MVF-Knowledge-Hubs/1.0 (https://knowledge-hubs.m-vf.de)"


def hol(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def studien(wirkstoff: str) -> tuple[int, list[str]]:
    """(Trefferzahl, die juengsten Titel)."""
    # Phase-3- und Zulassungsstudien, nicht jede Erwaehnung: Der Filter
    # "clinical trial" schliesst Uebersichtsarbeiten und Kommentare aus.
    frage = (f'"{wirkstoff}"[Title/Abstract] AND '
             '(clinicaltrial[Filter] OR "clinical trial"[Publication Type])')
    a = hol(ESEARCH + urllib.parse.quote(frage))
    ergebnis = a.get("esearchresult", {})
    zahl = int(ergebnis.get("count", 0))
    pmids = ergebnis.get("idlist", [])[:3]
    titel = []
    if pmids:
        time.sleep(0.4)
        b = hol(ESUMMARY + ",".join(pmids))
        for p in pmids:
            satz = b.get("result", {}).get(p, {})
            titel.append(f"{satz.get('pubdate','?')[:7]} · "
                         f"{satz.get('title','')[:78]}")
    return zahl, titel


heute = dt.date.today()
kopf, satz, _ = liste_holen(heute.year, heute.month)
k_inn = spalte(kopf, "non-proprietary")
k_gen = spalte(kopf, "generic")
k_ind = spalte(kopf, "indication")
k_start = spalte(kopf, "start of evaluation")
neu = [z for z in satz if str(z.get(k_gen, "")).strip().upper() != "Y"]
neu.sort(key=lambda z: str(z.get(k_start, "")), reverse=True)

print(f"{len(neu)} neue Wirkstoffe in EU-Pruefung. Geprueft werden die 20 "
      "mit dem juengsten Verfahrensbeginn.\n")

mit = ohne = 0
for z in neu[:20]:
    inn = str(z.get(k_inn, "")).split("/")[0].strip()
    if len(inn) < 5:
        continue
    try:
        zahl, titel = studien(inn)
    except Exception as fehler:                        # noqa: BLE001
        print(f"  {inn[:26]:<27} Abfrage fehlgeschlagen ({str(fehler)[:40]})")
        continue
    if zahl:
        mit += 1
    else:
        ohne += 1
    print(f"  {inn[:26]:<27} {zahl:>4} klinische Studien   "
          f"{str(z.get(k_ind,''))[:38]}")
    for t in titel[:1]:
        print(f"      {t}")
    time.sleep(0.4)

print(f"\n  mit mindestens einer klinischen Studie: {mit} von {mit + ohne}")
print(f"  ohne:                                  {ohne}")
print("\nZum Vergleich: In den Hub-Archiven fanden sich 3 von 57 (5 %).")
