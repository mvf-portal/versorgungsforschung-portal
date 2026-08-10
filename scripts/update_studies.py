#!/usr/bin/env python3
"""Aktualisiert den Studien-Block in index.html mit den neuesten PubMed-Treffern.

Ablauf:
  1. PubMed E-utilities: neueste Treffer zu "health services research" (nach Datum).
  2. Claude-API: 5-7 relevante Studien mit konkreten Ergebnissen auswaehlen und
     auf Deutsch zusammenfassen (strukturierte JSON-Ausgabe).
  3. Nur den Marker-Block (SNAP_DATE + STUDIES) in index.html ersetzen.

Bricht mit Exit-Code != 0 ab, wenn etwas fehlschlaegt - dann bleibt index.html
unveraendert und der Workflow schlaegt sichtbar fehl (kein kaputter Commit).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

import anthropic
import requests

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TERM = '"health services research"'
MODEL = os.environ.get("MODEL", "claude-opus-5")  # z. B. "claude-haiku-4-5" fuer geringere Kosten
INDEX = "index.html"

START = "// === STUDIES-BLOCK-START (wird woechentlich vom Cloud-Agenten ersetzt) ==="
END = "// === STUDIES-BLOCK-ENDE ==="

MONTHS = {1: "Jan.", 2: "Feb.", 3: "März", 4: "Apr.", 5: "Mai", 6: "Juni",
          7: "Juli", 8: "Aug.", 9: "Sept.", 10: "Okt.", 11: "Nov.", 12: "Dez."}

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["studies"],
    "properties": {
        "studies": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["journal", "year", "pmid", "title", "sum", "result"],
                "properties": {
                    "journal": {"type": "string"},
                    "year": {"type": "string"},
                    "pmid": {"type": "string"},
                    "title": {"type": "string"},
                    "sum": {"type": "string"},
                    "result": {"type": "string"},
                },
            },
        }
    },
}

SYSTEM = (
    "Du bist Fachredakteur fuer Versorgungsforschung / Health Services Research. "
    "Aus einer Liste von PubMed-Abstracts waehlst du die relevantesten aktuellen "
    "Studien aus und fasst sie praezise auf Deutsch zusammen."
)

USER_TEMPLATE = """Unten stehen aktuelle PubMed-Abstracts (nach Datum sortiert).

Waehle GENAU 6 Studien aus, die (a) fuer Versorgungsforschung / Health Services Research
relevant sind UND (b) im Abstract KONKRETE quantitative Ergebnisse nennen
(Prozentwerte, Odds/Hazard Ratios, p-Werte, Fallzahlen). Ueberspringe Studien ohne
Abstract oder ohne konkrete Ergebnisse. Achte auf thematische Vielfalt; die neuesten zuerst.

Fuer jede Studie:
- journal: Journalname (Originalsprache)
- year: Erscheinungsjahr, z. B. "2026"
- pmid: die PubMed-ID
- title: praegnanter deutscher Titel
- sum: 1 Satz auf Deutsch, was die Studie untersucht hat
- result: Deutsch, die konkreten Zahlen/Befunde + ein kurzer Einordnungssatz.
  Deutsches Zahlenformat mit Komma (z. B. 0,63).

Gib ausschliesslich das geforderte JSON zurueck.

=== ABSTRACTS ===
{abstracts}
"""


def fetch_pubmed() -> str:
    r = requests.get(
        f"{EUTILS}/esearch.fcgi",
        params={"db": "pubmed", "term": TERM, "sort": "date", "retmax": "25", "retmode": "json"},
        timeout=30,
    )
    r.raise_for_status()
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        raise RuntimeError("esearch lieferte keine PMIDs")
    r2 = requests.get(
        f"{EUTILS}/efetch.fcgi",
        params={"db": "pubmed", "id": ",".join(ids), "rettype": "abstract", "retmode": "text"},
        timeout=60,
    )
    r2.raise_for_status()
    return r2.text


def pick_studies(abstracts: str) -> list[dict]:
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        thinking={"type": "disabled"},
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM,
        messages=[{"role": "user", "content": USER_TEMPLATE.format(abstracts=abstracts)}],
    )
    text = next(b.text for b in resp.content if b.type == "text")
    studies = json.loads(text)["studies"]
    if not 5 <= len(studies) <= 7:
        raise RuntimeError(f"Unerwartete Studienanzahl: {len(studies)}")
    return studies


def build_block(studies: list[dict]) -> str:
    now = dt.datetime.now(ZoneInfo("Europe/Berlin"))
    snap = f"{now.day}. {MONTHS[now.month]} {now.year}, {now:%H:%M} Uhr"

    def js(v: str) -> str:  # sichere JS-String-Literale (JSON-Strings sind gueltiges JS)
        return json.dumps(v, ensure_ascii=False)

    items = []
    for s in studies:
        items.append(
            "  {\n"
            f"    journal:{js(s['journal'])}, year:{js(s['year'])}, pmid:{js(s['pmid'])},\n"
            f"    title:{js(s['title'])},\n"
            f"    sum:{js(s['sum'])},\n"
            f"    result:{js(s['result'])}\n"
            "  }"
        )
    return (
        f"{START}\n"
        f"const SNAP_DATE = {js(snap)};\n"
        "const STUDIES = [\n"
        + ",\n".join(items)
        + ",\n];\n"
        f"{END}"
    )


def main() -> int:
    abstracts = fetch_pubmed()
    studies = pick_studies(abstracts)
    block = build_block(studies)

    with open(INDEX, encoding="utf-8") as f:
        html = f.read()

    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(html):
        raise RuntimeError("Marker-Block nicht in index.html gefunden")
    new_html = pattern.sub(lambda _m: block, html, count=1)

    if new_html == html:
        print("Inhalt unveraendert.")
        return 0

    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"index.html aktualisiert: {len(studies)} Studien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
