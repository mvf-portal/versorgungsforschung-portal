#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zulassungsradar: neue Arzneimittel der EMA, den Hubs zugeordnet.

Zwei Stufen, beide aus derselben Quelle:

  **Stufe 1 - Zulassung.** Das Mittel ist in der EU zugelassen.
  **Stufe 2 - CHMP-Gutachten.** Der Ausschuss hat empfohlen, die Kommission
  hat noch nicht entschieden. Das ist der *frühere* Zeitpunkt - rund zwei
  Monate vor der Zulassung - und der eigentliche Grund für diesen Radar.

**Dieses Skript laeuft nur im Versorgungsforschungs-Hub**, wie der
Ausschreibungsradar: Die Quelle wird einmal geholt, nicht fuenfzehnmal, und es
gibt einen Stand statt fuenfzehn.

Quelle
------
Eine einzige: die Tabelle "Medicines" der EMA, als XLSX zum Herunterladen,
**nachts automatisch aktualisiert**. Am 22.10.2026 gemessen: 2.754 Zeilen,
davon 2.357 Humanarzneimittel; juengster Eintrag vom Vortag. Sie fuehrt je
Mittel den Wirkstoff, das Therapiegebiet als **MeSH-Begriff**, den ATC-Code,
die Kennzeichen Orphan / PRIME / bedingt / beschleunigt, den Indikationstext
und die Adresse der EMA-Seite.

    https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx

Warum nur diese eine: Das BfArM hat auf seiner gesamten Seite **keinen Feed**
und keine offene Schnittstelle (geprueft 22.10.2026), und die innovativen
Arzneimittel laufen ohnehin ueber das zentralisierte EU-Verfahren. openFDA
waere die zweite Quelle und ist offen, liefert aber zu den neuesten
Zulassungen **keine Namen**: Am 22.10.2026 trugen nur 11 von 43
Erstzulassungen der letzten 90 Tage einen Markennamen, und zwar die aelteren.
Das ist als eigene Stufe vorgemerkt, nicht hier.

Zwei Fallen, beide am 22.10.2026 zugeschlagen
---------------------------------------------
1. **Die Daten stehen als Text da**, im Format TT/MM/JJJJ. Ein Vergleich gegen
   `date` liefert dann nicht etwa einen Fehler, sondern stillschweigend nichts:
   Der erste Messversuch ergab "null Zulassungen in zwoelf Monaten" und sah aus
   wie eine veraltete Tabelle.
2. **"European Commission decision date" ist nicht das Zulassungsdatum.** Es ist
   der *juengste* Beschluss und steht auch bei Aenderungen an alten Mitteln:
   GONAL-f trug am 22.10.2026 einen Beschluss vom Vortag und ist seit 1995
   zugelassen (Revision 28). Die Erstzulassung steht in **"Marketing
   authorisation date"**. Wer die Felder verwechselt, baut genau den Radar, der
   Etikettenaenderungen als Neuigkeit verkauft.

Gemessen am 22.10.2026
----------------------
  Stufe 1: 12 Erstzulassungen in 90 Tagen, 81 in zwoelf Monaten;
           davon einem Hub zugeordnet 9 beziehungsweise 55.
  Stufe 2: 29 Mittel im Gutachtenstand, davon 25 positiv und 4 negativ.

Die Zuordnung zu den Hubs steht in `zulassungen_themen.py` und laeuft **ohne
Modell** ueber den MeSH-Begriff. Das Modell schreibt nur den deutschen Satz.

Aufruf
------
    py scripts/zulassungen.py            # holen, zuordnen, schreiben
    py scripts/zulassungen.py --probe    # alles zeigen, nichts schreiben
    py scripts/zulassungen.py --roh      # ohne Modell, nur die Rohdaten
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

import openpyxl

HIER = pathlib.Path(__file__).resolve().parent
WURZEL = HIER.parent
sys.path.insert(0, str(HIER))
import zulassungen_themen as themen  # noqa: E402

ZIEL = WURZEL / "zulassungen.json"
SEITE = WURZEL / "zulassungen.html"

BLOCK_START = "// === ZULASSUNGEN-BLOCK-START (taeglich von GitHub Actions ersetzt) ==="
BLOCK_ENDE = "// === ZULASSUNGEN-BLOCK-ENDE ==="

