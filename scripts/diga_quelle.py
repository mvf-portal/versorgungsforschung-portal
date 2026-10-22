# -*- coding: utf-8 -*-
"""Digitale Gesundheitsanwendungen aus den Bekanntmachungen des BfArM.

Die dritte Stufe des Zulassungsradars. Eine DiGA wird nicht zugelassen, sie
wird in das **Verzeichnis erstattungsfaehiger digitaler
Gesundheitsanwendungen** aufgenommen (§§ 33a, 139e SGB V) - vorlaeufig zur
Erprobung oder dauerhaft. Fuer den Leser ist das dieselbe Frage wie bei einem
Arzneimittel: Was ist neu, und wird es bezahlt.

Quelle
------
Die quartalsweisen Bekanntmachungen des BfArM, als PDF. Erreichbar ueber einen
**offenen** Endpunkt des DiGA-Verzeichnisses:

    https://diga.bfarm.de/api/diga-vz/proclamations      (JSON, Liste)
    https://diga.bfarm.de/api/diga-vz/media/<id>         (das PDF)

**Nicht** ueber die FHIR-Schnittstelle desselben Verzeichnisses: Die verlangt
eine Autorisierung, die nur die Webseite selbst bekommt, und antwortet von
aussen mit 401. Eine Zugangssperre zu umgehen kommt nicht in Frage; die
Bekanntmachungen sind der dokumentierte Weg und amtlich dazu.

Der Preis dafuer steht in der Quelle selbst: **Die Bekanntmachung nennt kein
Anwendungsgebiet.** Sie fuehrt je Eintrag nur Bezeichnung, DiGA-ID, Datum und
Hersteller. Das Verzeichnis kennt die Indikation samt ICD-Schluessel - aber
eben hinter jener Schnittstelle. Zugeordnet wird deshalb nach dem Namen, und
jede DiGA steht in jedem Fall im Hub Digitalisierung, KI & Gesundheit.

Zwei Fallen, beide am 22.10.2026 zugeschlagen
---------------------------------------------
1. **Die Zwischenueberschriften brechen ueber Zeilen um.** Ein Muster gegen den
   Rohtext findet dann nur die letzte Rubrik - gemessen: eine von vier. Der
   Text wird deshalb zuerst flachgezogen.
2. **Die DiGA-ID hat nicht immer fuenf Stellen.** Die juengsten Eintraege
   tragen "02857", die bis 2024 nur "294". Ein Muster auf genau fuenf Stellen
   las siebzehn der fuenfundzwanzig Bekanntmachungen als leer - ohne Fehler,
   denn eine Bekanntmachung ohne Eintraege ist denkbar.

Gegengelesen am 22.10.2026 ueber alle 25 Bekanntmachungen: 418 Eintraege,
keine Bekanntmachung ohne Treffer, 17 Zeilen ohne erkennbare Rechtsform im
Herstellernamen (die werden gemeldet, nicht stillschweigend geraten).
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import ssl
import urllib.request

import pypdf

LISTE = "https://diga.bfarm.de/api/diga-vz/proclamations"
MEDIUM = "https://diga.bfarm.de/api/diga-vz/media/{}"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")

# Welche Rubriken der Bekanntmachung eine Nachricht sind. "Aenderung" und
# "Verlaengerung" sind es nicht: Dass eine Erprobung um drei Monate verlaengert
# oder ein Impressum geaendert wurde, ist Verwaltungsvorgang, keine Neuigkeit.
# Sie werden gelesen und gezaehlt, aber nicht gezeigt.
RUBRIKEN = [
    ("aufnahme", r"vorläufig zur Erprobung in das Verzeichnis aufgenommen wurden", True),
    ("dauerhaft", r"dauerhaft in das Verzeichnis aufgenommen wurden", True),
    ("aenderung", r"wesentliche Veränderungen an dem Verzeichnis angezeigt wurden", False),
    ("verlaengert", r"vorläufige Aufnahme zur Erprobung in das Verzeichnis verlängert wurde", False),
    ("streichung", r"aus dem Verzeichnis gestrichen wurden", True),
]
ZEIGEN = {a for a, _, z in RUBRIKEN if z}

# Anker jeder Tabellenzeile: DiGA-ID, dann das Datum.
ZEILE = re.compile(r"(\d{2,5})\s+(\d{2}\.\d{2}\.\d{4})")
# Woran der Herstellername endet. Die Liste ist gewachsen, nicht geraten:
# METEDA s.r.l. hat am 22.10.2026 zwei Zeilen unsicher gemacht.
RECHTSFORM = re.compile(
    r".*?(?:GmbH|AG|SE|UG|mbH|e\.\s?V\.|Ltd\.?|B\.\s?V\.|GbR|KG|Inc\.?"
    r"|s\.r\.l\.|S\.p\.A\.|LLC|ApS|A/S|Oy|AB|SAS|SARL)"
    r"(?:\s*\([^)]{0,40}\))?")


def _hol(url: str, art: str = "application/json") -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": art})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return r.read()


def _text(medium_id: int) -> str:
    roh = _hol(MEDIUM.format(medium_id), "application/pdf")
    seiten = pypdf.PdfReader(io.BytesIO(roh)).pages
    return "\n".join((s.extract_text() or "") for s in seiten)


def _auslesen(text: str, warnungen: list[str], stand: str) -> list[dict]:
    flach = " ".join(text.split())
    marken = sorted((m.end(), art)
                    for art, muster, _ in RUBRIKEN
                    for m in re.finditer(muster, flach))
    eintraege: list[dict] = []
    for i, (start, art) in enumerate(marken):
        ende = marken[i + 1][0] if i + 1 < len(marken) else len(flach)
        teil = flach[start:ende]
        teil = teil.replace("Bezeichnung der digitalen Gesundheitsanwendung", "")
        teil = re.sub(r"DiGA-ID\s*Datum der (Aufnahme|Änderung im Verzeichnis|Streichung)",
                      "", teil)
        teil = teil.replace("Hersteller", "", 1)
        treffer = list(ZEILE.finditer(teil))
        # `pos` wandert mit: Der Name einer Zeile beginnt dort, wo der
        # Hersteller der VORIGEN endet - nicht hinter deren ID.
        pos = 0
        for k, m in enumerate(treffer):
            name = " ".join(teil[pos:m.start()].strip(" :,").split())
            nach = teil[m.end():(treffer[k + 1].start()
                                 if k + 1 < len(treffer) else len(teil))]
            rf = RECHTSFORM.match(nach)
            hersteller = " ".join((rf.group(0) if rf else nach[:60]).split())
            pos = m.end() + (rf.end() if rf else 0)
            if not rf:
                warnungen.append(
                    f"DiGA {stand}: Hersteller von '{name[:30]}' ohne erkennbare "
                    "Rechtsform - Name moeglicherweise abgeschnitten")
            eintraege.append({"art": art, "name": name, "diga_id": m.group(1),
                              "datum": m.group(2), "hersteller": hersteller})
    return eintraege


def holen(fenster_tage: int, warnungen: list[str]) -> tuple[list[dict], dict]:
    """Die Eintraege der letzten Bekanntmachungen innerhalb des Fensters.

    Gelesen werden so viele Bekanntmachungen, wie das Fenster beruehren kann -
    bei 180 Tagen also die letzten drei Quartale. Ein Eintrag kann aelter sein
    als seine Bekanntmachung: Die vom 01.10. fuehrt Aufnahmen vom 10.08. an.
    """
    heute = dt.date.today()
    seit = heute - dt.timedelta(days=fenster_tage)
    liste = json.loads(_hol(LISTE).decode("utf-8", "replace"))["data"]
    liste.sort(key=lambda x: x["attributes"]["datum"], reverse=True)
    anzahl = max(2, fenster_tage // 90 + 1)

    roh: list[dict] = []
    gelesen = 0
    for x in liste[:anzahl]:
        stand = x["attributes"]["datum"]
        medien = (x.get("relationships", {}).get("media", {}).get("data") or [])
        if not medien:
            warnungen.append(f"DiGA {stand}: keine Mediendatei verknuepft")
            continue
        try:
            teil = _auslesen(_text(medien[0]["id"]), warnungen, stand)
        except Exception as fehler:            # noqa: BLE001
            warnungen.append(f"DiGA {stand}: nicht lesbar - {str(fehler)[:70]}")
            continue
        gelesen += 1
        if not teil:
            # Lautlos leer ist der gefaehrliche Fall: Eine Bekanntmachung ohne
            # Eintraege ist denkbar, ein geaendertes Format sieht genauso aus.
            warnungen.append(f"DiGA {stand}: keine Eintraege gefunden - "
                             "Aufbau der Bekanntmachung geprueft?")
        roh += teil

    eintraege = []
    gesehen = set()
    for e in roh:
        if e["art"] not in ZEIGEN:
            continue
        try:
            datum = dt.datetime.strptime(e["datum"], "%d.%m.%Y").date()
        except ValueError:
            warnungen.append(f"DiGA: Datum '{e['datum']}' nicht lesbar ({e['name'][:30]})")
            continue
        if datum < seit:
            continue
        # Dieselbe DiGA kann in zwei Bekanntmachungen stehen (erst aufgenommen,
        # dann verlaengert). Entdoppelt wird ueber ID, Art und Datum.
        schluessel = (e["diga_id"], e["art"], e["datum"])
        if schluessel in gesehen:
            continue
        gesehen.add(schluessel)
        e["iso"] = datum.isoformat()
        eintraege.append(e)

    zahlen = {"bekanntmachungen_gelesen": gelesen,
              "diga_roh": len(roh), "diga_gezeigt": len(eintraege)}
    return eintraege, zahlen
