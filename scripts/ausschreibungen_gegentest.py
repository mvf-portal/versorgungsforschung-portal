#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft, dass `hol()` bei Stoerungen wiederholt und bei Ablehnungen nicht.

    py scripts/ausschreibungen_gegentest.py

WARUM ES DIESEN GEGENTEST GIBT
------------------------------
Die Wiederholung ist eine Vorkehrung, die im Normalbetrieb nie zuendet. Ob
sie taugt, zeigt sich erst an dem Morgen, an dem die Gegenseite stoert, und
dann ist es zu spaet, es nachzusehen.

Am 19.11.2026 war dieser Morgen. Vierzehn Suchen bei grants.gov endeten mit
"502 Bad Gateway", keine wurde wiederholt, zehn von zwanzig Themengebieten
standen danach leer da. Die Zeile, die das verursachte, sah richtig aus und
trug einen Kommentar, der fuer 403 und 404 stimmte.

Hier wird kein Netz angefasst. `urlopen` wird durch einen Stellvertreter
ersetzt, der genau die Antworten gibt, die geprueft werden sollen.
"""
from __future__ import annotations

import io
import pathlib
import sys
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ausschreibungen as A  # noqa: E402

A.PAUSE = 0          # der Gegentest soll messen, nicht warten


class Antwort:
    def __init__(self, inhalt: bytes) -> None:
        self._inhalt = inhalt

    def read(self) -> bytes:
        return self._inhalt

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def stellvertreter(folge: list):
    """Gibt der Reihe nach, was in `folge` steht. Zaehlt die Aufrufe mit."""
    zustand = {"aufrufe": 0}

    def ruf(req, timeout=None):                       # noqa: ARG001
        i = zustand["aufrufe"]
        zustand["aufrufe"] += 1
        was = folge[min(i, len(folge) - 1)]
        if isinstance(was, Exception):
            raise was
        return Antwort(was)

    return ruf, zustand


def http(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://beispiel.test", code,
                                  "Probe", {}, io.BytesIO(b""))


def fall(name: str, folge: list, erwartet_aufrufe: int,
         erwartet_erfolg: bool) -> int:
    ruf, zustand = stellvertreter(folge)
    A.urllib.request.urlopen = ruf
    erfolg, grund = True, ""
    try:
        A.hol("https://beispiel.test")
    except Exception as e:                            # noqa: BLE001
        erfolg, grund = False, type(e).__name__
    gut = (zustand["aufrufe"] == erwartet_aufrufe) and (erfolg == erwartet_erfolg)
    print(f"  {'OK ' if gut else 'FEHLER'} {name}: {zustand['aufrufe']} Aufruf(e), "
          f"{'durchgekommen' if erfolg else 'abgebrochen (' + grund + ')'}"
          f"{'' if gut else f'  erwartet: {erwartet_aufrufe} Aufruf(e), '
             + ('durchgekommen' if erwartet_erfolg else 'abgebrochen')}")
    return 0 if gut else 1


def main() -> int:
    echt = A.urllib.request.urlopen
    fehler = 0
    try:
        # Der Fall vom 19.11.2026: zweimal 502, beim dritten Mal geht es.
        fehler += fall("502, dann 502, dann Antwort",
                       [http(502), http(502), b"{}"], 3, True)
        # Dauerstoerung: dreimal versucht, dann aufgegeben.
        fehler += fall("502 durchgehend", [http(502)], A.VERSUCHE, False)
        for code in sorted(A.WIEDERHOLBAR):
            fehler += fall(f"{code} wird wiederholt", [http(code), b"{}"], 2, True)
        # Und die Gegenprobe: Eine Ablehnung darf NICHT wiederholt werden.
        # Ohne diese Haelfte wuerde ein `raise` entfernen auch "bestehen".
        for code in (400, 403, 404, 410):
            fehler += fall(f"{code} wird NICHT wiederholt", [http(code)], 1, False)
        # Abgerissene Verbindungen wie bisher.
        fehler += fall("Verbindungsabbruch wird wiederholt",
                       [urllib.error.URLError("weg"), b"{}"], 2, True)
    finally:
        A.urllib.request.urlopen = echt

    print(f"\n{fehler} Abweichung(en).")
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
