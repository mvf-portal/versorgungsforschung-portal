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

## Vorab: die Anmeldung auf monitor-versorgungsforschung.de

Der Hub zeigt in der rechten Spalte einen Kasten **„Studien-Newsletter"**. Der Knopf
darin führt auf die MVF-Startseite:

```
https://www.monitor-versorgungsforschung.de/?utm_source=knowledge-hub&utm_medium=referral&utm_campaign=studien-newsletter#studien-newsletter
```

Bewusst liegt **kein Formular auf dem Hub**: Er erhebt keine personenbezogenen Daten,
und das soll so bleiben. Einwilligung, Double-Opt-in und Abmeldung verwaltet MVF.

### Was auf der MVF-Seite einzurichten ist

In der rechten Seitenleiste steht bereits das Formular des allgemeinen Newsletters
(WPForms-Widget, Überschrift „Newsletter"). Darunter kommt ein **zweites Formular**:

1. **Neues WPForms-Formular** anlegen, Überschrift **„Studien-Newsletter"**, mit
   E-Mail-Feld und DSGVO-Kasten — analog zum bestehenden.
2. **Anker-ID vergeben:** Das umgebende Element braucht
   ```html
   id="studien-newsletter"
   ```
   Genau darauf zeigt der Link vom Hub. Fehlt die ID, landen Interessierte oben auf
   der Startseite und müssen die Seitenleiste selbst suchen — es ist also nichts
   kaputt, aber unbequem. **Die ID bitte nicht umbenennen**, sonst muss der Hub
   nachgezogen werden.
3. **Mit Mailchimp verbinden** und die Anmeldungen mit einem **Tag oder einer Gruppe**
   `Studien-Newsletter` versehen.
4. **Double-Opt-in** aktivieren.

> ### Der wichtigste Punkt
>
> Die RSS-Kampagne muss an ein **Segment** gehen, das auf diesen Tag gefiltert ist —
> nicht an die gesamte Audience. Sonst erhalten alle MVF-Abonnenten täglich die
> Studienauswahl, obwohl sie nur den allgemeinen Newsletter bestellt haben. Das wäre
> nicht nur lästig, sondern mangels Einwilligung auch rechtlich angreifbar.
>
> In Mailchimp: **Audience → Segments → Create segment**, Bedingung
> *Tags → contains → Studien-Newsletter*. Dieses Segment in Schritt 1 unten als
> Empfänger wählen.

---

## Schritt 1: Kampagne anlegen

1. In Mailchimp auf **Campaigns → Create → Email**.
2. Reiter **Automated**, dann **Share blog updates** wählen.
   (Das ist Mailchimps Bezeichnung für eine RSS-Kampagne; ein Blog ist dafür nicht nötig.)
3. Kampagnennamen vergeben, z. B. `MVF Studien-Newsletter`.
4. Als Empfänger das **Segment `Studien-Newsletter`** wählen — nicht die gesamte
   Audience (siehe Kasten oben).

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

Diese Punkte gehören in die Datenschutzerklärung des **Newsletters**, nicht in die
des Hubs. Beide Erklärungen sollten nicht vermischt werden: Die Aussage „keine
Cookies, kein Tracking" gilt weiterhin für wissen.m-vf.de und wäre für den
Newsletter falsch.

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
