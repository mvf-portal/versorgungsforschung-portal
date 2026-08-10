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

## Lokales Update (Windows, empfohlen)

`scripts/update-studies.ps1` erledigt alles auf dem eigenen Rechner — keine GitHub Actions,
kein Repo-Secret, kein Python nötig (nur Windows PowerShell + git):

1. PubMed abrufen (E-utilities, nach Datum),
2. per Claude-API 6 Studien auswählen und auf Deutsch zusammenfassen,
3. Marker-Block in `index.html` ersetzen (inkl. Zeitstempel „Zuletzt aktualisiert"),
4. committen und pushen — GitHub Pages veröffentlicht automatisch.

**Einmalig:** Anthropic-API-Key als Umgebungsvariable hinterlegen (PowerShell, dauerhaft):

```powershell
[Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY','<DEIN-KEY>','User')
```

Danach PowerShell neu öffnen. **Ausführen:** `scripts\Studien-aktualisieren.cmd` doppelklicken, oder:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\update-studies.ps1
```

Modell: Standard `claude-haiku-4-5`; über die Umgebungsvariable `MODEL` änderbar.

**Täglich automatisch (Aufgabenplanung):**

```powershell
$exe = "powershell.exe"
$arg = '-NoProfile -ExecutionPolicy Bypass -File "<REPO-PFAD>\scripts\update-studies.ps1"'
schtasks /Create /TN "VF-Portal Studien-Update" /TR "$exe $arg" /SC DAILY /ST 08:00 /F
```

Bei Fehlern (PubMed nicht erreichbar, API-Fehler, Marker fehlt) bricht das Skript ab und
lässt `index.html` unverändert — es entsteht kein kaputter Commit.

## Alternative: tägliche Aktualisierung per GitHub Actions

Der Workflow `.github/workflows/update-studies.yml` läuft **täglich (06:00 UTC)** — und kann
über **Actions → „Studien-Update (täglich)" → Run workflow** jederzeit manuell gestartet werden.
Er:

1. holt die neuesten Studien aus PubMed (E-utilities, nach Datum sortiert),
2. wählt per Claude-API 6 relevante Studien mit konkreten Ergebnissen aus und
   schreibt deutsche Zusammenfassungen (`scripts/update_studies.py`),
3. ersetzt in `index.html` **nur** den Block zwischen den Markern
   `// === STUDIES-BLOCK-START ...` und `// === STUDIES-BLOCK-ENDE ===`
   (die Konstanten `SNAP_DATE` und `STUDIES`) inkl. Zeitstempel „Zuletzt aktualisiert",
4. committet und pusht die Änderung mit dem eingebauten `GITHUB_TOKEN` —
   GitHub Pages veröffentlicht sie automatisch.

Der Rest der Datei (Datenbank-Kacheln, Layout, Suchlogik, Impressum) bleibt unangetastet.

### Voraussetzung: API-Key als Repo-Secret

Der Workflow braucht einen Anthropic-API-Key. Einmalig anlegen:

**Settings → Secrets and variables → Actions → New repository secret**
- Name: `ANTHROPIC_API_KEY`
- Value: dein Anthropic-API-Key

Modellwahl: Der Workflow nutzt `claude-haiku-4-5` (günstig, für die Zusammenfassung ausreichend).
Ändern über die `MODEL:`-Zeile im Workflow bzw. das Standardmodell in `scripts/update_studies.py`.

## Einmalige Einrichtung

1. Öffentliches Repo `versorgungsforschung-portal` mit `index.html` + `README.md` (Branch `main`).
2. **Settings → Pages →** Source „Deploy from a branch", Branch `main`, Ordner `/ (root)` → Save.
3. `ANTHROPIC_API_KEY` als Repo-Secret hinterlegen (siehe oben).
4. Fertig — der Workflow aktualisiert die Studien ab dann täglich.

## Struktur

- `index.html` — das komplette Portal (self-contained)
- `scripts/update_studies.py` — Update-Skript (PubMed → Claude → index.html)
- `.github/workflows/update-studies.yml` — täglicher GitHub-Actions-Workflow
- Austausch-Marker im `<script>`: `STUDIES-BLOCK-START` / `STUDIES-BLOCK-ENDE`
