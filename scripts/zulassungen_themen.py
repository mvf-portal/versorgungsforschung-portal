# -*- coding: utf-8 -*-
"""Welche Arzneimittelzulassung in welchen Hub gehoert - die Pflegestelle dafuer.

Zugeordnet wird **ohne Modell**, allein ueber das Feld "Therapeutic area
(MeSH)" der EMA-Tabelle. Das ist der Unterschied zum Ausschreibungsradar: Dort
muss ein Modell abwaegen, weil eine Foerderbekanntmachung ihr Thema nicht
nennt. Eine Zulassung nennt es - die EMA traegt den MeSH-Begriff selbst ein.
Was mechanisch geht, soll nicht raten: Das spart Geld, laeuft in Millisekunden
und ist nachvollziehbar, wenn jemand fragt, warum ein Mittel in einem Hub steht.

Die Regeln sind **Muster, keine Begriffsliste**: In 24 Monaten kamen 545
verschiedene MeSH-Begriffe vor (gemessen am 22.10.2026 an 1.456 Eintraegen).
Eine Liste waere nach dem naechsten Quartal unvollstaendig; ein Muster faengt
auch "Carcinoma, Hepatocellular" und "Neoplasms, Plasma Cell" mit.

Eine Zulassung darf in **mehrere** Hubs gehoeren. Orforglipron mit der
Indikation "Obesity;Overweight;Diabetes Mellitus, Type 2" steht im
Adipositas- und im Diabetes-Hub, und das ist richtig - im Ausschreibungsradar
gilt dieselbe Regel.

**Nicht jeder Hub bekommt Zulassungen.** Pflege, Gesundheitskompetenz, Klima,
KI, Geschlechtersensible Medizin, Patientensicherheit und Versorgungsforschung
haben kein Krankheitsbild, auf das eine Arzneimittelzulassung zeigt. Sie
stehen hier deshalb gar nicht erst - eine Rubrik, die immer leer bleibt, ist
ein Versprechen, das die Quelle nicht einloesen kann.

Deckung am 22.10.2026: 949 von 1.456 Eintraegen aus 24 Monaten (65 %). Die
507 uebrigen sind ueberwiegend seltene Erkrankungen, HIV, Haemophilie und
Diagnostika - sie gehoeren zu Recht in keinen der fuenfzehn Hubs, nicht etwa
in einen fehlenden. Wer eine Regel aendert, moege diese Zahl neu messen.
"""
import re

# slug -> (Anzeigename, Muster). Die Muster laufen gegen den MeSH-Begriff,
# Gross- und Kleinschreibung egal. Der slug MUSS dem SLUG in der portal.json
# des Hubs entsprechen - daran findet die Hinweiskarte spaeter ihr Gebiet.
REGELN = {
    "onkologie": ("Onkologie", [
        r"neoplasm", r"carcinoma", r"\bcancer", r"myeloma", r"leukemia",
        r"lymphoma", r"sarcoma", r"melanoma", r"\btumor", r"glioma",
        r"myelofibrosis", r"myelodysplastic", r"blast crisis", r"mesothelioma",
        # Am 22.10.2026 an den FDA-Texten nachgetragen: Polycythaemia vera und
        # die myeloproliferativen Neoplasien tragen keinen der Staemme oben
        # (MIMRYLO/Rusfertid stand deshalb in keinem Hub).
        r"polycythemia", r"myeloprolifer",
    ]),
    "kardio": ("Kardiologie", [
        r"\bheart", r"cardiac", r"cardiomyo", r"cardiovascular", r"myocardial",
        r"coronary", r"atrial", r"arrhythmi", r"hypertension", r"thromboembolism",
        r"thrombosis", r"\bstroke", r"hyperlipidemi", r"hypercholesterolemi",
        r"dyslipidemi", r"angina", r"aortic", r"amyloidosis, famil",
        # Am 22.10.2026 am zurueckgehaltenen FDA-Satz nachgetragen:
        # CARDAMYST (paroxysmale supraventrikulaere Tachykardie) und
        # REDEMPLO (familiaere Chylomikronaemie) standen in keinem Hub.
        r"tachycardi", r"supraventricular", r"chylomicronemi", r"triglycerid",
    ]),
    "diabetes": ("Diabetes", [
        r"diabet", r"hyperglycemi", r"insulin resistance", r"hypoglycemi",
    ]),
    "adipositas": ("Adipositas", [
        r"obesity", r"overweight", r"weight loss", r"\blipodystroph",
    ]),
    "mental": ("Psychische Gesundheit", [
        r"schizophren", r"depress", r"anxiety", r"bipolar", r"psychotic",
        r"\bmental", r"substance-related", r"alcohol", r"opioid-related",
        r"attention deficit", r"autis", r"insomnia", r"narcolepsy",
        r"post-traumatic", r"obsessive",
    ]),
    "impfen": ("Impfen & Prävention", [
        r"immuni[sz]ation", r"vaccin", r"influenza", r"covid-19", r"meningococc",
        r"pneumococc", r"papillomavirus", r"rotavirus", r"\brabies",
        r"tick-borne", r"\bmpox", r"respiratory syncytial",
    ]),
    "longevity": ("Gesundes Altern & Longevity", [
        r"alzheimer", r"dementia", r"parkinson", r"osteoporosis", r"bone resorption",
        r"frailty", r"sarcopeni", r"\baging", r"\bageing", r"macular degeneration",
        r"\bcataract", r"\bpresbyop",
    ]),
    "ncd": ("Nicht übertragbare Krankheiten", [
        r"asthma", r"pulmonary disease, chronic", r"\bcopd", r"arthritis",
        r"psoriasis", r"crohn", r"colitis", r"multiple sclerosis", r"epilep",
        r"spondylitis", r"lupus", r"\bgout", r"cystic fibrosis",
        r"inflammatory bowel", r"dermatitis", r"chronic kidney",
        r"renal insufficiency, chronic", r"hepatic", r"liver cirrhosis",
        # Ebenfalls am 22.10.2026 nachgetragen. "hepatic" faengt "hepatitis"
        # nicht (HEPCLUDEX gegen Hepatitis delta), und eine Nephropathie
        # steht in der Indikation als solche, nicht als "chronic kidney
        # disease" (TRUTAKNA gegen IgA-Nephropathie).
        r"hepatitis", r"nephropath", r"glomerulonephritis",
        # Ebenfalls aus dem zurueckgehaltenen Satz: LYNAVOY (primaer
        # biliaere Cholangitis), JASCAYD (idiopathische Lungenfibrose),
        # RHAPSIDO (chronische spontane Urtikaria).
        r"cholangitis", r"pulmonary fibrosis", r"urticaria",
    ]),
}

