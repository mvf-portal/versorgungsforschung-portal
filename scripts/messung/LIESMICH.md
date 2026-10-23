# Messskripte des Zulassungs-/DiGA-Radars

Hier liegen die Skripte, die **eine Frage beantworten, die wiederkommt**.
Sie gehören nicht in den nächtlichen Lauf und ändern nichts — sie messen.

Das Handbuch des Radars ist `portal-vorlage/ZULASSUNGSRADAR.md`; dort stehen
die Ergebnisse mit Datum. Hier steht nur, womit sie gemessen wurden.

## Was hier hingehört — und was nicht

| | |
|---|---|
| **Hierher** | Ein Skript, das eine Frage beantwortet, die beim nächsten Umbau wieder gestellt wird: „Woher kommt der Beipackzettel?", „Taugt die Zuordnung auf ungesehenen Daten?", „Was kostet der Modellweg?" |
| **Nicht hierher** | Ein Patch-Skript, das eine Datei einmal umbaut. Was es tat, steht danach in der Datei selbst; aufzubewahren wäre eine zweite Wahrheit. |

Am 22./23.10.2026 sind beim Bau des Radars rund 35 Skripte entstanden. Vier
davon waren Bauketten, dreizehn Messungen — der Rest war verbraucht.

## Die Skripte

### Zur FDA-Stufe

| Skript | Frage | Antwort am 22.10.2026 |
|---|---|---|
| `fda_quellen_vergleich.py` | Woher kommt der Beipackzettel? | DailyMed 25/32, openFDA 15/32 |
| `fda_texte_sichern.py` | — | holt die Indikationstexte einmal und legt sie ab, damit zwei Messungen dieselbe Grundgesamtheit haben |
| `fda_texte_pruefen.py` | Sind die ausgeschnittenen Texte wirklich Indikationen? | 25 echte, 0 unklar |
| `fda_zurueckgehalten.py` | Taugt die Zuordnung auf **ungesehenen** Daten? | 24/29, **0 falsch** |
| `fda_kosten.py` | Was kostet der Modellweg? | 0,04–1,49 USD im Jahr |
| `glossar_als_zuordnung.py` | Taugt das Hub-Glossar als Regel? | **nein**, 7 von 12 falsch |
| `diga_quelle_probe.py` | Ist das BfArM-PDF verlässlich lesbar? | ja, nach zwei Korrekturen |

### Zur Antragsstufe (Pipeline)

| Skript | Frage | Antwort am 22./23.10.2026 |
|---|---|---|
| `pipeline_quelle.py` | — | holt die monatliche EMA-Antragsliste (Modul, kein Lauf) |
| `pipeline_quellen.py` | Steht die Pipeline schon in Quellen, die wir haben? | nein — die EMA-Tabelle kennt keine laufenden Anträge |
| `pipeline_ema.py` | Was steht in der Antragsliste? | 12 Spalten, alle gefüllt, 92 Anträge |
| `pipeline_ema_vorsprung.py` | Wie viel Vorsprung? | 89 % sechs Monate vorher |
| `pipeline_ueberschneidung.py` | Wie viele sind in den USA schon zugelassen? | **10 von 57** |
| `pipeline_studien.py` | Liegen die Studien in den Hub-Archiven? | **nein**, 3 von 57 — und einer davon falsch |
| `pipeline_pubmed.py` | Liefert PubMed sie gezielt? | 14 von 20 |
| `pipeline_fehlerquote_hubs.py` | Wie viele Zuordnungen sind **falsch**? | 0 — 54 richtig, 3 fehlend |
| `pipeline_fehlerquote_studien.py` | Wie viele Studien gehören nicht dazu? | 86 % im Titel, 8 mit anderer Indikation |

### Zur Darstellung

| Skript | Frage |
|---|---|
| `kartentext_probe.py` | Liest sich der Text der Hinweiskarte in **allen** Zahlenkombinationen richtig? Holt die Logik aus `vorlage/index.html` und druckt alle zehn aus — eine abgeschriebene Fassung prüfte die Abschrift, nicht das Portal. |

Die Probe der Newsletter-Rubrik liegt nicht hier, sondern bei dem, was sie
prüft: `hub-scripts/rubrik_probe.py`.

## Zwei Regeln, die hier gelten

**Die Null ist wichtiger als die Quote.** Bei jeder Zuordnung wird getrennt
gezählt, was *falsch* und was *fehlend* ist. Ein fehlender Hub ist sichtbar —
der Eintrag steht dann nur unter „Alle". Eine falsche Zuordnung sieht aus wie
eine richtige.

**Eine Quote am eigenen Trainingsmaterial ist keine Messung.** Wer eine Regel
anfasst, hole mit `fda_zurueckgehalten.py --holen` oder
`pipeline_ema_vorsprung.py` ein **frisches** Fenster. Die Zahlen im Handbuch
sagen jeweils dazu, ob sie zurückgehalten waren.
