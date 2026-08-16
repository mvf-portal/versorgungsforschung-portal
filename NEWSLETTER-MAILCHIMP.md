# Studien-Newsletter über Mailchimp einrichten

Der Hub stellt seit dem Ausbau einen RSS-Feed bereit. Mailchimp kann daraus **ohne
weiteres Zutun** täglich einen Newsletter bauen und versenden — die Redaktion muss
nichts mehr zusammenstellen, kopieren oder freigeben.

**Zeitaufwand für die Einrichtung:** etwa 20 Minuten, einmalig.

---

## Was der Hub dafür bereitstellt

| Adresse | Inhalt |
|---|---|
| `https://wissen.m-vf.de/studien-feed.xml` | RSS 2.0, ein Eintrag je Studie, die letzten 60 |
| `https://wissen.m-vf.de/download/studien-aktuell.docx` | Word — nur die jüngste Tagesauswahl |
| `https://wissen.m-vf.de/download/studien-aktuell.csv` | Excel — dieselbe Auswahl |
| `https://wissen.m-vf.de/download/studien-archiv.docx` | Word — der vollständige Bestand |
| `https://wissen.m-vf.de/download/studien-archiv.csv` | Excel — derselbe Bestand |

Alle fünf Dateien werden vom täglichen Workflow um 06:00 Uhr neu geschrieben. Die
Adressen bleiben dabei konstant — ein einmal gesetzter Link im Newsletter oder auf
der Website liefert immer den aktuellen Stand.

> Die CSV-Dateien nutzen Semikolon als Trenner und tragen ein BOM. Damit öffnet
> Excel unter Windows sie per Doppelklick korrekt in Spalten und stellt Umlaute
> richtig dar — ohne den Importassistenten.

---

---

## Vorab: die Anmeldung

Die Anmeldung liegt seit August 2026 **auf dem Hub selbst**: `newsletter.html`, verlinkt
im Menü und im Studien-Kasten. Sie sendet unmittelbar an Mailchimp und setzt dabei drei
Kennzeichen:

| Was | Kennzeichen |
|---|---|
| Studien-Newsletter | Tag **Studien-Newsletter Pubmed** (`tags=3433296`) |
| MVF-Newsletter | Gruppe **Monitor Versorgungsforschung Newsletter** (`group[5629][4]`) |
| Einwilligung | Gruppe **Datenschutzerklärung gelesen** (`group[5629][64]`) |

Double-Opt-in ist in der Zielgruppe aktiv; Einwilligung, Bestätigung und Abmeldung
verwaltet Mailchimp. Ein zweites Formular auf m-vf.de ist dafür **nicht** nötig — das
dortige Formular bedient weiterhin den regulären MVF-Newsletter.

> ### Der wichtigste Punkt
>
> Die RSS-Kampagne muss an den **Tag `Studien-Newsletter Pubmed`** gehen — nicht an die
> gesamte Zielgruppe. Die Hausliste „eRelation GESAMT" zählt rund 5.900 Abonnenten;
> sie alle bekämen sonst täglich die Studienauswahl, obwohl sie nur den regulären
> Newsletter bestellt haben. Das wäre nicht nur lästig, sondern mangels Einwilligung
> auch rechtlich angreifbar.

---

## Der Versand heute: Entwurf zur Freigabe

`scripts/mailchimp_entwurf.py` läuft täglich als letzter Schritt des Workflows — nach
den Studien, nach Feed und Downloads. Es **verschickt nichts an die Leserschaft**:

1. Es nimmt den jüngsten Tag aus `studien-archiv.json`. Ist der nicht von heute, endet es
   ohne Entwurf — kein Versand ohne neue Studien.
2. Es prüft, ob für diesen Tag schon ein Entwurf besteht (bei doppelten Läufen).
3. Es legt die Kampagne an, Empfänger ist der Tag **Studien-Newsletter Pubmed**.
4. Es setzt den Inhalt — zunächst mit einem goldenen Freigabe-Kasten obenauf.
5. Es schickt eine Testausgabe an **stegmaier@m-vf.de**. Diese Testausgabe *ist* die
   Vorschau: Sie sehen genau, was hinausginge, und im Kasten steht der Link zum Freigeben.
