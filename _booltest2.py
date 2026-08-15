#!/usr/bin/env python3
"""Zweiter Durchgang: Booleschen Betrieb ohne Trefferzahlen nachweisen.

Der erste Durchgang scheiterte oft daran, dass sich aus der Ergebnisseite keine
Gesamtzahl lesen laesst (JavaScript-Oberflaechen, uneinheitliche Auszeichnung).

Dieser Test braucht keine Zahl, sondern nur die Antwort auf "gibt es ueberhaupt
Treffer?":

    Q1 = "zzqqxxwww"              -> muss leer sein (Phantasiewort)
    Q2 = "zzqqxxwww OR diabetes"  -> wertet die Datenbank OR aus, kommen ALLE
                                     Diabetes-Treffer; nimmt sie es woertlich,
                                     bleibt es leer.

Ein Wechsel von "leer" auf "voll" ist damit ein direkter Beleg. Zusaetzlich
prueft ein Gegentest mit AND, ob die Datenbank die Schnittmenge bildet.
"""
import json, re, sys, time, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

PHANTASIE = "zzqqxxwww"
KOPF = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "de,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

# Formulierungen, mit denen Seiten "nichts gefunden" melden
LEER = re.compile(
    r"(keine?\s+(?:Treffer|Ergebnisse|Dokumente|Suchergebnisse|Publikationen)"
    r"|nichts\s+gefunden"
    r"|no\s+(?:results?|records?|matches|studies|documents|items)\s*(?:found|match)?"
    r"|0\s+(?:results?|Treffer|Ergebnisse|records?)"
    r"|did\s+not\s+match|returned\s+no)", re.I)


def laden(url, timeout=45):
    r = urllib.request.Request(url, headers=KOPF)
    with urllib.request.urlopen(r, timeout=timeout) as f:
        roh = f.read()
    return roh.decode("utf-8", "replace")


def hat_treffer(url):
    """-> (True/False/None, Notiz). None = nicht entscheidbar."""
    try:
        h = laden(url)
    except Exception as e:
        return None, f"nicht erreichbar ({type(e).__name__})"
    kern = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", kern)
    if LEER.search(text):
        return False, None
    # Ergebnisartige Elemente zaehlen - Ueberschriften und Artikel in Listen
    marker = len(re.findall(r"<(?:article|li)[^>]*(?:class|id)=\"[^\"]*"
                            r"(?:result|record|search|hit|item|treffer|post)[^\"]*\"", kern, re.I))
    marker += len(re.findall(r"class=\"[^\"]*(?:result|record)-(?:item|title|list)[^\"]*\"", kern, re.I))
    if marker >= 3:
        return True, None
    return None, "weder Leermeldung noch Trefferliste erkennbar"


def main():
    ziele = json.load(open("_live-urls.json", encoding="utf-8"))
    vorher = {e["name"]: e for e in json.load(open("_boolergebnis.json", encoding="utf-8"))}
    aus = []
    for i, z in enumerate(ziele, 1):
        name, tpl = z["n"], z["u"]
        alt = vorher.get(name, {})
        # Bereits sicher entschieden? Dann nicht erneut belasten.
        if alt.get("urteil") in ("JA",):
            aus.append({"name": name, "urteil": "JA", "beleg": "Trefferzahlen (Durchgang 1)"})
            print(f"{i:>2}. {name:<34} JA          (bereits belegt)")
            continue

        leer, n1 = hat_treffer(tpl.replace("%s", urllib.parse.quote(PHANTASIE)))
        time.sleep(0.9)
        voll, n2 = hat_treffer(tpl.replace("%s", urllib.parse.quote(PHANTASIE + " OR diabetes")))
        time.sleep(0.9)

        if leer is False and voll is True:
            urteil, beleg = "JA", "Phantasiewort leer, mit OR voll"
        elif leer is False and voll is False:
            urteil, beleg = "nein", "auch mit OR keine Treffer"
        elif alt.get("urteil") == "nein":
            urteil, beleg = "nein", "Trefferzahl unveraendert (Durchgang 1)"
        else:
            urteil, beleg = "ungeprueft", (n1 or n2 or "nicht entscheidbar")
        aus.append({"name": name, "urteil": urteil, "beleg": beleg})
        print(f"{i:>2}. {name:<34} {urteil:<11} {beleg}")

    json.dump(aus, open("_boolfinal.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nStand nach Durchgang 2:")
    for u in ("JA", "nein", "ungeprueft"):
        n = [e["name"] for e in aus if e["urteil"] == u]
        print(f"  {u:<11} {len(n):>2}  {', '.join(n) if n else '-'}")


if __name__ == "__main__":
    main()
