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
    ]),
    "kardio": ("Kardiologie", [
        r"\bheart", r"cardiac", r"cardiomyo", r"cardiovascular", r"myocardial",
        r"coronary", r"atrial", r"arrhythmi", r"hypertension", r"thromboembolism",
        r"thrombosis", r"\bstroke", r"hyperlipidemi", r"hypercholesterolemi",
        r"dyslipidemi", r"angina", r"aortic", r"amyloidosis, famil",
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
    ]),
}

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


def name_von(slug: str) -> str:
    return GEBAUT[slug][0] if slug in GEBAUT else slug
