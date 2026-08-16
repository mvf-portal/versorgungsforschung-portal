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

## Studienfelder: `author`, `pubdate`, `added`

Alle drei stammen **nicht vom Sprachmodell**, sondern aus PubMeds `esummary` (`fetch_meta()` in `update_studies.py`) — es sind Fakten, keine Interpretation.

Beim Publikationsdatum wird die **genaueste echte** Angabe aus `pubdate` und `epubdate` genommen. `sortpubdate` ist bewusst ungenutzt: Bei reinen Monatsangaben setzt PubMed dort den 1. ein und täuscht damit einen Tag vor. Fehlt der Tag, steht `Aug. 2026` statt eines erfundenen Datums.

### Zwei Daten, die nicht verwechselt werden dürfen

| Feld | Bedeutung |
|---|---|
| `pubdate` | wann die Studie **erschienen** ist |
| `added` | wann **PubMed sie aufgenommen** hat (`history`, `pubstatus: entrez`) |

`esearch` wählt mit `sort=date` nach dem **Aufnahmedatum** aus — nicht nach dem Erscheinungsdatum. Beide liegen oft Wochen auseinander: Eine am 24.07. erschienene Arbeit kann erst am 14.08. in PubMed landen. Deshalb enthält eine Tagesauswahl regelmäßig ältere Publikationsdaten; das ist **kein Fehler**. Die Karte blendet `added` nur ein, wenn es von `pubdate` abweicht — sonst wäre es Rauschen.

Zum Sortieren dient `_sortschluessel()` (ISO-Datum aus den Rohfeldern), **nicht** der deutsche Anzeigetext. Sortiert wird in `main()`, nicht vom Modell: Aus einem Abstract lässt sich kein verlässliches Datum lesen, weshalb früher ältere Studien zwischen neueren standen.

## `SNAP_STATUS`: drei unterscheidbare Zustände

Die Seite soll nicht bloß „aktuell" behaupten, sondern sagen können, was zuletzt geschah:

| Zustand | Erkennung | Anzeige |
|---|---|---|
| normal | `SNAP_STATUS === "neu"` und Zeitstempel frisch | keine Meldung |
| Lauf ohne neue Studien | `SNAP_STATUS === "unveraendert"` | neutraler Hinweis |
| Lauf ausgefallen | `SNAP_DATE` älter als 30 Stunden | Warnhinweis |

`update_studies.py` setzt `SNAP_STATUS`, indem es die neuen PMIDs mit denen in der bestehenden `index.html` vergleicht. Den Ausfall erkennt die **Seite selbst** am Alter von `SNAP_DATE` — das funktioniert auch dann, wenn das Skript gar nicht erst lief. Die Auswertung ist gegen ein fehlendes `SNAP_STATUS` abgesichert (`typeof`), damit ältere Marker-Blöcke die Seite nicht brechen.

**Die Überschrift trägt bewusst kein Datum.** Um 06:00 Uhr hat der laufende Tag in PubMed praktisch nie schon Einträge — „Neu aufgenommen am [heute]" wäre fast täglich falsch, und das echte Datum stünde dauerhaft einen Tag zurück. Die Aktualität trägt stattdessen die Zeile „Zuletzt aktualisiert"; sie bezieht sich auf den Lauf und stimmt immer.

## Die Suche: nichts geschieht vor dem Absenden

Frueher schrieb die Seite die Links schon beim Tippen um — unsichtbar, ohne Rueckmeldung — und die Eingabetaste oeffnete ausgerechnet das MVF-Archiv, also eine von 56 Datenbanken. Beides ist abgeschafft.

| Aktion | Wirkung |
|---|---|
| Tippen | nichts; die Kacheln zeigen weiter auf die Startseiten |
| Enter, Knopf oder Schnellwahl-Chip | `suchen()`: Links vorbereiten, Ergebnisleiste einblenden, zur ersten **sichtbaren** Rubrik springen |
| Filter aendern | `zeigeErgebnis()`: nur die Zahlen nachfuehren |