# Welcher Hub unter welcher Adresse liegt. Nur die sieben, die Zulassungen
# bekommen - die uebrigen acht stehen gar nicht erst in zulassungen_themen.py.
HUB_DOMAIN = {
    "onkologie": "onkologie.m-vf.de",
    "kardio": "kardio.m-vf.de",
    "diabetes": "diabetes.m-vf.de",
    "adipositas": "adipositas.m-vf.de",
    "mental": "mental.m-vf.de",
    "impfen": "impfen.m-vf.de",
    "longevity": "longevity.m-vf.de",
    "ncd": "ncd.m-vf.de",
}

EMA_URL = ("https://www.ema.europa.eu/en/documents/report/"
           "medicines-output-medicines-report_en.xlsx")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0 Safari/537.36")

# Die EMA-Tabelle hat neun Vorspannzeilen; die Kopfzeile ist die zehnte.
# Fest verdrahtet waere das eine Zeitbombe - geprueft wird unten an den
# Spaltennamen, und weicht die Tabelle ab, bricht das Skript mit Ansage ab.
KOPFZEILE = 8
SPALTEN = {
    "kategorie": "Category",
    "name": "Name of medicine",
    "nummer": "EMA product number",
    "status": "Medicine status",
    "gutachten": "Opinion status",
    "inn": "International non-proprietary name (INN) / common name",
    "wirkstoff": "Active substance",
    "gebiet": "Therapeutic area (MeSH)",
    "atc": "ATC code (human)",
    "indikation": "Therapeutic indication",
    "beschleunigt": "Accelerated assessment",
    "bedingt": "Conditional approval",
    "orphan": "Orphan medicine",
    "prime": "PRIME: priority medicine",
    "inhaber": "Marketing authorisation developer / applicant / holder",
    "beschluss": "European Commission decision date",
    "gutachten_am": "Opinion adopted date",
    "zulassung_am": "Marketing authorisation date",
    "url": "Medicine URL",
}

# Wie weit zurueck eine Zulassung als "neu" gilt. 180 Tage, nicht 90: Bei 12
# Zulassungen im Quartal waere ein Hub mit zwei Treffern sonst die Regel, und
# eine Rubrik, die meistens leer ist, liest niemand mehr. Abgelaufen ist hier
# nichts - anders als bei einer Ausschreibung bleibt eine Zulassung gueltig.
FENSTER_TAGE = 180

# Das Modell schreibt nur den deutschen Satz - eine Uebersetzungs- und
# Kuerzungsaufgabe, keine Abwaegung. Dafuer genuegt das kleine Modell; der
# Ausschreibungsradar braucht Sonnet, weil er entscheiden muss, nicht
# formulieren. Dieselbe Wahl wie bei den Studienzusammenfassungen.
MODELL = "claude-haiku-4-5"

VERSUCHE = 3
PAUSE = 3


