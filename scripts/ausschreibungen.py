#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ausschreibungsradar: offene Forschungsfoerderung fuer alle zwoelf Hubs.

Angeregt am 26.08.2026 von einem Nutzer der Hubs: Wer zu einem Thema forscht,
sucht nicht nur Studien, sondern auch Geld. Der Radar sammelt taeglich offene
Foerderbekanntmachungen und ordnet sie den zwoelf Themengebieten zu.

**Dieses Skript laeuft nur im Versorgungsforschungs-Hub.** Entscheidung des
Herausgebers vom 28.08.2026: Der Radar steht einmal zentral auf
`ausschreibungen.html` und ist dort nach Themengebieten gegliedert; die elf
Schwesterhubs zeigen in ihrer Kopfkarte nur die Zahl ihres Gebiets und
verweisen dorthin (`scripts/radar_hinweis.py`). Die Quellen werden damit
einmal statt zwoelfmal abgefragt, und es gibt einen Stand statt zwoelf.

Die Gebiete, ihre Auswahlregeln und die Suchbegriffe stehen in
`scripts/radar_themen.py` - das ist die einzige Pflegestelle dafuer.

Quellen (am 26.08.2026 gemessen):
  1. **foerderinfo.bund.de** - RSS des Bundes, elf Fachfeeds. Traegt den Radar:
     10 bis 12 offene Bekanntmachungen je Fachbereich, darunter der
     Innovationsausschuss des G-BA. Die Fristen stehen im Titel.
  2. **grants.gov** - offene JSON-Schnittstelle der USA (auch NIH), ohne
     Anmeldung. Ergiebig, aber unscharf: "health services research" liefert
     1.470 Treffer, viele davon blosse Vorankuendigungen ohne Frist. Deshalb
     nur `posted` (keine Forecasts) und danach die Modellpruefung.
  3. **DFG** - RSS "Informationen fuer die Wissenschaft". Der Feed nennt nur
     Titel und Adresse, keine Frist. Die steht im Fliesstext der verlinkten
     Seite und wird von dort geholt. Am 28.08.2026 gemessen: 20 Eintraege,
     davon zehn mit erkennbarer Frist. Der Rest sind Kongresslisten,
     Personalmeldungen und Berichte ueber bereits Bewilligtes - genau das,
     was der Radar nicht zeigen soll. Die Fristpflicht sortiert sie aus.

Was NICHT drin ist: Das EU-Portal (Funding & Tenders). Der Endpunkt antwortet,
aber das Abfrageformat der SEDIA-Schnittstelle war am 26.08.2026 noch nicht
geknackt (HTTP 500). Nachzutragen - die Stelle ist mit TODO markiert.

**Fristen sind der Unterschied zu den Studien.** Eine Studie bleibt gueltig,
eine Ausschreibung ist nach dem Stichtag nicht nur wertlos, sondern eine Falle
fuer den, der darauf hin plant. Abgelaufenes wird deshalb bei jedem Lauf
entfernt, nicht nur nicht mehr ergaenzt.

Aufruf (im Versorgungsforschungs-Hub):
    python scripts/ausschreibungen.py            # holen, pruefen, Block setzen
    python scripts/ausschreibungen.py --probe    # nur zeigen, nichts schreiben
    python scripts/ausschreibungen.py --roh      # Rohtreffer ohne Modell
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
from html import unescape

import anthropic

from radar_themen import FEEDS, SUCHE, THEMEN

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = "MVF-Knowledge-Hubs/1.0 (+https://knowledge-hubs.m-vf.de)"
RSS = "https://www.foerderinfo.bund.de/foerderinfo/de/services/rss/{}/rssnewsfeed.xml"
GRANTS = "https://api.grants.gov/v1/api/search2"
DFG_FEED = "https://www.dfg.de/service/rss/de/323556/feed.rss"

# Der DFG-Feed haelt 20 Eintraege vor. Fuer jeden davon wird die verlinkte
# Seite geholt - anders ist an die Frist nicht heranzukommen.
DFG_MAX = 20
# "Kongresse und Tagungen" ist die monatliche Veranstaltungsliste der DFG:
# immer derselbe Titel, nie eine Ausschreibung. Am 28.08.2026 stand sie
# zweimal im Feed. Sie hier zu uebergehen spart zwei Seitenabrufe je Lauf;
# alles andere wird geholt und nachgemessen, nicht nach Titel vermutet.
DFG_UEBERGEHEN = ("kongresse und tagungen",)

# Der Radar hat eine eigene Seite: Zwoelf Themengebiete passen nicht in die
# 236 px schmale Kopfkarte, in der die erste Fassung stand.
SEITE = "ausschreibungen.html"
ARCHIV = "ausschreibungen.json"
START = "// === RADAR-BLOCK-START (taeglich von GitHub Actions ersetzt) ==="
ENDE = "// === RADAR-BLOCK-ENDE ==="