# --------------------------------------------------------------- Diagnostika
# **Ein Diagnostikum gehoert in keinen Hub**, auch wenn seine Indikation eine
# Krankheit nennt - und sie nennt immer eine. PIXCLARA (Floretyrosin F-18)
# dient der Abgrenzung eines Gliomrezidivs und waere am 22.10.2026 ueber das
# Wort "glioma" in der Onkologie gelandet; AMBELVIST ist ein
# Gadolinium-Kontrastmittel. Beide sagen nichts ueber die Behandlung einer
# Krankheit aus, und ein Leser im Onkologie-Hub erwartet dort Therapien.
#
# Das deckt sich mit der EMA-Seite: Dort haben Diagnostika gar kein
# Therapiegebiet und fallen schon deshalb heraus.
DIAGNOSTIK = re.compile(
    r"diagnostic (?:drug|agent|radiopharmaceutical)|contrast agent"
    r"|positron emission tomography|\bPET imaging\b|radioactive diagnostic"
    r"|for use with (?:magnetic resonance|positron)|imaging agent"
    r"|to (?:detect|visuali[sz]e|differentiate) ", re.I)

# Der Satz, der die Indikation TRAEGT. Alles andere im Abschnitt ist
# Begleitwerk - Hinweise zum Risikomanagement, Studienlage, Einschraenkungen.
# BAXFENDY (Baxdrostat, Hypertonie) nennt "diabetes management" zweimal in
# genau solchen Saetzen und landete am 22.10.2026 im Diabetes-Hub. Geprueft
# wird deshalb nur, wo "indicated" steht.
#
# Das abschliessende `|$` ist kein Schoenheitsfehler: Ein Indikationssatz kann
# am Textende abgeschnitten sein, und dann hat er keinen Punkt. Ohne diese
# Alternative findet der Ausdruck gar nichts und die Zuordnung entfaellt
# stillschweigend - derselbe Fall wie oben, nur eine Ebene tiefer.
INDIKATIONSSATZ = re.compile(r"[^.]*\bindicated\b[^.]*(?:\.|$)", re.I)


def hubs_fuer_text(indikation_en: str) -> list[str]:
    """Die Hub-Slugs zu einem englischen Indikationstext (FDA-Stufe).

    Dieselben Muster wie `hubs_fuer()`, aber eine andere Quelle: Die EMA
    liefert ein knappes MeSH-Feld, der Beipackzettel der FDA liefert Prosa.
    Prosa nennt Krankheiten, um die es **nicht** geht. Zwei Vorkehrungen:

      1. Geprueft wird nur der Satz, der "indicated" enthaelt - nicht der
         ganze Abschnitt.
      2. Diagnostika fallen heraus, bevor ein Muster greift.

    Gemessen am 22.10.2026 an 25 Indikationstexten der letzten 180 Tage:
    19 von 25 ohne diese Vorkehrungen richtig, mit ihnen 25 von 25. **Die
    Vorkehrungen sind an genau diesen 25 Faellen entstanden** - die Quote ist
    deshalb keine Vorhersage. Der Gegentest in zulassungen_gegentest.py
    prueft gegen einen zurueckgehaltenen Satz aelterer Zulassungen.
    """
    text = str(indikation_en or "")
    if not text.strip():
        return []
    if DIAGNOSTIK.search(text):
        return []
    saetze = INDIKATIONSSATZ.findall(text)
    # Findet sich kein solcher Satz, ist der Text nicht der Abschnitt, den wir
    # erwarten. Dann lieber nichts zuordnen als den ganzen Text durchsuchen:
    # Ein Eintrag ohne Hub ist sichtbar, eine falsche Zuordnung nicht.
    if not saetze:
        return []
    pruefstueck = " ".join(saetze)
    treffer = []
    for slug, (_, muster) in GEBAUT.items():
        if any(m.search(pruefstueck) for m in muster):
            treffer.append(slug)
    return treffer

