# -*- coding: utf-8 -*-
"""Die drei hub-eigenen Zahlen im Dach-Band taeglich nachfuehren.

WAS DAS BAND IST
----------------
Unter der Suche steht seit dem 02.11.2026 ein Band mit dreizehn Zahlen,
das zeigt, dass dieser Hub das ganze Fach traegt und nicht eines von
fuenfzehn Themen ist. Gebaut wird es von `vf-landkarte/dachband.py` auf
Peters Rechner und liegt zwischen zwei Marken in `index.html`.

WARUM DIESES SKRIPT TROTZDEM HIER LIEGT
---------------------------------------
Zehn der dreizehn Zahlen kommen aus Bestaenden, die es nur lokal gibt
(Studienregister, Innovationsfonds-Portal, Thesis-Portal). Im Laeufer
von GitHub Actions existiert davon nichts, das Band kann hier also
nicht neu gebaut werden.

Drei Zahlen aber kommen aus Dateien DIESES Repos, und genau die hat der
taegliche Lauf ohnehin frisch:

    neue Arbeiten, taeglich   studien-archiv.json
    offene Ausschreibungen    ausschreibungen.json
    Zulassungsverfahren       zulassungen.json

Am 02.11.2026 standen auf derselben Seite zwei verschiedene Zahlen fuer
dieselbe Sache: Das Band nannte 24 offene Ausschreibungen, der Kasten
darunter 25. Beide massen dasselbe, das Band war einen Tag alt.

⚠ DIESES SKRIPT BAUT DAS BAND NICHT NEU. Es ersetzt genau drei Zahlen
und die Summe. Alles andere, auch das Standdatum der uebrigen zehn,
bleibt unberuehrt - das Datum gehoert zu ihnen, nicht zu diesen dreien.

⚠ JEDE ERSETZUNG WIRD GEZAEHLT. Trifft ein Muster nicht genau einmal,
bricht das Skript ab und ruehrt die Datei nicht an. Ein halb
nachgefuehrtes Band waere schlimmer als ein altes.

    python scripts/dachband_nachfuehren.py
    python scripts/dachband_nachfuehren.py --zeigen     nichts schreiben
    python scripts/dachband_nachfuehren.py --gegentest  Pruefung beweisen
"""
import json
import pathlib
import re
import sys

HIER = pathlib.Path(__file__).resolve().parent.parent
ZIEL = HIER / "index.html"

ANFANG = "__DACH_BAND_ANFANG__"
ENDE = "__DACH_BAND_ENDE__"


def zahl(n):
    return "{:,}".format(int(n)).replace(",", ".")


def lies(name):
    p = HIER / name
    if not p.exists():
        raise SystemExit("ABBRUCH: %s fehlt" % name)
    return json.loads(p.read_text(encoding="utf-8"))


def hub_zahlen():
    """Die drei Zahlen, die dieses Repo selbst kennt.

    ⚠ KEINE VORGABE BEI FEHLERN. Eine Null waere hier eine Aussage ueber
    das Fach, keine Fehlermeldung.
    """
    archiv = lies("studien-archiv.json")
    if not isinstance(archiv, list):
        raise SystemExit("ABBRUCH: studien-archiv.json ist keine Liste")

    aus = lies("ausschreibungen.json")
    themen = aus.get("themen")
    if not isinstance(themen, list):
        raise SystemExit("ABBRUCH: ausschreibungen.json ohne 'themen'")
    offen = 0
    for t in themen:
        if "anzahl" not in t:
            raise SystemExit("ABBRUCH: ein Thema ohne 'anzahl'")
        offen += int(t["anzahl"] or 0)

    zul = lies("zulassungen.json")
    eintraege = zul.get("eintraege")
    if not isinstance(eintraege, list):
        raise SystemExit("ABBRUCH: zulassungen.json ohne 'eintraege'")

    return {
        "neue Arbeiten, täglich": len(archiv),
        "offene Ausschreibungen": offen,
        "Zulassungsverfahren": len(eintraege),
    }