# Die Rolle steht hier und nicht in thema.py: Das Skript arbeitet fuer alle
# zwoelf Gebiete, nicht fuer das des Hubs, in dem es liegt.
SYSTEM = (
    "Du bist Foerderreferent bei einer Fachzeitschrift fuer "
    "Versorgungsforschung. Du kennst die deutsche Foerderlandschaft und "
    "beurteilst nuechtern, ob eine Ausschreibung fuer eine bestimmte "
    "Leserschaft im Gesundheitswesen einschlaegig ist.")

# Haiku 4.5 hat diese Aufgabe am 28.08.2026 nicht bestanden: Der
# Innovationsausschuss stand in zehn von zwoelf Gebieten, auch nachdem der
# Auftrag ausdruecklich verlangte, allgemeine Ausschreibungen der
# Versorgungsforschung zu ueberlassen. Die Aufgabe ist eine Abwaegung, keine
# Zuordnung nach Stichwort - dafuer reicht das kleine Modell nicht.
MODELL = "claude-sonnet-5"
# An welchen Wochentagen gesucht wird (0 = Montag). Entscheidung des
# Herausgebers vom 28.08.2026: zweimal die Woche genuegt. Ausschreibungen
# aendern sich im Wochen-, nicht im Tagesrhythmus, und der Lauf kostet Geld.
#
# Das Veralten faengt die Seite selbst ab: Sie rechnet die Restlaufzeiten im
# Browser nach, eine abgelaufene Ausschreibung verschwindet also noch am
# Stichtag - auch wenn der naechste Lauf erst drei Tage spaeter kommt.
LAUFTAGE = (0, 3)
# Hoechstens so viele Ausschreibungen stehen je Themengebiet auf der Seite.
# Mehr liest niemand, und der Radar soll die Auswahl treffen, nicht sie dem
# Leser aufbuerden.
ANZEIGEN_MAX = 8
# Wie viele Rohtreffer dem Modell vorgelegt werden. Zentral hoeher als in der
# ersten Fassung (60): Der Pool muss zwoelf Gebiete bedienen, nicht eines.
# Gekappt wird nur grants.gov (siehe main): Die beiden deutschen Quellen sind
# vorgeprueft und kommen vollstaendig hinein.
POOL_MAX = 200


def hol(url: str, daten: bytes | None = None, kopf: dict | None = None) -> bytes:
    req = urllib.request.Request(url, data=daten,
                                 headers={"User-Agent": UA, **(kopf or {})})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def feld(eintrag: str, name: str) -> str:
    """Ein Element aus einem RSS-<item>, entschaerft und ohne CDATA."""
    m = re.search(rf"<{name}>(.*?)</{name}>", eintrag, re.S)
    return unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1))).strip() if m else ""


def frist_aus_titel(titel: str) -> dt.date | None:
    """Die Feeds haengen die Frist an den Titel: '... | 07.08.2026 - 23.09.2026'.

    Genommen wird das LETZTE Datum der Zeile - das ist der Stichtag. Steht nur
    eines da, ist es ebenfalls der Stichtag.
    """
    treffer = re.findall(r"(\d{2}\.\d{2}\.\d{4})", titel)
    if not treffer:
        return None
    try:
        return dt.datetime.strptime(treffer[-1], "%d.%m.%Y").date()
    except ValueError:
        return None


def titel_ohne_frist(titel: str) -> str:
    """Die Frist steht spaeter als eigenes Feld - im Titel waere sie doppelt."""
    return re.sub(r"\s*\|\s*\d{2}\.\d{2}\.\d{4}(\s*-\s*\d{2}\.\d{2}\.\d{4})?\s*$",
                  "", titel).strip()


def aus_bund(heute: dt.date, stoerungen: list[str]) -> list[dict]:
    """Offene Bekanntmachungen aus den Fachfeeds des Bundes."""
    gefunden: list[dict] = []
    for teil in FEEDS:
        try:
            d = hol(RSS.format(teil)).decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as fehler:
            stoerungen.append(f"Bund: Fachfeed '{teil}' nicht erreichbar "
                              f"({fehler}).")
            continue
        for eintrag in re.findall(r"<item>(.*?)</item>", d, re.S):
            titel = feld(eintrag, "title")
            frist = frist_aus_titel(titel)
            # Ohne erkennbare Frist keine Aufnahme: Der Radar verspricht,
            # dass man sich noch bewerben kann. Was er nicht weiss, verschweigt
            # er lieber, als es zu behaupten.
            if not frist or frist < heute:
                continue
            gefunden.append({
                "titel": titel_ohne_frist(titel),
                "frist": frist.isoformat(),
                "url": feld(eintrag, "link"),
                "quelle": "Bund (foerderinfo.bund.de)",
                "land": "DE",
                "beschreibung": feld(eintrag, "description")[:600],
            })
    return gefunden


