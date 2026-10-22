# -*- coding: utf-8 -*-
"""Die Studien zu einem Wirkstoff, der bei der EMA in Pruefung ist.

Der Herausgeber wuenschte die kommenden Arzneimittel mit ihren Studien auf
einem Zeitstrahl. Die naheliegende Annahme war, die Studien laegen in den
Hub-Archiven bereits vor. **Sie stimmt nicht:** Von 57 Wirkstoffen in
Pruefung kamen am 22.10.2026 drei in den 5.180 Eintraegen aller fuenfzehn
Archive vor, und einer davon war ein Fehltreffer. Das ist kein Mangel der
Hubs - sie waehlen Versorgungsforschung aus, keine Zulassungsstudien, und
rund 370 Eintraege je Hub koennen die Literatur zu 57 Molekuelen nicht
enthalten.

Gezielt bei PubMed gefragt findet man sie dagegen.

Die Regel, und warum sie so streng ist
--------------------------------------
Gemessen an 163 gefundenen Studien (pipeline_fehlerquote_studien.py):

  - In **141 (86 %)** stand der Wirkstoff im **Titel**.
  - In 22 (13 %) nur im Abstract. Das ist der schwaechere Beleg: "verglichen
    mit Semaglutid" macht aus einer Arbeit keine Semaglutid-Studie.
  - **Acht** gehoerten zum Wirkstoff, aber zu einer anderen Indikation als
    der beantragten - echte Studie, falscher Zusammenhang.
  - Drei erfundene Wirkstoffnamen lieferten je null Treffer.

Daraus zwei Festlegungen:

1. **Nur echte INN** werden gesucht. "Human IgG1 monoclonal antibody" ist
   eine Stoffklasse, kein Name; danach zu suchen liefert alles Moegliche.
2. **Der Wirkstoff muss im Titel stehen.** Das verwirft rund 13 % der
   Treffer - und zwar genau die, die ein Leser nicht nachpruefen kann.

Die acht abweichenden Indikationen bleiben. Sie werden nicht weggefiltert,
sondern **nicht behauptet**: Die Seite nennt den Block "Studien zum
Wirkstoff", nicht "Zulassungsstudien". Eine Ueberschrift, die weniger
verspricht, ist billiger als ein Filter, der sich irren kann.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
UA = "MVF-Knowledge-Hubs/1.0 (https://knowledge-hubs.m-vf.de)"
TAKT = 0.4          # PubMed erlaubt ohne Schluessel drei Abfragen je Sekunde
JE_WIRKSTOFF = 4    # mehr braucht ein Zeitstrahl nicht


def _hol(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


MONATE_EN = {"jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05",
             "jun": "06", "jul": "07", "aug": "08", "sep": "09", "oct": "10",
             "nov": "11", "dec": "12"}


def _monat(pubdate: str) -> str:
    """PubMeds Datum als JJJJ-MM.

    `esummary` liefert "2026 Jun", "2025 Nov 15" oder nur "2026" - niemals
    ISO. Am 22.10.2026 wurden die ersten sieben Zeichen genommen ("2026 Ju"),
    und der Zeitstrahl zeigte **einen** Studienpunkt statt 43: Jedes dieser
    Daten war im Browser ungueltig, und ein ungueltiges Datum faellt nicht
    auf - es zeichnet einfach nichts.
    """
    teile = str(pubdate or "").replace("-", " ").split()
    if not teile or not teile[0].isdigit():
        return ""
    jahr = teile[0]
    monat = "01"
    if len(teile) > 1:
        monat = MONATE_EN.get(teile[1][:3].lower(), "")
        if not monat:
            monat = teile[1].zfill(2) if teile[1].isdigit() else "01"
    return f"{jahr}-{monat}"


def _stamm(inn: str) -> str:
    """Der Wortstamm, gegen den der Titel geprueft wird. Das englische End-e
    faellt im Deutschen weg (Temozolomid/temozolomide) - und manche Titel
    schreiben den Wirkstoff eingedeutscht."""
    s = str(inn or "").strip().lower()
    return s[:-1] if s.endswith("e") and len(s) > 6 else s


def fuer(inn: str, warnungen: list[str]) -> list[dict]:
    """Bis zu vier Studien zum Wirkstoff, juengste zuerst."""
    erster = re.split(r"[/,;+]", str(inn or ""))[0].strip()
    if not (len(erster) >= 6 and " " not in erster and erster.isalpha()):
        return []
    frage = (f'"{erster}"[Title/Abstract] AND '
             '(clinicaltrial[Filter] OR "clinical trial"[Publication Type])')
    try:
        a = _hol(EUTILS + "esearch.fcgi?db=pubmed&retmode=json&sort=date"
                 f"&retmax={JE_WIRKSTOFF * 2}&term=" + urllib.parse.quote(frage))
        pmids = a.get("esearchresult", {}).get("idlist", [])
        if not pmids:
            return []
        time.sleep(TAKT)
        b = _hol(EUTILS + "esummary.fcgi?db=pubmed&retmode=json&id="
                 + ",".join(pmids))
    except Exception as fehler:                        # noqa: BLE001
        warnungen.append(f"{erster}: PubMed nicht erreichbar "
                         f"({str(fehler)[:60]})")
        return []

    stamm = _stamm(erster)
    raus = []
    for p in pmids:
        s = b.get("result", {}).get(p, {})
        titel = " ".join(str(s.get("title", "")).split())
        # **Der Wirkstoff muss im Titel stehen.** Siehe Kopf dieser Datei.
        if stamm not in titel.lower():
            continue
        raus.append({
            "pmid": p,
            "titel": titel.rstrip("."),
            "datum": _monat(s.get("pubdate", "")),
            "journal": str(s.get("source", "")),
        })
        if len(raus) >= JE_WIRKSTOFF:
            break
    return raus


def anreichern(eintraege: list[dict], alt: dict, warnungen: list[str]) -> int:
    """Jedem Antrag seine Studien - einmal gesucht, dann aufbewahrt.

    Aufbewahrt wird ueber die EMA-Produktnummer, wie der deutsche Satz: Ein
    Wirkstoff steht ein Jahr lang in der Liste, und 57 PubMed-Abfragen jede
    Nacht waeren 20.000 im Jahr fuer eine Literatur, die sich monatlich
    kaum aendert. Gesucht wird deshalb nur, was noch keine Studien hat.
    """
    bekannt = {e.get("nummer"): e.get("studien")
               for e in alt.get("eintraege", []) if e.get("studien")}
    neu = 0
    for e in eintraege:
        if e["stufe"] != "antrag":
            continue
        if e["nummer"] in bekannt:
            e["studien"] = bekannt[e["nummer"]]
            continue
        if not e.get("suchbar"):
            e["studien"] = []
            continue
        e["studien"] = fuer(e["name"], warnungen)
        neu += 1
        time.sleep(TAKT)
    return neu
