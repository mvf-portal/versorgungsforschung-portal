# Tägliche Aktualisierung per GitHub Actions einrichten

Diese Anleitung richtet die vollautomatische, tägliche Aktualisierung der Studienliste ein.
Danach läuft alles ohne dein Zutun: GitHub holt jeden Morgen die neuesten PubMed-Studien,
lässt sie von Claude auf Deutsch zusammenfassen, schreibt sie in `index.html` und
veröffentlicht sie über GitHub Pages.

**Zeitaufwand:** etwa 10 Minuten. **Voraussetzung:** ein Anthropic-API-Key.

---

## Was passiert später jeden Tag?

```
06:00 UTC  →  PubMed abfragen        (neueste Treffer zu "health services research")
           →  Claude auswählen        (6 Studien mit konkreten Ergebnissen, deutsche Texte)
           →  index.html aktualisieren (nur der Studien-Block + Zeitstempel)
           →  committen & pushen      (nur wenn sich wirklich etwas geändert hat)
           →  GitHub Pages baut       (~1 Minute später ist es live)
```

06:00 UTC entspricht **08:00 Uhr** deutscher Sommerzeit bzw. **07:00 Uhr** Winterzeit.
GitHub startet geplante Läufe bei hoher Auslastung mit einigen Minuten Verzögerung —
das ist normal und unkritisch.

---

## Schritt 1: Anthropic-API-Key besorgen

1. Auf https://console.anthropic.com anmelden.
2. **Settings → API keys → Create key**, Namen vergeben (z. B. `versorgungsforschung-portal`).
3. Den Key **sofort kopieren** — er wird nur ein einziges Mal angezeigt.

> Der Key beginnt mit `sk-ant-`. Behandle ihn wie ein Passwort: nicht in Dateien speichern,
> nicht in Chats posten, nicht committen. Im nächsten Schritt kommt er verschlüsselt zu GitHub.

**Kosten:** Der Workflow nutzt `claude-haiku-4-5`, das günstigste Modell. Pro Lauf werden
etwa 15.000–25.000 Eingabe-Tokens verarbeitet (die PubMed-Abstracts) und rund 2.000 Tokens
erzeugt. Das liegt im Bereich weniger Cent pro Tag. In der Console kannst du unter
**Settings → Limits** ein monatliches Ausgabenlimit setzen, falls du das absichern willst.

---

## Schritt 2: Key als Repository-Secret hinterlegen

1. Im Repo auf **Settings** (oben rechts im Repo-Menü, nicht im Konto-Menü).
2. Links im Menü: **Secrets and variables → Actions**.
3. Button **New repository secret**.
4. Ausfüllen:
   - **Name:** `ANTHROPIC_API_KEY` — exakt so, Großbuchstaben mit Unterstrichen
   - **Secret:** dein Key aus Schritt 1
5. **Add secret**.

Der Key ist danach nicht mehr lesbar, auch nicht für dich — er lässt sich nur ersetzen.
In den Logs der Actions-Läufe wird er automatisch durch `***` maskiert.

---

## Schritt 3: Workflow-Datei ins Repo bringen

Die Datei liegt lokal bereits unter `.github/workflows/update-studies.yml`.
Sie muss noch zu GitHub — dafür gibt es zwei Wege.

### Weg A — über die GitHub-Weboberfläche (kein Terminal nötig)

1. Im Repo auf **Add file → Create new file**.
2. Als Dateinamen exakt eintragen:
   ```
   .github/workflows/update-studies.yml
   ```
   Die Schrägstriche legen die Ordner automatisch an.
3. Den kompletten Inhalt der lokalen Datei
   `C:\Users\Stegmaier\Documents\versorgungsforschung-portal\.github\workflows\update-studies.yml`
   hineinkopieren.
4. Unten **Commit changes**.

### Weg B — per Kommandozeile

Das normale GitHub-Login reicht für Workflow-Dateien **nicht** aus; es braucht zusätzlich
die Berechtigung `workflow`. Einmalig freischalten:

```bash
gh auth refresh -h github.com -s workflow
```

Es öffnet sich der Browser zur Bestätigung. Danach:

```bash
cd C:\Users\Stegmaier\Documents\versorgungsforschung-portal
git add .github/workflows/update-studies.yml
git commit -m "Taeglicher Studien-Update-Workflow"
git push
```

---

## Schritt 4: Testlauf starten

Nicht bis zum nächsten Morgen warten — der Workflow lässt sich sofort manuell auslösen.

1. Im Repo auf den Reiter **Actions**.
2. Links **Studien-Update (täglich)** anklicken.
3. Rechts **Run workflow** → im Auswahlfeld `main` lassen → grüner Button **Run workflow**.
4. Nach ein paar Sekunden erscheint der Lauf in der Liste; anklicken und zusehen.

Alternativ per Kommandozeile:

```bash
gh workflow run "Studien-Update (täglich)" --repo mvf-portal/versorgungsforschung-portal
gh run watch --repo mvf-portal/versorgungsforschung-portal
```

