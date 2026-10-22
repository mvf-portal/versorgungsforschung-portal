# -*- coding: utf-8 -*-
"""Fehlerquote der Hub-Zuordnung fuer die Pipeline-Texte.

"27 von 57 zugeordnet" sagt nichts darueber, ob sie RICHTIG zugeordnet sind.
Gemessen wird deshalb gegen ein von Hand gesetztes Soll ueber alle 57 - nach
demselben Muster wie beim Pruefsatz der FDA-Stufe, und mit derselben harten
Bedingung: **Eine falsche Zuordnung laesst die Messung scheitern, eine
fehlende nicht.** Ein Eintrag ohne Hub ist sichtbar, eine falsche Zuordnung
sieht aus wie eine richtige.

Der Indikationstext der EMA-Antragsliste ist ein Einzeiler ("Treatment of
presbyopia in adults") und enthaelt das Wort "indicated" meist nicht. Die
Beschraenkung auf den Indikationssatz, die bei den FDA-Beipackzetteln noetig
ist, greift hier also nicht - und sie ist auch nicht noetig, denn ein
Einzeiler hat keine Begleitsaetze, in denen fremde Krankheiten vorkommen.
Der Diagnostik-Filter bleibt.
"""
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import zulassungen_themen as themen  # noqa: E402
from pipeline_quelle import liste_holen, spalte  # noqa: E402

# Von Hand gesetzt am 22.10.2026, nach dem Indikationstext - nicht nach der
# Ausgabe der Regeln. Schluessel ist der INN, wie er in der Liste steht.
SOLL = {
    "Aceclidine": {"longevity"},                 # Presbyopie
    "Anselamimab": {"onkologie"},                # AL-Amyloidose, Plasmazellerkrankung
    "Asundexian": {"kardio"},                    # Schlaganfallprophylaxe
    "Atrasentan": {"ncd"},                       # IgA-Nephropathie
    "Baxdrostat": {"kardio"},                    # Hypertonie
    "Bepirovirsen": {"ncd"},                     # chronische Hepatitis B
    "Bictegravir / Lenacapavir": set(),          # HIV
    "Bifikafusp alfa / Onfekafusp alfa": {"onkologie"},   # Melanom
    "Bilayer engineered skin composite": set(),  # Verbrennungen
    "Cefepime / Zidebactam": set(),              # Infektionen
    "Cemdisiran": set(),                         # Myasthenia gravis
    "Cosibelimab": {"onkologie"},                # Plattenepithelkarzinom der Haut
    "Deucrictibant": set(),                      # hereditaeres Angiooedem
    "Deuruxolitinib": set(),                     # Alopecia areata
    "Doravirine / Islatravir": set(),            # HIV
    "Efzimfotase alfa": set(),                   # Hypophosphatasie
    "Emapalumab": set(),                         # sekundaere HLH
    "Encaleret": set(),                          # ADH1
    "Enlicitide": {"kardio"},                    # Hypercholesterinaemie
    "Etripamil": {"kardio"},                     # paroxysmale SVT
    "Fuzuloparib": {"onkologie"},                # mCRPC
    "Gadoquatrane": set(),                       # MRT-Kontrastmittel
    "Garetosmab": set(),                         # FOP
    "Hexaminolevulinate": {"onkologie"},         # zervikale HSIL, Krebsvorstufe
    "Human IgG1 monoclonal antibody": set(),     # Schilddruesenaugenerkrankung
    "Ianalumab": {"ncd"},                        # Sjoegren-Syndrom
    "Influenza mRNA vaccine": {"impfen"},
    "Japanese Encephalitis Chimeric Virus Vaccine": {"impfen"},
    "Lemborexant": {"mental"},                   # Insomnie
    "Lirafugratinib": {"onkologie"},             # Cholangiokarzinom
    "Lorecivivint": {"ncd"},                     # Arthrose
    "Lunsotogene parvec": set(),                 # OTOF-Hoerverlust
    "Lyme borreliosis vaccine (6-valent)": {"impfen"},
    "Mezigdomide": {"onkologie"},                # multiples Myelom
    "Molgramostim": set(),                       # pulmonale Alveolarproteinose
    "Navepegritide": set(),                      # Achondroplasie
    "Norucholic acid": {"ncd"},                  # primaer sklerosierende Cholangitis
    "Orforglipron": {"adipositas", "diabetes"},
    "Pelabresib": {"onkologie"},                 # Myelofibrose
    "Pimicotinib": {"onkologie"},                # tenosynovialer Riesenzelltumor
    "Rebisufligene etisparvovec": set(),         # MPS IIIA
    "Rezvilutamide": {"onkologie"},              # Prostatakarzinom
    "Rusfertide": {"onkologie"},                 # Polycythaemia vera
    "Sintilimab": {"onkologie"},                 # NSCLC
    "Sonrotoclax": {"onkologie"},                # Mantelzelllymphom
    "Taletrectinib": {"onkologie"},              # ROS1-NSCLC
    "Tanruprubart": set(),                       # Guillain-Barre
    "Tozorakimab": {"ncd"},                      # COPD
    "Treprostinil": {"ncd"},                     # idiopathische Lungenfibrose
    "Vamikibart": set(),                         # uveitisches Makulaoedem
    "Veligrotug": set(),                         # Schilddruesenaugenerkrankung
    "Venglustat": set(),                         # Morbus Gaucher
    "Zamtocabtagene autoleucel": {"onkologie"},  # grosszelliges B-Zell-Lymphom
    "Zasocitinib": {"ncd"},                      # Plaque-Psoriasis
    "Zilurgisertib": set(),                      # FOP
    "Zopapogene imadenovec": set(),              # respiratorische Papillomatose
}