def aus_grants_gov(heute: dt.date, stoerungen: list[str]) -> list[dict]:
    """Offene US-Ausschreibungen. Nur 'posted' - keine Vorankuendigungen.

    Am 26.08.2026 gemessen: 'health services research' liefert 1.470 Treffer,
    ein grosser Teil davon "Notice of Intent to Publish" oder "Forecast" - also
    Ankuendigungen einer kuenftigen Ausschreibung, auf die sich niemand
    bewerben kann. `oppStatuses: posted` haelt sie heraus.
    """
    gefunden: list[dict] = []
    gesehen: set[str] = set()
    for begriff in SUCHE:
        koerper = json.dumps({"keyword": begriff, "oppStatuses": "posted",
                              "rows": 25}).encode()
        try:
            d = json.loads(hol(GRANTS, koerper,
                               {"Content-Type": "application/json"}))
        except Exception as fehler:  # noqa: BLE001 - eine Quelle darf ausfallen
            stoerungen.append(f"grants.gov: Suche '{begriff}' fehlgeschlagen "
                              f"({fehler}).")
            continue
        for o in (d.get("data") or {}).get("oppHits", []):
            kennung = str(o.get("id") or o.get("number") or "")
            if not kennung or kennung in gesehen:
                continue
            frist = o.get("closeDate") or ""
            try:                      # grants.gov schreibt MM/TT/JJJJ
                stichtag = dt.datetime.strptime(frist, "%m/%d/%Y").date()
            except ValueError:
                continue              # ohne Frist nicht aufnehmen
            if stichtag < heute:
                continue
            gesehen.add(kennung)
            gefunden.append({
                "titel": (o.get("title") or "").strip(),
                "frist": stichtag.isoformat(),
                "url": f"https://www.grants.gov/search-results-detail/{kennung}",
                "quelle": f"grants.gov ({o.get('agencyCode', 'US')})",
                "land": "US",
                "beschreibung": "",
            })
    return gefunden


# TODO: EU Funding & Tenders Portal (SEDIA). Der Endpunkt
# api.tech.ec.europa.eu/search-api/prod/rest/search?apiKey=SEDIA antwortet,
# erwartet aber ein multipart-Formular mit einer Elasticsearch-artigen Query;
# am 26.08.2026 kam damit HTTP 500 zurueck. Erst nachtragen, wenn eine Abfrage
# nachweislich Treffer liefert - eine halb funktionierende Quelle ist
# schlimmer als keine, weil ihr Schweigen wie "nichts ausgeschrieben" aussieht.


# ------------------------------------------------- Fristen im Fliesstext
# foerderinfo haengt die Frist an den Titel, die DFG nicht. Dort steht sie im
# Text der verlinkten Seite, und zwar in vier Schreibweisen, die am 28.08.2026
# alle vorkamen: "27 November 2026", "30. September 2026", "November 27, 2026"
# und "30.09.2026". Einmal sogar ohne Leerzeichen ("2 December2026") - deshalb
# steht zwischen Zahl und Monatsnamen \s* und nicht \s+.
MONATE = {"januar": 1, "februar": 2, "maerz": 3, "märz": 3, "april": 4,
          "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9,
          "oktober": 10, "november": 11, "dezember": 12,
          "january": 1, "february": 2, "march": 3, "may": 5, "june": 6,
          "july": 7, "october": 10, "december": 12}
_NAMEN = "|".join(sorted(MONATE, key=len, reverse=True))
DATUM = re.compile(
    rf"(?ix)(?P<t1>\d{{1,2}})\.\s*(?P<m1>{_NAMEN})\s*(?P<j1>\d{{4}})"
    rf"|(?P<t2>\d{{1,2}})\s*(?P<m2>{_NAMEN})\s*(?P<j2>\d{{4}})"
    rf"|(?P<m3>{_NAMEN})\s*(?P<t3>\d{{1,2}}),?\s*(?P<j3>\d{{4}})"
    rf"|(?P<t4>\d{{1,2}})\.(?P<m4>\d{{1,2}})\.(?P<j4>\d{{4}})")

# Ein Datum allein ist keine Frist - auf denselben Seiten stehen Gruendungs-
# jahre, Foerderzeitraeume und Workshoptermine. Genommen wird nur, wovor eines
# dieser Woerter steht.
FRISTWORT = re.compile(
    r"(?i)(frist|stichtag|einzureichen|eingereicht|einreichung|antragstellung|"
    r"antr(a|ä)ge|bewerbung|spätestens|bis zum|bis einschließlich|"
    r"deadline|submit|submission|received by|no later than|apply|proposals?|"
    r"applications?)")
