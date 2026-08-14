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
import html
import json
import os
import re
import sys
import time
from zoneinfo import ZoneInfo

import anthropic
import requests

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TERM = os.environ.get("SEARCH_TERM", '"health services research"')
MODEL = os.environ.get("MODEL", "claude-haiku-4-5")  # Standard: guenstig; via MODEL-env aenderbar
INDEX = "index.html"

# NCBI bittet bei automatisierten Zugriffen um Tool-Kennung und Kontaktadresse.
NCBI_TOOL = "versorgungsforschung-portal"
NCBI_EMAIL = os.environ.get("NCBI_EMAIL", "stegmaier@m-vf.de")

START = "// === STUDIES-BLOCK-START (wird woechentlich vom Cloud-Agenten ersetzt) ==="
END = "// === STUDIES-BLOCK-ENDE ==="
ARCHIVE = "studien-archiv.json"   # Vollstaendige Historie; die Seite laedt sie fuer den Ordner
                                  # "Aeltere Suchergebnisse" nach und blendet die aktuellen aus.

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

WICHTIG - Fachterminologie: Etablierte englische Fachbegriffe NICHT eindeutschen.
Sie sind auch im deutschen Fachdeutsch stehende Begriffe; eine woertliche Uebersetzung
wirkt unprofessionell und erschwert das Wiederfinden. Beispiele fuer Begriffe, die
englisch bleiben: Door-to-Balloon-Zeit, Patient-Reported Outcomes, Shared Decision
Making, Case Management, Disease Management, Public Health, Screening, Follow-up,
Outcome, Adherence, Value-Based Care, Hazard Ratio, Odds Ratio, Confounder, Baseline,
Setting, Cluster. Gaengige Abkuerzungen ebenfalls unveraendert lassen: STEMI, COPD,
ICU, PROM, DRG, ACSC.
Faustregel: Wuerde eine deutsche Fachzeitschrift wie Monitor Versorgungsforschung den
Begriff englisch stehen lassen, dann tue es auch. Im Zweifel englisch belassen und bei
Bedarf eine kurze deutsche Erlaeuterung in Klammern ergaenzen.
Umgekehrt gilt: Wo es ein gebraeuchliches deutsches Fachwort gibt (Verweildauer,
Hausarztkontakt, Nutzenbewertung, Fallzahl), dieses verwenden.

Gib ausschliesslich das geforderte JSON zurueck.

