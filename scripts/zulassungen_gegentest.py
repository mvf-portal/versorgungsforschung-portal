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
import json
import pathlib
import re
import sys

HIER = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import zulassungen_themen as themen  # noqa: E402
from zulassungen import pruefen  # noqa: E402

PRUEFSATZ = HIER / "zulassungen_pruefsatz.json"

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

    (True, "diga", "",
     "Ich kann diese Anfrage nicht beantworten, da die notwendigen Informationen "
     "fehlen: Der Wirkstoff von \"Una Health\" ist nicht angegeben und die "
     "Indikation liegt mir nicht vor.",
     "Rueckfrage des Modells statt eines Satzes - der Fehler vom 22.10.2026"),
    (True, "diga", "",
     "Diese digitale Gesundheitsanwendung ist in das Verzeichnis aufgenommen worden. "
     + "Sie hilft bei vielerlei Beschwerden. " * 12,
     "viel zu lang, also kein einzelner Satz"),

    # --- Stufe 4: FDA. Die Falle ist hier die *richtige* Zulassung an der
    # falschen Stelle: Jeder dieser Saetze ist woertlich wahr.
    (True, "fda", "tavapadon",
     "Juvmo (Tavapadon) ist zur Behandlung der Parkinson-Krankheit bei "
     "Erwachsenen zugelassen.",
     "FDA-Satz nennt die Behoerde nicht - liest sich als EU-Zulassung"),
    (True, "fda", "daraxonrasib",
     "Die FDA hat Rasonque (Daraxonrasib) zugelassen; in der EU entscheidet "
     "der CHMP noch.",
     "FDA-Satz behauptet etwas ueber den Stand bei der EMA"),
    (True, "fda", "insulin efsitora alfa-gobe",
     "Die FDA hat Onswik (Insulin efsitora alfa) zugelassen; das Mittel ist in "
     "Deutschland erstattungsfähig.",
     "FDA-Satz behauptet Erstattung in Deutschland"),
    (False, "fda", "tavapadon",
     "Die FDA hat Tavapadon (Juvmo) zur Behandlung der Parkinson-Krankheit bei "
     "Erwachsenen zugelassen.",
     "richtiger FDA-Satz - muss durchgehen"),
    (False, "fda", "zilurgisertib fumarate",
     "Die US-Arzneimittelbehörde FDA hat Zilurgisertib-Fumarat (Atebrioz) zur "
     "Reduktion heterotoper Ossifikationen zugelassen.",
     "FDA ausgeschrieben statt als Kuerzel - muss durchgehen"),

    (False, "diga", "",
     "ACTICORE1 ist vorläufig zur Erprobung in das Verzeichnis erstattungsfähiger "
     "digitaler Gesundheitsanwendungen aufgenommen worden und damit auf Rezept "
     "erstattungsfähig.",
     "richtiger DiGA-Satz ohne Wirkstoff - muss durchgehen"),

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


# --------------------------------------------------------------------------
# Zweiter Teil: die Zuordnung der FDA-Stufe (hubs_fuer_text).
#
# Hier ist eine Quote allein kein Beweis. Die Regeln sind am Arbeitssatz
# entstanden, also muss er stimmen - das sagt nichts. Drei Dinge werden
# deshalb geprueft:
#
#   1. **Der zurueckgehaltene Satz.** 29 Zulassungen aus dem Fenster davor,
#      die bei der Regelarbeit nicht vorlagen. Am 22.10.2026 ergaben sie
#      24 von 29 - **ohne** die fuenf Muster, die danach aus genau diesen
#      Fehlschlaegen nachgetragen wurden (Cholangitis, Lungenfibrose,
#      Urtikaria, Tachykardie, Chylomikronaemie). Die 29 von 29, die der
#      Lauf heute zeigt, sind deshalb KEINE zurueckgehaltene Messung mehr.
#      Wer die Regeln anfasst, moege ein frisches Fenster holen.
#   2. **Kein falscher Hub.** Das ist die harte Bedingung, nicht die Quote:
#      Ein fehlender Hub ist sichtbar - der Eintrag steht dann nur unter
#      "Alle". Eine falsche Zuordnung sieht aus wie eine richtige.
#   3. **Die absichtlich schlechte Fassung muss schlechter sein.** Ohne die
#      Beschraenkung auf den Indikationssatz und ohne den Diagnostik-Filter
#      ergab derselbe Arbeitssatz 19 von 25 mit zwei falschen Zuordnungen.
#      Bleibt die schlechte Fassung gleich gut, messen die Vorkehrungen
#      nichts und koennen weg.

