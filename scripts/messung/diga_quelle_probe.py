# -*- coding: utf-8 -*-
"""Probe: Laesst sich die DiGA-Bekanntmachung verlaesslich auslesen?"""
import io
import re
import sys
import urllib.request
import ssl
import json
import certifi
import pypdf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CTX = ssl.create_default_context(cafile=certifi.where())
H = {"User-Agent": "Mozilla/5.0"}

RUBRIKEN = [
    ("aufnahme", r"vorläufig zur Erprobung in das Verzeichnis aufgenommen wurden"),
    ("dauerhaft", r"dauerhaft in das Verzeichnis aufgenommen wurden"),
    ("aenderung", r"wesentliche Veränderungen an dem Verzeichnis angezeigt wurden"),
    ("verlaengert", r"vorläufige Aufnahme zur Erprobung in das Verzeichnis verlängert wurde"),
    ("streichung", r"aus dem Verzeichnis gestrichen wurden"),
]

# Anker jeder Tabellenzeile: fuenfstellige DiGA-ID, dann das Datum. Der Name
# steht davor, der Hersteller dahinter - beide koennen ueber mehrere Zeilen
# laufen, deshalb wird der Text vorher flachgezogen.
ZEILE = re.compile(r"(\d{2,5})\s+(\d{2}\.\d{2}\.\d{4})")


def hol(u, acc="application/json"):
    r = urllib.request.Request(u, headers={**H, "Accept": acc})
    with urllib.request.urlopen(r, timeout=45, context=CTX) as f:
        return f.read()


def text_von(mid: int) -> str:
    roh = hol(f"https://diga.bfarm.de/api/diga-vz/media/{mid}", "application/pdf")
    seiten = pypdf.PdfReader(io.BytesIO(roh)).pages
    t = "\n".join((p.extract_text() or "") for p in seiten)
    # Seitenzahlen wie "- 2 -" wegnehmen, sonst landen sie im Herstellernamen
    return re.sub(r"\n\s*-\s*\d+\s*-\s*\n", "\n", t)


def auslesen(t: str) -> list[dict]:
    # **Zuerst flachziehen.** Die Zwischenueberschriften brechen im PDF ueber
    # Zeilen um ("... in das Verzeichnis aufgenommen \nwurden:"), und ein
    # Muster gegen den Rohtext findet dann nur die letzte Rubrik - gemessen am
    # 22.10.2026: eine von vier statt vier von vier.
    t = " ".join(t.split())
    marken = []
    for art, muster in RUBRIKEN:
        for m in re.finditer(muster, t):
            marken.append((m.end(), art))
    marken.sort()
    eintraege = []
    for i, (start, art) in enumerate(marken):
        ende = marken[i + 1][0] if i + 1 < len(marken) else len(t)
        teil = t[start:ende]
        # Kopfzeile der Tabelle wegwerfen
        teil = teil.replace("Bezeichnung der digitalen Gesundheitsanwendung", "")
        teil = re.sub(r"DiGA-ID\s*Datum der (Aufnahme|Änderung im Verzeichnis|Streichung)", "", teil)
        teil = teil.replace("Hersteller", "", 1)
        treffer = list(ZEILE.finditer(teil))
        # `pos` wandert mit: Der Name einer Zeile beginnt dort, wo der
        # Hersteller der VORIGEN endet - nicht hinter deren ID. Ohne das stand
        # am 22.10.2026 in jedem zweiten Namen der vorige Hersteller mit drin
        # ("Endo Health GmbH Frieda Menova").
        pos = 0
        for k, m in enumerate(treffer):
            name = teil[pos:m.start()].strip(" :,")
            nach = teil[m.end():(treffer[k + 1].start() if k + 1 < len(treffer) else len(teil))]
            # Der Hersteller endet an seiner Rechtsform. Die traegt fast jeder;
            # fehlt sie, wird bis zum naechsten Eintrag genommen und die Zeile
            # als unsicher gemeldet, statt stillschweigend zu raten.
            m2 = re.search(r".*?(?:GmbH|AG|SE|UG|mbH|e\.\s?V\.|Ltd\.?|B\.\s?V\.|GbR|KG|Inc\.?|s\.r\.l\.|S\.p\.A\.|LLC|ApS|A/S|Oy|AB|SAS|SARL)"
                           r"(?:\s*\([^)]{0,40}\))?", nach)
            hersteller = (m2.group(0) if m2 else nach[:60]).strip()
            pos = m.end() + (m2.end() if m2 else 0)
            eintraege.append({"art": art, "name": " ".join(name.split()),
                              "diga_id": m.group(1), "datum": m.group(2),
                              "hersteller": " ".join(hersteller.split()),
                              "sicher": bool(m2)})
    return eintraege


d = json.loads(hol("https://diga.bfarm.de/api/diga-vz/proclamations").decode("utf-8", "replace"))
neueste = max(d["data"], key=lambda x: x["attributes"]["datum"])
mid = neueste["relationships"]["media"]["data"][0]["id"]
print(f"Bekanntmachung vom {neueste['attributes']['datum']} (Datei {mid})\n")
eintraege = auslesen(text_von(mid))
for art, _ in RUBRIKEN:
    meine = [e for e in eintraege if e["art"] == art]
    if not meine:
        continue
    print(f"== {art} ({len(meine)}) ==")
    for e in meine:
        print(f"   {e['datum']}  {e['diga_id']}  {e['name'][:42]:<42} {e['hersteller'][:34]}")
print(f"\nSumme: {len(eintraege)}")