# So weit wird vor einem Datum nach dem Fristwort gesucht. 160 Zeichen sind
# etwa ein Satz - der Fall "Proposals must be written in English and submitted
# to the DFG by 27 November 2026" braucht 60 davon. Bewusst kein Satzschnitt:
# "bis zum 30. September 2026" enthaelt selbst einen Punkt und zerfiele dabei.
FRIST_UMFELD = 160


def seitentext(seite: str) -> str:
    """Der Fliesstext einer DFG-Seite, ohne Menue und Fusszeile.

    Die DFG setzt zwei Vorlagen ein: "IfW..." fuer Informationen fuer die
    Wissenschaft, "PM..." fuer Pressemitteilungen. Gemeinsam ist beiden die
    Endung "Flietext" in der Absatzklasse; daran haengt sich die Auslese fest -
    ohne sie stand die halbe Navigation im Text. Findet sich keiner dieser
    Absaetze, wird die ganze Seite genommen: Ein Fristwort steht im Menue
    nicht, die Auslese unten laeuft dann eben ins Leere.
    """
    seite = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", seite)
    absaetze = re.findall(r'(?is)<p class="[^"]*Flietext[^"]*"[^>]*>(.*?)</p>',
                          seite)
    roh = " ".join(absaetze) if absaetze else seite
    return re.sub(r"\s+", " ",
                  unescape(re.sub(r"(?s)<[^>]+>", " ", roh))).strip()


def frist_aus_text(text: str, heute: dt.date) -> dt.date | None:
    """Der FRUEHESTE kuenftige Termin, vor dem ein Fristwort steht.

    Warum der frueheste und nicht der letzte: Auf einer Ausschreibungsseite
    stehen meist zwei Termine - die Anmeldung im elan-Portal und die
    Einreichung selbst. Am 28.08.2026 beim SPP 1294 gemessen: Registrierung
    bis 13.11., Antrag bis 27.11.2026. Wer die spaetere Zahl zeigt, laesst den
    Eintrag noch stehen, wenn der erste notwendige Schritt schon vorbei ist.
    Der fruehere Termin nimmt ihn hoechstens zu frueh von der Seite - und das
    ist die Richtung, in die dieser Radar irren darf.
    """
    kandidaten: list[dt.date] = []
    for m in DATUM.finditer(text):
        g = m.groupdict()
        try:
            if g["t1"]:
                d = dt.date(int(g["j1"]), MONATE[g["m1"].lower()], int(g["t1"]))
            elif g["t2"]:
                d = dt.date(int(g["j2"]), MONATE[g["m2"].lower()], int(g["t2"]))
            elif g["t3"]:
                d = dt.date(int(g["j3"]), MONATE[g["m3"].lower()], int(g["t3"]))
            else:
                d = dt.date(int(g["j4"]), int(g["m4"]), int(g["t4"]))
        except (ValueError, KeyError):
            continue      # 31.02. und aehnliche Verschreiber
        if d < heute:
            continue
        if FRISTWORT.search(text[max(0, m.start() - FRIST_UMFELD):m.start()]):
            kandidaten.append(d)
    return min(kandidaten) if kandidaten else None


def aus_dfg(heute: dt.date, stoerungen: list[str]) -> list[dict]:
    """Offene DFG-Ausschreibungen. Die Frist kommt von der verlinkten Seite.

    Der Feed "Informationen fuer die Wissenschaft" ist die einzige Stelle, an
    der die DFG maschinenlesbar bekanntgibt - er enthaelt aber alles: Aufrufe,
    Kongresslisten, Preise, Personalmeldungen, Berichte ueber schon Bewilligtes.
    Aussortiert wird nicht nach Titel (das waere Raterei), sondern ueber die
    Frist: Was keine hat, ist nichts, worauf man sich noch bewerben kann.

    Anders als die beiden anderen Quellen kostet das je Eintrag einen eigenen
    Seitenabruf. Deshalb DFG_MAX - der Feed haelt ohnehin nur 20 Stueck vor.
    """
    gefunden: list[dict] = []
    try:
        d = hol(DFG_FEED).decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as fehler:
        stoerungen.append(f"DFG-Feed nicht erreichbar ({fehler}).")
        return gefunden
    stumm = 0
    for eintrag in re.findall(r"<item>(.*?)</item>", d, re.S)[:DFG_MAX]:
        titel, url = feld(eintrag, "title"), feld(eintrag, "link")
        if not url or titel.casefold() in DFG_UEBERGEHEN:
            continue
        try:
            text = seitentext(hol(url).decode("utf-8", "replace"))
        except (urllib.error.URLError, TimeoutError) as fehler:
            print(f"  DFG-Seite nicht erreichbar ({fehler}): {url}")
            stumm += 1
            continue
        frist = frist_aus_text(text, heute)
        if not frist:
            continue      # dieselbe Regel wie beim Bund: ohne Frist nicht rein
        gefunden.append({
            "titel": titel,
            "frist": frist.isoformat(),
            "url": url,
            "quelle": "DFG",
            "land": "DE",
            "beschreibung": text[:600],
        })
    # Einzelne unerreichbare Seiten sind Alltag; faellt die Haelfte aus, ist
    # etwas kaputt, und dann gehoert das in den Bericht statt in die Konsole.
    if stumm > DFG_MAX // 2:
        stoerungen.append(f"DFG: {stumm} von {DFG_MAX} Seiten nicht erreichbar.")
    return gefunden


