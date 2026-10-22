# -*- coding: utf-8 -*-
"""Gegentest fuer den Torwaechter in zulassungen.py.

Eine Pruefung, die nichts beanstandet, ist noch keine Pruefung: Sie koennte
auch kaputt sein. Hier stehen deshalb absichtlich falsche Saetze - jeder muss
durchfallen - und richtige, die durchgehen muessen.

    py scripts/zulassungen_gegentest.py

Die beiden Faelle aus dem ersten Lauf vom 22.10.2026 stehen als Nummer 1 und 5
darin: der Gutachtensatz, der eine Zulassung behauptete, und der deutsche
Wirkstoffname mit weggefallenem End-e.
"""
import pathlib
import sys

HIER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
from zulassungen import pruefen  # noqa: E402

FAELLE = [
    # (muss durchfallen?, Stufe, Wirkstoff, Satz, Beschreibung)
    (True, "gutachten", "daraxonrasib",
     "Rasonque (Daraxonrasib) ist zur Behandlung des Pankreasadenokarzinoms zugelassen.",
     "Gutachten behauptet eine Zulassung - der Fehler vom 22.10.2026"),
    (True, "gutachten", "omalizumab",
     "Adcomfo (Omalizumab) wird bei Asthma und chronischer Urtikaria angewendet.",
     "Gutachten nennt die Empfehlung gar nicht"),
    (True, "zulassung", "tafamidis",
     "Zokovea (Ensitrelvir) ist zur Postexpositionsprophylaxe von COVID-19 zugelassen.",
     "Satz gehoert zu einem ganz anderen Mittel - die Verwechslung"),
    (True, "zulassung", "ensitrelvir fumaric acid",
     "Zokovea ist zur Postexpositionsprophylaxe von COVID-19 zugelassen.",
     "nur der Handelsname, kein Wirkstoff"),

    (False, "zulassung", "temozolomide",
     "Kizfizo (Temozolomid) ist zur Behandlung des Glioblastoms zugelassen.",
     "deutsche Schreibweise ohne End-e - muss durchgehen"),
    (False, "gutachten", "Orforglipron hemicalcium",
     "Der CHMP empfiehlt die Zulassung von Foundayo (Orforglipron hemicalcium) "
     "zur Behandlung von Adipositas und Typ-2-Diabetes.",
     "richtiges Gutachten"),
    (False, "zulassung", "levodopa;carbidopa",
     "Onerji (Levodopa/Carbidopa) ist zur Behandlung des Morbus Parkinson zugelassen.",
     "Kombination mit Semikolon in der Quelle"),
    (False, "zulassung", "ranibizumab",
     "Susvimo (Ranibizumab) ist zur Behandlung der feuchten Makuladegeneration zugelassen.",
     "Wirkstoff ohne End-e - die Regel darf nicht zu viel abschneiden"),

    # **Bekannte Grenze, bewusst als bestandener Fall gefuehrt.** Der
    # Torwaechter prueft, ob der EIGENE Wirkstoff im Satz steht - nicht, ob
    # zusaetzlich ein fremder darin vorkommt. Dafuer muesste er alle INN
    # kennen, und er wuerde dann jede berechtigte Nennung eines
    # Vergleichspraeparats anschlagen ("bei unzureichendem Ansprechen auf
    # Methotrexat"). Eine Pruefung, die staendig Fehlalarm gibt, liest
    # irgendwann niemand mehr. Wer die Grenze verschieben will, moege vorher
    # messen, wie oft ein Vergleichspraeparat legitim vorkommt.
    (False, "zulassung", "tafamidis",
     "Tafamidis Accord (Tafamidis) ist zur Behandlung der Amyloidose "
     "nach Vorbehandlung mit Patisiran zugelassen.",
     "GRENZE: fremder Wirkstoff zusaetzlich genannt - wird NICHT gefangen"),
]


def main() -> int:
    fehler = 0
    for i, (soll_durchfallen, stufe, wirkstoff, satz, was) in enumerate(FAELLE, 1):
        eintrag = [{"stufe": stufe, "wirkstoff": wirkstoff, "satz": satz,
                    "name": f"Fall {i}"}]
        warnungen: list[str] = []
        raus, _ = pruefen(eintrag, warnungen)
        gefallen = raus == 1
        ok = gefallen == soll_durchfallen
        if not ok:
            fehler += 1
        zeichen = "ok  " if ok else "FEHL"
        erwartet = "faellt durch" if soll_durchfallen else "geht durch"
        print(f"  {zeichen} Fall {i}: {was}")
        print(f"       erwartet: {erwartet} · tatsaechlich: "
              + ("durchgefallen" if gefallen else "durchgegangen"))
        if gefallen and warnungen:
            print(f"       Grund: {warnungen[0].split(': ', 1)[1]}")
    print()
    if fehler:
        print(f"{fehler} von {len(FAELLE)} Faellen falsch bewertet - "
              "der Torwaechter prueft nicht, was er pruefen soll.")
        return 1
    print(f"Alle {len(FAELLE)} Faelle richtig bewertet.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
