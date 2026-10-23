# -*- coding: utf-8 -*-
"""Sind die 25 Texte wirklich Indikationen?

Der Ausdruck in fda_beipackzettel.py schneidet zwischen zwei Ueberschriften aus.
Das kann auch eine Inhaltsangabe treffen statt des Abschnitts selbst. Drei
Proben im Volltext, und eine mechanische Probe an allen 25:
Ein echter Indikationsabschnitt nennt den Handelsnamen ODER den Wirkstoff und
enthaelt eine Formel wie "is indicated for".
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
FORMEL = re.compile(r"\bis indicated\b|\bindicated (?:for|in|as)\b|\bfor the treatment\b"
                    r"|\bfor the diagnosis\b|\bindicated to\b", re.I)


def hole(url, roh=False):
    req = urllib.request.Request(url, headers={"User-Agent": "MVF-Knowledge-Hubs/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = r.read()
    return d if roh else json.loads(d)


def text_von(name, wirkstoff):
    for wert in (name, wirkstoff.split(";")[0].strip()):
        if not wert:
            continue
        q = urllib.parse.quote(wert)
        a = hole(f"https://dailymed.nlm.nih.gov/dailymed/services/v2/"
                 f"spls.json?drug_name={q}&pagesize=5")
        for r in a.get("data", []):
            setid = r.get("setid")
            if not setid:
                continue
            xml = hole("https://dailymed.nlm.nih.gov/dailymed/services/v2/"
                       f"spls/{setid}.xml", roh=True).decode("utf-8", "replace")
            nur = " ".join(re.sub(r"<[^>]+>", " ", xml).split())
            m = ABSCHNITT.search(nur)
            if m and len(m.group(1).strip()) > 60:
                return m.group(1).strip(), r.get("published_date", ""), setid
        break
    return "", "", ""


eintraege = json.load(open(pathlib.Path(__file__).resolve().parent / "fda_messung.json", encoding="utf-8"))

print("=== Drei Proben im Volltext ===\n")
for name in ("JUVMO", "RASONQUE", "AMBELVIST"):
    e = next(x for x in eintraege if x["name"] == name)
    text, veroeff, setid = text_von(e["name"], e["wirkstoff"])
    print(f"--- {name} ({e['wirkstoff']}), SPL vom {veroeff} ---")
    print(text[:700])
    print()
    time.sleep(0.3)

print("\n=== Mechanische Probe an allen ===\n")
echt = unklar = leer = 0
for e in eintraege:
    text, veroeff, setid = text_von(e["name"], e["wirkstoff"])
    if not text:
        leer += 1
        urteil = "kein Text"
    else:
        nennt = (e["name"].lower() in text.lower()
                 or any(w.strip().split()[0].lower() in text.lower()
                        for w in e["wirkstoff"].split(";") if w.strip()))
        formel = bool(FORMEL.search(text))
        if nennt and formel:
            echt += 1
            urteil = "Indikation"
        else:
            unklar += 1
            urteil = ("UNKLAR: " + ("Formel fehlt" if nennt else "Name fehlt"))
    print(f"  {e['name'][:24]:<24} {urteil:<22} {len(text):>5} Zeichen")
    time.sleep(0.3)

print(f"\n  echte Indikation : {echt}")
print(f"  unklar           : {unklar}")
print(f"  kein Text        : {leer}")