# Die schlechte Fassung: alle Muster gegen den GANZEN Abschnitt, ohne
# Ruecksicht auf Diagnostika. So war der erste Entwurf vom 22.10.2026.
def _schlecht(text: str) -> list[str]:
    treffer = []
    for slug, (_, muster) in themen.GEBAUT.items():
        if any(m.search(str(text or "")) for m in muster):
            treffer.append(slug)
    return treffer


def zuordnung_pruefen() -> int:
    if not PRUEFSATZ.exists():
        print(f"  ! {PRUEFSATZ.name} fehlt - Zuordnung nicht geprueft.")
        return 1
    faelle = json.loads(PRUEFSATZ.read_text(encoding="utf-8"))["faelle"]
    fehler = 0
    gesamt_falsch = gesamt_schlecht_falsch = 0
    for herkunft in ("zurueckgehalten", "arbeitssatz"):
        meine = [f for f in faelle if f["herkunft"] == herkunft]
        genau = falsch = fehlend = 0
        schlecht_genau = schlecht_falsch = 0
        for f in meine:
            ist = set(themen.hubs_fuer_text(f["text"]))
            soll = set(f["soll"])
            if ist == soll:
                genau += 1
            else:
                print(f"       {f['name'][:18]:<19} ist={','.join(sorted(ist)) or '-':<14}"
                      f" soll={','.join(sorted(soll)) or '-':<14}")
            falsch += len(ist - soll)
            fehlend += len(soll - ist)
            s_ist = set(_schlecht(f["text"]))
            schlecht_genau += s_ist == soll
            schlecht_falsch += len(s_ist - soll)

        print(f"  {herkunft}: {genau} von {len(meine)} genau richtig, "
              f"{falsch} falsch, {fehlend} fehlend")
        print(f"       schlechte Fassung: {schlecht_genau} richtig, "
              f"{schlecht_falsch} falsch")

        gesamt_falsch += falsch
        gesamt_schlecht_falsch += schlecht_falsch

        # **Die harte Bedingung.** Eine falsche Zuordnung laesst den Gegentest
        # scheitern, eine fehlende nicht.
        if falsch:
            print(f"  FEHL {falsch} falsche Zuordnung(en) - das ist der Fehler, "
                  "den ein Leser nicht erkennen kann.")
            fehler += 1

    # **Der Gegentest zum Massstab - ueber den ganzen Pruefsatz, nicht je
    # Teilmenge.** Am 22.10.2026 war die schlechte Fassung am
    # zurueckgehaltenen Satz genau gleich gut: Dort kommt kein Diagnostikum
    # vor und kein Begleitsatz, der eine fremde Krankheit nennt. Die beiden
    # Vorkehrungen greifen in 54 Faellen bei **zwei** - PIXCLARA (F-18-
    # Diagnostikum) und BAXFENDY ("diabetes management" im Begleitsatz). Das
    # ist selten, aber beide Male war es eine FALSCHE Zuordnung, und die ist
    # der Fehler, den niemand sieht. Wer die Vorkehrungen fuer teuer haelt,
    # moege sie an diesen zwei Faellen abwaegen, nicht an der Quote.
    print(f"\n  ueber alle {len(faelle)} Faelle: {gesamt_falsch} falsch, "
          f"schlechte Fassung {gesamt_schlecht_falsch} falsch")
    if gesamt_schlecht_falsch <= gesamt_falsch:
        print("  FEHL die absichtlich schlechte Fassung ist nicht schlechter - "
              "Indikationssatz-Beschraenkung und Diagnostik-Filter messen nichts.")
        fehler += 1
    return fehler


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
    if fehler:
        print()
        print(f"{fehler} von {len(FAELLE)} Faellen falsch bewertet - "
              "der Torwaechter prueft nicht, was er pruefen soll.")
        return 1
    print(f"\nAlle {len(FAELLE)} Torwaechter-Faelle richtig bewertet.")

    print("\n--- Zuordnung der FDA-Stufe ---")
    if zuordnung_pruefen():
        return 1
    print("  Zuordnung in Ordnung: kein falscher Hub, schlechte Fassung schlechter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
