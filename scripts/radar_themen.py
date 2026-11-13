# -*- coding: utf-8 -*-
"""Die fuenfzehn Themengebiete des Ausschreibungsradars - an einer Stelle.

Entscheidung des Herausgebers vom 28.08.2026: Der Radar laeuft **einmal
zentral** im Versorgungsforschungs-Hub und ist dort nach Themengebieten
gegliedert (`ausschreibungen.html`). Die vierzehn Schwesterhubs suchen nicht
selbst; sie zeigen in ihrer Kopfkarte nur die Zahl ihres Gebiets und verweisen
auf die zentrale Seite (`scripts/radar_hinweis.py`).

Warum zentral: Fuenfzehn Hubs, die dieselben drei Quellen abfragen, holen jede
Nacht fuenfzehnmal dasselbe - und fuenfzehnmal muss ein Modell dieselben
Kandidaten lesen. Der Unterschied liegt allein in der Auswahlregel, und die
passt in eine Zeile je Gebiet. Aus fuenfzehn Laeufen wird so einer, aus
fuenfzehn Fassungen des Wahrheitsstands eine.

Diese Datei ist die einzige Pflegestelle dafuer. Kommt ein Hub hinzu, gehoert
er hier hinein. PORTALE in `knowledge-hubs/scripts/versand_bericht.py` kommt
seit dem 04.09.2026 aus portale.json (portale_pflegen.py); von Hand bleiben
ausserdem `dirigent.yml` und `laufwache.py` in knowledge-hubs.

**Die Auswahlregeln sind vom Herausgeber bestaetigt** (28.08.2026). Abgeleitet
sind sie aus den Themenprofilen der Hubs (`themen/<slug>.json`: kriterium_a,
ausschluss). Wo eine Regel zu weit ist, stehen fremde Ausschreibungen im Hub;
wo sie zu eng ist, schweigt er, obwohl es etwas zu melden gaebe - eine Regel zu
aendern heisst deshalb, den Zuschnitt eines Hubs zu aendern.

Vier Abgrenzungen sind dabei ausdruecklich entschieden worden; sie stehen unten
in den betroffenen Regeln und sind keine Nebensache:

  1. **Adipositas erscheint nicht zusaetzlich unter "Nicht uebertragbare
     Krankheiten".** Medizinisch waere die Doppelung vertretbar - der Hub
     Adipositas haette dann aber kaum etwas Eigenes.
  2. **Sucht bleibt bei "Psychische Gesundheit"**, auch wenn darueber die
     Alkoholprogramme der NIH mit hereinkommen.
  3. **Breit angelegte Praeventionsprogramme ohne Krankheitsbezug gehoeren
     allein in die Versorgungsforschung.** Sonst stuende dieselbe
     Bekanntmachung in vier Gebieten, und keines davon meinte sie wirklich.
  4. **Krebs, Herz-Kreislauf und Diabetes erscheinen nicht mehr unter "Nicht
     uebertragbare Krankheiten"** (11.09.2026, mit dem Scharfschalten der drei
     Indikationshubs). Das ist Punkt 1 fortgeschrieben, und der Preis steht
     fest: NCD verliert damit seine drei groessten Brocken und behaelt
     Atemwege, muskuloskelettale Erkrankungen, Nieren und Leber,
     Multimorbiditaet und das Krankheitsuebergreifende. Konsistenz im Radar
     wiegt schwerer als die Fuelle eines Gebiets - wer Krebs-Ausschreibungen
     sucht, hat jetzt einen Krebs-Hub.

     AUSNAHME davon ist das Paar Diabetes/Adipositas: Zwei gleich spezielle
     Gebiete duerfen dieselbe Bekanntmachung fuehren, wenn sie beide meint.
     Die Begruendung steht in der Diabetes-Regel.
"""

# Die zentrale Seite, auf die alle vierzehn anderen Hubs verweisen. Der Anker
# ist der Slug des Themengebiets - deshalb traegt jede Rubrik dort eine id.
ZENTRALE = "https://wissen.m-vf.de/ausschreibungen.html"