**Erfolgreich sieht so aus:** alle Schritte mit grünem Haken, und im Schritt
*Studienliste aktualisieren* steht eine Zeile wie `index.html aktualisiert: 6 Studien.`

---

## Schritt 5: Ergebnis prüfen

1. **Commit:** Auf der Startseite des Repos sollte der jüngste Commit
   „Studien-Update TT.MM.JJJJ" von *VF-Portal Bot* stammen.
2. **Live-Seite:** https://mvf-portal.github.io/versorgungsforschung-portal/ öffnen und im
   rechten Frame den Eintrag „Zuletzt aktualisiert" prüfen.
   Falls noch der alte Stand erscheint: mit **Strg + F5** neu laden — der Browser hält die
   alte Fassung im Cache.

Damit ist die Einrichtung abgeschlossen. Ab jetzt läuft es täglich von selbst.

---

## Fehlersuche

GitHub schickt dir bei jedem fehlgeschlagenen Lauf automatisch eine E-Mail. Den Lauf findest
du unter **Actions → Studien-Update (täglich)**; der rote Schritt zeigt die Ursache.

| Meldung im Log | Ursache und Lösung |
|---|---|
| `authentication_error` / `invalid x-api-key` | Der Key ist falsch, abgelaufen oder das Secret heißt anders. Secret unter Settings → Secrets and variables → Actions neu anlegen — der Name muss exakt `ANTHROPIC_API_KEY` lauten. |
| `credit balance is too low` | Guthaben im Anthropic-Konto aufladen (Console → Settings → Billing). |
| `PubMed nicht erreichbar` | NCBI hatte eine Störung. Das Skript versucht es dreimal; ansonsten einfach am nächsten Tag erneut — es ist selbstheilend, ein ausgefallener Tag hat keine Folgen. |
| `Marker-Block nicht in index.html gefunden` | Die Markerzeilen `// === STUDIES-BLOCK-START …` bzw. `… -ENDE ===` wurden aus `index.html` entfernt. Beide Zeilen wiederherstellen. |
| `Unerwartete Studienanzahl` | Claude hat zu wenige passende Studien gefunden (z. B. an einem publikationsarmen Tag). Kein Handlungsbedarf; beim nächsten Lauf klappt es wieder. |
| Lauf grün, aber Live-Seite unverändert | Wenn im Log „Keine Änderung" steht, gab es tatsächlich keine neuen Studien. Andernfalls unter **Actions** den Lauf `pages-build-deployment` prüfen. |
| Workflow startet gar nicht | GitHub deaktiviert geplante Workflows in Repos, in denen 60 Tage lang nichts passiert. Einmal manuell starten (Schritt 4) reaktiviert ihn. |

---

## Anpassungen

Alle Stellschrauben stehen im Abschnitt `env:` der Workflow-Datei.

**Uhrzeit ändern** — der `cron`-Ausdruck steht in **UTC**, nicht in deutscher Zeit:

```yaml
- cron: "0 6 * * *"     # täglich 06:00 UTC  = 08:00 Uhr Sommerzeit
- cron: "30 4 * * *"    # täglich 04:30 UTC  = 06:30 Uhr Sommerzeit
- cron: "0 6 * * 1"     # nur montags        (wieder wöchentlich)
```

**Anderes Modell** — mehr Qualität gegen etwas höhere Kosten:

```yaml
MODEL: claude-sonnet-5
```

**Anderer Suchbegriff** — die auskommentierte Zeile aktivieren:

```yaml
SEARCH_TERM: '"patient reported outcomes"'
```

**Automatik pausieren** — unter **Actions → Studien-Update (täglich) → ⋯ → Disable workflow**.
Wieder einschalten geht an derselben Stelle.

---

## Wie es intern funktioniert

- **`scripts/update_studies.py`** erledigt die Arbeit: PubMed abfragen (mit drei Wiederholversuchen),
  Claude mit erzwungenem JSON-Schema befragen, den Marker-Block in `index.html` ersetzen.
  Bei jedem Problem bricht es mit einem Fehler ab — dann bleibt `index.html` unangetastet und
  der Workflow schlägt sichtbar fehl, statt etwas Kaputtes zu committen.
- **Ersetzt wird ausschließlich** der Bereich zwischen den beiden Markerzeilen. Datenbank-Kacheln,
  Layout, Footer, Impressum und Datenschutzhinweise werden nie angefasst.
- **Texte werden HTML-maskiert**, bevor sie in die Datei geschrieben werden. Ein `<` oder `&` in
  einem Studientext kann die Seite dadurch nicht zerlegen.
- **Committet wird nur bei echter Änderung** — an Tagen ohne neue Studien entsteht kein Leer-Commit.
- Der Push nutzt das eingebaute `GITHUB_TOKEN`; ein zusätzlicher Zugangsschlüssel ist nicht nötig.
  Weil ein solcher Push nicht immer einen Pages-Build auslöst, stößt der Workflow ihn danach
  ausdrücklich an.

Die Dateien `scripts/update-studies.ps1` und `scripts/Studien-aktualisieren.cmd` sind eine ältere
lokale Variante für den Rechner. Sie werden von der Automatik nicht verwendet und können bleiben
oder gelöscht werden.
