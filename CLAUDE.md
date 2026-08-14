# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekt

„Knowledge-Hub Versorgungsforschung" — ein Rechercheportal für Versorgungsforschung / Health Services Research. Ein Angebot von **Monitor Versorgungsforschung** (Betreiber: eRelation AG – Content in Health, Bonn).

Live: https://wissen.m-vf.de/

Projektsprache ist **Deutsch** — Oberfläche, Inhalte, Commit-Messages und Code-Kommentare.

## Kein Build, kein Test, kein Framework

`index.html` ist eine vollständig eigenständige Datei (CSS + HTML + JS inline). Es gibt **kein** npm/package.json, keinen Build-Schritt, keinen Linter und keine Testsuite — entsprechend gibt es auch keine Build-/Test-Kommandos.

| Aufgabe | Vorgehen |
|---|---|
| Lokal ansehen | `index.html` direkt im Browser öffnen (kein Server nötig) |
| Deployen | Commit auf `main` pushen — GitHub Pages baut automatisch (~1 Min) |
| Live prüfen | `curl -s "https://wissen.m-vf.de/?cb=$(date +%s)"` — Cache-Buster nötig, sonst kommt die alte Fassung |
| Pages-Build-Status | `gh api repos/mvf-portal/versorgungsforschung-portal/pages/builds/latest` |

`gh` liegt unter `C:\Program Files\GitHub CLI\gh.exe` (nicht im PATH) und ist als `mvf-portal` angemeldet; Scopes: `repo`, `workflow`, `gist`, `read:org`.

Die Seite läuft unter der eigenen Domain **`wissen.m-vf.de`** (CNAME-Datei im Repo-Wurzelverzeichnis, HTTPS erzwungen). Die alte Adresse `mvf-portal.github.io/versorgungsforschung-portal/` leitet dauerhaft dorthin um.

## Architektur: datengetriebenes Rendering

Die Seite hat praktisch kein statisches Markup im Body — HTML-Shell plus vier JS-Konstanten, aus denen alles per DOM-Aufbau erzeugt wird:

| Konstante | Erzeugt | Wichtig |
|---|---|---|
| `CATS` | Kategorie-Sektionen + Sprungnavigation | Array-Reihenfolge = Anzeigereihenfolge. `h` ist ein **HSL-Farbton** (0–360), der als CSS-Variable `--h` die Akzentfarbe der Kategorie setzt. `num` ist nur Anzeigetext und muss bei Umsortierung mitgepflegt werden. |
| `DB` | Datenbank-Kacheln | `c` verweist auf `CATS[].id`; die Reihenfolge innerhalb einer Kategorie folgt der Array-Reihenfolge (`filter` erhält sie). |
| `STUDIES` + `SNAP_DATE` | Studien-Frame rechts | Liegt im Marker-Block (siehe unten) und wird maschinell ersetzt. |
| `CHIPS` | Schnellwahl-Buttons unter dem Suchfeld | Reine Strings; setzen das Suchfeld und lösen `apply()` aus. |

### Das `%s`-Mechanismus (Kern der Anwendung)

Jeder `DB`-Eintrag hat einen Typ `t`, der Badge **und** Link-Verhalten steuert:

- **`live`** — `u` enthält `%s`. `apply()` ersetzt `%s` bei jeder Eingabe durch den URL-kodierten Suchbegriff und schreibt den `href` aller Kacheln neu. Ohne Suchbegriff fällt der Link auf die Basis-URL zurück.
- **`portal`** — feste URL (Anbieter ohne Deeplink-Suche, z. B. LIVIVO, DRKS).
- **`lic`** — feste URL, kostenpflichtig/lizenziert (Scopus, Web of Science …).

Eine neue Datenbank mit Suchunterstützung aufzunehmen heißt also: einen `DB`-Eintrag mit `t:"live"` und `%s` in der URL anlegen — die Verdrahtung passiert automatisch über `cardIndex` und `apply()`.

### Marker-Block — die einzige maschinell editierte Stelle

```js
// === STUDIES-BLOCK-START (taeglich 06:00 Uhr von GitHub Actions ersetzt) ===
const SNAP_DATE = "…";
const STUDIES = [ … ];
// === STUDIES-BLOCK-ENDE ===
```

Studien-Updates ersetzen **ausschließlich** diesen Bereich (beide Marker-Zeilen bleiben stehen). Alles andere — CSS, `DB`, `CATS`, Footer, Impressum — bleibt unangetastet. `SNAP_DATE` erscheint sichtbar als „Zuletzt aktualisiert" und muss bei jedem Update auf den aktuellen Zeitpunkt gesetzt werden (Format `"TT. Mon. JJJJ, HH:MM Uhr"`, deutsche Monatsabkürzung).