def entdoppeln(kandidaten: list[dict]) -> list[dict]:
    """Dieselbe Bekanntmachung steht oft in mehreren Fachfeeds.

    Am 26.08.2026 im Versorgungsforschungs-Hub: "Transferinitiative F.A.S.T."
    kam aus dem Gesundheits- und aus dem Sozialwissenschaftsfeed. Ohne diese
    Zeile stuende sie zweimal auf der Seite - und das Modell haette sie zweimal
    zu bewerten, was einen der acht Plaetze kostet.

    Erkannt wird ueber Titel und Frist, nicht ueber die Adresse: Dieselbe
    Bekanntmachung kann je Feed eine andere Verweisadresse tragen.
    """
    gesehen: set[tuple[str, str]] = set()
    behalten: list[dict] = []
    for k in kandidaten:
        merkmal = (k["titel"].casefold(), k["frist"])
        if merkmal in gesehen:
            continue
        gesehen.add(merkmal)
        behalten.append(k)
    return behalten


def liste_bauen(kandidaten: list[dict]) -> str:
    """Der Kandidatenpool als nummerierte Liste - fuer alle zwoelf Aufrufe gleich.

    Genau deshalb steht er in einer eigenen Funktion: Die Liste ist der lange,
    unveraenderliche Teil der Anfrage und wird zwischengespeichert (siehe
    `waehlen`). Jedes Zeichen, das sich zwischen den Aufrufen aendert, macht
    diese Ersparnis zunichte.
    """
    # Der Titel allein reicht nicht: 'Priority Programme "Combinatorial
    # Synergies" (SPP 2458)' sagt ueber das Fach nichts. Deshalb steht der
    # Anfang der Beschreibung darunter, soweit die Quelle einen liefert.
    return "\n".join(
        f"{i}. [{k['land']}] {k['titel']} (Frist {k['frist']})"
        + (f"\n   {k['beschreibung'][:220]}" if k.get("beschreibung") else "")
        for i, k in enumerate(kandidaten, 1))


