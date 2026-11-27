"""Saisie, validation, vérification des grilles et grilles multiples."""

import random
from collections import Counter
from fractions import Fraction

import pytest

from proba_loto.grilles import (
    ErreurGrille,
    Grille,
    configurations_multiples,
    nb_combinaisons_simples,
    repartition_gains,
    verifier,
)
from proba_loto.jeux import ETOILE_PLUS, EUROMILLIONS as EM, LOTO
from proba_loto.multiples import analyser_multiple, cout_multiple
from proba_loto.probabilites import probabilite_gain, probabilite_rang

# Tableau officiel des combinaisons multiples EuroMillions (art. 3.1) :
# numéros → {étoiles : nombre de grilles simples}.
TABLEAU_FDJ_EUROMILLIONS = {
    5: {2: 1, 3: 3, 4: 6, 5: 10, 6: 15, 7: 21, 8: 28, 9: 36, 10: 45, 11: 55, 12: 66},
    6: {2: 6, 3: 18, 4: 36, 5: 60, 6: 90, 7: 126, 8: 168, 9: 216, 10: 270, 11: 330, 12: 396},
    7: {2: 21, 3: 63, 4: 126, 5: 210, 6: 315},
    8: {2: 56, 3: 168, 4: 336},
    9: {2: 126, 3: 378},
    10: {2: 252},
}
# Tableau officiel Loto (art. 3.1.1.6 et 5.1) : numéros → N° Chance autorisés.
TABLEAU_FDJ_LOTO = {5: range(1, 11), 6: range(1, 11), 7: range(1, 9), 8: range(1, 4), 9: range(1, 2)}


def test_formats_de_saisie_equivalents():
    attendu = Grille.simple(EM, [3, 5, 37, 44, 49], [5, 6])
    for texte in (
        "3 5 37 44 49 + 5 6",
        "3-5-37-44-49 / 5-6",
        "3,5,37,44,49 étoiles 5,6",
        "49 44 37 5 3 * 6 5",
        "03 05 37 44 49 ★ 05 06",
        "3 5 37 44 49 5 6",
    ):
        assert Grille.depuis_texte(EM, texte) == attendu
    assert Grille.depuis_texte(LOTO, "1 2 3 4 5 chance 7") == Grille.simple(LOTO, [1, 2, 3, 4, 5], [7])


def test_numeros_tries_et_affichage():
    grille = Grille.simple(EM, [49, 3, 44, 5, 37], [6, 5])
    assert grille.numeros == (3, 5, 37, 44, 49)
    assert grille.bonus == (5, 6)
    assert str(grille) == "03 05 37 44 49  ★  05 06"
    assert repr(grille) == "Grille(euromillions: 03 05 37 44 49  ★  05 06)"
    assert str(Grille.simple(LOTO, [1, 2, 3, 4, 5], [7])) == "01 02 03 04 05  |  N° Chance 7"


@pytest.mark.parametrize(
    "texte, message",
    [
        ("1 2 3 4 4 + 1 2", "en double"),
        ("1 2 3 4 51 + 1 2", "hors bornes"),
        ("1 2 3 4 5 + 1 13", "hors bornes"),
        ("1 2 3 4 + 1 2", "de 5 à 10 numéros"),
        ("1 2 3 4 5 + 1", "de 2 à 12"),
        ("1 2 3 4 5 6 7 8 9 10 11 + 1 2", "de 5 à 10 numéros"),
        ("1 2 3 4 5 6 7 8 + 1 2 3 4 5", "396"),
        ("1 2 3 4 5 6", "séparez"),
    ],
)
def test_grilles_invalides(texte, message):
    with pytest.raises(ErreurGrille, match=message):
        Grille.depuis_texte(EM, texte)


def test_grille_simple_exigee():
    with pytest.raises(ErreurGrille, match="exactement"):
        Grille.depuis_texte(EM, "1 2 3 4 5 6 + 1 2", autoriser_multiple=False)
    with pytest.raises(ErreurGrille):
        Grille.depuis_texte(LOTO, "1 2 3 4 5 + 11")


def test_tableau_officiel_des_multiples_euromillions():
    autorisees = {}
    for n, e in configurations_multiples(EM):
        autorisees.setdefault(n, {})[e] = nb_combinaisons_simples(EM, n, e)
    assert autorisees == TABLEAU_FDJ_EUROMILLIONS
    # Prix publiés : 6 numéros × 3 étoiles = 45 € ; 7 × 6 = 787,50 € ; 10 × 2 = 630 €.
    assert cout_multiple(EM, 6, 3) == 45
    assert cout_multiple(EM, 7, 6) == Fraction("787.5")
    assert cout_multiple(EM, 10, 2) == 630
    # Avec Étoile+ : 3,50 € la grille simple, 1 386 € pour 6 × 12, 1 323 € pour 9 × 3.
    assert cout_multiple(EM, 5, 2, [ETOILE_PLUS]) == Fraction("3.5")
    assert cout_multiple(EM, 6, 12, [ETOILE_PLUS]) == 1386
    assert cout_multiple(EM, 9, 3, [ETOILE_PLUS]) == 1323


