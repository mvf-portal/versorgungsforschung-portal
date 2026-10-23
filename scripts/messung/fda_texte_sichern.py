# -*- coding: utf-8 -*-
"""Die 25 Indikationstexte einmal holen und ablegen.

Jede weitere Messung laeuft dann gegen die Datei, nicht gegen DailyMed - das
ist schneller und, wichtiger, vergleichbar: Zwei Messungen an zwei Abrufen
waeren zwei verschiedene Grundgesamtheiten, sobald ein Label nachkommt.
"""
import json
import re
import pathlib
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ABSCHNITT = re.compile(
    r"INDICATIONS AND USAGE(.{40,4000}?)(?:DOSAGE AND ADMINISTRATION|CONTRAINDICATIONS)",
    re.S | re.I)


def hole(url, roh=False):
    req = urllib.request.Request(url, headers={"User-Agent": "MVF-Knowledge-Hubs/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = r.read()
    return d if roh else json.loads(d)


def text_von(name, wirkstoff):
    for wert in (name, wirkstoff.split(";")[0].strip()):
        if not wert:
            continue
        a = hole("https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"
                 f"?drug_name={urllib.parse.quote(wert)}&pagesize=5")
        for r in a.get("data", []):
            if not r.get("setid"):
                continue
            xml = hole("https://dailymed.nlm.nih.gov/dailymed/services/v2/"
                       f"spls/{r['setid']}.xml", roh=True).decode("utf-8", "replace")
            nur = " ".join(re.sub(r"<[^>]+>", " ", xml).split())
            m = ABSCHNITT.search(nur)
            if m and len(m.group(1).strip()) > 60:
                return m.group(1).strip()
        break
    return ""


eintraege = json.load(open(pathlib.Path(__file__).resolve().parent / "fda_messung.json", encoding="utf-8"))
texte = {}
for e in eintraege:
    t = text_von(e["name"], e["wirkstoff"])
    if t:
        texte[e["name"]] = t
        print(f"  {e['name'][:14]:<15} {len(t):>5} Zeichen")
    time.sleep(0.3)

json.dump(texte, open(pathlib.Path(__file__).resolve().parent / "fda_texte.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"\n{len(texte)} Texte in fda_texte.json")