def waehlen(kandidaten: list[dict], liste: str, thema: dict,
            client: "anthropic.Anthropic") -> list[dict]:
    """Das Modell behaelt, was in dieses eine Themengebiet passt.

    Die Quellen sind fachlich breit - im Gesundheitsfeed des Bundes stehen
    auch Bioökonomie und agrarnahe Start-ups. Ohne diese Pruefung stuende im
    Pflege-Hub eine Ausschreibung zur industriellen Biotechnologie.

    Gefoerdert werden muss **Forschung** (Entscheidung des Herausgebers vom
    28.08.2026). Der erste Lauf brachte sonst "Older Adults Home Modification
    Grant Program" und "Disaster Assistance for State Units on Aging" ins
    Gebiet Gesundes Altern - Foerderung ja, Forschungsfoerderung nein. Beides
    haette in einem Hub gestanden, der Studien sammelt.

    Aufgerufen wird zwoelfmal ueber denselben Pool, einmal je Gebiet. Das ist
    Absicht: Eine Ausschreibung darf in zwei Gebiete gehoeren (Adipositas ist
    auch eine chronische Erkrankung), und faellt ein Aufruf aus, fehlt ein
    Gebiet statt aller zwoelf. Damit das bezahlbar bleibt, steht die lange
    Kandidatenliste vor der kurzen Regel und traegt `cache_control`: Ab dem
    zweiten Aufruf liest das Modell sie aus dem Zwischenspeicher.
    """
    if not kandidaten:
        return []
    # Der Titel allein reicht nicht: 'Priority Programme \"Combinatorial
    # Synergies\" (SPP 2458)' sagt ueber das Fach nichts. Deshalb steht der
    # Anfang der Beschreibung darunter, soweit die Quelle einen liefert.
    # Am 28.08.2026 im ersten Lauf gemessen: Ohne den Absatz unten stand
    # "Klinische Studien mit hoher Relevanz fuer die Patientenversorgung" in
    # sechs von zwoelf Gebieten und der Innovationsausschuss in zehn. Das
    # Modell fuellt die acht Plaetze auf, statt zu schweigen - und eine
    # allgemeine Versorgungsausschreibung ist mit jedem Thema vereinbar. Die
    # Regel ist dieselbe, die der Herausgeber fuer breit angelegte
    # Praeventionsprogramme entschieden hat, nur allgemein gefasst.
    eigenes = "" if thema["slug"] == "versorgungsforschung" else (
        "Entscheidend ist, ob das Thema dieses Gebiets in der Ausschreibung "
        "selbst vorkommt - nicht, ob es dazu passen könnte. Eine "
        "allgemein gehaltene Ausschreibung zur Gesundheitsversorgung oder "
        "-forschung, die für jedes der zwölf Gebiete gleich gut "
        "passen würde, gehört NICHT hierher: Sie steht im Gebiet "
        "Versorgungsforschung. Nimm sie nur auf, wenn die Bekanntmachung "
        "dieses Thema ausdrücklich nennt oder erkennbar meint.\n\n")
    auftrag = (
        f"Oben stehen offene Förderausschreibungen. Wähle die aus, die für den "
        f"Knowledge-Hub \"{thema['name']}\" einschlägig sind.\n\n"
        f"{thema['regel']}\n\n{eigenes}"
        f"Nicht gemeint sind Kongress- und Tagungsankündigungen, Preise, "
        f"Wettbewerbe, Personalmeldungen und Berichte über bereits bewilligte "
        f"Projekte: Der Radar zeigt nur Ausschreibungen, auf die sich jemand "
        f"bewerben kann.\n\n"
        f"**Gefördert werden muss Forschung** — Projekte, Studien, Verbünde, "
        f"Forschungsinfrastruktur, Nachwuchs- und Strukturförderung in der "
        f"Wissenschaft. Nicht gemeint sind Programme, die Leistungen, Betrieb "
        f"oder Ausstattung fördern: Versorgungs- und Beratungsangebote, "
        f"Nothilfe und Katastrophenhilfe, Beschaffung, Bau- und "
        f"Modernisierungszuschüsse, Fortbildungsangebote ohne "
        f"Forschungsanteil.\n\n"
        f"Gib die passenden Ausschreibungen zurück, höchstens "
        f"{ANZEIGEN_MAX}, die einschlägigste zuerst. **Lieber keine als eine "
        f"unpassende**: Ein Radar, der Beliebiges zeigt, ist schlechter als "
        f"einer, der schweigt. Passt nichts, gib eine leere Liste zurück.\n\n"
        f"Zu jeder Nummer gehört ein `beleg`: die Stelle aus Titel oder "
        f"Beschreibung, an der dieses Thema vorkommt — wenige Wörter, wörtlich "
        f"abgeschrieben. Findest du keine solche Stelle und müsstest den Bezug "
        f"selbst herstellen, dann gehört die Ausschreibung nicht hierher und "
        f"du lässt sie weg.")
    antwort = client.messages.create(
        # Grosszuegig bemessen: Sonnet denkt vor der Antwort, und am
        # 28.08.2026 endeten erst fuenf, dann noch zwei von zwoelf Aufrufen
        # beim Nachdenken, bevor das JSON kam - die Antwort enthielt dann
        # ueberhaupt keinen Textblock. Getroffen hat es die Gebiete mit den
        # meisten Treffern, weil dort acht Belege zu schreiben waren.
        model=MODELL, max_tokens=16000, system=SYSTEM,
        # "medium" statt der Voreinstellung "high": Die Abwaegung braucht
        # Nachdenken, aber nicht das aeusserste - und der Denkschritt ist der
        # teuerste Teil des Laufs. Entscheidung des Herausgebers vom
        # 28.08.2026, zusammen mit dem Zwei-Tage-Takt unten.
        # Das Schema erzwingt zu jeder Nummer einen Beleg. Ohne ihn nahm
        # das Modell alles, was zum Thema passen KOENNTE - siehe waehlen().
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": {
                "type": "object", "additionalProperties": False,
                "required": ["treffer"],
                "properties": {"treffer": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["nummer", "beleg"],
                    "properties": {"nummer": {"type": "integer"},
                                   "beleg": {"type": "string"}}}}}}}},
        messages=[{"role": "user", "content": [
            # Die Liste zuerst und mit Haltepunkt, die Regel danach: Der
            # Zwischenspeicher greift auf das gemeinsame Praefix.
            {"type": "text", "text": liste,
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": auftrag},
        ]}])
    # Alle Textbloecke, nicht der erste: Vor dem JSON koennen Denkbloecke
    # stehen, und `next(...)` warf dann ein StopIteration ohne jede Meldung -
    # im Bericht stand "Auswahl fehlgeschlagen ()".
    text = "".join(b.text for b in antwort.content if b.type == "text")
    if not text.strip():
        raise RuntimeError(
            f"keine Textantwort (stop_reason: {antwort.stop_reason}). "
            f"Meist zu wenig max_tokens fuer Nachdenken plus Antwort.")
    gewaehlt: list[dict] = []
    for treffer in json.loads(text).get("treffer", []):
        n = treffer.get("nummer")
        if not isinstance(n, int) or not 1 <= n <= len(kandidaten):
            continue
        # Kopie, kein Verweis: Derselbe Kandidat kann in zwei Gebieten stehen,
        # und der Beleg gilt jeweils nur fuer eines davon.
        eintrag = dict(kandidaten[n - 1])
        eintrag["beleg"] = (treffer.get("beleg") or "").strip()
        gewaehlt.append(eintrag)
    return gewaehlt[:ANZEIGEN_MAX]