### Archiv „Ältere Suchergebnisse"

`studien-archiv.json` im Wurzelverzeichnis ist die **vollständige Historie** aller je gezeigten Studien — ein flaches Array mit `pmid`, `journal`, `year`, `title`, `sum`, `result` und `aufgenommen` (ISO-Datum der ersten Sichtung). Dedupliziert über die PMID; das früheste Aufnahmedatum bleibt erhalten.

Die einzige Stelle, an der die Seite **nachlädt**: Der `<details>`-Ordner unter dem Studien-Frame holt die Datei per `fetch` — aber erst beim Aufklappen. Dadurch bleibt `index.html` schlank, während das Archiv beliebig wachsen darf. Beim Rendern werden die aktuell angezeigten PMIDs ausgeblendet, gruppiert wird nach `aufgenommen` (neueste zuerst).

`update_studies.py` schreibt die Datei bei jedem Lauf fort; der Workflow committet sie zusammen mit `index.html`.

### Newsletter-Feed & Download-Dateien

`scripts/build_newsletter.py` erzeugt aus `studien-archiv.json` fünf Dateien, die der Workflow mitcommittet:

| Datei | Zweck |
|---|---|
| `studien-feed.xml` | RSS 2.0 für Mailchimps RSS-to-Email. Ein `<item>` je Studie, **GUID = PMID** — dadurch versendet Mailchimp keine Studie doppelt. |
| `download/studien-aktuell.{docx,csv}` | nur der jüngste Tag |
| `download/studien-archiv.{docx,csv}` | der vollständige Bestand |

Das Skript liest **nur** das Archiv — kein API-Key, kein Netz. Es ist deshalb jederzeit einzeln aufrufbar (`py scripts/build_newsletter.py`, benötigt `python-docx`).

**Die Ausgabe ist bewusst deterministisch:** Alle Zeitstempel — `lastBuildDate`, der „Stand" im Word-Dokument, die Metadaten und sogar die ZIP-Einträge des docx (`normalize_docx()`) — werden aus dem Archivinhalt abgeleitet, nicht aus der Systemuhr. Zwei Läufe erzeugen bitgleiche Dateien. Ohne das entstünde täglich ein Commit samt Pages-Build, auch an Tagen ohne neue Studien. **Wer hier Zeitstempel einführt, bricht diese Eigenschaft.**

Das `pubDate` eines Items zieht den Rang sekundenweise **ab**: Mailchimp sortiert nach `pubDate`, die erste Studie der Tagesauswahl braucht also den spätesten Zeitstempel.

Einrichtung und Kampagnenvorlage: `NEWSLETTER-MAILCHIMP.md` und `newsletter/mailchimp-vorlage.html`. Die Vorlage ist Tabellen-Layout mit Inline-Styles — Outlook rendert mit der Word-Engine und kann kein modernes CSS. Sichtbarer Text dort **mit echten Umlauten** (die ASCII-Umschreibungen in den Python-Kommentaren sind eine Code-Konvention und gehören nicht in Lesertext).

### Studien aktualisieren

**Automatisch, täglich** — das ist der aktive Weg: `.github/workflows/update-studies.yml` läuft um 04:00 UTC — das sind 06:00 Uhr deutscher Sommerzeit, 05:00 Uhr Winterzeit — (und per *Run workflow* manuell), ruft `scripts/update_studies.py` auf → PubMed → Claude-API (`claude-haiku-4-5`, Secret `ANTHROPIC_API_KEY`) → Marker-Block ersetzen → commit & push. Einrichtung dokumentiert in `EINRICHTUNG-GITHUB-ACTIONS.md`.

**Manuell auf Zuruf** — der Slash-Command **`/studien-update`** (`~/.claude/commands/studien-update.md`): Claude recherchiert und formuliert selbst im Chat, ohne API-Key. Nützlich für Sonderfälle (anderer Suchbegriff, Zwischenstand), ersetzt aber nicht die Automatik.

`scripts/update-studies.ps1` und `scripts/Studien-aktualisieren.cmd` sind eine ältere lokale PowerShell-Variante und werden von der Automatik nicht verwendet.

## Gestaltung: das Erscheinungsbild von m-vf.de

Der Hub übernimmt seit August 2026 Schrift und Farben von **monitor-versorgungsforschung.de** (die Kurzadresse `m-vf.de` leitet dorthin um).

