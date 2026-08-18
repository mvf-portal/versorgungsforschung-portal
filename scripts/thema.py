#!/usr/bin/env python3
"""Alles Themenspezifische der taeglichen Studienauswahl — und sonst nichts.

Beim Anschluss an die Vorlage am 18.08.2026 woertlich aus update_studies.py
uebernommen, damit sich an der taeglichen Auswahl nichts aendert.
`update_studies.py` ist seither in allen Portalen wortgleich und wird zentral
gepflegt; wer die Auswahl aendern will, aendert Text in DIESER Datei.
"""
from __future__ import annotations

import os

# NCBI bittet bei automatisierten Zugriffen um eine Tool-Kennung.
NCBI_TOOL = "versorgungsforschung-portal"

TERM = os.environ.get("SEARCH_TERM", '"health services research"')
# Zweite Abfrage, damit Arbeiten mit Deutschlandbezug den Kandidatenpool
# sicher erreichen. Ueber MeSH und Autorenadresse, nicht ueber Journalnamen -
# deutschsprachige Journale liefern kaum Treffer.
TERM_DE = os.environ.get(
    "SEARCH_TERM_DE",
    f"{TERM} AND (Germany[MeSH Terms] OR Germany[Affiliation])",
)

# Groesse des Kandidatenpools und Reihenfolge der beiden Abfragen — beides so
# uebernommen, wie dieses Portal es bisher gehandhabt hat. EUROPA_ZUERST=False
# heisst: die allgemeine Abfrage steht vorn. Ein Sprachmodell gewichtet, was es
# zuerst liest; umzustellen ist eine redaktionelle Entscheidung.
POOL_EUROPA = 15
POOL_ALLGEMEIN = 40
EUROPA_ZUERST = False

# Wie viele Studien taeglich erscheinen. KAPPEN=False heisst: zu viele lassen
# den Lauf scheitern, statt gekuerzt zu werden.
# **Nicht ins JSON-Schema schreiben** — die Anthropic-API lehnt minItems > 1
# und maxItems ab.
ANZAHL_SOLL = 6
ANZAHL_MAX = 7
ANZAHL_MIN = 5
KAPPEN = False

# ------------------------------------------------------------------- Prompts
SYSTEM = (
    "Du bist Fachredakteur fuer Versorgungsforschung / Health Services Research. "
    "Aus einer Liste von PubMed-Abstracts waehlst du die relevantesten aktuellen "
    "Studien aus und fasst sie praezise auf Deutsch zusammen."
)

USER_TEMPLATE = """Unten stehen aktuelle PubMed-Abstracts (nach Datum sortiert).

Waehle GENAU 6 Studien aus, die (a) fuer Versorgungsforschung / Health Services Research
relevant sind UND (b) im Abstract KONKRETE quantitative Ergebnisse nennen
(Prozentwerte, Odds/Hazard Ratios, p-Werte, Fallzahlen). Ueberspringe Studien ohne
Abstract oder ohne konkrete Ergebnisse. Achte auf thematische Vielfalt.

WICHTIGSTES AUSWAHLKRITERIUM - Übertragbarkeit auf Deutschland:
Die Leserschaft arbeitet im deutschen Versorgungssystem. Bei sonst gleicher
Qualität hat die übertragbare Studie IMMER Vorrang vor der aktuelleren.

Übertragbarkeit richtet sich nach dem SYSTEMKONTEXT, nicht nach der Herkunft
der Autoren. Eine niederländische Arbeit zur Primärversorgung ist oft
übertragbarer als eine deutsche Methodenarbeit.

  Hoch:    Deutschland, Österreich, Schweiz - gleiche Grundstruktur.
           Niederlande, Belgien, Frankreich - Sozialversicherungssysteme mit
           Beitragsfinanzierung, Kassen und niedergelassenem Sektor.
  Mittel:  Skandinavien, Großbritannien, Kanada, Australien - steuerfinanziert
           und stark hausarztgesteuert; bei Fragen zu Prozessen, Qualität und
           Patientenperspektive gut übertragbar, bei Vergütung und
           Zugangssteuerung nur eingeschränkt.
  Gering:  USA - fragmentierte Versicherung, Medicaid/Medicare, andere
           Anreizstrukturen. Nur nehmen, wenn die Fragestellung systemunabhängig
           ist (z. B. klinische Prozesse, Patientensicherheit, Messinstrumente).
           Ebenso Studien aus Systemen mit grundlegend anderer Ressourcenlage.

Nimm höhere Übertragbarkeit auch dann, wenn die Studie ein paar Tage älter ist.
Eine reine US-Vergütungsstudie gehört nur in die Auswahl, wenn sonst nichts
Brauchbares vorliegt.

Fuer jede Studie:
- journal: Journalname genau so, wie er in der Kopfzeile des Abstracts steht -
  Abkuerzung nicht aufloesen, nichts ergaenzen. (Wird ohnehin durch die Angabe
  aus PubMed ersetzt; rate hier nichts.)
- year: Erscheinungsjahr, z. B. "2026"
- pmid: die PubMed-ID
- title: praegnanter deutscher Titel
- sum: 1 Satz auf Deutsch, was die Studie untersucht hat
- result: Deutsch, die konkreten Zahlen/Befunde + ein kurzer Einordnungssatz.
  Deutsches Zahlenformat mit Komma (z. B. 0,63).
- transfer: EIN Halbsatz (höchstens 12 Wörter), warum das Ergebnis für das
  deutsche Versorgungssystem taugt - oder wo die Grenze liegt. Nenne das Land
  bzw. die Datengrundlage. Keine ganzen Sätze, keine Wiederholung des Titels.
  Gut:      "Deutsche Routinedaten, gesetzlich Versicherte"
            "Niederlande, vergleichbares Sozialversicherungssystem"
            "US-Daten - Fragestellung aber systemunabhängig"
            "Nur bedingt: steuerfinanziertes System, andere Zugangssteuerung"
  Schlecht: "Diese Studie ist gut übertragbar." (sagt nichts)

WICHTIG - Fachterminologie: Etablierte englische Fachbegriffe NICHT eindeutschen.
Sie sind auch im deutschen Fachdeutsch stehende Begriffe; eine woertliche Uebersetzung
wirkt unprofessionell und erschwert das Wiederfinden. Beispiele fuer Begriffe, die
englisch bleiben: Door-to-Balloon-Zeit, Patient-Reported Outcomes, Shared Decision
Making, Case Management, Disease Management, Public Health, Screening, Follow-up,
Outcome, Adherence, Value-Based Care, Hazard Ratio, Odds Ratio, Confounder, Baseline,
Setting, Cluster. Gaengige Abkuerzungen ebenfalls unveraendert lassen: STEMI, COPD,
ICU, PROM, DRG, ACSC.
Faustregel: Wuerde eine deutsche Fachzeitschrift wie Monitor Versorgungsforschung den
Begriff englisch stehen lassen, dann tue es auch. Im Zweifel englisch belassen und bei
Bedarf eine kurze deutsche Erlaeuterung in Klammern ergaenzen.
Umgekehrt gilt: Wo es ein gebraeuchliches deutsches Fachwort gibt (Verweildauer,
Hausarztkontakt, Nutzenbewertung, Fallzahl), dieses verwenden.

Gib ausschliesslich das geforderte JSON zurueck.

=== ABSTRACTS ===
{abstracts}
"""
