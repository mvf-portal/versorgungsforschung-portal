# -*- coding: utf-8 -*-
"""Was kostete der Modellweg fuer die FDA-Stufe wirklich?

Gezaehlt mit `messages.count_tokens` an einem echten Auftrag, nicht geschaetzt.
Der Auftrag ist der, den die FDA-Stufe braeuchte: Zuordnung zu den Hubs UND
der deutsche Satz in einem Aufruf - zwei Aufrufe waeren die doppelten
Eingabe-Token fuer dieselbe Information.
"""
import os
import sys

import anthropic

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

GEBIETE = """onkologie (Onkologie), kardio (Kardiologie), diabetes (Diabetes),
adipositas (Adipositas), mental (Psychische Gesundheit), impfen (Impfen &
Prävention), longevity (Gesundes Altern & Longevity), ncd (Nicht übertragbare
Krankheiten), ki-gesundheit (Digitalisierung, KI & Gesundheit)"""

SYSTEM = f"""Du ordnest neue Arzneimittelzulassungen der US-Arzneimittelbehörde
FDA den Themengebieten der MVF-Knowledge-Hubs zu und schreibst je einen
deutschen Satz dazu.

Die Gebiete: {GEBIETE}

Regeln für die Zuordnung:
- Ein Mittel darf in mehrere Gebiete gehören, etwa ein GLP-1-Analogon in
  Diabetes und Adipositas.
- Passt keines, gib eine leere Liste zurück. Lieber schweigen als danebenliegen.
- Entscheide nach dem Anwendungsgebiet, nicht nach der Stoffklasse.
- Diagnostika, Kontrastmittel und Radiopharmaka gehören in kein Gebiet, auch
  wenn sie bei einer Krankheit eingesetzt werden.

Regeln für den Satz:
- Höchstens 35 Wörter, ein einziger Satz, Fachsprache des deutschen
  Gesundheitswesens, keine Werbesprache.
- Er muss sagen, dass die FDA zugelassen hat, nicht die EU.
- Keine Wertung: kein "erstmals", kein "vielversprechend".
- Nenne den Wirkstoff. Übersetze die Krankheitsbezeichnung genau:
  "adenocarcinoma" ist ein Adenokarzinom, kein Adenom.
- Steht keine Indikation zur Verfügung, schreibe keinen Satz, sondern gib das
  Feld leer zurück. Nichts erfinden.

Antworte als JSON: {{"hubs": [...], "satz": "..."}}"""

# Zwei echte Faelle vom 22.10.2026: einer mit Beipackzettel, einer ohne.
MIT_TEXT = """Handelsname: RASONQUE
Wirkstoff: daraxonrasib
Antragsart: NDA, TYPE 1 (neuer Wirkstoff)
Zulassungsdatum: 2026-09-26
Indikation (Beipackzettel der FDA): RASONQUE is indicated for the treatment of
adult patients with metastatic pancreatic adenocarcinoma who have received at
least one prior systemic therapy. This indication is approved under accelerated
approval based on overall response rate and duration of response."""

OHNE_TEXT = """Handelsname: HOVILPR
Wirkstoff: pritelivir
Antragsart: NDA, TYPE 1 (neuer Wirkstoff)
Zulassungsdatum: 2026-10-09
Indikation (Beipackzettel der FDA): liegt noch nicht vor"""

print("Eingabe-Token je Aufruf (gemessen, nicht geschaetzt):\n")
zahlen = {}
for name, text in (("mit Beipackzettel", MIT_TEXT), ("ohne Beipackzettel", OHNE_TEXT)):
    n = client.messages.count_tokens(
        model="claude-haiku-4-5",
        system=SYSTEM,
        messages=[{"role": "user", "content": text}],
    ).input_tokens
    zahlen[name] = n
    print(f"  {name:<20} {n:>5} Token")

# Ausgabe: ein Satz plus die Hub-Liste als JSON. Gemessen an den deutschen
# Saetzen, die der EMA-Teil heute schreibt: im Mittel 160 Zeichen, laengster
# 310 - das sind rund 60 bzw. 110 Token. Mit JSON-Rahmen grosszuegig 120.
AUSGABE = 120
print(f"  Ausgabe (grosszuegig)  {AUSGABE:>5} Token\n")

# Menge: 42 Erstzulassungen ohne Generika in 90 Tagen = rund 170 im Jahr.
# Jedes Mittel wird EINMAL gefragt, der Satz danach aufbewahrt - wie beim
# EMA-Teil. Zusaetzlich ein Nachschlag fuer die, deren Beipackzettel spaeter
# kommt und die deshalb ein zweites Mal gefragt werden: rund drei Viertel.
JE_JAHR = 170
NACHSCHLAG = int(JE_JAHR * 0.75)
aufrufe = JE_JAHR + NACHSCHLAG
eingabe = (zahlen["mit Beipackzettel"] + zahlen["ohne Beipackzettel"]) / 2 * aufrufe
ausgabe = AUSGABE * aufrufe
print(f"Aufrufe im Jahr: {JE_JAHR} + {NACHSCHLAG} Nachschlag = {aufrufe}")
print(f"  Eingabe: {eingabe/1e6:.3f} Mio. Token · Ausgabe: {ausgabe/1e6:.3f} Mio. Token\n")

PREISE = [
    ("claude-haiku-5-5", 0.10, 0.50),
    ("claude-haiku-4-5 (heute im Einsatz)", 1.00, 5.00),
    ("claude-sonnet-5-5", 2.00, 10.00),
    ("claude-opus-5-5", 4.00, 20.00),
]
print("Kosten im Jahr:")
for name, ein, aus in PREISE:
    kosten = eingabe / 1e6 * ein + ausgabe / 1e6 * aus
    print(f"  {name:<38} {kosten:>6.2f} USD")
print("\nZum Vergleich: der EMA-Teil schreibt rund 170 Saetze im Jahr und")
print("laeuft heute auf claude-haiku-4-5.")
