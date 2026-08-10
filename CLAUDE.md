# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projekt

„Knowledge-Hub Versorgungsforschung" — ein Rechercheportal für Versorgungsforschung / Health Services Research. Ein Angebot von **Monitor Versorgungsforschung** (Betreiber: eRelation AG – Content in Health, Bonn).

Live: https://mvf-portal.github.io/versorgungsforschung-portal/

Projektsprache ist **Deutsch** — Oberfläche, Inhalte, Commit-Messages und Code-Kommentare.

## Kein Build, kein Test, kein Framework

`index.html` ist eine vollständig eigenständige Datei (CSS + HTML + JS inline). Es gibt **kein** npm/package.json, keinen Build-Schritt, keinen Linter und keine Testsuite — entsprechend gibt es auch keine Build-/Test-Kommandos.

| Aufgabe | Vorgehen |
|---|---|
| Lokal ansehen | `index.html` direkt im Browser öffnen (kein Server nötig) |
| Deployen | Commit auf `main` pushen — GitHub Pages baut automatisch (~1 Min) |
| Live prüfen | `curl -s "https://mvf-portal.github.io/versorgungsforschung-portal/?cb=$(date +%s)"` — Cache-Buster nötig, sonst kommt die alte Fassung |
| Pages-Build-Status | `gh api repos/mvf-portal/versorgungsforschung-portal/pages/builds/latest` |

`gh` liegt unter `C:\Program Files\GitHub CLI\gh.exe` (nicht im PATH) und ist als `mvf-portal` angemeldet. Das Token hat **keinen `workflow`-Scope** — Dateien unter `.github/workflows/` lassen sich damit nicht pushen.

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
// === STUDIES-BLOCK-START (wird woechentlich vom Cloud-Agenten ersetzt) ===
const SNAP_DATE = "…";
const STUDIES = [ … ];
// === STUDIES-BLOCK-ENDE ===
```

Studien-Updates ersetzen **ausschließlich** diesen Bereich (beide Marker-Zeilen bleiben stehen). Alles andere — CSS, `DB`, `CATS`, Footer, Impressum — bleibt unangetastet. `SNAP_DATE` erscheint sichtbar als „Zuletzt aktualisiert" und muss bei jedem Update auf den aktuellen Zeitpunkt gesetzt werden (Format `"TT. Mon. JJJJ, HH:MM Uhr"`, deutsche Monatsabkürzung).

### Studien aktualisieren

Der vorgesehene Weg ist der Slash-Command **`/studien-update`** (liegt unter `~/.claude/commands/studien-update.md`): PubMed E-utilities abrufen → 6 Studien mit konkreten quantitativen Ergebnissen auswählen → deutsche Zusammenfassungen schreiben → Marker-Block ersetzen → committen und pushen. Kein API-Key, kein Skript.

Die Dateien unter `scripts/` (`update_studies.py`, `update-studies.ps1`, `Studien-aktualisieren.cmd`) sind eine **ungenutzte Alternative**, die einen `ANTHROPIC_API_KEY` erwartet. Der Nutzer hat sich bewusst gegen den API-Weg entschieden — nicht als Standardpfad vorschlagen.

## Fallstricke

- **Kein HTML-Escaping.** Alle Inhalte werden per `innerHTML`-Stringkonkatenation eingesetzt. Texte mit `<`, `>` oder `&` zerlegen das Markup — beim Anlegen von `DB`- oder `STUDIES`-Einträgen vermeiden bzw. maskieren.
- **Keine geraden doppelten Anführungszeichen in `STUDIES`-Strings** — die Objekte stehen in inline-JS; ein `"` bricht das Skript und die Seite bleibt leer. Notfalls „…" oder Klammern verwenden.
- **Deutsches Zahlenformat** in Studientexten (`0,63` statt `0.63`).
- **Impressum und Datenschutzhinweise im Footer sind rechtlich erforderlich** (§ 5 DDG, § 18 Abs. 2 MStV) und inhaltlich mit dem Betreiber abgestimmt — nicht beiläufig umformulieren. Die Datenschutzhinweise beschreiben bewusst eine statische Seite ohne Cookies/Tracking; das muss stimmen, wenn Skripte hinzukommen.
- **Ein Fehler bricht die ganze Seite.** Da das gesamte JS inline in einem `<script>`-Block liegt, macht ein Syntaxfehler die Seite komplett leer (Kacheln *und* Studien werden per JS erzeugt). Nach Änderungen am Skriptteil immer die Live-Seite prüfen.
- **Dark Mode.** Farben laufen über CSS-Variablen mit drei Quellen: `prefers-color-scheme`, `:root[data-theme="dark"]` und `:root[data-theme="light"]`. Neue Farbwerte in allen relevanten Blöcken ergänzen, nicht nur im Light-Default.
