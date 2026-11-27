"""Simulation de Monte-Carlo."""

import random

import pytest

from proba_loto.simulation import _poisson, simuler


def test_simulation_reproductible_et_coherente():
    a = simuler(annees=2, joueurs=200, graine=11)
    b = simuler(annees=2, joueurs=200, graine=11)
    assert a.bilans == b.bilans
    assert a.tirages == round(2 * 52.1775 * 2)
    assert a.mise_par_joueur == pytest.approx(2.5 * a.tirages)
    # Sans jackpot ni My Million (quasi impossibles ici), on récupère ≈ 0,44 € par grille.
    assert a.taux_retour == pytest.approx(0.176, abs=0.03)
    assert a.part_joueurs_gagnants < 0.05
    assert a.gain_median <= a.meilleur_bilan
    assert sum(n for (jeu, _), n in a.victoires.items() if jeu == "EuroMillions") > 0


def test_simulation_avec_etoile_plus_et_plusieurs_grilles():
    r = simuler(annees=1, joueurs=50, grilles_par_tirage=3, etoile_plus=True, graine=2)
    assert r.mise_par_joueur == pytest.approx(3.5 * 3 * r.tirages)
    assert any(jeu == "Étoile+" for jeu, _ in r.victoires)


def test_parametres_invalides():
    with pytest.raises(ValueError):
        simuler(annees=0)
    with pytest.raises(ValueError):
        simuler(joueurs=0)
    with pytest.raises(ValueError):
        simuler(annees=100, joueurs=100_000)


def test_loi_de_poisson():
    rng = random.Random(3)
    tirages = [_poisson(rng, 2.0) for _ in range(20_000)]
    assert sum(tirages) / len(tirages) == pytest.approx(2.0, abs=0.05)
    assert _poisson(rng, 0) == 0
    assert _poisson(rng, 100) > 50
