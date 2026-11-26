"""Modèle de popularité estimé à partir des rapports officiels."""

import random
import statistics

import pytest

from proba_loto.grilles import Grille
from proba_loto.jeux import EUROMILLIONS as EM, LOTO
from proba_loto.popularite import _resoudre, estimer_popularite, indice_par_defaut


def test_modele_valide_hors_echantillon(modele):
    assert modele.correlation_validation > 0.9
    assert modele.nb_tirages >= 1061


def test_numeros_et_etoiles_les_plus_et_moins_joues(modele):
    plus_joues = [n for n, _ in modele.classement_numeros()[:5]]
    moins_joues = [n for n, _ in modele.classement_numeros()[-5:]]
    assert 7 in plus_joues
    assert all(n > 31 for n in moins_joues)
    assert modele.classement_etoiles()[0][0] == 7
    assert modele.classement_etoiles()[-1][0] == 12
    dates = [f for n, f in modele.facteurs_numeros.items() if n <= 31]
    autres = [f for n, f in modele.facteurs_numeros.items() if n > 31]
    assert statistics.mean(dates) > 1 > statistics.mean(autres)
    assert statistics.mean(modele.facteurs_numeros.values()) == pytest.approx(1)
    assert statistics.mean(modele.facteurs_etoiles.values()) == pytest.approx(1)


def test_indice_moyen_vaut_un(modele):
    rng = random.Random(1)
    indices = [
        modele.indice(Grille.simple(EM, rng.sample(range(1, 51), 5), rng.sample(range(1, 13), 2)))
        for _ in range(20_000)
    ]
    assert statistics.mean(indices) == pytest.approx(1.0, abs=0.02)


def test_indices_extremes(modele):
    assert modele.indice(Grille.depuis_texte(EM, "7 13 17 19 23 + 3 7")) > 2
    assert modele.indice(Grille.depuis_texte(EM, "36 41 43 46 48 + 11 12")) < 0.4
    with pytest.raises(ValueError):
        modele.indice(Grille.depuis_texte(EM, "1 2 3 4 5 6 + 1 2"))
    with pytest.raises(ValueError):
        modele.indice(Grille.depuis_texte(LOTO, "1 2 3 4 5 + 1"))


def test_modele_neutre_et_donnees_insuffisantes(historique):
    neutre = indice_par_defaut()
    assert neutre.indice(Grille.depuis_texte(EM, "1 2 3 4 5 + 1 2")) == pytest.approx(1)
    assert not neutre.estime_sur_donnees
    with pytest.raises(ValueError):
        estimer_popularite(historique[:50])


def test_solveur_lineaire():
    assert _resoudre([[2.0, 1.0], [1.0, 3.0]], [3.0, 5.0]) == pytest.approx([0.8, 1.4])
    with pytest.raises(ValueError):
        _resoudre([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0])
