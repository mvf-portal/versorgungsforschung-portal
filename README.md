# Versorgungsforschung · Rechercheportal

Ein Rechercheportal zur **Versorgungsforschung / Health Services Research**: gebündelte Live-Suchen
über alle wichtigen Datenbanken (deutsch + international) plus ein rechtes Frame mit den **neuesten
Studien** samt **deutscher Zusammenfassung**.

Die Seite ist eine einzelne, eigenständige `index.html` (kein Build, keine Abhängigkeiten) und wird
über **GitHub Pages** ausgeliefert.

## Live-URL

Nach dem Aktivieren von GitHub Pages (siehe unten):

```
https://<DEIN-GITHUB-NAME>.github.io/versorgungsforschung-portal/
```

Diese URL ist stabil und ändert sich nicht.

## Automatische Wochen-Aktualisierung

Ein geplanter Cloud-Agent (Claude Code Routine) läuft **jeden Montagmorgen** und:

1. holt die neuesten Studien aus PubMed (E-utilities, nach Datum sortiert),
2. wählt 5–7 relevante Studien mit konkreten Ergebnissen aus,
3. schreibt deutsche Zusammenfassungen,
4. ersetzt in `index.html` **nur** den Block zwischen den Markern
   `// === STUDIES-BLOCK-START ...` und `// === STUDIES-BLOCK-ENDE ===`
   (die Konstanten `SNAP_DATE` und `STUDIES`),
5. committet und pusht die Änderung — GitHub Pages veröffentlicht sie automatisch.

Der Rest der Datei (Datenbank-Kacheln, Layout, Suchlogik) bleibt unangetastet.

## Einmalige Einrichtung

1. Neues **öffentliches** Repo `versorgungsforschung-portal` anlegen.
2. `index.html` und diese `README.md` hinein committen (Branch `main`).
3. **Settings → Pages →** Source: „Deploy from a branch", Branch `main`, Ordner `/ (root)` → Save.
4. Nach ~1 Minute ist die Live-URL erreichbar.
5. Danach wird die Claude-Routine auf dieses Repo umgestellt (übernimmt Claude).

## Struktur

- `index.html` — das komplette Portal (self-contained)
- Austausch-Marker im `<script>`: `STUDIES-BLOCK-START` / `STUDIES-BLOCK-ENDE`
