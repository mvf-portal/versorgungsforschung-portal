# -*- coding: utf-8 -*-
"""Taugt das Hub-Glossar als Zuordnungsregel - und als Uebersetzungshilfe?

Jeder Hub traegt in index.html einen eigenen GLOSSAR-Block: deutsche
Fachbegriffe mit ihrer englischen Entsprechung, von Hand gepflegt, damit die
Suche international findet. Das ist zweierlei auf einmal:

  1. eine **Begriffsliste je Hub** - steht ein englischer Begriff aus dem
     Onkologie-Glossar im Indikationstext, ist das ein Hinweis auf diesen Hub;
  2. ein **englisch-deutsches Woerterbuch** fuer genau das Fachgebiet, in dem
     der deutsche Satz geschrieben werden soll.

Gemessen wird, was davon traegt. Ein Glossar, das zu neun Zehnteln aus
Methodenbegriffen besteht ("Kohortenstudie", "Metaanalyse"), ordnet nichts zu.
"""
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# **Dieses Skript sieht absichtlich AUS dem Repo heraus**: Es vergleicht die
# Glossare aller fuenfzehn Portale, und die liegen als Schwesterordner
# daneben. Abgeleitet aus dem eigenen Ort, nicht fest eingetragen - sonst
# laeuft es nur auf einem Rechner.
WURZEL = pathlib.Path(__file__).resolve().parents[3]

BLOCK = re.compile(r"// === GLOSSAR-BLOCK-START.*?\nconst GLOSSAR = (\[.*?\]);", re.S)

glossare = {}
for ordner in sorted(WURZEL.glob("*-portal")):
    datei = ordner / "index.html"
    if not datei.exists():
        continue
    m = BLOCK.search(datei.read_text(encoding="utf-8"))
    if not m:
        print(f"  ! {ordner.name}: kein GLOSSAR-Block")
        continue
    try:
        glossare[ordner.name.replace("-portal", "")] = json.loads(m.group(1))
    except ValueError as f:
        print(f"  ! {ordner.name}: Block nicht lesbar ({f})")

print(f"Glossare gefunden: {len(glossare)} Hubs\n")
alle = {}
for slug, g in sorted(glossare.items()):
    print(f"  {slug:<24} {len(g):>3} Begriffe")
    for p in g:
        alle.setdefault(p["en"].lower(), set()).add(slug)
print(f"\n  zusammen {sum(len(g) for g in glossare.values())} Begriffe, "
      f"{len(alle)} verschiedene englische Ausdruecke")

# Wie viele davon sind EINDEUTIG, also nur in einem Hub? Nur die taugen als
# Zuordnungsregel - "prevention" steht in fast jedem Glossar und sagt nichts.
eindeutig = {en: next(iter(s)) for en, s in alle.items() if len(s) == 1}
print(f"  davon nur in einem Hub: {len(eindeutig)}")

# Und wie viele sind Krankheitsbegriffe statt Methoden- oder Systembegriffe?
# Mechanisch nicht entscheidbar, aber abschaetzbar: Ein Krankheitsbegriff
# endet oder beginnt typischerweise anders als "...studie" oder "Versorgungs...".
METHODE = re.compile(
    r"stud(y|ies)|trial|review|analysis|meta-|research|survey|data|method"
    r"|cohort|cross-sectional|modelling|policy|economics|expenditure"
    r"|cost|quality|literacy|participation|workforce|personnel|system"
    r"|reimbursement|assessment|interoperab|protection|safety|guideline", re.I)
krankheit = {en: slug for en, slug in eindeutig.items() if not METHODE.search(en)}
print(f"  davon keine Methoden-/Systembegriffe: {len(krankheit)}")

print("\nBeispiele der brauchbaren Begriffe je Hub:")
je_hub = {}
for en, slug in sorted(krankheit.items()):
    je_hub.setdefault(slug, []).append(en)
for slug, begriffe in sorted(je_hub.items(), key=lambda x: -len(x[1])):
    print(f"  {slug:<24} {len(begriffe):>3}  {', '.join(begriffe[:6])}")

# ---------------------------------------------------- Gegenprobe an den Texten
print("\n\n=== Was die Glossarbegriffe an den 25 FDA-Texten finden ===\n")
try:
    texte = json.load(open(pathlib.Path(__file__).resolve().parent / "fda_texte.json", encoding="utf-8"))
except FileNotFoundError:
    print("  fda_texte.json fehlt - erst fda_texte_sichern.py laufen lassen.")
    sys.exit(0)

MUSTER = {en: re.compile(r"\b" + re.escape(en) + r"\b", re.I)
          for en in krankheit}
for name, text in texte.items():
    treffer = {krankheit[en] for en, m in MUSTER.items() if m.search(text)}
    gefunden = sorted({en for en, m in MUSTER.items() if m.search(text)})
    if treffer:
        print(f"  {name[:12]:<13} -> {','.join(sorted(treffer)):<22} "
              f"({', '.join(gefunden[:3])})")