**Die Trennung von `suchen()` und `zeigeErgebnis()` ist die Pointe.** Ruft `filtern()` am Ende `suchen()` auf, springt die Seite bei jedem Filterklick nach unten — mehrere Filter zu setzen wird dann unmoeglich. Gesprungen wird ausschliesslich beim Absenden.

### Filter

`FILTER` haelt vier Gruppen: `zugang`, `suchart`, `bool`, `rubrik` (Mehrfachauswahl als `Set`). `filtern()` blendet Kacheln aus, versteckt leere Rubriken samt Sprungmarke und fuehrt Zaehler, Plakette und Ruecksetz-Knopf nach.

**Vier Filter zusammen koennen alles ausblenden** — etwa „frei" + „Boolesch" + Rubrik „deutsch", denn keine deutsche Datenbank ist als boolesch belegt. Dafuer gibt es `#leerHinweis`; ohne ihn staende die Seite leer da.

### Boolesche Operatoren: `b` ist dreiwertig

| Wert | Bedeutung | Kennzeichen |
|---|---|---|
| `b:1` | geprueft, Operatoren wirken | `AND/OR ✓` |
| `b:0` | geprueft, wirken nicht | `AND/OR ✗` |
| fehlt | **ungeprueft** | keines |

Die Werte stammen aus einer Messreihe: dieselbe Suche mit `OR` und mit `AND`, verglichen mit einem Phantasiewort. Wertet eine Datenbank `OR` aus, steigt die Trefferzahl sprunghaft; wertet sie `AND` aus, faellt sie auf null. Belegt: 11 ja, 4 nein, 13 offen (Bot-Sperre oder reine JavaScript-Oberflaeche).

**Ungeprueftes zaehlt nie als „kann es".** Der Beschreibungstext sagt ausdruecklich, dass ein fehlendes Zeichen Unwissen bedeutet, nicht Unvermoegen — sonst wuerden Datenbanken wie Cochrane faelschlich festgelegt.

### Hinweise unter dem Suchfeld

Zweispaltig ueber **CSS-Textspalten** (`columns:2`), nicht ueber ein Raster. Ein Raster richtet Zeilen an der hoechsten Karte aus und streckte den kurzen Absatz, was knapp 50 px Loch hinterliess. Textspalten packen dicht. Unter 760 px einspaltig.

## Studienauswahl: kein Algorithmus, ein Prompt

Es gibt **keine Gewichtung und kein Ranking**. PubMed liefert Kandidaten, ein Sprachmodell waehlt daraus nach schriftlichen Kriterien aus. Wer die Auswahl aendern will, aendert `USER_TEMPLATE` in `update_studies.py` — nicht Code.

### Zwei Abfragen statt einer

`fetch_pubmed()` fragt zweimal: `TERM` (40 neueste) und `TERM_DE` (15 neueste mit `Germany[MeSH Terms] OR Germany[Affiliation]`), zusammengefuehrt und ueber die PMID entdoppelt.

**Warum:** Nur etwa 17 % der Neuaufnahmen haben Deutschlandbezug (gemessen 08/2026: 35 von 209). In dichten Wochen — 92 Neuaufnahmen in sieben Tagen — fielen deutsche Arbeiten aus dem 25er-Fenster, bevor das Modell sie sah. Mit der zweiten Abfrage steigt ihr Anteil im Pool von 22 auf 33 %.

**Ueber Journalnamen zu suchen bringt nichts** — deutschsprachige Fachjournale liefern in PubMed kaum Treffer (August 2026: genau einer). Nicht erneut versuchen.

### Uebertragbarkeit ist das oberste Kriterium

Der Prompt ordnet Systeme nach Vergleichbarkeit: hoch (DACH, Niederlande, Belgien, Frankreich — Sozialversicherung), mittel (Skandinavien, UK, Kanada, Australien — steuerfinanziert), gering (USA). **Massgeblich ist der Systemkontext, nicht die Autorenadresse.**

Jede Studie traegt das Feld `transfer`: ein Halbsatz, worauf die Uebertragbarkeit beruht. Es steht auf der Karte, im Archiv, in beiden Downloads und im Feed. Ohne dieses Feld waere das Kriterium unpruefbar — man muesste glauben, dass es wirkt.