def warnungen_bilden(vorher: dict, jetzt: dict[str, int],
                     stoerungen: list[str]) -> list[str]:
    """Was an diesem Lauf auffaellig ist - fuer den Sammelbericht.

    Der Radar schweigt von sich aus, wenn er nichts findet; bei eng gefassten
    Themen ist das der Normalfall und steht so auf der Seite. Faellt aber eine
    Quelle aus - geaenderte Adresse, neues Seitenlayout, abgeschaltete
    Schnittstelle -, sieht ihr Schweigen genauso aus. Deshalb wird gegen den
    letzten Lauf verglichen: Eine Quelle, die gestern zwoelf Bekanntmachungen
    lieferte und heute keine, ist eine Meldung wert.

    Beim allerersten Lauf gibt es nichts zu vergleichen - dann bleibt es still,
    statt eine Warnung zu erfinden.
    """
    warnungen = list(stoerungen)
    vorlauf = (vorher or {}).get("quellen") or {}
    for name, zahl in jetzt.items():
        frueher = vorlauf.get(name, 0)
        if zahl == 0 and frueher > 0:
            warnungen.append(
                f"{name}: heute 0 offene Ausschreibungen, im letzten Lauf "
                f"{frueher}. Quelle nachsehen - ein Adress- oder Layoutwechsel "
                f"sieht von hier aus wie 'nichts ausgeschrieben'.")
    return warnungen


def js(s: str) -> str:
    """Text als JS-Literal. Einfache Anfuehrungszeichen und Zeilenumbrueche
    wuerden das inline-JS zerlegen - dieselbe Falle wie beim STUDIES-Block."""
    return json.dumps(s or "", ensure_ascii=False)


def block(gebiete: list[dict], stand: str) -> str:
    """Der Marker-Block fuer ausschreibungen.html - zwoelf Gebiete am Stueck.

    Auch leere Gebiete stehen drin: Die Seite soll alle zwoelf Rubriken zeigen,
    damit ein Anker nie ins Leere fuehrt und der Leser sieht, dass zu seinem
    Gebiet gesucht wurde. Die Null-Ansage steht dann in der Rubrik.
    """
    zeilen = [START,
              f'const RADAR_STAND = "{stand}";',
              "const RADAR = ["]
    for g in gebiete:
        zeilen.append("  {slug:%s, name:%s, domain:%s, eintraege:[" %
                      (js(g["slug"]), js(g["name"]), js(g["domain"])))
        for e in g["ausschreibungen"]:
            zeilen.append(
                "    {titel:%s, frist:%s, url:%s, quelle:%s, land:%s}," %
                (js(e["titel"]), js(e["frist"]), js(e["url"]),
                 js(e["quelle"]), js(e["land"])))
        zeilen.append("  ]},")
    zeilen += ["];", ENDE]
    return "\n".join(zeilen)