def band_grenzen(t):
    i, j = t.find(ANFANG), t.find(ENDE)
    if i < 0 or j < 0 or j < i:
        raise SystemExit(
            "ABBRUCH: Die Marken des Dach-Bands stehen nicht in index.html.\n"
            "  Wurde das Band entfernt? Dann gehoert dieser Schritt aus dem\n"
            "  Arbeitsablauf heraus.")
    if t.count(ANFANG) != 1 or t.count(ENDE) != 1:
        raise SystemExit("ABBRUCH: Marken stehen mehrfach in index.html")
    return i, j + len(ENDE)


def ersetze(band, beschriftung, neu):
    """Die Zahl vor einer Beschriftung austauschen, genau einmal."""
    muster = re.compile(
        r"(<li><b>)([0-9.]+)(</b><span>" + re.escape(beschriftung)
        + r"</span></li>)")
    treffer = muster.findall(band)
    if len(treffer) != 1:
        raise SystemExit(
            "ABBRUCH: %r steht %dmal im Band, erwartet genau einmal."
            % (beschriftung, len(treffer)))
    alt = treffer[0][1]
    return muster.sub(lambda m: m.group(1) + zahl(neu) + m.group(3),
                      band, count=1), alt


def summe_ersetzen(band, wert):
    muster = re.compile(
        r'(<b class="mvf-dach-summe">)([0-9.]+)(</b>)')
    if len(muster.findall(band)) != 1:
        raise SystemExit("ABBRUCH: Die Summe steht nicht genau einmal im Band")
    alt = muster.findall(band)[0][1]
    return muster.sub(lambda m: m.group(1) + zahl(wert) + m.group(3),
                      band, count=1), alt


def alle_zahlen(band):
    return [int(x.replace(".", ""))
            for x in re.findall(r"<li><b>([0-9.]+)</b>", band)]


def gegentest():
    print("GEGENTEST")
    ok = True
    gut_band = ("<li><b>460</b><span>neue Arbeiten, täglich</span></li>"
                '<b class="mvf-dach-summe">17.943</b>')
    neu, alt = ersetze(gut_band, "neue Arbeiten, täglich", 479)
    traegt = "<b>479</b>" in neu and alt == "460"
    ok = ok and traegt
    print("   %s eine Zahl wird ersetzt, die alte wird gemeldet (%s)"
          % ("ok " if traegt else "FEHLER", alt))

    for name, probe in (
            ("Beschriftung fehlt", "<li><b>7</b><span>etwas anderes</span></li>"),
            ("Beschriftung zweimal",
             "<li><b>1</b><span>X</span></li><li><b>2</b><span>X</span></li>")):
        try:
            ersetze(probe, "X" if "zweimal" in name else
                    "neue Arbeiten, täglich", 1)
        except SystemExit:
            print("   ok  %s fuehrt zum Abbruch" % name)
            continue
        ok = False
        print("   FEHLER %s wird durchgewunken" % name)

    print("\n" + ("Gegentest bestanden." if ok else "GEGENTEST GESCHEITERT."))
    return 0 if ok else 1


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--gegentest" in sys.argv:
        return gegentest()

    t = ZIEL.read_text(encoding="utf-8")
    i, j = band_grenzen(t)
    band = t[i:j]

    neu_werte = hub_zahlen()
    geaendert = []
    for beschriftung, wert in neu_werte.items():
        band, alt = ersetze(band, beschriftung, wert)
        if alt.replace(".", "") != str(wert):
            geaendert.append("%s %s -> %s" % (beschriftung, alt, zahl(wert)))

    band, alt_summe = summe_ersetzen(band, sum(alle_zahlen(band)))
    if alt_summe.replace(".", "") != str(sum(alle_zahlen(band))):
        geaendert.append("Summe %s -> %s"
                         % (alt_summe, zahl(sum(alle_zahlen(band)))))

    if not geaendert:
        print("Dach-Band: nichts zu tun, die drei Zahlen stimmen.")
        return 0

    print("Dach-Band nachgefuehrt:")
    for z in geaendert:
        print("   " + z)

    if "--zeigen" in sys.argv:
        print("   (--zeigen: nichts geschrieben)")
        return 0

    ZIEL.write_text(t[:i] + band + t[j:], encoding="utf-8")
    print("-> index.html geschrieben")
    return 0


if __name__ == "__main__":
    sys.exit(main())