6. Es setzt den Inhalt erneut, diesmal ohne den Kasten — die Leserschaft sieht ihn nie.

Der Versand bleibt danach **ein Klick von Hand** in Mailchimp. Bei einer KI-kuratierten
Auswahl ist das Absicht, nicht Umständlichkeit.

### Einrichtung: ein Schlüssel

In Mailchimp unter **Account → Extras → API-Schlüssel** einen Schlüssel erzeugen
(`https://us6.admin.mailchimp.com/account/api/`). Ihn **nicht** im Klartext weitergeben,
sondern in GitHub hinterlegen: *Settings → Secrets and variables → Actions → New
repository secret*, Name **`KNOWLEDGEHUB`** (so heisst es im Repository; `MAILCHIMP_API_KEY` wird ebenfalls akzeptiert).

Ohne diesen Schlüssel überspringt der Schritt sich selbst und meldet das im Protokoll;
der Rest des Laufs bleibt davon unberührt. Auch ein Fehler beim Anlegen lässt das
Studien-Update nicht scheitern (`continue-on-error`).

### Was im Skript fest steht

| Wert | Bedeutung |
|---|---|
| `LIST_ID = 1c8fc10ec7` | Zielgruppe „eRelation GESAMT" |
| `TAG_ID = 3433296` | Tag „Studien-Newsletter Pubmed" — **der Empfänger** |
| `REPLY_TO = cms@m-vf.de` | wie in der Zielgruppe hinterlegt |
| `FREIGABE_MAIL` | wohin die Testausgabe geht |

Die E-Mail entsteht in `newsletter_html()` — Tabellen-Layout, Inline-Styles, feste
600 Pixel, in den Hub-Farben Blau und Gold. `newsletter/mailchimp-vorlage.html` ist die
ältere RSS-Fassung; sie bleibt als Beleg, wird aber nicht mehr benutzt.

Zum Prüfen ohne Konto: `python scripts/mailchimp_entwurf.py --probe` schreibt die fertige
E-Mail nach `_probe.html`.

---

> ## ⚠ Dieser Weg ist versperrt (Stand: 16. August 2026)
>
> **Mailchimp hat die klassischen Automationen im Juni 2025 abgeschaltet** — darunter
> „Blog-Updates teilen" / *Share blog updates*, die RSS-Kampagne. Nachgeprüft am
> 16.08.2026 im Konto: `campaigns/create?type=rss` liefert 404, und der Journey-Builder,
> der die Automationen ersetzt, bietet **keinen RSS-Auslöser** (Trigger-Rubriken:
> Kontakt-, Kauf-, Marketing-, Buchungs-, Zahlungsaktivität, Datum, API).
>
> Die Schritte 1 bis 5 unten sind damit **Historie**. Sie bleiben stehen, weil sie
> beschreiben, was der Feed leisten soll — nicht, weil man ihnen noch folgen könnte.
>
> **Der Weg, der bleibt:** die Mailchimp-API. Der tägliche GitHub-Lauf, der um 06:00 Uhr
> die Studien holt, legt anschließend eine Kampagne an und verschickt sie an den Tag
> `Studien-Newsletter Pubmed`. Der Inhalt entsteht ohnehin schon — `build_newsletter.py`
> baut Feed, Word und Excel; die Vorlage `newsletter/mailchimp-vorlage.html` ist fertig.
> Nötig wäre ein API-Schlüssel als Repository-Geheimnis, den **der Betreiber selbst**
> hinterlegt.

## Schritt 1: Kampagne anlegen

1. **Erstellen → E-Mail** (englisch: *Campaigns → Create → Email*).
2. Reiter **Automatisiert** / *Automated*, darin **Blog-Updates teilen**
   / *Share blog updates*. Das ist Mailchimps Name für eine RSS-Kampagne;
   ein Blog wird dafür nicht gebraucht.
3. Kampagnennamen vergeben, z. B. `MVF Studien-Newsletter`.
4. Zielgruppe **eRelation GESAMT**, und dort **nicht** „Gesamte Zielgruppe",
   sondern **Segment oder Tag** → **Studien-Newsletter Pubmed**.
   Ein eigenes Segment muss man dafür nicht anlegen: Mailchimp lässt den Tag
   unmittelbar als Empfänger wählen.