| Merkmal | Wert | Herkunft |
|---|---|---|
| Schrift | **Lato** 300/400/700 | dieselbe wie auf m-vf.de, dort ebenfalls selbst gehostet |
| Hausfarbe | `#0051A1` | Kopfbereich und Akzente der MVF-Seite |
| Handlungsfarbe | `#BE9E53` | die goldenen Knöpfe („Abonnieren", „Alle News") |
| Seitengrund | `#EDF2FA` | Flächenfarbe der MVF-Seite |
| Eckradien | 5–6 px | MVF nutzt 5–6 px |

Das Logo (`logo/mvf-logo.png`) besteht aus **genau zwei Farben**: Blau `#0060A0` und Gold `#C0A060` — es bestätigt die Palette.

**Regeln, die nicht beiläufig gebrochen werden sollten:**

- **Nur Lato.** Keine zweite Schriftfamilie. Die Klasse `.mono` erzeugt ihren technischen Charakter über `font-variant-numeric:tabular-nums`, nicht über eine Monospace-Schrift; `.serif` ist auf `inherit` gesetzt. MVF nutzt durchgängig Lato, auch in Überschriften.
- **Schriften liegen in `fonts/` und werden selbst ausgeliefert.** Kein Google Fonts: Das wäre ein Verbindungsaufbau zu Dritten und widerspräche den Datenschutzhinweisen. MVF macht es genauso.
- **Nur die Stärken 300/400/700 existieren.** Zwischenstärken wie 600 lässt der Browser auf 700 einrasten — deshalb überall direkt 700 setzen.
- **Gold nur auf Knöpfen.** Als kleine Textfarbe erreicht `#BE9E53` nur 3,0:1. Aus demselben Grund trägt die Knopfschrift auf Gold **dunkles** `#2A2207` (6,2:1) und nicht Weiß — die MVF-Seite selbst nutzt dort Weiß mit 2,6:1, das wird bewusst nicht übernommen.
- **Das Logo wird im Dark Mode nicht umgefärbt**, sondern auf eine weiße Fläche gestellt. Ein `filter:invert` würde den Goldanteil der Wortmarke tilgen.
- **Kategorien tragen alle die Hausfarbe.** Das `--h`-System in `CATS` besteht weiter, wird aber von `.cat{ --cat:var(--brand); }` überschrieben — ein Regenbogen widerspräche der Zweifarbigkeit. Eine Zeile genügt, um die Farbcodierung zurückzuholen.

## Studienfelder: `author` und `pubdate`

Beide stammen **nicht vom Sprachmodell**, sondern aus PubMeds `esummary` (`fetch_meta()` in `update_studies.py`) — es sind Fakten, keine Interpretation.

Beim Datum wird die **genaueste echte** Angabe aus `pubdate` und `epubdate` genommen. `sortpubdate` ist bewusst ungenutzt: Bei reinen Monatsangaben setzt PubMed dort den 1. ein und täuscht damit einen Tag vor. Fehlt der Tag, steht `Aug. 2026` statt eines erfundenen Datums.

## Fallstricke

- **Kein HTML-Escaping.** Alle Inhalte werden per `innerHTML`-Stringkonkatenation eingesetzt. Texte mit `<`, `>` oder `&` zerlegen das Markup — beim Anlegen von `DB`- oder `STUDIES`-Einträgen vermeiden bzw. maskieren.
- **Keine geraden doppelten Anführungszeichen in `STUDIES`-Strings** — die Objekte stehen in inline-JS; ein `"` bricht das Skript und die Seite bleibt leer. Notfalls „…" oder Klammern verwenden.
- **Deutsches Zahlenformat** in Studientexten (`0,63` statt `0.63`).
- **Impressum und Datenschutzhinweise im Footer sind rechtlich erforderlich** (§ 5 DDG, § 18 Abs. 2 MStV) und inhaltlich mit dem Betreiber abgestimmt — nicht beiläufig umformulieren. Die Datenschutzhinweise beschreiben bewusst eine statische Seite ohne Cookies/Tracking; das muss stimmen, wenn Skripte hinzukommen.
- **Ein Fehler bricht die ganze Seite.** Da das gesamte JS inline in einem `<script>`-Block liegt, macht ein Syntaxfehler die Seite komplett leer (Kacheln *und* Studien werden per JS erzeugt). Nach Änderungen am Skriptteil immer die Live-Seite prüfen.
- **Dark Mode.** Farben laufen über CSS-Variablen mit drei Quellen: `prefers-color-scheme`, `:root[data-theme="dark"]` und `:root[data-theme="light"]`. Neue Farbwerte in allen relevanten Blöcken ergänzen, nicht nur im Light-Default.
