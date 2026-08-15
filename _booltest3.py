#!/usr/bin/env python3
"""Dritter Durchgang: Boolescher Betrieb ueber die Groesse der Ergebnisseite.

Trefferzahlen liessen sich bei diesen Anbietern nicht zuverlaessig auslesen -
die Auszeichnung ist zu uneinheitlich. Die Seitengroesse genuegt aber:
Eine leere Trefferliste ist kurz, eine volle deutlich laenger.

Dreisatz mit einem Phantasiewort:
  P                  -> leer (kurz)
  P OR diabetes      -> voll, wenn OR ausgewertet wird
  P AND diabetes     -> leer, wenn AND ausgewertet wird

Daraus:
  OR lang  und AND kurz -> JA
  OR kurz               -> nein (Operatoren als Woerter gesucht)
  OR lang  und AND lang -> nein (unbekannte Woerter werden verworfen)
"""
import json, re, sys, time, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
P = "zzqqxxwww"

KOPF = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
              "image/webp,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none", "Upgrade-Insecure-Requests": "1",
}


def groesse(url):
    """Laenge des sichtbaren Textes - Skripte zaehlen nicht mit."""
    try:
        r = urllib.request.Request(url, headers=KOPF)
        with urllib.request.urlopen(r, timeout=50) as f:
            h = f.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}"
    h = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", h, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", h)
    return len(re.sub(r"\s+", " ", text)), None


ZU_PRUEFEN = ["Epistemonikos", "Trip Database", "Semantic Scholar", "BASE", "CORE",
              "The Lens", "Dimensions", "Innovationsfonds (G-BA)", "Fernleihe (K10plus)",
              "WHO IRIS", "medRxiv", "OSF", "OpenGrey / Graue Literatur"]


def main():
    ziele = {z["n"]: z["u"] for z in json.load(open("_live-urls.json", encoding="utf-8"))}
    aus = []
    for i, name in enumerate(ZU_PRUEFEN, 1):
        tpl = ziele[name]
        werte = {}
        for etikett, q in (("leer", P), ("or", P + " OR diabetes"), ("and", P + " AND diabetes")):
            werte[etikett], fehler = groesse(tpl.replace("%s", urllib.parse.quote(q)))
            if fehler:
                werte[etikett] = None
                werte["fehler"] = fehler
            time.sleep(1.0)

        l, o, a = werte.get("leer"), werte.get("or"), werte.get("and")
        if None in (l, o, a):
            urteil, beleg = "ungeprueft", werte.get("fehler", "nicht abrufbar")
        elif o > l * 1.35 and a < l * 1.35:
            urteil, beleg = "JA", f"leer={l} OR={o} AND={a}"
        elif o <= l * 1.35:
            urteil, beleg = "nein", f"OR bringt nichts (leer={l} OR={o})"
        else:
            urteil, beleg = "nein", f"verwirft unbekannte Woerter (OR={o} AND={a})"
        aus.append({"name": name, "urteil": urteil, "beleg": beleg})
        print(f"{i:>2}. {name:<32} {urteil:<11} {beleg}")

    json.dump(aus, open("_bool3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
