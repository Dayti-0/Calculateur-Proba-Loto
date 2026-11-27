"""Probabilités exactes, comparées aux tableaux des règlements officiels FDJ."""

import itertools
import math
from fractions import Fraction

import pytest

from proba_loto.jeux import (
    ETOILE_PLUS,
    EUROMILLIONS as EM,
    Jeu,
    Rang,
    TableDeGains,
    obtenir_jeu,
)
from proba_loto.probabilites import (
    distribution_somme,
    gain_moyen_theorique,
    nb_combinaisons,
    nb_correspondances,
    nb_tirages_pour,
    probabilite,
    probabilite_au_moins_une_fois,
    probabilite_gain,
    probabilite_rang,
    tableau_probabilites,
)

# Règlement EuroMillions (art. 4.2.3.3) : « une chance sur », arrondi au dixième.
COTES_EUROMILLIONS = {
    1: 139_838_160.0,
    2: 6_991_908.0,
    3: 3_107_514.7,
    4: 621_502.9,
    5: 31_075.2,  # valeur exacte 31 075,15 : la FDJ arrondit au dixième supérieur
    6: 14_125.1,
    7: 13_811.2,
    8: 985.5,
    9: 706.3,
    10: 313.9,
    11: 187.7,
    12: 49.3,
    13: 21.9,
}
# Règlement Étoile+ (art. 6.1.3).
COTES_ETOILE_PLUS = {
    1: 6_991_908.0,
    2: 621_502.9,
    3: 31_075.2,
    4: 14_125.1,
    5: 985.5,
    6: 706.3,
    7: 187.7,
    8: 114.5,
    9: 49.3,
    10: 5.7,
}
def test_nombre_de_combinaisons():
    assert nb_combinaisons(EM) == 139_838_160 == math.comb(50, 5) * math.comb(12, 2)


@pytest.mark.parametrize("rang, cote", COTES_EUROMILLIONS.items())
def test_cotes_euromillions_conformes_au_reglement(rang, cote):
    p = probabilite_rang(EM, EM.gains.rang(rang))
    assert float(1 / p) == pytest.approx(cote, abs=0.1)


@pytest.mark.parametrize("rang, cote", COTES_ETOILE_PLUS.items())
def test_cotes_etoile_plus_conformes_au_reglement(rang, cote):
    p = probabilite_rang(EM, ETOILE_PLUS.rang(rang))
    assert float(1 / p) == pytest.approx(cote, abs=0.1)


def test_probabilites_globales():
    # « environ une chance sur 13 ».
    assert float(1 / probabilite_gain(EM)) == pytest.approx(12.97, abs=0.005)
    # Le règlement annonce « environ 4,8 » pour Étoile+, mais ses propres rangs
    # totalisent 29 594 459 combinaisons gagnantes, soit 1 sur 4,73.
    total_etoile_plus = sum(
        nb_correspondances(EM, a, b) for r in ETOILE_PLUS.rangs for a, b in r.correspondances
    )
    assert total_etoile_plus == 29_594_459
    assert float(1 / probabilite_gain(EM, ETOILE_PLUS)) == pytest.approx(4.725, abs=0.001)


def test_la_somme_de_toutes_les_issues_vaut_exactement_un():
    jeu = EM
    total = sum(
        probabilite(jeu, a, b)
        for a in range(jeu.numeros_par_grille + 1)
        for b in range(jeu.bonus_par_grille + 1)
    )
    assert total == 1


