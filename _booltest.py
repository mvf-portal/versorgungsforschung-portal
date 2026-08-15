#!/usr/bin/env python3
"""Prueft je Datenbank, ob AND/OR/NOT ausgewertet werden.

Verfahren: dieselbe Suche dreimal - ohne Operator, mit OR, mit AND.
Wertet eine Datenbank OR aus, muss die Trefferzahl deutlich STEIGEN
(Vereinigungsmenge statt Schnittmenge). Behandelt sie OR als Wort,
bleibt sie gleich oder sinkt.

Wo eine Schnittstelle existiert, wird exakt gezaehlt. Sonst wird versucht,
die Trefferzahl aus der HTML-Seite zu lesen. Was sich nicht auslesen laesst,
bleibt ausdruecklich "ungeprueft" - lieber keine Aussage als eine geratene.
"""
import json, re, sys, time, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

A = "diabetes telemedicine"     # beide Woerter
O = "diabetes OR telemedicine"  # Vereinigung, wenn ausgewertet
N = "diabetes AND telemedicine" # Schnittmenge, wenn ausgewertet

KOPF = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "de,en;q=0.8"}


def laden(url: str, timeout: int = 40) -> str:
    r = urllib.request.Request(url, headers=KOPF)
    with urllib.request.urlopen(r, timeout=timeout) as f:
        return f.read().decode("utf-8", "replace")


def jzahl(url: str, pfad) -> int | None:
    try:
        return pfad(json.loads(laden(url)))
    except Exception:
        return None


# --- Schnittstellen: exakte Zahlen ----------------------------------------
def api_pubmed(q):
    return jzahl("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed"
                 f"&term={urllib.parse.quote(q)}&rettype=count&retmode=json",
                 lambda j: int(j["esearchresult"]["count"]))

def api_pmc(q):
    return jzahl("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc"
                 f"&term={urllib.parse.quote(q)}&rettype=count&retmode=json",
                 lambda j: int(j["esearchresult"]["count"]))

def api_epmc(q):
    return jzahl("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
                 f"query={urllib.parse.quote(q)}&format=json&pageSize=1",
                 lambda j: j["hitCount"])

def api_openalex(q):
    return jzahl(f"https://api.openalex.org/works?search={urllib.parse.quote(q)}"
                 "&per-page=1&mailto=stegmaier@m-vf.de", lambda j: j["meta"]["count"])

def api_zenodo(q):
    return jzahl(f"https://zenodo.org/api/records?q={urllib.parse.quote(q)}&size=1",
                 lambda j: j["hits"]["total"])

def api_ctgov(q):
    return jzahl("https://clinicaltrials.gov/api/v2/studies?"
                 f"query.term={urllib.parse.quote(q)}&countTotal=true&pageSize=1",
                 lambda j: j["totalCount"])

def api_osf(q):
    return jzahl(f"https://api.osf.io/v2/search/?q={urllib.parse.quote(q)}&page[size]=1",
                 lambda j: j["links"]["meta"]["total"])


# --- HTML: Trefferzahl aus der Seite lesen --------------------------------
ZAHL = r"([\d][\d.,  ]*)"
MUSTER = [
    rf"{ZAHL}\s*(?:results?|Ergebnisse?|Treffer|records?|hits?|Publikationen|Dokumente)",
    rf"(?:von|of|aus)\s+{ZAHL}\s*(?:Treffern?|results?|Ergebnissen?)?",
    rf"\"(?:total|totalCount|hitCount|numFound|totalResults)\"\s*:\s*(\d+)",
    rf"{ZAHL}\s*(?:Suchergebnisse)",
]

def html_zahl(url: str):
    try:
        h = laden(url)
    except Exception as e:
        return None, f"nicht erreichbar ({type(e).__name__})"
    # Skripte und Stile raus - dort stehen oft irrefuehrende Zahlen
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S | re.I)
    for m in MUSTER:
        tr = re.search(m, h, re.I)
        if tr:
            roh = re.sub(r"[.,  ]", "", tr.group(1))
            if roh.isdigit():
                return int(roh), None
    return None, "keine Trefferzahl auslesbar"


API = {
    "PubMed / MEDLINE": api_pubmed,
    "PubMed Central (PMC)": api_pmc,
    "Europe PMC": api_epmc,
    "OpenAlex": api_openalex,
    "Zenodo": api_zenodo,
    "ClinicalTrials.gov": api_ctgov,
    "OSF": api_osf,
}


def main():
    ziele = json.load(open("_live-urls.json", encoding="utf-8"))
    ergebnis = []
    for i, z in enumerate(ziele, 1):
        name, tpl = z["n"], z["u"]
        werte, notiz = {}, None
        if name in API:
            quelle = "Schnittstelle"
            for etikett, q in (("plain", A), ("or", O), ("and", N)):
                werte[etikett] = API[name](q)
                time.sleep(0.34)
        else:
            quelle = "Ergebnisseite"
            for etikett, q in (("plain", A), ("or", O), ("and", N)):
                werte[etikett], notiz = html_zahl(tpl.replace("%s", urllib.parse.quote(q)))
                time.sleep(0.8)

        p, o, a = werte.get("plain"), werte.get("or"), werte.get("and")
        if p is None or o is None:
            urteil = "ungeprueft"
        elif o > p * 2:
            urteil = "JA"
        elif o <= p * 1.2:
            urteil = "nein"
        else:
            urteil = "unklar"
        ergebnis.append({"name": name, "quelle": quelle, "plain": p, "or": o, "and": a,
                         "urteil": urteil, "notiz": notiz})
        print(f"{i:>2}. {name:<34} {quelle:<14} "
              f"plain={str(p):<10} OR={str(o):<10} AND={str(a):<10} -> {urteil}"
              + (f"   ({notiz})" if notiz else ""))

    json.dump(ergebnis, open("_boolergebnis.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\nZusammenfassung:")
    for u in ("JA", "nein", "unklar", "ungeprueft"):
        n = [e["name"] for e in ergebnis if e["urteil"] == u]
        print(f"  {u:<11} {len(n):>2}  {', '.join(n) if n else '-'}")


if __name__ == "__main__":
    main()