GEBAUT = {slug: (name, [re.compile(m, re.I) for m in muster])
          for slug, (name, muster) in REGELN.items()}


def hubs_fuer(mesh_feld: str) -> list[str]:
    """Die Hub-Slugs zu einem MeSH-Feld der EMA-Tabelle.

    Das Feld fuehrt mehrere Begriffe, getrennt durch Semikolon oder
    Zeilenbruch. Jeder wird einzeln geprueft; ein Treffer genuegt.
    """
    roh = [t.strip() for t in str(mesh_feld or "").replace("\n", ";").split(";")]
    # **MeSH dreht die Begriffe um.** In der Tabelle steht "Dermatitis, Atopic"
    # und "Fibrosis, Cystic", nicht die natuerliche Wortfolge. Am 22.10.2026
    # sind daran sieben Mukoviszidose- und vier Neurodermitis-Zulassungen
    # vorbeigelaufen, weil die Muster in natuerlicher Folge geschrieben waren -
    # und zwar lautlos, denn ein nicht zugeordneter Eintrag sieht genauso aus
    # wie einer, der in keinen Hub gehoert. Geprueft wird deshalb gegen beides:
    # den Begriff, wie er dasteht, und die an den Kommas umgedrehte Fassung.
    begriffe = []
    for t in roh:
        if not t:
            continue
        begriffe.append(t)
        if "," in t:
            begriffe.append(" ".join(reversed([x.strip() for x in t.split(",")])))
    treffer = []
    for slug, (_, muster) in GEBAUT.items():
        if any(m.search(b) for b in begriffe for m in muster):
            treffer.append(slug)
    return treffer


# --------------------------------------------------------------- DiGA
# Digitale Gesundheitsanwendungen kommen aus einer anderen Quelle und tragen
# **kein Anwendungsgebiet**: Die Bekanntmachung des BfArM nennt nur
# Bezeichnung, DiGA-ID, Datum und Hersteller. Das Verzeichnis selbst kennt die
# Indikation samt ICD-Schluessel, aber nur hinter einer Schnittstelle, die
# von aussen mit 401 antwortet.
#
# Zugeordnet wird deshalb nach dem **Namen**, und das geht erstaunlich weit:
# DiGA heissen "Oviva Direkt für Adipositas", "HelloBetter Diabetes",
# "Pia-App bei Regelschmerzen". Was sich daraus nicht erschliesst, steht
# trotzdem im Digitalisierungs-Hub - dort gehoert jede DiGA hin, unabhaengig
# vom Krankheitsbild.
DIGA_HEIMAT = "ki-gesundheit"
DIGA_HEIMAT_NAME = "Digitalisierung, KI & Gesundheit"

DIGA_MUSTER = {
    "diabetes": [r"diabet", r"\bhba1c"],
    "adipositas": [r"adipositas", r"abnehm", r"gewicht", r"\bovivA?\b"],
    "mental": [r"depress", r"angst", r"panik", r"schlaf", r"insomn", r"stress",
               r"burnout", r"sucht", r"alkohol", r"psych", r"vaginismus"],
    "onkologie": [r"krebs", r"cancer", r"tumor", r"onkolog", r"mamma"],
    "kardio": [r"herz", r"blutdruck", r"hyperton", r"kardio"],
    "ncd": [r"schmerz", r"rücken", r"ruecken", r"arthros", r"rheuma", r"copd",
            r"asthma", r"tinnitus", r"migräne", r"migraene", r"reizdarm",
            r"multiple sklerose"],
    "longevity": [r"demen", r"alzheim", r"sturz", r"osteoporos"],
}
DIGA_GEBAUT = {slug: [re.compile(m, re.I) for m in muster]
               for slug, muster in DIGA_MUSTER.items()}

NAMEN_SONST = {DIGA_HEIMAT: DIGA_HEIMAT_NAME}


def hubs_fuer_diga(bezeichnung: str) -> list[str]:
    """Die Hub-Slugs zu einer DiGA - immer der Digitalisierungs-Hub, dazu was
    der Name hergibt."""
    treffer = [DIGA_HEIMAT]
    for slug, muster in DIGA_GEBAUT.items():
        if any(m.search(bezeichnung or "") for m in muster):
            treffer.append(slug)
    return treffer


def name_von(slug: str) -> str:
    if slug in GEBAUT:
        return GEBAUT[slug][0]
    return NAMEN_SONST.get(slug, slug)