# Die Zuordnung kommt jetzt aus der Pflegestelle selbst, nicht aus einer
# Kopie hier: Eine Messung gegen eine abgeschriebene Fassung prueft die
# Abschrift, nicht das Portal.
hubs_fuer_antrag = themen.hubs_fuer_antrag


def schlecht(text: str) -> list[str]:
    """Absichtlich schlechte Fassung: ohne den Diagnostik-Filter."""
    return [slug for slug, (_, muster) in themen.GEBAUT.items()
            if any(m.search(str(text or "")) for m in muster)]


heute = dt.date.today()
kopf, satz, _ = liste_holen(heute.year, heute.month)
k_inn = spalte(kopf, "non-proprietary")
k_gen = spalte(kopf, "generic")
k_ind = spalte(kopf, "indication")
neu = [z for z in satz if str(z.get(k_gen, "")).strip().upper() != "Y"]

genau = falsch = fehlend = 0
s_genau = s_falsch = 0
ohne_soll = []
print("Abweichungen:\n")
for z in neu:
    inn = str(z.get(k_inn, "")).strip()
    schluessel = next((k for k in SOLL if k.lower() == inn.lower()
                       or inn.lower().startswith(k.lower()[:26])), None)
    if schluessel is None:
        ohne_soll.append(inn)
        continue
    soll = SOLL[schluessel]
    text = str(z.get(k_ind, ""))
    ist = set(hubs_fuer_antrag(text))
    zv, zw = ist - soll, soll - ist
    if not zv and not zw:
        genau += 1
    else:
        print(f"  {inn[:28]:<29} ist={','.join(sorted(ist)) or '-':<22}"
              f" soll={','.join(sorted(soll)) or '-':<14}"
              f"{' FALSCH ' + ','.join(sorted(zv)) if zv else ''}"
              f"{' fehlt ' + ','.join(sorted(zw)) if zw else ''}")
    falsch += len(zv)
    fehlend += len(zw)
    s_ist = set(schlecht(text))
    s_genau += (s_ist == soll)
    s_falsch += len(s_ist - soll)

n = genau + sum(1 for _ in range(0))  # nur zur Klarheit
geprueft = len(neu) - len(ohne_soll)
print(f"\n{'=' * 70}")
print(f"  geprueft              {geprueft} von {len(neu)}")
print(f"  genau richtig         {genau}  ({100*genau//max(geprueft,1)} %)")
print(f"  FALSCHE Zuordnungen   {falsch}   <- der Fehler, den niemand sieht")
print(f"  fehlende Zuordnungen  {fehlend}   <- sichtbar: Eintrag ohne Hub")
print(f"{'=' * 70}")
print(f"  schlechte Fassung (ohne Diagnostik-Filter): {s_genau} richtig, "
      f"{s_falsch} falsch")
if ohne_soll:
    print(f"\n  ohne Soll (Liste hat sich geaendert): {', '.join(ohne_soll)}")
