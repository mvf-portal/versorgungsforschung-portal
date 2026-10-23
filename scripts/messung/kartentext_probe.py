# -*- coding: utf-8 -*-
"""Liest sich die Hinweiskarte in ALLEN Zahlenkombinationen richtig?

    py kartentext_probe.py          # baut die Probeseite
    py kartentext_probe.py --zeigen # und nennt den Pfad zum Oeffnen

Die Karte in `index.html` baut ihren Satz aus vier Zahlen - EU-Zulassungen,
CHMP-Empfehlungen, FDA-Zulassungen und DiGA. Bei vier Stufen gibt es
fuenfzehn Kombinationen, und welche davon einen schiefen Satz ergibt, sieht
man **nicht beim Lesen des Codes**. Man sieht es, wenn man sie ausdruckt.

Am 22.10.2026 kamen so drei Fehler heraus, einer davon aelter als die
FDA-Stufe:

  - Zwischen Ueberschrift und Aufzaehlung fehlte jedes Trennzeichen
    ("...Themengebiet4 Zulassungen").
  - "1 digitale Gesundheitsanwendungen" im Singular.
  - "5 digitale Gesundheitsanwendungen ... 5 DiGA" - die Zahl zweimal.

**Die Logik wird aus der Vorlage geholt, nicht abgeschrieben.** Eine
abgeschriebene Fassung prueft die Abschrift und nicht das Portal; sie geht
beim naechsten Umbau auseinander, ohne dass es jemand merkt.

Gebraucht wird eine echte JavaScript-Maschine. Auf diesem Rechner gibt es
kein `node` - deshalb schreibt das Skript eine Seite, die man oeffnet. Das
ist ohnehin der ehrlichere Weg: Geprueft wird dann dieselbe Maschine, die
auch der Leser benutzt.
"""
from __future__ import annotations

import json
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HIER = pathlib.Path(__file__).resolve().parent
# parents[2] ist der Ordner, in dem die Repos nebeneinander liegen:
#   messung -> scripts -> versorgungsforschung-portal -> Claude-Daten
WURZEL = HIER.parents[2]
VORLAGE = WURZEL / "portal-vorlage" / "vorlage" / "index.html"
ZIEL = WURZEL / "portal-vorlage" / "entwuerfe" / "kartentext-probe.html"

# Von Hand gesetzte Faelle - jede Stufe allein, jede Mischung, und die
# Einzahl ueberall, weil der Numerus die haeufigste Fehlerquelle ist.
FAELLE = [
    ("nur EU-Zulassungen",       {"zul": 4, "gut": 0, "fda": 0, "diga": 0}),
    ("eine EU-Zulassung",        {"zul": 1, "gut": 0, "fda": 0, "diga": 0}),
    ("nur CHMP-Empfehlungen",    {"zul": 0, "gut": 3, "fda": 0, "diga": 0}),
    ("eine CHMP-Empfehlung",     {"zul": 0, "gut": 1, "fda": 0, "diga": 0}),
    ("nur FDA",                  {"zul": 0, "gut": 0, "fda": 5, "diga": 0}),
    ("eine FDA-Zulassung",       {"zul": 0, "gut": 0, "fda": 1, "diga": 0}),
    ("nur DiGA (KI-Hub)",        {"zul": 0, "gut": 0, "fda": 0, "diga": 5}),
    ("eine einzige DiGA",        {"zul": 0, "gut": 0, "fda": 0, "diga": 1}),
    ("EU + CHMP",                {"zul": 7, "gut": 7, "fda": 0, "diga": 0}),
    ("EU + CHMP + FDA (Onko)",   {"zul": 7, "gut": 7, "fda": 9, "diga": 0}),
    ("alle vier",                {"zul": 2, "gut": 1, "fda": 3, "diga": 1}),
    ("DiGA plus Arzneimittel",   {"zul": 1, "gut": 0, "fda": 0, "diga": 2}),
    ("je genau eines",           {"zul": 1, "gut": 1, "fda": 1, "diga": 1}),
]


def logik_holen() -> str:
    """Den Rechenteil der Karte aus der Vorlage schneiden."""
    t = VORLAGE.read_text(encoding="utf-8")
    anfang = t.index("  const hatNeu = (typeof ZUL_ZULASSUNG !== 'undefined');")
    ende = t.index("karte.innerHTML", anfang)
    return t[anfang:ende].replace("{{SLUG}}", "onkologie")


def main() -> int:
    if not VORLAGE.exists():
        print(f"{VORLAGE} fehlt.")
        return 1
    try:
        logik = logik_holen()
    except ValueError:
        print("Der Rechenteil der Karte sieht anders aus als erwartet - "
              "in vorlage/index.html nachsehen, wo der Satz gebaut wird.")
        return 1

    teile = ["const AUS = [];"]
    for name, f in FAELLE:
        eigene = sum(f.values())
        teile.append(f"""
{{
  const ZUL_EIGENE = {eigene}, ZUL_GUTACHTEN = {f['gut']},
        ZUL_ZULASSUNG = {f['zul']}, ZUL_FDA = {f['fda']}, ZUL_DIGA = {f['diga']};
  const eigene = ZUL_EIGENE, gut = ZUL_GUTACHTEN;
{logik}
  AUS.push([{json.dumps(name)}, text]);
}}""")

    seite = (
        '<!doctype html><meta charset="utf-8">'
        "<title>Kartentext-Probe</title>"
        '<body style="font:15px/1.7 Lato,sans-serif;max-width:52em;'
        'margin:2em auto;padding:0 1em">'
        "<h2>Hinweiskarte: der Satz in allen Zahlenkombinationen</h2>"
        "<p style=\"color:#555\">Gebaut aus der Logik in "
        "<code>portal-vorlage/vorlage/index.html</code>. Zu pr&uuml;fen ist "
        "jede Zeile auf Trennzeichen, Numerus und doppelte Zahlen.</p>"
        '<div id="a"></div><script>' + "\n".join(teile)
        + 'document.getElementById("a").innerHTML = AUS.map(function(p){'
        '  return "<p style=\\"border-left:3px solid #0051A1;padding-left:11px\\">"'
        '    + "<b style=\\"color:#555;font-size:13px\\">" + p[0] + "</b><br>"'
        '    + p[1] + "</p>"; }).join("");'
        "</" + "script>")
    ZIEL.parent.mkdir(parents=True, exist_ok=True)
    ZIEL.write_text(seite, encoding="utf-8")

    print(f"{len(FAELLE)} Fälle, Probeseite geschrieben:")
    print(f"  {ZIEL}")
    print("\nIm Browser öffnen und jede Zeile lesen. Worauf zu achten ist:")
    print("  - Steht zwischen Überschrift und Aufzählung ein Trennzeichen?")
    print("  - Stimmt die Einzahl ('1 digitale Gesundheitsanwendung')?")
    print("  - Steht eine Zahl zweimal da?")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
