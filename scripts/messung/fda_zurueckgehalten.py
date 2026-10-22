# -*- coding: utf-8 -*-
"""Der zurueckgehaltene Satz: Zulassungen aus dem Zeitraum VOR dem Fenster.

Die Regeln in zulassungen_themen.hubs_fuer_text() sind an den 25 Texten der
letzten 180 Tage entstanden. An denselben 25 gemessen ergeben sie 25 von 25 -
das ist zu erwarten und sagt nichts. Gemessen wird deshalb hier, an
Zulassungen aus den 180 Tagen davor, die bei der Regelarbeit nicht vorlagen.

Das Urteil setze ich nach dem Indikationstext, und zwar **bevor** ich die
Ausgabe der Regeln ansehe - sonst ist es kein Urteil, sondern eine
Bestaetigung. Der Lauf hat deshalb zwei Schritte:

    py fda_zurueckgehalten.py --holen    # Texte holen und Soll-Gerippe schreiben
    py fda_zurueckgehalten.py            # messen, nachdem das Soll gefuellt ist
"""
import datetime as dt
import json
import pathlib
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import fda_quelle  # noqa: E402
import zulassungen_themen as themen  # noqa: E402

DATEI = pathlib.Path(__file__).resolve().parent / "fda_zurueckgehalten.json"


def holen():
    """Das Fenster 181 bis 400 Tage zurueck - disjunkt zum Arbeitsfenster."""
    heute = dt.date.today()
    bis = heute - dt.timedelta(days=181)
    von = heute - dt.timedelta(days=400)
    suche = (f"submissions.submission_status_date:[{von:%Y%m%d}+TO+{bis:%Y%m%d}]"
             '+AND+submissions.submission_status:"AP"'
             '+AND+submissions.submission_class_code:"TYPE+1"')
    antwort = fda_quelle.hol(f"{fda_quelle.OPENFDA}?search={suche}&limit=1000")
    gefunden = {}
    for d in antwort.get("results", []):
        produkte = d.get("products") or []
        if not produkte:
            continue
        treffer = next((s for s in d.get("submissions", [])
                        if s.get("submission_status") == "AP"
                        and s.get("submission_class_code") == "TYPE 1"
                        and f"{von:%Y%m%d}" <= str(s.get("submission_status_date", ""))
                        <= f"{bis:%Y%m%d}"), None)
        if not treffer:
            continue
        name = (produkte[0].get("brand_name") or "").strip()
        if not name:
            continue
        wirk = []
        for p in produkte:
            for w in p.get("active_ingredients") or []:
                if w.get("name"):
                    wirk.append(w["name"].strip())
        datum = str(treffer["submission_status_date"])
        gefunden.setdefault(str(d.get("application_number", "")), {
            "name": name, "wirkstoff": "; ".join(dict.fromkeys(wirk)),
            "iso": f"{datum[:4]}-{datum[4:6]}-{datum[6:8]}",
        })
    print(f"{len(gefunden)} Erstzulassungen im zurueckgehaltenen Fenster "
          f"({von:%d.%m.%Y} bis {bis:%d.%m.%Y})\n")

    satz = {}
    for nr, e in sorted(gefunden.items(), key=lambda x: x[1]["iso"], reverse=True):
        text, _, _ = fda_quelle._indikation(e)
        if not text:
            continue
        satz[e["name"]] = {"wirkstoff": e["wirkstoff"], "datum": e["iso"],
                           "text": text, "soll": None}
        print(f"  {e['name'][:20]:<21} {e['wirkstoff'][:30]:<31} {len(text):>5}")
        time.sleep(0.3)
    DATEI.write_text(json.dumps(satz, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    print(f"\n{len(satz)} Texte in {DATEI}. Jetzt 'soll' je Eintrag fuellen "
          "(Liste von Hub-Slugs, leere Liste = kein Hub).")


def messen():
    satz = json.loads(DATEI.read_text(encoding="utf-8"))
    offen = [n for n, e in satz.items() if e["soll"] is None]
    if offen:
        print(f"Noch ohne Urteil: {len(offen)} - {', '.join(offen[:6])}")
        return 1
    genau = zuviel = zuwenig = 0
    for name, e in satz.items():
        ist = set(themen.hubs_fuer_text(e["text"]))
        soll = set(e["soll"])
        zv, zw = ist - soll, soll - ist
        if not zv and not zw:
            genau += 1
        else:
            print(f"  {name[:16]:<17} ist={','.join(sorted(ist)) or '-':<16} "
                  f"soll={','.join(sorted(soll)) or '-':<16}"
                  f"{' ZUVIEL ' + ','.join(sorted(zv)) if zv else ''}"
                  f"{' FEHLT ' + ','.join(sorted(zw)) if zw else ''}")
        zuviel += len(zv)
        zuwenig += len(zw)
    n = len(satz)
    print(f"\n  Zurueckgehaltener Satz: {genau} von {n} genau richtig")
    print(f"  falsche Zuordnungen : {zuviel}")
    print(f"  fehlende            : {zuwenig}")
    return 0


if __name__ == "__main__":
    if "--holen" in sys.argv:
        holen()
    else:
        sys.exit(messen())