def test_formule_validee_par_enumeration_sur_un_jeu_reduit():
    """Sur un petit jeu, l'énumération exhaustive confirme la formule hypergéométrique."""
    jeu = Jeu(
        cle="mini",
        nom="Mini",
        numeros_max=9,
        numeros_par_grille=3,
        bonus_max=5,
        bonus_par_grille=2,
        bonus_nom="bonus",
        bonus_nom_pluriel="bonus",
        prix_grille=Fraction(1),
        gains=TableDeGains("Mini", (Rang(1, ((3, 2),)),), Fraction(1), Fraction(1, 2)),
        options=(),
        multiple_numeros_max=3,
        multiple_bonus_max=2,
        multiple_combinaisons_max=1,
        jours_tirage=("lundi",),
        reference="test",
    )
    tirage_numeros, tirage_bonus = {1, 2, 3}, {1, 2}
    comptes = {}
    for numeros in itertools.combinations(range(1, 10), 3):
        for bonus in itertools.combinations(range(1, 6), 2):
            cle = (len(tirage_numeros & set(numeros)), len(tirage_bonus & set(bonus)))
            comptes[cle] = comptes.get(cle, 0) + 1
    for (a, b), nombre in comptes.items():
        assert nb_correspondances(jeu, a, b) == nombre
    assert sum(comptes.values()) == nb_combinaisons(jeu)


def test_tableau_et_libelles():
    lignes = tableau_probabilites(EM)
    assert [ligne.rang.numero for ligne in lignes] == list(range(1, 14))
    assert lignes[0].libelle == "5 numéros + 2 étoiles"
    assert lignes[10].libelle == "1 numéro + 2 étoiles"
    assert lignes[12].libelle == "2 numéros + 0 étoile"
    assert lignes[0].cas_favorables == 1


def test_parts_reglementaires():
    parts_em = sum(r.part for r in EM.gains.rangs)
    assert parts_em == Fraction("0.90")  # + 10 % pour le Fonds de Super Cagnotte
    assert sum(r.part for r in ETOILE_PLUS.rangs) == 1
    assert EM.gains.masse_par_grille == Fraction("1.10")
    assert ETOILE_PLUS.masse_par_grille == Fraction("0.60")


def test_gain_moyen_theorique():
    assert gain_moyen_theorique(EM, EM.gains.rang(13)) == pytest.approx(3.996, abs=0.001)
    assert gain_moyen_theorique(EM, EM.gains.rang(1)) is None  # jackpot variable
    assert gain_moyen_theorique(EM, ETOILE_PLUS.rang(10), ETOILE_PLUS) == pytest.approx(2.50, abs=0.01)


def test_probabilite_au_moins_une_fois_stable_pour_les_petites_probabilites():
    p = 1 / 139_838_160
    assert probabilite_au_moins_une_fois(p, 139_838_160) == pytest.approx(1 - math.exp(-1), rel=1e-6)
    assert probabilite_au_moins_une_fois(p, 1) == pytest.approx(p, rel=1e-9)
    assert probabilite_au_moins_une_fois(0, 10) == 0
    assert probabilite_au_moins_une_fois(1, 10) == 1


def test_nb_tirages_pour():
    assert nb_tirages_pour(0.5, 0.5) == pytest.approx(1)
    p = 1 / 139_838_160
    assert nb_tirages_pour(p, 0.5) == pytest.approx(math.log(2) * 139_838_160, rel=1e-6)
    with pytest.raises(ValueError):
        nb_tirages_pour(p, 1.5)


def test_distribution_des_sommes():
    sommes = distribution_somme(EM)
    assert sum(sommes) == math.comb(50, 5)
    assert sommes[15] == 1 and sommes[240] == 1 and sum(sommes[:15]) == 0
    moyenne = sum(s * n for s, n in enumerate(sommes)) / sum(sommes)
    assert moyenne == pytest.approx(127.5)
    assert sommes[100] == sommes[255 - 100]  # symétrie autour de 127,5


def test_saisies_invalides():
    with pytest.raises(ValueError):
        nb_correspondances(EM, 6, 0)
    with pytest.raises(ValueError):
        nb_correspondances(EM, 2, 3)
    assert obtenir_jeu("EuroMillions") is EM
    assert obtenir_jeu("em") is EM
    with pytest.raises(KeyError):
        obtenir_jeu("loto")
    assert EM.option("etoile+") is ETOILE_PLUS
    with pytest.raises(KeyError):
        EM.option("super")