def hol(url: str) -> bytes:
    """Wie im Ausschreibungsradar: abgerissene Verbindungen wiederholen,
    abgelehnte Zugriffe nicht - ein 403 wird beim zweiten Mal nicht besser."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    letzter: Exception | None = None
    for versuch in range(VERSUCHE):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError) as fehler:
            if isinstance(fehler, urllib.error.HTTPError):
                raise
            letzter = fehler
            if versuch < VERSUCHE - 1:
                time.sleep(PAUSE)
    raise letzter if letzter else RuntimeError(f"{url} nicht erreichbar")


def datum(wert) -> dt.date | None:
    """TT/MM/JJJJ als Text - siehe Falle 1 im Kopf dieser Datei."""
    if isinstance(wert, dt.datetime):
        return wert.date()
    if isinstance(wert, dt.date):
        return wert
    if isinstance(wert, str):
        for form in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(wert.strip(), form).date()
            except ValueError:
                pass
    return None


def ja(wert) -> bool:
    return str(wert).strip().lower() in ("yes", "true", "ja")


def tabelle_lesen(roh: bytes) -> list[dict]:
    """Die XLSX in Zeilen mit benannten Feldern.

    Die Spalten werden ueber ihre **Ueberschrift** gefunden, nicht ueber ihre
    Nummer. Die EMA hat am 22.10.2026 in der Kopfzeile 1.024 Spalten gefuehrt,
    von denen nur 39 beschriftet sind - eine feste Nummer waere beim naechsten
    Umbau still falsch.
    """
    ws = openpyxl.load_workbook(io.BytesIO(roh), read_only=True, data_only=True).active
    zeilen = list(ws.iter_rows(values_only=True))
    kopf = [str(c).replace("\n", " ").strip() if c else "" for c in zeilen[KOPFZEILE]]
    stelle = {}
    for schluessel, titel in SPALTEN.items():
        passend = [i for i, k in enumerate(kopf) if k.lower() == titel.lower()]
        if not passend:
            raise SystemExit(
                f"Spalte '{titel}' steht nicht in der EMA-Tabelle. "
                "Der Aufbau hat sich geaendert - SPALTEN nachziehen, "
                "nicht die Pruefung entfernen.")
        stelle[schluessel] = passend[0]
    satz = []
    for z in zeilen[KOPFZEILE + 1:]:
        if not z or not any(z):
            continue
        satz.append({k: (z[i] if i < len(z) else None) for k, i in stelle.items()})
    return satz


def eintrag_bauen(z: dict, stufe: str, am: dt.date, hubs: list[str]) -> dict:
    kennzeichen = [name for name, feld in (
        ("Orphan Drug", "orphan"), ("PRIME", "prime"),
        ("bedingte Zulassung", "bedingt"), ("beschleunigt", "beschleunigt"),
    ) if ja(z[feld])]
    return {
        "stufe": stufe,
        "datum": am.isoformat(),
        "name": str(z["name"] or "").strip(),
        "wirkstoff": str(z["wirkstoff"] or z["inn"] or "").strip(),
        "gebiet_mesh": str(z["gebiet"] or "").replace("\n", "; ").strip(),
        "atc": str(z["atc"] or "").strip(),
        "inhaber": str(z["inhaber"] or "").strip(),
        "kennzeichen": kennzeichen,
        "gutachten": str(z["gutachten"] or "").strip(),
        "nummer": str(z["nummer"] or "").strip(),
        "url": str(z["url"] or "").strip(),
        "indikation_en": " ".join(str(z["indikation"] or "").split())[:1200],
        "hubs": hubs,
        "satz": "",
    }


def sammeln(satz: list[dict], heute: dt.date,
            warnungen: list[str]) -> tuple[list[dict], dict]:
    """Die beiden Stufen aus der Tabelle holen und den Hubs zuordnen."""
    seit = heute - dt.timedelta(days=FENSTER_TAGE)
    eintraege: list[dict] = []
    ohne_hub = 0
    zahlen = {"zulassung": 0, "gutachten": 0}

    for z in satz:
        if str(z["kategorie"]).strip().lower() != "human":
            continue  # Tierarzneimittel gehoeren in keinen der Hubs
        hubs = themen.hubs_fuer(z["gebiet"])

        # --- Stufe 2 zuerst: Was im Gutachtenstand steht, ist noch nicht
        # zugelassen und kann deshalb nicht auch Stufe 1 sein.
        if str(z["status"]).strip() == "Opinion":
            am = datum(z["gutachten_am"])
            if am:
                zahlen["gutachten"] += 1
                if hubs:
                    eintraege.append(eintrag_bauen(z, "gutachten", am, hubs))
                else:
                    ohne_hub += 1
            continue

        # --- Stufe 1: Erstzulassung im Fenster. NICHT der Kommissionsbeschluss,
        # siehe Falle 2 im Kopf dieser Datei.
        am = datum(z["zulassung_am"])
        if am and am >= seit:
            zahlen["zulassung"] += 1
            if hubs:
                eintraege.append(eintrag_bauen(z, "zulassung", am, hubs))
            else:
                ohne_hub += 1

    if ohne_hub:
        # Keine Warnung, sondern eine Zahl: Dass etwas in keinen Hub passt, ist
        # der Normalfall - HIV, Haemophilie und Diagnostika haben hier kein
        # Gebiet. Auffaellig waere erst, wenn der Anteil springt.
        zahlen["ohne_hub"] = ohne_hub
    gesamt = zahlen["zulassung"] + zahlen["gutachten"]
    if gesamt and ohne_hub / gesamt > 0.6:
        warnungen.append(
            f"{ohne_hub} von {gesamt} Eintraegen ohne Hub ({100*ohne_hub//gesamt} %) "
            "- sonst rund ein Drittel. Muster in zulassungen_themen.py pruefen.")
    eintraege.sort(key=lambda e: e["datum"], reverse=True)
    return eintraege, zahlen


def saetze_schreiben(eintraege: list[dict], alt: dict, warnungen: list[str]) -> int:
    """Ein deutscher Satz je Eintrag - einmal, dann aufbewahrt.

    Der Indikationstext der EMA ist englisch und oft zehn Zeilen lang. Ein
    englischer Absatz in einem deutschen Hub waere ein Bruch; die Hubs fassen
    seit jeher jede Studie auf Deutsch zusammen.

    **Aufbewahrt wird ueber die EMA-Produktnummer.** Ein Mittel wird damit
    genau einmal uebersetzt, auch wenn es ein halbes Jahr im Fenster steht.
    Ohne das kostete jeder Lauf erneut, und zwei Laeufe lieferten zwei
    verschiedene Formulierungen fuer dasselbe Mittel.
    """
    bekannt = {e.get("nummer"): e.get("satz", "")
               for e in alt.get("eintraege", []) if e.get("satz")}
    offen = [e for e in eintraege if not bekannt.get(e["nummer"])]
    for e in eintraege:
        e["satz"] = bekannt.get(e["nummer"], "")
    if not offen:
        return 0

    schluessel = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not schluessel:
        warnungen.append("ANTHROPIC_API_KEY nicht gesetzt - Eintraege ohne deutschen Satz")
        return 0
    import anthropic
    client = anthropic.Anthropic(api_key=schluessel)

    geschrieben = 0
    for e in offen:
        # **Der Stand muss im Satz stehen.** Im ersten Lauf am 22.10.2026 hiess
        # es auch bei Gutachten "ist zugelassen" - und das ist genau falsch:
        # Ein Gutachten ist die Empfehlung des Ausschusses, die Kommission hat
        # noch nicht entschieden. Der Vorsprung von zwei Monaten ist der Zweck
        # dieses Radars; ihn mit einer falschen Behauptung zu erkaufen, waere
        # schlimmer als gar kein Radar.
        if e["stufe"] == "gutachten":
            lage = ("Der Ausschuss fuer Humanarzneimittel (CHMP) der EMA hat "
                    "EMPFOHLEN, dieses Mittel zuzulassen. Es ist NOCH NICHT "
                    "zugelassen - die EU-Kommission entscheidet erst.")
            vorgabe = ("Der Satz muss diesen Stand wiedergeben, etwa: "
                       "'Der CHMP empfiehlt die Zulassung von X zur Behandlung "
                       "von ...'. Schreibe NICHT 'ist zugelassen'.")
        else:
            lage = "Dieses Mittel ist in der EU zugelassen."
            vorgabe = "Der Satz sagt, wogegen das Mittel zugelassen ist und bei wem."
        auftrag = (
            f"{lage}\n\n"
            f"Mittel: {e['name']}\nWirkstoff: {e['wirkstoff']}\n"
            f"Indikation (englisch, Originaltext der EMA): {e['indikation_en']}\n\n"
            f"{vorgabe}\n\n"
            "Regeln:\n"
            "- Hoechstens 35 Woerter, ein einziger Satz.\n"
            "- **Nenne den Wirkstoff**, in Klammern hinter dem Handelsnamen. "
            "Der Handelsname allein genuegt nicht: Fachleser erkennen das "
            "Mittel am Wirkstoff, und bei einer Kombination sagt erst er, was "
            "drin ist. Bei mehreren Wirkstoffen genuegt der fuehrende.\n"
            "- Fachsprache des deutschen Gesundheitswesens, keine Werbesprache.\n"
            "- Keine Wertung und keine Einordnung: kein 'erstmals', kein "
            "'vielversprechend', kein 'wichtiger Fortschritt'.\n"
            "- **Uebersetze die Krankheitsbezeichnung genau.** 'adenocarcinoma' "
            "ist ein Adenokarzinom, kein Adenom; 'carcinoma' ist kein Karzinoid. "
            "Bist du dir bei einem Begriff nicht sicher, nimm den englischen "
            "Originalbegriff in Klammern dazu.\n"
            "- Keine Angaben erfinden: Steht die Altersgruppe nicht in der "
            "Indikation, nenne sie nicht.\n"
            "- Antworte mit dem Satz, sonst nichts.")
        try:
            antwort = client.messages.create(
                model=MODELL, max_tokens=300,
                messages=[{"role": "user", "content": auftrag}])
            teile = [t.text for t in antwort.content if getattr(t, "type", "") == "text"]
            satz = " ".join(" ".join(teile).split())
            if not satz:
                warnungen.append(f"{e['name']}: leere Antwort ({antwort.stop_reason})")
                continue
            e["satz"] = satz
            geschrieben += 1
        except Exception as fehler:          # noqa: BLE001
            warnungen.append(f"{e['name']}: Satz fehlgeschlagen - {str(fehler)[:90]}")
    return geschrieben


def pruefen(eintraege: list[dict], warnungen: list[str]) -> tuple[int, int]:
    """Torwaechter fuer die deutschen Saetze - nach dem Vorbild aus dem Versand.

    Zwei Pruefungen, beide aus Fehlern vom 22.10.2026 entstanden:

    **1. Ein Gutachten darf nicht behaupten, das Mittel sei zugelassen.**
    Im ersten Lauf stand bei allen 18 Gutachten "ist zugelassen", weil mein
    Auftrag ans Modell nicht zwischen den Stufen unterschied. Das ist der
    gefaehrlichste Fehler dieses Radars: Sein ganzer Zweck ist der Vorsprung
    von zwei Monaten vor der Zulassung - erkauft man ihn mit der falschen
    Behauptung, es sei schon zugelassen, ist er nichts mehr wert.

    **2. Der Wirkstoff muss im Satz vorkommen.** Faengt die Verwechslung
    zweier Mittel - der Fall, den ein Leser nicht nachpruefen kann, weil der
    Satz in sich stimmig klingt.

    Was durchfaellt, verliert seinen Satz, nicht seinen Eintrag: Das
    Therapiegebiet bleibt stehen, nur die Formulierung entfaellt. Faellt mehr
    als ein Drittel durch, stimmt etwas Grundsaetzliches nicht - dann schreibt
    der Lauf gar nichts, wie es der Torwaechter beim Newsletter haelt.
    """
    raus = 0
    geprueft = [e for e in eintraege if e["satz"]]
    for e in geprueft:
        satz = e["satz"]
        klein = satz.lower()
        grund = ""

        if e["stufe"] == "gutachten":
            # "empfiehlt die Zulassung" ist richtig und enthaelt das Substantiv
            # "Zulassung"; das **Partizip** "zugelassen" hat in einem
            # Gutachtensatz dagegen nichts zu suchen - es behauptet den
            # Zustand, der noch nicht eingetreten ist.
            #
            # Eine Liste fester Wendungen ("ist zugelassen", "wurde zugelassen")
            # reichte nicht: Im Gegentest vom 22.10.2026 lautete der falsche
            # Satz "ist zur Behandlung des Pankreasadenokarzinoms zugelassen"
            # und kam durch keine davon. Geprueft wird deshalb auf das Partizip
            # selbst. Der Preis ist ein seltener Fehlalarm - "...die bereits mit
            # einem zugelassenen Mittel behandelt wurden" faellt mit durch. Das
            # ist die richtige Richtung: Der Eintrag verliert dann seinen Satz,
            # nicht der Leser die Wahrheit.
            behauptet = "zugelassen" in klein
            empfiehlt = any(w in klein for w in ("empfiehlt", "empfohlen", "chmp"))
            if behauptet or not empfiehlt:
                grund = ("Gutachten, aber der Satz "
                         + ("behauptet eine Zulassung" if behauptet
                            else "nennt die Empfehlung nicht"))

        if not grund:
            # Der Wirkstoff steht in der Tabelle in mehreren Gestalten: mit
            # Salzzusatz ("Orforglipron hemicalcium"), als Kombination mit
            # Semikolon ("levodopa;carbidopa") und als Impfstoffbezeichnung mit
            # Schraegstrichen ("A/(H1N1)"). Am 22.10.2026 hat die erste Fassung
            # dieser Pruefung daran siebzehn einwandfreie Saetze aussortiert,
            # weil sie nur am Leerzeichen trennte und dann "ezetimibe;obicetrapib"
            # als einen Begriff suchte.
            #
            # Genommen wird deshalb der erste Wortbestandteil **jedes**
            # Wirkstoffs, und es genuegt, wenn EINER davon im Satz steht: Bei
            # einer Kombination nennt der Satz oft nur den fuehrenden Stoff.
            teile = re.split(r"[;,/()]+", str(e["wirkstoff"]))
            staemme = [t.replace("-", " ").split()[0].lower()
                       for t in teile if t.replace("-", " ").split()]
            staemme = [s for s in staemme if len(s) >= 5]
            # **Der deutsche INN laesst das End-e weg**: Temozolomid,
            # Liraglutid, Furosemid, Teriparatid - die EMA-Tabelle fuehrt sie
            # englisch mit -e. Am 22.10.2026 sind daran vier einwandfreie
            # Saetze gescheitert, und zwar genau die, in denen das Modell
            # richtig eingedeutscht hatte. Geprueft wird deshalb gegen beide
            # Endungen; "ranibizumab" und andere ohne End-e beruehrt das nicht.
            if staemme:
                haystack = klein.replace("-", " ")
                gesucht = {s for s in staemme} | {s[:-1] for s in staemme
                                                  if s.endswith("e") and len(s) > 5}
                if not any(s in haystack for s in gesucht):
                    grund = (f"Wirkstoff '{'/'.join(staemme[:2])}' "
                             "kommt im Satz nicht vor")

        if grund:
            warnungen.append(f"{e['name']}: {grund} - Satz entfernt")
            e["satz"] = ""
            raus += 1
    return raus, len(geprueft)


def js(wert) -> str:
    """Text als JS-Literal. Ein einfaches Anfuehrungszeichen oder ein
    Zeilenumbruch zerlegte das inline-JS der Seite - dieselbe Falle wie beim
    STUDIES-Block und beim Radar."""
    return json.dumps(wert if wert is not None else "", ensure_ascii=False)


def block(eintraege: list[dict], stand: str) -> str:
    """Der Marker-Block fuer zulassungen.html, nach Hubs gegliedert.

    **Auch leere Gebiete stehen drin.** Die Seite zeigt alle sieben Rubriken,
    damit ein Anker nie ins Leere fuehrt und der Leser sieht, dass zu seinem
    Gebiet gesucht wurde - dieselbe Entscheidung wie beim Ausschreibungsradar.

    Ein Eintrag kann in mehreren Rubriken stehen (Orforglipron in Diabetes und
    Adipositas). Das ist kein Doppel, sondern der Zweck: Wer im Diabetes-Hub
    liest, soll ihn dort finden, ohne den Adipositas-Hub zu kennen.
    """
    zeilen = [BLOCK_START, f'const ZUL_STAND = "{stand}";', "const ZULASSUNGEN = ["]
    for slug in themen.REGELN:
        meine = [e for e in eintraege if slug in e["hubs"]]
        zeilen.append("  {slug:%s, name:%s, domain:%s, eintraege:[" %
                      (js(slug), js(themen.name_von(slug)), js(HUB_DOMAIN.get(slug, ""))))
        for e in meine:
            zeilen.append(
                "    {stufe:%s, datum:%s, name:%s, wirkstoff:%s, satz:%s, "
                "gebiet_mesh:%s, atc:%s, inhaber:%s, kennzeichen:%s, url:%s}," %
                (js(e["stufe"]), js(e["datum"]), js(e["name"]), js(e["wirkstoff"]),
                 js(e["satz"]), js(e["gebiet_mesh"]), js(e["atc"]), js(e["inhaber"]),
                 json.dumps(e["kennzeichen"], ensure_ascii=False), js(e["url"])))
        zeilen.append("  ]},")
    zeilen += ["];", BLOCK_ENDE]
    return "\n".join(zeilen)


def seite_schreiben(eintraege: list[dict], stand: str,
                    warnungen: list[str]) -> bool:
    """Den Block in zulassungen.html ersetzen - nur ihn, nichts sonst."""
    if not SEITE.exists():
        warnungen.append(f"{SEITE.name} fehlt - Block nicht geschrieben")
        return False
    text = SEITE.read_text(encoding="utf-8")
    muster = re.compile(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_ENDE), re.S)
    if not muster.search(text):
        warnungen.append(
            f"Marker in {SEITE.name} nicht gefunden - Block nicht geschrieben. "
            "Die Marker duerfen nicht veraendert werden, der Lauf sucht sie woertlich.")
        return False
    # Die Ersetzung als Funktion, nicht als Zeichenkette: Ein Rueckverweis wie
    # \1 im Block wuerde sonst als Gruppenbezug gelesen und still Text fressen.
    SEITE.write_text(muster.sub(lambda _: block(eintraege, stand), text),
                     encoding="utf-8")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="Zulassungsradar (EMA)")
    p.add_argument("--probe", action="store_true", help="zeigen, nichts schreiben")
    p.add_argument("--roh", action="store_true", help="ohne Modell, nur Rohdaten")
    a = p.parse_args()

    heute = dt.date.today()
    warnungen: list[str] = []

    print(f"Hole die EMA-Tabelle ({EMA_URL.rsplit('/', 1)[1]}) ...")
    roh = hol(EMA_URL)
    satz = tabelle_lesen(roh)
    print(f"  {len(satz)} Zeilen, davon "
          f"{sum(1 for z in satz if str(z['kategorie']).strip().lower() == 'human')} "
          "Humanarzneimittel.")

    eintraege, zahlen = sammeln(satz, heute, warnungen)
    zul = [e for e in eintraege if e["stufe"] == "zulassung"]
    gut = [e for e in eintraege if e["stufe"] == "gutachten"]
    print(f"\nStufe 1 - Zulassungen der letzten {FENSTER_TAGE} Tage: "
          f"{zahlen['zulassung']}, davon einem Hub zugeordnet {len(zul)}")
    print(f"Stufe 2 - CHMP-Gutachten ohne Beschluss: "
          f"{zahlen['gutachten']}, davon einem Hub zugeordnet {len(gut)}")

    je_hub: dict[str, int] = {}
    for e in eintraege:
        for h in e["hubs"]:
            je_hub[h] = je_hub.get(h, 0) + 1
    print("\nJe Hub:")
    for h, n in sorted(je_hub.items(), key=lambda x: -x[1]):
        print(f"  {themen.name_von(h):<32} {n}")

    alt = {}
    if ZIEL.exists():
        try:
            alt = json.loads(ZIEL.read_text(encoding="utf-8"))
        except ValueError:
            warnungen.append(f"{ZIEL.name} war nicht lesbar - Saetze werden neu geschrieben")

    if not a.roh:
        neu = saetze_schreiben(eintraege, alt, warnungen)
        print(f"\nDeutsche Saetze: {neu} neu geschrieben, "
              f"{sum(1 for e in eintraege if e['satz']) - neu} uebernommen.")
        raus, geprueft = pruefen(eintraege, warnungen)
        print(f"Torwaechter: {geprueft - raus} von {geprueft} Saetzen durch, "
              f"{raus} entfernt.")
        # Dieselbe Schwelle wie die Vorpruefung des Newsletter-Torwaechters:
        # Ein einzelner missglueckter Satz soll die Ausgabe nicht aufhalten,
        # ein Drittel schon - dann liegt es nicht am Einzelfall.
        if geprueft and raus / geprueft > 1 / 3:
            print(f"\nMehr als ein Drittel der Saetze faellt durch "
                  f"({raus} von {geprueft}). Es wird nichts geschrieben - "
                  "das liegt nicht am Einzelfall, sondern am Auftrag ans Modell "
                  "oder an der Quelle.")
            for w in warnungen:
                print("  ! " + w)
            return 1

    if a.probe or a.roh:
        print("\n--- Vorschau ---")
        for e in eintraege[:12]:
            marke = "GUTACHTEN" if e["stufe"] == "gutachten" else "ZULASSUNG"
            kenn = (" [" + ", ".join(e["kennzeichen"]) + "]") if e["kennzeichen"] else ""
            print(f"\n  {e['datum']}  {marke}  {e['name']} ({e['wirkstoff']}){kenn}")
            print(f"    Hubs: {', '.join(themen.name_von(h) for h in e['hubs'])}")
            print(f"    {e['satz'] or '(' + e['gebiet_mesh'][:70] + ')'}")

    for w in warnungen:
        print("  ! " + w)

    if a.probe or a.roh:
        print("\nProbelauf - nichts geschrieben.")
        return 0

    ZIEL.write_text(json.dumps({
        "stand": heute.strftime("%d.%m.%Y"),
        "quelle": "European Medicines Agency",
        "fenster_tage": FENSTER_TAGE,
        "zahlen": zahlen,
        "warnungen": warnungen,
        "eintraege": eintraege,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{ZIEL.name} geschrieben ({len(eintraege)} Eintraege).")

    if seite_schreiben(eintraege, heute.strftime("%d.%m.%Y"), warnungen):
        print(f"{SEITE.name}: Block ersetzt.")
    return 1 if warnungen else 0


if __name__ == "__main__":
    raise SystemExit(main())