# Welche Fachfeeds von foerderinfo.bund.de abgefragt werden. Die elf Namen
# stehen unter foerderinfo.bund.de/foerderinfo/de/services/rss/rss_node.html;
# am 28.08.2026 von dort ausgelesen, nicht geraten.
#
# Sechs davon koennen Gesundheitsthemen tragen. "bekanntmachungen-alle" ist
# NICHT dabei: Der Feed fuehrt fast nur das Forschungsministerium und ist damit
# schmaler, als sein Name verspricht - siehe den Quellenhinweis auf der Seite.
FEEDS = [
    "bekanntmachungen-gesundheit-ernaehrung",
    "bekanntmachungen-sozial-geistes-sozialwissenschaften",
    "bekanntmachungen-klima-energie",
    "bekanntmachungen-schluesseltechnologien",
    "bekanntmachungen-kommunikation",
    "bekanntmachungen-internationales",
]

# Die fuenfzehn Themengebiete in der Reihenfolge der Hub-Reihe.
#   slug   - Anker auf der zentralen Seite und Kennung in ausschreibungen.json.
#            MUSS dem SLUG in der portal.json des Hubs entsprechen: Daran
#            findet scripts/radar_hinweis.py sein Gebiet wieder. Zwei heissen
#            anders, als man vermuten wuerde - klima-gesundheit und
#            ki-gesundheit, nicht klima und ki.
#   name   - so heisst das Gebiet auf der Seite und in der Hinweiskarte
#   domain - der Hub, der die Zahl dieses Gebiets zeigt
#   suche  - englische Begriffe fuer grants.gov (kurz und gaengig; die
#            Schnittstelle sucht unscharf ueber alle Woerter)
#   regel  - woran das Modell entscheidet, ob eine Ausschreibung hierher
#            gehoert. Wie bei den Studien gilt: lieber schweigen als
#            danebenliegen.
THEMEN = [
    {
        "slug": "versorgungsforschung",
        "name": "Versorgungsforschung",
        "domain": "wissen.m-vf.de",
        "suche": ["health services research", "health care delivery"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Forschung zur
Gesundheitsversorgung fördert - Versorgungsformen, Versorgungsqualität,
Gesundheitssystem, Patientenversorgung, Gesundheitsdienstleistungen.

Hierher gehören auch **breit angelegte Präventions- und
Gesundheitsförderungsprogramme ohne Bezug auf ein bestimmtes Krankheitsbild**.
Sie passen sonst überallhin und nirgends richtig; entschieden am 28.08.2026.

Hierher gehören ebenso **alle Förderbekanntmachungen des Innovationsausschusses
beim G-BA** - auch die zu NEUEN VERSORGUNGSFORMEN. Dort wird die Erprobung
einer Versorgungsform samt Evaluation gefördert; formal ist das keine
Forschungsausschreibung, für die Leserschaft dieses Hubs aber die wichtigste
Fördermöglichkeit überhaupt. Die Regel "nur Forschungsförderung" gilt für sie
nicht (entschieden am 05.10.2026).

NICHT einschlägig sind reine Grundlagenforschung ohne Versorgungsbezug,
Medikamentenentwicklung, Agrar- und Ernährungsforschung, Biotechnologie,
Energie- und Umwelttechnik - auch dann nicht, wenn sie im selben Fachfeed
stehen.""",
    },
    {
        "slug": "klima-gesundheit",
        "name": "Hitze, Klima & Gesundheit",
        "domain": "klima.m-vf.de",
        "suche": ["climate change health", "heat health"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie die Folgen von
Klimawandel, Hitze, Luftqualität oder Extremwetter für die Gesundheit oder für
das Versorgungssystem erforschen lässt - einschließlich Hitzeschutz,
klimaresilienter Kliniken und der Anpassung des öffentlichen
Gesundheitsdienstes.

NICHT einschlägig ist Klima- und Energieforschung ohne Gesundheitsbezug:
Energiewandlung, Netze, Gebäudetechnik, Verkehr, Landwirtschaft, Klimamodelle
und Emissionsminderung, solange kein Endpunkt beim Menschen benannt ist.""",
    },
    {
        "slug": "ki-gesundheit",
        "name": "Digitalisierung, KI & Gesundheit",
        "domain": "ki.m-vf.de",
        "suche": ["artificial intelligence health care", "digital health"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie eine digitale
Technologie oder ein KI-Verfahren IN DER GESUNDHEITSVERSORGUNG fördert -
digitale Anwendungen, Telemedizin, elektronische Akten, Gesundheitsdaten und
ihre Infrastruktur, Entscheidungsunterstützung.

NICHT einschlägig ist Technologieförderung ohne Versorgungsbezug: Verfahren
und Modellentwicklung an sich, Halbleiter, Quantentechnik, Robotik in der
Industrie, allgemeine Digitalisierung von Wirtschaft und Verwaltung.""",
    },
    {
        "slug": "pflege",
        "name": "Pflege & Langzeitversorgung",
        "domain": "pflege.m-vf.de",
        "suche": ["long-term care", "nursing workforce"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie die
pflegerische Versorgung, die Langzeitpflege oder die Lage der Pflegenden
fördert - stationär, ambulant und häuslich, einschließlich pflegender
Angehöriger, Personalgewinnung und Arbeitsbedingungen in der Pflege.

NICHT einschlägig sind medizinische Ausschreibungen, in denen Pflegekräfte nur
als Studienpersonal vorkommen, sowie allgemeine Arbeitsmarkt- und
Fachkräfteprogramme ohne Bezug zur Pflege.""",
    },
    {
        "slug": "longevity",
        "name": "Gesundes Altern & Longevity",
        "domain": "longevity.m-vf.de",
        "suche": ["healthy aging", "care for older adults"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie das Altern,
die gesunde Lebenszeit oder die Versorgung älterer Menschen fördert -
Geriatrie, Prävention im Alter, Multimorbidität, Selbstständigkeit im Alter,
altersgerechte Versorgungsformen.

NICHT einschlägig sind Grundlagenforschung zu Alterungsmechanismen an
Modellorganismen, Anti-Aging-Angebote ohne gemessenes Ergebnis, breit angelegte
Präventionsprogramme ohne Altersbezug sowie Programme, die ältere Menschen nur
als eine von vielen Zielgruppen mitführen.""",
    },
    {
        "slug": "healthliteracy",
        "name": "Gesundheitskompetenz",
        "domain": "healthliteracy.m-vf.de",
        "suche": ["health literacy", "patient engagement"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie
Gesundheitskompetenz, die Verständlichkeit von Gesundheitsinformationen oder
die Beteiligung von Patientinnen und Patienten fördert - auch
Risikokommunikation und der Umgang mit Fehlinformation.

NICHT einschlägig sind Bildungsprogramme ohne Gesundheitsbezug und
Ausschreibungen, die ein digitales Werkzeug entwickeln oder technisch bewerten
- die gehören zu Digitalisierung, KI & Gesundheit.""",
    },
    {
        "slug": "impfen",
        "name": "Impfen & Impfprävention",
        "domain": "impfen.m-vf.de",
        "suche": ["vaccination coverage", "immunization program"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Impfungen,
Impfprogramme, Impfquoten, Impfbereitschaft oder die Sicherheit von Impfstoffen
in der Anwendung fördert - einschließlich Infektionsprävention, soweit sie am
Impfen hängt.

NICHT einschlägig sind präklinische Impfstoffentwicklung, Immunologie im Labor,
Erregergenomik und Wirkstoffforschung ohne Bezug zur Anwendung in der
Bevölkerung - ebenso wenig allgemeine Präventionsprogramme, in denen das Impfen
nicht vorkommt.""",
    },
    {
        "slug": "ncd",
        "name": "Nicht übertragbare Krankheiten",
        "domain": "ncd.m-vf.de",
        "suche": ["chronic disease management", "noncommunicable diseases"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Versorgung,
Prävention oder Krankheitslast chronischer, nicht übertragbarer Erkrankungen
fördert - Atemwege, muskuloskelettale Erkrankungen, chronische Nieren- und
Lebererkrankungen, Multimorbidität sowie krankheitsübergreifendes Chronic
Disease Management.

NICHT einschlägig sind Grundlagenforschung, Molekularbiologie, Tiermodelle und
die Entwicklung einzelner Wirkstoffe ohne Versorgungsbezug.

NICHT einschlägig sind außerdem **Ausschreibungen zu Adipositas, Krebs,
Herz-Kreislauf-Erkrankungen und Diabetes** - für jedes dieser vier gibt es ein
eigenes Themengebiet, und dieses hier nennt sie auch dann nicht, wenn sie als
eine chronische Erkrankung unter mehreren vorkommen. Ebenso wenig breit
angelegte Präventionsprogramme ohne Bezug auf ein bestimmtes Krankheitsbild;
die gehören in die Versorgungsforschung.""",
    },
    {
        "slug": "gender",
        "name": "Geschlechtersensible Medizin",
        "domain": "gender.m-vf.de",
        "suche": ["sex and gender differences health", "women's health"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Geschlecht als
Einflussgröße in der Versorgung fördert - in Diagnostik, Therapie, Zugang,
Arzneimittelwirkung oder Ergebnisqualität -, ebenso Frauen- und
Männergesundheit als Versorgungsthema.

NICHT einschlägig sind Gleichstellungsprogramme in Wissenschaft und Karriere
sowie Ausschreibungen, die Geschlecht nur als eines von vielen
Auswertungsmerkmalen verlangen.""",
    },
    {
        "slug": "adipositas",
        "name": "Adipositas",
        "domain": "adipositas.m-vf.de",
        "suche": ["obesity treatment", "obesity prevention"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Versorgung,
Prävention oder Krankheitslast bei Adipositas fördert - einschließlich
Ernährungs- und Bewegungsprogrammen mit Bezug auf Gewicht, Erstattung und
Zugang zu Adipositastherapie.

NICHT einschlägig sind Ernährungsforschung ohne Adipositasbezug, einzelne
Nährstoffe und Nahrungsergänzung, Lebensmitteltechnologie, Agrarforschung sowie
breit angelegte Präventionsprogramme, in denen Gewicht nur eines von vielen
Themen ist.""",
    },
    {
        "slug": "safety",
        "name": "Patientensicherheit",
        "domain": "safety.m-vf.de",
        "suche": ["patient safety", "healthcare associated infection"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie vermeidbaren
Schaden in der Versorgung fördert zu erkennen oder zu verhindern -
Behandlungs-, Medikations- und Diagnosefehler, nosokomiale Infektionen, Sepsis,
Meldesysteme, Sicherheitskultur.

NICHT einschlägig sind mikrobiologische Grundlagenforschung,
Resistenzmechanismen und Wirkstoffentwicklung ohne Bezug zur Versorgung sowie
Arbeitsschutz ohne Patientenbezug.""",
    },
    {
        "slug": "mental",
        "name": "Psychische Gesundheit",
        "domain": "mental.m-vf.de",
        "suche": ["mental health services", "behavioral health care"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie die Versorgung
psychisch erkrankter Menschen fördert - Zugang, Wartezeiten,
Behandlungsformen, Übergänge zwischen den Sektoren, Zwang und Rechte,
Prävention. **Sucht zählt dazu** (entschieden am 28.08.2026), soweit sie als
Versorgungsthema auftritt.

NICHT einschlägig sind Neurobiologie, Bildgebung, Genetik, Tiermodelle und
Wirkstoffstudien ohne Versorgungsbezug.""",
    },
    {
        "slug": "onkologie",
        "name": "Onkologie",
        "domain": "onkologie.m-vf.de",
        "suche": ["cancer research", "oncology care"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Forschung zu
Krebserkrankungen fördert - Früherkennung, Diagnostik, Therapie, Nachsorge,
Palliativversorgung, onkologische Versorgungsstrukturen, Krebsregister und
Tumorboards; einschließlich translationaler Projekte mit erkennbarem Bezug zum
Menschen.

NICHT einschlägig sind reine Zell- und Tiermodelle ohne Anwendungsbezug,
präklinische Wirkstoffentwicklung sowie breit angelegte Präventionsprogramme
ohne Bezug auf ein bestimmtes Krankheitsbild; die gehören in die
Versorgungsforschung.""",
    },
    {
        "slug": "kardio",
        "name": "Kardiologie",
        "domain": "kardio.m-vf.de",
        "suche": ["cardiovascular disease", "heart failure care"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Forschung zu
Herz-, Kreislauf- und Gefäßerkrankungen fördert - koronare Herzkrankheit,
Herzinsuffizienz, Rhythmusstörungen, Schlaganfall, kardiologische
Rehabilitation, Notfallketten und Versorgungsstrukturen.

NICHT einschlägig sind Grundlagenforschung ohne Anwendungsbezug, Tiermodelle
und Medizintechnikentwicklung ohne Versorgungsbezug.""",
    },
    {
        "slug": "diabetes",
        "name": "Diabetes",
        "domain": "diabetes.m-vf.de",
        "suche": ["diabetes care", "diabetes prevention"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Forschung zu
Diabetes fördert - Typ 1 und Typ 2, Folgeerkrankungen (Retinopathie,
Nephropathie, diabetisches Fußsyndrom), Technik (CGM, Insulinpumpen, Closed
Loop), Schulung und Selbstmanagement sowie Diabetesprävention durch Lebensstil
einschließlich Ernährungstherapie mit Diabetesbezug.

Geschnitten wird nach der **Zielgröße**, nicht nach dem Mittel: Zielt ein
Ernährungs- oder Bewegungsprogramm auf das Gewicht, gehört es nach Adipositas;
zielt es auf den Blutzucker, hierher. Nennt eine Ausschreibung beides - der
häufigste Fall bei Präventionsbekanntmachungen -, darf sie in beiden Gebieten
stehen. Das ist der Unterschied zur Abgrenzung gegen "Nicht übertragbare
Krankheiten": Dort schluckt ein allgemeines Gebiet ein spezielles, hier
überschneiden sich zwei gleich spezielle.

NICHT einschlägig sind Ernährungsforschung ohne Diabetesbezug, einzelne
Nährstoffe und Nahrungsergänzung, Lebensmitteltechnologie und
Agrarforschung.""",
    },
    {
        # Hinzugekommen am 12.11.2026 mit dem siebzehnten Hub. Regel aus
        # themen/muskel.json abgeleitet (kriterium_a, ausschluss, Quoten 4
        # und 5), vom Herausgeber am 12.11.2026 bestaetigt.
        "slug": "muskel",
        "name": "Muskuloskelettale Erkrankungen",
        "domain": "muskel.m-vf.de",
        "suche": ["musculoskeletal research", "rheumatology care"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Forschung zu
Erkrankungen des Bewegungsapparats fördert - Arthrose, rheumatoide Arthritis,
Spondyloarthritiden, Kollagenosen und Vaskulitiden, Gicht, Osteoporose und
Frakturrisiko, Rückenschmerz und Wirbelsäulenerkrankungen, Fibromyalgie - sowie
zur Versorgung damit: Endoprothetik und ihre Qualitätssicherung,
Rehabilitation, Teilhabe, Rückkehr in den Beruf, Schmerzversorgung;
einschließlich translationaler Projekte mit erkennbarem Bezug zum Menschen.

Die rheumatische Augenbeteiligung (Uveitis, Skleritis, Sjögren-Auge) gehört in
beide Gebiete und ist hier NICHT ausgeschlossen - dieselbe Teilung wie im Hub:
Steht die rheumatische Grunderkrankung im Mittelpunkt, gehört die
Ausschreibung hierher; steht das Auge im Mittelpunkt, zur Augenheilkunde.

NICHT einschlägig sind reine Zell- und Tiermodelle ohne Anwendungsbezug,
tiermedizinische Orthopädie, rheumatisches Fieber und rheumatische
Herzkrankheit (das ist Kardiologie), Implantat- und Materialentwicklung ohne
klinische Fragestellung sowie Sportwissenschaft ohne Krankheitsbezug.""",
    },
    {
        # Hinzugekommen am 12.11.2026 mit dem sechzehnten Hub. Die Regel ist
        # aus themen/auge.json abgeleitet (kriterium_a, ausschluss, Quote 4)
        # und vom Herausgeber am 12.11.2026 bestaetigt.
        "slug": "auge",
        "name": "Augenheilkunde",
        "domain": "auge.m-vf.de",
        "suche": ["ophthalmology research", "vision care"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Forschung zu
Augenerkrankungen und zur augenärztlichen Versorgung fördert - Glaukom,
Katarakt, altersbedingte Makuladegeneration und übrige Netzhauterkrankungen,
Hornhaut und trockenes Auge, Uveitis, Schielen und Amblyopie, Fehlsichtigkeit
und Myopie bei Kindern, Augenverletzungen, dazu Früherkennung, intravitreale
Therapie, operative Verfahren sowie Rehabilitation und Teilhabe bei
Sehbehinderung; einschließlich translationaler Projekte mit erkennbarem Bezug
zum Menschen.

Die diabetische Retinopathie gehört in beide Gebiete und ist hier NICHT
ausgeschlossen - dieselbe Teilung wie im Hub: Steht das Auge im Mittelpunkt
(Screening, intravitreale Therapie, Verlauf der Sehschärfe), gehört die
Ausschreibung hierher; steht die Stoffwechseleinstellung im Mittelpunkt, zu
Diabetes.

NICHT einschlägig sind reine Zell- und Tiermodelle ohne Anwendungsbezug,
tiermedizinische Augenheilkunde, Bilderkennung und maschinelles Lernen als
eigentlicher Gegenstand (die gehören zu Digitalisierung und KI) sowie
optische Mess- und Gerätetechnik ohne klinische Fragestellung.""",
    },
    {
        # Hinzugekommen am 13.11.2026 mit dem achtzehnten Hub. Regel aus
        # themen/kinder.json abgeleitet (kriterium_a, ausschluss, Quoten).
        "slug": "kinder",
        "name": "Kinder- und Jugendmedizin",
        "domain": "kinder.m-vf.de",
        "suche": ["child health research", "pediatric care"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Forschung zur
Gesundheit von Kindern und Jugendlichen oder zu ihrer Versorgung fördert -
Neonatologie und Frühgeborenenversorgung, chronische Erkrankungen im
Kindesalter, Vorsorgeuntersuchungen, Entwicklung und Entwicklungsstörungen,
Kinderschutz, Jugendgesundheit, der Übergang in die Erwachsenenmedizin sowie
die kinderärztliche und kinderklinische Versorgung; einschließlich
translationaler Projekte mit erkennbarem Bezug zum Menschen.

Die seelische Gesundheit junger Menschen gehört in beide Gebiete und ist hier
NICHT ausgeschlossen - dieselbe Teilung wie im Hub: Steht die Entwicklung oder
die pädiatrische Versorgung im Mittelpunkt, gehört die Ausschreibung hierher;
steht die psychische Erkrankung im Mittelpunkt, zu Psychische Gesundheit.

NICHT einschlägig sind Schulforschung und Pädagogik ohne Gesundheitsbezug,
Geburtshilfe mit Blick allein auf die Mutter, reine Zell- und Tiermodelle ohne
Anwendungsbezug sowie Kinderarzneimittelentwicklung ohne klinische
Fragestellung.""",
    },
    {
        # Hinzugekommen am 13.11.2026 mit dem neunzehnten Hub. Regel aus
        # themen/neuro.json abgeleitet (kriterium_a, ausschluss, Quoten 4 und 5).
        "slug": "neuro",
        "name": "Neurologie",
        "domain": "neuro.m-vf.de",
        "suche": ["neurology research", "stroke care"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Forschung zu
neurologischen Erkrankungen oder zu ihrer Versorgung fördert - Schlaganfall
von der Stroke Unit bis zur Nachsorge, Demenzen, Parkinson und andere
Bewegungsstörungen, Multiple Sklerose, Epilepsie, Kopfschmerz und Migräne,
ALS, Schädel-Hirn-Trauma, dazu neurologische Rehabilitation und Teilhabe;
einschließlich translationaler Projekte mit erkennbarem Bezug zum Menschen.

Die Demenzversorgung gehört in beide Gebiete und ist hier NICHT ausgeschlossen
- dieselbe Teilung wie im Hub: Steht die neurologische Erkrankung im
Mittelpunkt, gehört die Ausschreibung hierher; steht die Pflege und Betreuung
im Mittelpunkt, zu Pflege und Langzeitversorgung.

NICHT einschlägig sind reine Neurowissenschaft ohne Krankheitsbezug (die
Grundlagenforschung ist hier besonders groß), psychiatrische Fragestellungen
ohne neurologisches Korrelat (die gehören zu Psychische Gesundheit),
Bildauswertung des Gehirns als eigentlicher Gegenstand (Digitalisierung und
KI) sowie Geräte- und Sensorentwicklung ohne klinische Fragestellung.""",
    },
    {
        # Hinzugekommen am 13.11.2026 mit dem zwanzigsten Hub. Regel aus
        # themen/genom.json abgeleitet (kriterium_a, ausschluss, Quoten 3 und 4).
        "slug": "genom",
        "name": "Genommedizin & Seltene Erkrankungen",
        "domain": "genom.m-vf.de",
        "suche": ["genomic medicine", "rare disease research"],
        "regel": """Einschlägig ist eine Ausschreibung, wenn sie Forschung zur
genetischen Diagnostik, zur personalisierten Therapie oder zur Versorgung bei
Seltenen Erkrankungen fördert - Genom- und Exomsequenzierung, genetische
Beratung, Pharmakogenetik, Neugeborenen- und Anlageträgerscreening, genetisch
begründete Pränatal- und Präimplantationsdiagnostik, Gentherapie, Biobanken,
Genomdatenschutz, Zentrumsstruktur und Diagnosewege bei Seltenen Erkrankungen;
einschließlich translationaler Projekte mit erkennbarem Bezug zum Menschen.

Die Präzisionsonkologie gehört in beide Gebiete und ist hier NICHT
ausgeschlossen - dieselbe Teilung wie im Hub: Steht das genetische Verfahren im
Mittelpunkt, gehört die Ausschreibung hierher; steht die Tumortherapie im
Mittelpunkt, zu Onkologie.

NICHT einschlägig sind Impfstoffe, auch solche mit viralem Vektor oder mRNA
(die gehören zu Impfen und Prävention) - ein viraler Vektor ist dieselbe
Technik, einmal zur Immunisierung und einmal zum Gentransfer, und die
Abgrenzung entscheidet der Zweck, nicht das Werkzeug. Ebenfalls nicht
einschlägig sind Pflanzen- und Tierzüchtung, bioinformatische Methodenarbeiten
ohne klinische Fragestellung sowie Sequenziertechnik ohne
Versorgungsbezug.""",
    },
]

# Alle Suchbegriffe der achtzehn Gebiete, entdoppelt und in fester Reihenfolge:
# Der Pool wird einmal geholt und danach achtzehnmal befragt.
SUCHE = list(dict.fromkeys(b for t in THEMEN for b in t["suche"]))
