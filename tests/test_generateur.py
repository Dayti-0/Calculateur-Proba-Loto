"""Générateurs de grilles : validité, reproductibilité, corrections des anciens bugs."""

import random
import statistics
from collections import Counter

import pytest

from proba_loto.analyse import motifs_populaires, profil_equilibre
from proba_loto.generateur import STRATEGIES, Generateur
from proba_loto.grilles import ErreurGrille, Grille
from proba_loto.jeux import EUROMILLIONS as EM, LOTO
from proba_loto.popularite import indice_par_defaut
from proba_loto.statistiques import khi2_uniformite


def _valide(grille, jeu):
    assert len(grille.numeros) == jeu.numeros_par_grille == len(set(grille.numeros))
    assert len(grille.bonus) == jeu.bonus_par_grille == len(set(grille.bonus))
    assert all(1 <= n <= jeu.numeros_max for n in grille.numeros)
    assert all(1 <= b <= jeu.bonus_max for b in grille.bonus)
    assert list(grille.numeros) == sorted(grille.numeros)


@pytest.mark.parametrize("jeu", [EM, LOTO])
@pytest.mark.parametrize("strategie", STRATEGIES)
def test_toutes_les_strategies_produisent_des_grilles_valides(jeu, strategie):
    grilles = Generateur(jeu, graine=1).grilles(60, strategie)
    assert len(grilles) == 60 == len(set(grilles))
    for grille in grilles:
        _valide(grille, jeu)


def test_graine_reproductible_et_aleatoire_systeme_par_defaut():
    assert Generateur(EM, graine=5).grilles(5) == Generateur(EM, graine=5).grilles(5)
    assert Generateur(EM, graine=5).grilles(5) != Generateur(EM, graine=6).grilles(5)
    assert isinstance(Generateur(EM).rng, random.SystemRandom)


def test_aleatoire_uniforme():
    grilles = Generateur(EM, graine=123).grilles(20_000, distinctes=False)
    numeros = Counter(n for g in grilles for n in g.numeros)
    etoiles = Counter(e for g in grilles for e in g.bonus)
    assert khi2_uniformite(numeros, 50, 5, len(grilles)).p_valeur > 0.001
    assert khi2_uniformite(etoiles, 12, 2, len(grilles)).p_valeur > 0.001


def test_un_seul_favori_ne_plante_plus():
    # Ancien bug : random.randint(2, 1) → ValueError avec un seul favori.
    grille = Generateur(EM, graine=1).grille("aleatoire", [7])
    assert 7 in grille.numeros


def test_favoris_inclus_et_sous_ensemble_si_trop_nombreux():
    favoris = [1, 2, 3, 4, 5, 6, 7, 8]
    for grille in Generateur(EM, graine=3).grilles(30, "aleatoire", favoris, [3]):
        assert set(grille.numeros) <= set(favoris)
        assert 3 in grille.bonus
    grille = Generateur(EM, graine=3).grille("anti-partage", [7, 13], [5])
    assert {7, 13} <= set(grille.numeros) and 5 in grille.bonus


def test_favoris_invalides_refuses():
    # Ancien bug : des favoris en double produisaient des grilles avec doublons.
    with pytest.raises(ErreurGrille, match="double"):
        Generateur(EM).grille("aleatoire", [7, 7, 7])
    with pytest.raises(ErreurGrille, match="hors bornes"):
        Generateur(EM).grille("aleatoire", [51])
    with pytest.raises(ErreurGrille, match="hors bornes"):
        Generateur(EM).grille("aleatoire", [], [13])


def test_equilibree_respecte_le_profil():
    for grille in Generateur(EM, graine=8).grilles(100, "equilibree"):
        assert profil_equilibre(grille)


def test_anti_partage_avec_modele(modele, historique):
    dernier = historique[-1].combinaison
    generateur = Generateur(EM, graine=4, modele=modele, dernier_tirage=dernier)
    grilles = generateur.grilles(300, "anti-partage")
    indices = [modele.indice(g) for g in grilles]
    assert statistics.median(indices) < 0.6
    assert all(not motifs_populaires(g, dernier) for g in grilles)
    # Pas de concentration excessive : les 50 numéros restent utilisés.
    assert len({n for g in grilles for n in g.numeros}) >= 45
    aleatoires = [modele.indice(g) for g in Generateur(EM, graine=4).grilles(300)]
    assert statistics.mean(aleatoires) == pytest.approx(1.0, abs=0.1)


def test_anti_partage_sans_donnees():
    generateur = Generateur(EM, graine=2, modele=indice_par_defaut())
    for grille in generateur.grilles(100, "anti-partage"):
        assert sum(1 for n in grille.numeros if n > 31) >= 2
        assert not motifs_populaires(grille)


def test_couverture():
    grilles = Generateur(EM, graine=7).grilles(10, "couverture")
    assert sorted(n for g in grilles for n in g.numeros) == list(range(1, 51))
    six = Generateur(EM, graine=7).grilles(6, "couverture")
    assert sorted(e for g in six for e in g.bonus) == list(range(1, 13))
    avec_favori = Generateur(EM, graine=7).grilles(5, "couverture", [7])
    assert all(7 in g.numeros for g in avec_favori)
    with pytest.raises(ErreurGrille):
        Generateur(EM).grilles(2, "couverture", [1, 2, 3, 4, 5, 6])


def test_parametres_invalides():
    with pytest.raises(ValueError):
        Generateur(EM).grille("magique")
    with pytest.raises(ValueError):
        Generateur(EM).grilles(0)
    with pytest.raises(ErreurGrille):
        # 5 favoris imposés : une seule grille possible, pas deux distinctes.
        Generateur(EM, graine=1).grilles(2, "aleatoire", [1, 2, 3, 4, 5], [1, 2])


def test_grille_retournee_est_bien_une_grille():
    assert isinstance(Generateur(LOTO, graine=1).grille(), Grille)
