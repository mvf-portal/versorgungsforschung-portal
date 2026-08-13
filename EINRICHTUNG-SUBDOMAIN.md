# Portal auf wissen.m-vf.de umstellen

Diese Anleitung stellt das Portal von `mvf-portal.github.io/versorgungsforschung-portal/`
auf die eigene Adresse **`https://wissen.m-vf.de`** um.

**Aufwand:** 5 Minuten Arbeit, danach 10 Minuten bis mehrere Stunden Wartezeit für DNS und
Zertifikat. **Voraussetzung:** Zugriff auf die DNS-Verwaltung von `m-vf.de` (beim Hoster
oder Domain-Anbieter).

---

## Warum das lohnt

| | vorher | nachher |
|---|---|---|
| Adresse | `mvf-portal.github.io/versorgungsforschung-portal/` | `wissen.m-vf.de` |
| Domain-Inhaber | GitHub | **ihr** |
| Suchmaschinen-Wirkung | zahlt auf github.io ein | zahlt auf **m-vf.de** ein |
| Statistik | fremde Domain, getrennte Zählung | **eine** Domain, Hub-Besuche zählen als MVF-Besuche |
| Marke | GitHub-Adresse | eigene Adresse |

---

## ⚠️ Reihenfolge beachten

**Zuerst der DNS-Eintrag, danach die Umstellung bei GitHub.** Andersherum ist das Portal
zwischenzeitlich nicht erreichbar: GitHub leitet die alte Adresse dann bereits auf
`wissen.m-vf.de` um, das ohne DNS-Eintrag ins Leere läuft.

---

## Schritt 1: DNS-Eintrag anlegen

In der DNS-Verwaltung von `m-vf.de` einen neuen Eintrag anlegen:

| Feld | Wert |
|---|---|
| **Typ** | `CNAME` |
| **Name / Host / Subdomain** | `wissen` — manche Anbieter erwarten `wissen.m-vf.de.` mit Punkt am Ende |
| **Ziel / Wert / Points to** | `mvf-portal.github.io` — falls ein Punkt am Ende verlangt wird: `mvf-portal.github.io.` |
| **TTL** | `3600` (oder der Standardwert) |

Hinweise:

- **Kein A-Eintrag.** Für eine Subdomain ist `CNAME` richtig; A-Einträge mit IP-Adressen
  braucht man nur für die Hauptdomain ohne `www`.
- Das Ziel ist die **GitHub-Benutzeradresse** `mvf-portal.github.io`, **nicht** die volle
  Projektadresse mit `/versorgungsforschung-portal/`.
- Existiert für `wissen` bereits ein Eintrag, muss er vorher entfernt werden.
- Falls eure Domain **CAA-Einträge** nutzt: `letsencrypt.org` muss zulässig sein, sonst
  kann GitHub kein HTTPS-Zertifikat ausstellen.

### Wirkt der Eintrag schon?

Im Terminal prüfen:

```bash
nslookup wissen.m-vf.de
```

Sobald dort `mvf-portal.github.io` auftaucht, ist der Eintrag aktiv. Das dauert meist einige
Minuten, in seltenen Fällen bis zu 24 Stunden.

---

## Schritt 2: Domain bei GitHub eintragen

Erst machen, wenn Schritt 1 nachweislich wirkt.

**Weg A — im Browser:** Repo → **Settings** → **Pages** → Abschnitt *Custom domain* →
`wissen.m-vf.de` eintragen → **Save**. GitHub prüft den DNS-Eintrag und legt automatisch
eine Datei namens `CNAME` im Repo an.

**Weg B — Datei committen:** Im Repo liegt bereits eine vorbereitete `CNAME`-Datei mit dem
Inhalt `wissen.m-vf.de`. Sie muss nur committet und gepusht werden; GitHub übernimmt die
Einstellung dann von selbst.

---

## Schritt 3: HTTPS erzwingen

Nach der Umstellung besorgt GitHub automatisch ein kostenloses Zertifikat (Let's Encrypt).
Das dauert typischerweise wenige Minuten, gelegentlich länger.

Sobald unter **Settings → Pages** das Häkchen **Enforce HTTPS** anklickbar ist: setzen.
Danach wird jeder Aufruf automatisch auf `https://` umgeleitet.

Steht dort noch *„Certificate not yet created"*, einfach abwarten und die Seite später neu
laden — es ist kein Fehler.

---

## Schritt 4: Prüfen

```bash
curl -sI https://wissen.m-vf.de | head -3
```

Erwartet: `HTTP/2 200`.

Danach im Browser öffnen und stichprobenartig testen: Suchfeld, Auswahlmenü, Studien rechts,
Impressum im Fußbereich.

**Die alte Adresse bleibt gültig** — GitHub leitet sie automatisch auf die neue um. Bereits
verschickte Links funktionieren also weiter.

---

## Was danach noch anzupassen ist

Die neue Adresse taucht an einigen Stellen auf, die nachgezogen werden sollten
(erledigt Claude auf Zuruf):

- `README.md` und `EINRICHTUNG-GITHUB-ACTIONS.md` — die genannte Live-Adresse
- `CLAUDE.md` — Live-Adresse und der Prüfbefehl
- Der Slash-Befehl `~/.claude/commands/studien-update.md` — die Adresse für die Endkontrolle

Am Portal selbst ist **nichts** zu ändern: Es enthält keine absoluten Pfade und lädt keine
externen Dateien, funktioniert unter jeder Adresse unverändert.

---

## Wichtig für die Traffic-Zurechnung

Die Subdomain allein genügt noch nicht. Alle ausgehenden Links tragen derzeit
`rel="noopener noreferrer"` — das `noreferrer` **unterdrückt die Herkunftsangabe**. Klicks vom
Hub auf `m-vf.de` erscheinen in eurer Statistik dadurch als Direkteinstieg, nicht als
Weiterleitung aus dem Hub.

Für eine saubere Zurechnung zusätzlich:

1. `noreferrer` entfernen (`noopener` bleibt) — die Herkunft wird dann übermittelt.
2. UTM-Parameter an die MVF-Links hängen, z. B. `&utm_source=knowledge-hub`.

Beides ist in Minuten erledigt und hat keine datenschutzrechtlichen Folgen.

---

## Wenn etwas klemmt

| Symptom | Ursache und Lösung |
|---|---|
| GitHub meldet *„Domain does not resolve to the GitHub Pages server"* | DNS-Eintrag noch nicht aktiv oder falsches Ziel. Mit `nslookup wissen.m-vf.de` prüfen; Ziel muss `mvf-portal.github.io` sein. |
| Seite nicht erreichbar, GitHub zeigt aber alles grün | DNS-Zwischenspeicher. Anderes Netz oder Gerät probieren, sonst abwarten. |
| *„Certificate not yet created"* bleibt lange stehen | Domain in den Pages-Einstellungen entfernen, speichern, erneut eintragen — das stößt die Zertifikatsanforderung neu an. Vorher CAA-Einträge prüfen. |
| Browser warnt vor unsicherer Verbindung | Zertifikat noch nicht fertig. Warten, danach **Enforce HTTPS** setzen. |
| 404 unter der neuen Adresse | Die `CNAME`-Datei muss im Wurzelverzeichnis des Branches `main` liegen und **exakt** `wissen.m-vf.de` enthalten (keine Leerzeichen, kein `https://`). |