=== ABSTRACTS ===
{abstracts}
"""


def _get(path: str, params: dict, timeout: int) -> requests.Response:
    """GET mit drei Versuchen - PubMed ist gelegentlich kurz nicht erreichbar."""
    params = {**params, "tool": NCBI_TOOL, "email": NCBI_EMAIL}
    last: Exception | None = None
    for attempt in range(3):
        try:
            r = requests.get(f"{EUTILS}/{path}", params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            last = exc
            if attempt < 2:
                wait = 5 * (attempt + 1)
                print(f"PubMed-Abruf fehlgeschlagen ({exc}); neuer Versuch in {wait}s ...")
                time.sleep(wait)
    raise RuntimeError(f"PubMed nicht erreichbar: {last}")


def fetch_pubmed() -> str:
    r = _get(
        "esearch.fcgi",
        {"db": "pubmed", "term": TERM, "sort": "date", "retmax": "25", "retmode": "json"},
        timeout=30,
    )
    ids = r.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        raise RuntimeError("esearch lieferte keine PMIDs")
    print(f"{len(ids)} PMIDs gefunden.")
    r2 = _get(
        "efetch.fcgi",
        {"db": "pubmed", "id": ",".join(ids), "rettype": "abstract", "retmode": "text"},
        timeout=60,
    )
    return r2.text


MONATE_NUM = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
               "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}


def _datum_teile(roh: str) -> tuple[int, str]:
    """PubMed-Datum -> (Genauigkeit, deutsche Schreibweise).

    Genauigkeit 3 = Tag, 2 = Monat, 1 = Jahr, 0 = unbrauchbar.
    """
    if not roh:
        return (0, "")
    m = re.match(r"^(\d{4})(?:\s+([A-Za-z]{3})[a-z]*)?(?:\s+(\d{1,2}))?", roh.strip())
    if not m:
        return (0, "")
    jahr, mon, tag = m.group(1), m.group(2), m.group(3)
    if mon and mon[:3] in MONATE_NUM:
        nr = MONATE_NUM[mon[:3]]
        if tag:
            return (3, f"{int(tag):02d}.{nr:02d}.{jahr}")
        return (2, f"{MONTHS[nr]} {jahr}")
    return (1, jahr)


def fetch_meta(pmids: list[str]) -> dict[str, dict]:
    """Autor und Publikationsdatum ueber esummary holen.

    Bewusst nicht vom Sprachmodell erraten lassen: Das sind harte Fakten.
    sortpubdate wird ignoriert - PubMed setzt dort bei reinen Monatsangaben
    den 1. ein, was einen Tag vortaeuschen wuerde. Genommen wird die
    genaueste ECHTE Angabe aus pubdate und epubdate.
    """
    r = _get("esummary.fcgi",
             {"db": "pubmed", "retmode": "json", "id": ",".join(pmids)},
             timeout=60)
    roh = r.json().get("result", {})
    aus: dict[str, dict] = {}
    for pmid in pmids:
        e = roh.get(pmid)
        if not e or "error" in e:
            continue
        namen = e.get("authors") or []
        erster = e.get("sortfirstauthor") or (namen[0]["name"] if namen else "")
        autor = f"{erster} et al." if erster and len(namen) > 1 else erster
        datum = max(_datum_teile(e.get("pubdate", "")),
                    _datum_teile(e.get("epubdate", "")),
                    key=lambda x: x[0])[1]
        aus[pmid] = {"author": autor, "pubdate": datum}
    print(f"Metadaten zu {len(aus)}/{len(pmids)} PMIDs geladen.")
    return aus


def pick_studies(abstracts: str) -> list[dict]:
    client = anthropic.Anthropic()
    # Nur strukturierte Ausgabe erzwingen (kein effort/thinking), damit es auch
    # mit guenstigen Modellen wie claude-haiku-4-5 laeuft (die effort/thinking
    # nicht unterstuetzen).
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
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

    def js(v: str) -> str:
        """Sicheres JS-String-Literal MIT HTML-Escaping.

        Zwei Ebenen muessen stimmen: index.html setzt die Werte per innerHTML ein,
        deshalb wird zuerst HTML-maskiert (& < >), damit ein Zeichen wie < im
        generierten Text das Markup nicht zerlegt. json.dumps erzeugt danach ein
        gueltiges JS-Literal (Anfuehrungszeichen, Backslashes, Zeilenumbrueche).
        """
        return json.dumps(html.escape(v, quote=False), ensure_ascii=False)

    items = []
    for s in studies:
        items.append(
            "  {\n"
            f"    journal:{js(s['journal'])}, year:{js(s['year'])}, pmid:{js(s['pmid'])},\n"
            f"    author:{js(s.get('author', ''))}, pubdate:{js(s.get('pubdate', ''))},\n"
            f"    title:{js(s['title'])},\n"
            f"    sum:{js(s['sum'])},\n"
            f"    result:{js(s['result'])}\n"
            "  }"
        )
    # SNAP_DATE wird per textContent gesetzt, nicht per innerHTML -> kein HTML-Escaping.
    return (
        f"{START}\n"
        f"const SNAP_DATE = {json.dumps(snap, ensure_ascii=False)};\n"
        "const STUDIES = [\n"
        + ",\n".join(items)
        + ",\n];\n"
        f"{END}"
    )


def update_archive(studies: list[dict]) -> int:
    """Nimmt die aktuellen Studien ins Archiv auf. Rueckgabe: Gesamtzahl im Archiv.

    Dedupliziert ueber die PMID; das zuerst gesehene Aufnahmedatum bleibt erhalten,
    damit eine Studie nicht bei jedem Lauf nach vorne rutscht.
    """
    try:
        with open(ARCHIVE, encoding="utf-8") as f:
            entries = json.load(f)
    except FileNotFoundError:
        entries = []

    known = {e["pmid"] for e in entries}
    heute = dt.datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d")
    neu = 0
    for s in studies:
        if s["pmid"] in known:
            continue
        entries.append({
            "pmid": s["pmid"], "journal": s["journal"], "year": s["year"],
            "author": s.get("author", ""), "pubdate": s.get("pubdate", ""),
            "title": s["title"], "sum": s["sum"], "result": s["result"],
            "aufgenommen": heute,
        })
        known.add(s["pmid"])
        neu += 1

    entries.sort(key=lambda e: (e["aufgenommen"], e["pmid"]), reverse=True)
    with open(ARCHIVE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    print(f"Archiv: {neu} neu, {len(entries)} gesamt.")
    return len(entries)


def main() -> int:
    abstracts = fetch_pubmed()
    studies = pick_studies(abstracts)
    meta = fetch_meta([s["pmid"] for s in studies])
    for s in studies:
        s.update(meta.get(s["pmid"], {"author": "", "pubdate": ""}))
    block = build_block(studies)
    update_archive(studies)

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