## Schritt 2: Feed und Sendezeit

1. **RSS feed URL:**
   ```
   https://wissen.m-vf.de/studien-feed.xml
   ```
2. **Send timing:** *Daily*.
3. **Uhrzeit:** frühestens **08:00 Uhr**. Der Hub aktualisiert um 06:00 Uhr; der
   Abstand fängt Verzögerungen ab, die GitHub bei hoher Auslastung gelegentlich hat.
4. Wochentage nach Bedarf. Publikationsarme Wochenenden lassen sich abwählen —
   die Studien gehen dann am Montag mit hinaus, verloren geht keine.

Mailchimp versendet **nur, wenn der Feed neue Einträge enthält**. An Tagen ohne
neue Studien passiert nichts; eine leere Ausgabe kann nicht entstehen.

## Schritt 3: Betreffzeile

```
Neueste Studien der Versorgungsforschung — *|RSSFEED:DATE|*
```

`*|RSSFEED:DATE|*` setzt Mailchimp beim Versand auf das Datum der Ausgabe.

## Schritt 4: Vorlage einfügen

1. Bei der Vorlagenauswahl **Code your own → Paste in code** wählen.
2. Den gesamten Inhalt von `newsletter/mailchimp-vorlage.html` (in diesem Repo)
   in das Feld kopieren.
3. **Save**, dann über **Preview → Enter preview mode** ansehen.

Die Vorlage enthält bereits: Kopfbereich im MVF-Grün, die Studienschleife, den
Download-Kasten, einen Knopf zum Hub und einen Fußbereich mit Abmeldelink.

## Schritt 5: Testversand

**Preview → Send a test email** an die eigene Adresse. Prüfen Sie dabei drei Dinge:

- Erscheinen die Studien einzeln, jeweils mit dem grün hinterlegten Ergebnisblock?
- Öffnen die vier Download-Links die Dateien?
- Sieht die Darstellung in Outlook sauber aus? (Outlook ist der kritische Client —
  Gmail und Apple Mail sind unproblematisch.)

Danach die Automation **starten**. Ab dann läuft sie ohne weiteres Zutun.

---

## Wie die Vorlage aufgebaut ist

Der Kern ist die Schleife, die Mailchimp für jeden Feed-Eintrag einmal durchläuft:

```html
*|RSSITEMS:|*
  <h2><a href="*|RSSITEM:URL|*">*|RSSITEM:TITLE|*</a></h2>
  *|RSSITEM:CONTENT_FULL|*
*|END:RSSITEMS|*
```

| Merge-Tag | Wird ersetzt durch |
|---|---|
| `*|RSSITEM:TITLE|*` | deutscher Titel + Journal + Jahr |
| `*|RSSITEM:URL|*` | PubMed-Link der Studie, inklusive UTM-Parametern |
| `*|RSSITEM:CONTENT_FULL|*` | Fragestellung, Ergebnisblock und PubMed-Link als fertiges HTML |
| `*|RSSFEED:DATE|*` | Datum der Ausgabe |

Das Markup ist bewusst altmodisch: Tabellen-Layout, Inline-Styles, feste 600 Pixel
Breite, keine CSS-Variablen und kein Flexbox. Outlook rendert E-Mails mit der
Word-Engine und beherrscht modernes CSS nicht — deshalb sieht die Vorlage schlichter
aus als der Hub, läuft dafür aber in jedem Client.

---

## Warum keine Studie doppelt versendet wird

Jeder Feed-Eintrag trägt als GUID seine PubMed-ID:

```xml
<guid isPermaLink="false">pmid-42594509</guid>
```

Mailchimp merkt sich die gesendeten GUIDs. Eine Studie, die an mehreren Tagen in
den PubMed-Treffern auftaucht, geht deshalb nur einmal hinaus — auch dann, wenn
sie im Hub erneut angezeigt wird.

Die Reihenfolge innerhalb einer Ausgabe steuert das `pubDate`: Die erste Studie der
Tagesauswahl trägt den spätesten Zeitstempel und steht damit oben.

---

## Zurechnung des Traffics

Sämtliche Links in Feed und Vorlage tragen UTM-Parameter:

```
utm_source=newsletter  utm_medium=email  utm_campaign=studien-feed
```

`utm_content` unterscheidet zusätzlich, worauf geklickt wurde: `studie`,
`dl-word`, `dl-excel`, `dl-archiv-word`, `dl-archiv-excel`, `cta`. In der
Auswertung lässt sich damit ablesen, ob die Leserschaft eher zu den Studien selbst,
zu den Downloads oder zum Hub geht.

---

## Datenschutz — ein wichtiger Unterschied

Der Hub selbst setzt **keine Cookies und kein Tracking**; das steht so in seinen
Datenschutzhinweisen und muss auch so bleiben.

Mailchimp misst dagegen standardmäßig **Öffnungen und Klicks**. Das ist beim
Newsletter üblich und zulässig, erfordert aber:

- eine **Einwilligung beim Abonnieren** (Double-Opt-in — in Mailchimp unter
  *Audience → Settings → Audience name and defaults* aktivieren),
- einen **Hinweis auf die Messung** in der Datenschutzerklärung des Newsletters,
- einen Hinweis auf die **Verarbeitung durch Mailchimp** (Intuit, USA) samt
  Rechtsgrundlage für die Übermittlung.

**Seit der Anmeldeseite steht das im Hub selbst** — `index.html`, Datenschutzhinweise
Abschnitt 3 (Newsletter-Anmeldung, Double-Opt-in, Widerruf, Erfolgsmessung) und
Abschnitt 4 (Mailchimp als Auftragsverarbeiter, USA-Übermittlung). Wer den Anmeldeweg
ändert, muss diese beiden Abschnitte mitändern.

Die Aussage „keine Cookies, kein Tracking" gilt unverändert für das Portal — das ist
etwas anderes als der Newsletter und darf nicht vermischt werden.

Die Vorlage enthält im Fußbereich bereits `*|UNSUB|*` (Abmeldelink) und
`*|HTML:LIST_ADDRESS_HTML|*` (Absenderanschrift) — beides ist gesetzlich
vorgeschrieben und darf nicht entfernt werden.

---

## Fehlersuche

| Beobachtung | Ursache und Lösung |
|---|---|
| Mailchimp meldet „Feed not found" | Feed im Browser aufrufen: `https://wissen.m-vf.de/studien-feed.xml`. Erscheint er nicht, ist der letzte Workflow-Lauf fehlgeschlagen — unter **Actions** nachsehen. |
| Kampagne versendet nicht | Mailchimp sendet nur bei neuen Einträgen. Prüfen, ob das jüngste `pubDate` im Feed nach dem letzten Versand liegt. |
| Studien erscheinen ohne Formatierung | In der Vorlage steht `*|RSSITEM:CONTENT|*` statt `*|RSSITEM:CONTENT_FULL|*`. Die kurze Variante liefert nur Text. |
| Alles in einem Block statt einzeln | Die Schleife `*|RSSITEMS:|*` … `*|END:RSSITEMS|*` fehlt oder ist unvollständig. |
| In Outlook zerfällt das Layout | Es wurde modernes CSS ergänzt. Bei Tabellen und Inline-Styles bleiben. |
| Download-Link führt ins Leere | Der Ordner `download/` fehlt im Repo. `py scripts/build_newsletter.py` lokal ausführen und committen. |

---

## Feed und Downloads von Hand neu bauen

Das Skript liest ausschließlich `studien-archiv.json` — kein API-Key, kein Netzzugriff:

```bash
py scripts/build_newsletter.py
```

Nützlich, wenn an der Vorlage oder am Feed-Aufbau etwas geändert wurde und das
Ergebnis nicht bis zum nächsten Morgen warten soll.

Einmalig nötig: `py -m pip install --user python-docx`

> **Hinweis zum Aufbau:** Die Ausgabe hängt allein vom Archivinhalt ab, nicht von
> der Uhrzeit des Laufs — auch die Zeitstempel im Word-Dokument werden aus den
> Daten abgeleitet. Zwei Läufe hintereinander erzeugen deshalb bitgleiche Dateien.
> Das ist Absicht: Sonst entstünde jeden Tag ein Commit, auch wenn es gar keine
> neuen Studien gab.
