#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Trennung von WARNUNG und AUSFALL im Zulassungsradar.

    cd versorgungsforschung-portal
    py scripts/zulassungen_ausfall_probe.py

WARUM
-----
Am 24.11.2026 hat der Torwaechter einen Satz entfernt (LEMBAZ: FDA-Zulassung,
aber der Satz behauptete etwas ueber die EU). Genau das soll er tun. Weil
`zulassungen.py` mit `return 1 if warnungen else 0` endete, wurde daraus ein
roter Lauf, und das Werk schickte eine Mail mit dem Satz, zulassungen.json und
die Radarseite stuenden auf dem Stand des Vortags. Beides war geschrieben.

DIE STELLE, AN DER ES LAUTLOS VERSAGT, ist nicht die Unterscheidung selbst,
sondern ihre Richtung. Wer sie falsch herum baut, bekommt einen Lauf, der auch
dann gruen meldet, wenn die Seite NICHT geschrieben wurde - und das merkt
niemand, weil eine Seite auf dem Stand von gestern wie ein ruhiger Tag
aussieht. Deshalb hat jede Haelfte hier ihre Gegenprobe.

Gemessen wird an den echten Eintraegen aus zulassungen.json, nicht an
gebauten Beispielen: Eine geschlossene Liste wird von Testfaellen aus
derselben Quelle nie widerlegt.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

import zulassungen as Z

WURZEL = pathlib.Path(__file__).resolve().parent.parent


def echte_eintraege(wie_viele: int = 20) -> list[dict]:
    d = json.loads((WURZEL / "zulassungen.json").read_text(encoding="utf-8"))
    e = [x for x in d["eintraege"] if x.get("satz")]
    if len(e) < wie_viele:
        raise SystemExit("zulassungen.json ist zu duenn fuer die Probe.")
    return json.loads(json.dumps(e[:wie_viele]))        # eigene Kopie


def main() -> int:
    fehler = 0

    # ------------------------------------------------------------------
    # 1. Der Torwaechter entfernt einen Satz. Das ist eine WARNUNG.
    # ------------------------------------------------------------------
    eintraege = echte_eintraege()
    opfer = next((e for e in eintraege if e["stufe"] in ("fda", "gutachten")),
                 eintraege[0])
    opfer["satz"] = ("Das Mittel ist in der EU zugelassen und wird von den "
                     "Krankenkassen erstattet.")
    warnungen: list[str] = []
    raus, geprueft = Z.pruefen(eintraege, warnungen)
    gut = raus >= 1 and len(warnungen) >= 1
    print(f"  {'OK ' if gut else 'FEHLER'} Torwaechter: {raus} von {geprueft} "
          f"entfernt, {len(warnungen)} Warnung(en)")
    fehler += 0 if gut else 1

    # Gegenprobe: unveraenderte Saetze duerfen nichts ausloesen. Ohne sie
    # bestuende die Haelfte oben auch dann, wenn der Torwaechter jeden Satz
    # entfernte.
    sauber = echte_eintraege()
    w2: list[str] = []
    raus2, geprueft2 = Z.pruefen(sauber, w2)
    gut = raus2 == 0 and not w2
    print(f"  {'OK ' if gut else 'FEHLER'} unveraenderte Saetze: {raus2} von "
          f"{geprueft2} entfernt, {len(w2)} Warnung(en)")
    fehler += 0 if gut else 1

    # ------------------------------------------------------------------
    # 2. seite_schreiben entscheidet ueber rot und gruen. Drei Lagen.
    # ------------------------------------------------------------------
    echte_seite = (WURZEL / "zulassungen.html").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as ordner:
        ort = pathlib.Path(ordner)
        alt_seite = Z.SEITE
        try:
            # a) Seite fehlt - AUSFALL
            Z.SEITE = ort / "gibtsnicht.html"
            w: list[str] = []
            ok = Z.seite_schreiben(eintraege, "24.11.2026", w)
            gut = ok is False and len(w) == 1
            print(f"  {'OK ' if gut else 'FEHLER'} Seite fehlt: "
                  f"geschrieben={ok}, {len(w)} Warnung(en)")
            fehler += 0 if gut else 1

            # b) Seite da, aber ohne Marker - AUSFALL
            Z.SEITE = ort / "ohne-marker.html"
            Z.SEITE.write_text("<html>nichts</html>", encoding="utf-8")
            w = []
            ok = Z.seite_schreiben(eintraege, "24.11.2026", w)
            gut = ok is False and len(w) == 1
            print(f"  {'OK ' if gut else 'FEHLER'} Marker fehlen: "
                  f"geschrieben={ok}, {len(w)} Warnung(en)")
            fehler += 0 if gut else 1

            # c) Die ECHTE Seite - muss geschrieben werden, ohne Warnung.
            #    Das ist die Gegenprobe zu a) und b): Ohne sie bestuenden die
            #    beiden auch dann, wenn seite_schreiben immer False gaebe.
            Z.SEITE = ort / "echt.html"
            Z.SEITE.write_text(echte_seite, encoding="utf-8")
            w = []
            ok = Z.seite_schreiben(eintraege, "24.11.2026", w)
            neu = Z.SEITE.read_text(encoding="utf-8")
            gut = (ok is True and not w
                   and neu != echte_seite
                   and Z.BLOCK_START in neu and Z.BLOCK_ENDE in neu)
            print(f"  {'OK ' if gut else 'FEHLER'} echte Seite: "
                  f"geschrieben={ok}, {len(w)} Warnung(en), Block ersetzt="
                  f"{neu != echte_seite}")
            fehler += 0 if gut else 1
        finally:
            Z.SEITE = alt_seite

    # ------------------------------------------------------------------
    # 3. Die Regel selbst steht genau einmal im Skript und lautet auf
    #    ausfaelle, nicht auf warnungen.
    # ------------------------------------------------------------------
    quelle = (WURZEL / "scripts" / "zulassungen.py").read_text(encoding="utf-8")
    gut = (quelle.count("return 1 if ausfaelle else 0") == 2
           and "return 1 if warnungen else 0" not in quelle)
    print(f"  {'OK ' if gut else 'FEHLER'} Regel im Skript: rot nur bei "
          "Ausfaellen")
    fehler += 0 if gut else 1

    print(f"\n{fehler} Abweichung(en).")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