Altbestand hat `transfer` nicht; die Anzeige laesst die Zeile dann weg.

## Suchglossar: deutsch suchen, international finden

`GLOSSAR` steht als Konstante **in** `index.html` (167 Begriffe, rund 9 KB) — nicht nachgeladen, weil es bei jeder Suche gebraucht wird. Die Pflegefassung mit Sachgebieten liegt als `_glossar.json` auf `entwurf/suche`.

Bewusst **kein Uebersetzungsdienst**: Ein Schluessel fuer DeepL oder Google muesste im Quelltext stehen und waere damit oeffentlich. Ein gepflegtes Verzeichnis ist ausserdem redaktionell kontrollierbar.

**Massgeblich ist der Suchbegriff, nicht die woertliche Uebersetzung:** `Nutzenbewertung` → `health technology assessment` (nicht *benefit assessment*), `Routinedaten` → `claims data`, `Wirksamkeit unter Alltagsbedingungen` → `effectiveness` (im Unterschied zu *efficacy*).

`uebersetze()` ersetzt wortweise, **laengste Begriffe zuerst** — sonst zerfaellt „integrierte Versorgung" in „Versorgung". Wortgrenzen ueber Leerzeichen und Komma statt ``, weil `` bei Umlauten und Bindestrichen falsch trennt.

`istDeutsch()` entscheidet, welche Datenbank den deutschen Begriff behaelt: Rubrik `deutsch` plus einzeln mit `de:1` gekennzeichnete Kataloge (Nationallizenzen, subito, K10plus, DRKS). Alle uebrigen bekommen die uebersetzte Fassung.

Sichtbar gemacht wird das in der Ergebnisleiste („In internationalen Datenbanken wird gesucht als …"); der Schalter `#uebersetzenAn` stellt es ab und wirkt sofort, ohne Sprung.

## Fallstricke

- **`const` vor seiner Definition benutzen legt die ganze Seite lahm.** Beim Einbau des Glossars stand `document.getElementById('cntGlossar').textContent = GLOSSAR.length;` vor der `const GLOSSAR`-Zeile. `const` wird zwar hochgezogen, ist davor aber nicht benutzbar — die Folge war ein `ReferenceError`, und weil das gesamte Skript in einem Block liegt, wurden **weder Kacheln noch Studien** gerendert. Nach Aenderungen am Skriptteil immer die Konsole pruefen.

- **Kein HTML-Escaping.** Alle Inhalte werden per `innerHTML`-Stringkonkatenation eingesetzt. Texte mit `<`, `>` oder `&` zerlegen das Markup — beim Anlegen von `DB`- oder `STUDIES`-Einträgen vermeiden bzw. maskieren.
- **Keine geraden doppelten Anführungszeichen in `STUDIES`-Strings** — die Objekte stehen in inline-JS; ein `"` bricht das Skript und die Seite bleibt leer. Notfalls „…" oder Klammern verwenden.
- **Deutsches Zahlenformat** in Studientexten (`0,63` statt `0.63`).
- **Impressum und Datenschutzhinweise im Footer sind rechtlich erforderlich** (§ 5 DDG, § 18 Abs. 2 MStV) und inhaltlich mit dem Betreiber abgestimmt — nicht beiläufig umformulieren. Die Datenschutzhinweise beschreiben bewusst eine statische Seite ohne Cookies/Tracking; das muss stimmen, wenn Skripte hinzukommen.
- **Ein Fehler bricht die ganze Seite.** Da das gesamte JS inline in einem `<script>`-Block liegt, macht ein Syntaxfehler die Seite komplett leer (Kacheln *und* Studien werden per JS erzeugt). Nach Änderungen am Skriptteil immer die Live-Seite prüfen.
- **Dark Mode.** Farben laufen über CSS-Variablen mit drei Quellen: `prefers-color-scheme`, `:root[data-theme="dark"]` und `:root[data-theme="light"]`. Neue Farbwerte in allen relevanten Blöcken ergänzen, nicht nur im Light-Default.
