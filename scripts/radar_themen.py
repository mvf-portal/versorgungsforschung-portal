# -*- coding: utf-8 -*-
"""Die zwoelf Themengebiete des Ausschreibungsradars - an einer Stelle.

Entscheidung des Herausgebers vom 28.08.2026: Der Radar laeuft **einmal
zentral** im Versorgungsforschungs-Hub und ist dort nach Themengebieten
gegliedert (`ausschreibungen.html`). Die elf Schwesterhubs suchen nicht selbst;
sie zeigen in ihrer Kopfkarte nur die Zahl ihres Gebiets und verweisen auf die
zentrale Seite (`scripts/radar_hinweis.py`).

Warum zentral: Zwoelf Hubs, die dieselben drei Quellen abfragen, holen jede
Nacht zwoelfmal dasselbe - und zwoelfmal muss ein Modell dieselben Kandidaten
lesen. Der Unterschied liegt allein in der Auswahlregel, und die passt in eine
Zeile je Gebiet. Aus zwoelf Laeufen wird so einer, aus zwoelf Fassungen des
Wahrheitsstands eine.

Diese Datei ist die einzige Pflegestelle dafuer. Kommt ein Hub hinzu, gehoert
er hier hinein - und in PORTALE in `knowledge-hubs/scripts/versand_bericht.py`.

**Die Auswahlregeln sind vom Herausgeber bestaetigt** (28.08.2026). Abgeleitet
sind sie aus den Themenprofilen der Hubs (`themen/<slug>.json`: kriterium_a,
ausschluss). Wo eine Regel zu weit ist, stehen fremde Ausschreibungen im Hub;
wo sie zu eng ist, schweigt er, obwohl es etwas zu melden gaebe - eine Regel zu
aendern heisst deshalb, den Zuschnitt eines Hubs zu aendern.

Drei Abgrenzungen sind dabei ausdruecklich entschieden worden; sie stehen unten
in den betroffenen Regeln und sind keine Nebensache:

  1. **Adipositas erscheint nicht zusaetzlich unter "Nicht uebertragbare
     Krankheiten".** Medizinisch waere die Doppelung vertretbar - der Hub
     Adipositas haette dann aber kaum etwas Eigenes.
  2. **Sucht bleibt bei "Psychische Gesundheit"**, auch wenn darueber die
     Alkoholprogramme der NIH mit hereinkommen.
  3. **Breit angelegte Praeventionsprogramme ohne Krankheitsbezug gehoeren
     allein in die Versorgungsforschung.** Sonst stuende dieselbe
     Bekanntmachung in vier Gebieten, und keines davon meinte sie wirklich.
"""

# Die zentrale Seite, auf die alle elf anderen Hubs verweisen. Der Anker ist
# der Slug des Themengebiets - deshalb traegt jede Rubrik dort eine id.
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

# Die zwoelf Themengebiete in der Reihenfolge der Hub-Reihe.
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
fördert - Herz-Kreislauf, Krebs, Diabetes, Atemwege, muskuloskelettale
Erkrankungen.

NICHT einschlägig sind Grundlagenforschung, Molekularbiologie, Tiermodelle und
die Entwicklung einzelner Wirkstoffe ohne Versorgungsbezug.

NICHT einschlägig sind außerdem **Ausschreibungen zu Adipositas** - dafür gibt
es ein eigenes Themengebiet, und dieses hier nennt sie auch dann nicht, wenn
Adipositas als eine chronische Erkrankung unter mehreren vorkommt. Ebenso wenig
breit angelegte Präventionsprogramme ohne Bezug auf ein bestimmtes
Krankheitsbild; die gehören in die Versorgungsforschung.""",
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
]

# Alle Suchbegriffe der zwoelf Gebiete, entdoppelt und in fester Reihenfolge:
# Der Pool wird einmal geholt und danach zwoelfmal befragt.
SUCHE = list(dict.fromkeys(b for t in THEMEN for b in t["suche"]))