def test_tableau_officiel_des_multiples_loto():
    autorisees = {}
    for n, c in configurations_multiples(LOTO):
        autorisees.setdefault(n, []).append(c)
    assert autorisees == {n: list(r) for n, r in TABLEAU_FDJ_LOTO.items()}
    assert cout_multiple(LOTO, 9, 1) == Fraction("277.2")
    assert cout_multiple(LOTO, 8, 3) == Fraction("369.6")
    assert cout_multiple(LOTO, 6, 10) == 132


def test_rang_de_chaque_correspondance():
    tirage = Grille.simple(EM, [1, 2, 3, 4, 5], [1, 2])
    attendus = {(5, 2): 1, (5, 1): 2, (5, 0): 3, (4, 2): 4, (4, 1): 5, (3, 2): 6, (4, 0): 7,
                (2, 2): 8, (3, 1): 9, (3, 0): 10, (1, 2): 11, (2, 1): 12, (2, 0): 13}
    for a in range(6):
        for b in range(3):
            numeros = list(range(1, a + 1)) + list(range(40, 45 - a))
            etoiles = list(range(1, b + 1)) + list(range(10, 12 - b))
            resultat = verifier(Grille.simple(EM, numeros, etoiles), tirage)
            rang = resultat.rang.numero if resultat.rang else None
            assert rang == attendus.get((a, b)), (a, b)


def test_multiple_identique_a_la_decomposition():
    rng = random.Random(2024)
    for _ in range(40):
        n, e = rng.choice(list(configurations_multiples(EM)))
        grille = Grille(EM, tuple(rng.sample(range(1, 51), n)), tuple(rng.sample(range(1, 13), e)))
        tirage = Grille.simple(EM, rng.sample(range(1, 51), 5), rng.sample(range(1, 13), 2))
        for table in (EM.gains, ETOILE_PLUS):
            attendu = Counter()
            for simple in grille.combinaisons_simples():
                rang = verifier(simple, tirage, table).rang
                if rang:
                    attendu[rang.numero] += 1
            assert verifier(grille, tirage, table).gains == dict(sorted(attendu.items()))
        assert sum(1 for _ in grille.combinaisons_simples()) == grille.nb_combinaisons_simples


def test_verification_tirage_et_jeux():
    grille = Grille.depuis_texte(EM, "3 5 37 44 49 10 + 5 6 9")
    tirage = Grille.depuis_texte(EM, "3 5 37 44 49 + 5 6")
    resultat = verifier(grille, tirage)
    assert resultat.gains == {1: 1, 2: 2, 4: 5, 5: 10}
    assert resultat.rang.numero == 1
    assert resultat.nb_gagnantes == 18
    with pytest.raises(ErreurGrille):
        verifier(tirage, grille)  # un tirage ne peut pas être une multiple
    with pytest.raises(ErreurGrille):
        verifier(Grille.depuis_texte(LOTO, "1 2 3 4 5 + 1"), tirage)


def test_repartition_reproduit_le_tableau_fdj():
    # 6 numéros dont 5 bons, 3 étoiles dont 2 bonnes.
    assert repartition_gains(EM, 6, 3, 5, 2) == {1: 1, 2: 2, 4: 5, 5: 10}


def test_analyse_multiple():
    simple = analyser_multiple(EM, 5, 2)
    assert simple.probabilite_gain == probabilite_gain(EM)
    multiple = analyser_multiple(EM, 7, 3)
    assert multiple.nb_simples == 63
    assert sum(s.probabilite for s in multiple.scenarios) == 1
    # Au plus une combinaison peut être au rang 1 : 63 chances sur 139 838 160.
    assert multiple.probabilite_au_moins_un()[1] == Fraction(63, 139_838_160)
    # Linéarité de l'espérance : nb moyen de grilles gagnantes = 63 × P(rang).
    for rang, esperance in multiple.esperance_gagnantes().items():
        assert esperance == 63 * probabilite_rang(EM, EM.gains.rang(rang))
    assert sum(multiple.probabilite_meilleur_rang().values()) == multiple.probabilite_gain
    with pytest.raises(ErreurGrille):
        analyser_multiple(EM, 8, 5)