def main() -> int:
    p = argparse.ArgumentParser(description="Ausschreibungsradar")
    p.add_argument("--probe", action="store_true", help="nur zeigen")
    p.add_argument("--roh", action="store_true", help="Rohtreffer ohne Modell")
    p.add_argument("--jetzt", action="store_true",
                   help="auch an einem Tag laufen, der nicht in LAUFTAGE steht")
    a = p.parse_args()

    heute = dt.date.today()
    # --probe und --roh schreiben nichts und duerfen deshalb jeden Tag laufen:
    # Wer nachsehen will, was der Radar faende, soll nicht bis Montag warten.
    if heute.weekday() not in LAUFTAGE and not (a.jetzt or a.probe or a.roh):
        tage = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag",
                "Samstag", "Sonntag")
        print(f"Heute ist {tage[heute.weekday()]} - der Radar sucht "
              + " und ".join(tage[i] for i in LAUFTAGE)
              + ". Nichts geaendert. (--jetzt erzwingt den Lauf.)")
        return 0
    stoerungen: list[str] = []
    # Je Quelle gezaehlt, nicht nur in Summe: Nur so faellt auf, wenn eine von
    # dreien verstummt, waehrend die anderen weiterliefern.
    quellen: dict[str, int] = {}
    geholt: dict[str, list[dict]] = {}
    for name, holen in (("Bund", aus_bund),
                        ("grants.gov", aus_grants_gov),
                        ("DFG", aus_dfg)):
        teil = holen(heute, stoerungen)
        quellen[name] = len(teil)
        geholt[name] = teil
    # Gekappt wird nur grants.gov, und zwar zuletzt. Am 28.08.2026 gemessen:
    # Bund 73, DFG 12, grants.gov 297 - eine gemeinsame Kappung nach Frist
    # haette die spaeteren deutschen Bekanntmachungen aus dem Pool gedraengt,
    # weil die US-Schnittstelle unscharf sucht und zu jedem Stichtag etwas
    # liefert (Bergbau, Botschaftsprogramme, Sportdiplomatie). Die beiden
    # deutschen Quellen sind vorgeprueft und kommen deshalb vollstaendig in
    # den Pool; grants.gov fuellt den Rest auf.
    deutsch = entdoppeln(geholt["Bund"] + geholt["DFG"])
    rest = max(0, POOL_MAX - len(deutsch))
    usa = sorted(geholt["grants.gov"], key=lambda k: k["frist"])[:rest]
    kandidaten = entdoppeln(deutsch + usa)
    kandidaten.sort(key=lambda k: k["frist"])
    print(f"{len(kandidaten)} offene Ausschreibungen in den Quellen "
          + "(" + ", ".join(f"{n}: {z}" for n, z in quellen.items()) + ").")

    vorher: dict = {}
    archiv = pathlib.Path(ARCHIV)
    if archiv.exists():
        try:
            vorher = json.loads(archiv.read_text(encoding="utf-8"))
        except ValueError:
            pass          # eine kaputte Vorgaengerdatei ist kein Grund abzubrechen
    warnungen = warnungen_bilden(vorher, quellen, stoerungen)
    for w in warnungen:
        print(f"  ! {w}")

    if a.roh:
        for k in kandidaten:
            print(f"  [{k['frist']}] [{k['land']}] {k['titel'][:88]}")
        return 0

    import os
    schluessel = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not schluessel:
        raise SystemExit("ANTHROPIC_API_KEY ist nicht gesetzt.")
    client = anthropic.Anthropic(api_key=schluessel)
    liste = liste_bauen(kandidaten)
    gebiete: list[dict] = []
    for thema in THEMEN:
        try:
            gewaehlt = waehlen(kandidaten, liste, thema, client)
        except Exception as fehler:  # noqa: BLE001 - ein Gebiet darf ausfallen
            # Ohne diesen Fang stuenden nach einem einzelnen Fehlschlag elf
            # fertige Gebiete nicht auf der Seite. Der Ausfall gehoert in den
            # Bericht, nicht in einen Abbruch.
            # !r statt !s: Eine Ausnahme ohne Text stuende sonst als
            # "fehlgeschlagen ()" da und waere nicht zu deuten.
            warnungen.append(f"{thema['name']}: Auswahl fehlgeschlagen "
                             f"({fehler!r}). Gebiet bleibt heute leer.")
            print(f"  ! {warnungen[-1]}")
            gewaehlt = []
        gebiete.append({"slug": thema["slug"], "name": thema["name"],
                        "domain": thema["domain"], "anzahl": len(gewaehlt),
                        "ausschreibungen": gewaehlt})
        print(f"  {len(gewaehlt):2d} × {thema['name']}")
        # Bei der Probe zaehlt nicht die Zahl, sondern was drinsteht: Ob eine
        # Regel zu weit oder zu eng ist, sieht man nur an den Titeln.
        if a.probe:
            for g in gewaehlt:
                tage = (dt.date.fromisoformat(g["frist"]) - heute).days
                print(f"        [noch {tage:4d} T] [{g['land']}] "
                      f"{g['titel'][:76]}")
                if g.get("beleg"):
                    print(f"                     ↳ {g['beleg'][:88]}")
    print(f"{sum(g['anzahl'] for g in gebiete)} Zuordnungen über "
          f"{len(THEMEN)} Themengebiete.")

    if a.probe:
        print(f"\n[Probe] {SEITE} unverändert.")
        return 0

    stand = heute.strftime("%d.%m.%Y")
    # `quellen` und `warnungen` stehen mit in der Datei: Sie sind der Stoff,
    # aus dem der Sammelbericht (knowledge-hubs/scripts/versand_bericht.py)
    # seine Radar-Zeile baut, und `quellen` ist zugleich der Vergleichswert
    # fuer den naechsten Lauf.
    archiv.write_text(
        json.dumps({"stand": stand, "quellen": quellen,
                    "warnungen": warnungen, "themen": gebiete},
                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    seite = pathlib.Path(SEITE)
    text = seite.read_text(encoding="utf-8")
    muster = re.compile(re.escape(START) + r".*?" + re.escape(ENDE), re.DOTALL)
    if not muster.search(text):
        raise SystemExit(f"Marker-Block fehlt in {SEITE} - nichts geaendert.")
    seite.write_text(muster.sub(lambda _: block(gebiete, stand), text),
                     encoding="utf-8")
    print(f"{SEITE} aktualisiert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
