"""Khi², écarts et rétro-test sur l'historique réel."""

import datetime as dt
import math

import pytest

from proba_loto.grilles import Grille
from proba_loto.historique import TirageHistorique, trouver_tirage
from proba_loto.jeux import EUROMILLIONS as EM
from proba_loto.statistiques import (
    p_valeur_khi2,
    retro_tester,
    statistiques_numeros,
    khi2_uniformite,
)


@pytest.mark.parametrize("x", [0.1, 1.0, 3.7, 12.0, 45.0, 120.0])
def test_p_valeur_formes_closes(x):
    assert p_valeur_khi2(x, 1) == pytest.approx(math.erfc(math.sqrt(x / 2)), abs=1e-12)
    assert p_valeur_khi2(x, 2) == pytest.approx(math.exp(-x / 2), abs=1e-12)
    assert p_valeur_khi2(x, 4) == pytest.approx(math.exp(-x / 2) * (1 + x / 2), abs=1e-12)
    assert p_valeur_khi2(x, 6) == pytest.approx(math.exp(-x / 2) * (1 + x / 2 + x * x / 8), abs=1e-12)


def test_p_valeur_limites():
    assert p_valeur_khi2(0, 49) == 1
    assert p_valeur_khi2(49, 49) == pytest.approx(0.47, abs=0.01)  # médiane ≈ ddl
    assert p_valeur_khi2(1000, 49) < 1e-100
    with pytest.raises(ValueError):
        p_valeur_khi2(3, 0)


def khi2_uniformite_parfaite_et_correction_sans_remise():
    parfait = khi2_uniformite({v: 100 for v in range(1, 51)}, 50, 5, 1000)
    assert parfait.statistique == 0 and parfait.p_valeur == 1
    comptes = {v: 100 + (10 if v % 2 else -10) for v in range(1, 51)}
    pearson = sum((c - 100) ** 2 / 100 for c in comptes.values())
    assert khi2_uniformite(comptes, 50, 5, 1000).statistique == pytest.approx(pearson * 49 / 45)


def test_tirages_reels_compatibles_avec_le_hasard(historique):
    n = len(historique)
    numeros = {s.numero: s.sorties for s in statistiques_numeros(historique)}
    etoiles = {s.numero: s.sorties for s in statistiques_numeros(historique, etoiles=True)}
    assert sum(numeros.values()) == 5 * n and sum(etoiles.values()) == 2 * n
    assert khi2_uniformite(numeros, 50, 5, n).p_valeur > 0.01
    assert khi2_uniformite(etoiles, 12, 2, n).p_valeur > 0.01


def _tirage(jour, numeros, etoiles):
    return TirageHistorique(
        date=dt.date(2026, 1, jour),
        numeros=tuple(numeros),
        etoiles=tuple(etoiles),
        gagnants_europe=(0,) * 13,
        gagnants_france=(0,) * 13,
        rapports=(0.0,) * 13,
    )


def test_ecarts_sur_un_historique_synthetique():
    tirages = [
        _tirage(2, [1, 2, 3, 4, 5], [1, 2]),
        _tirage(6, [1, 6, 7, 8, 9], [1, 3]),
        _tirage(9, [10, 11, 12, 13, 14], [4, 5]),
        _tirage(13, [1, 15, 16, 17, 18], [1, 2]),
    ]
    stats = {s.numero: s for s in statistiques_numeros(tirages)}
    assert stats[1].sorties == 3 and stats[1].ecart_actuel == 0 and stats[1].ecart_max == 1
    assert stats[2].ecart_actuel == 3 and stats[2].derniere_sortie == dt.date(2026, 1, 2)
    assert stats[50].sorties == 0 and stats[50].ecart_actuel == 4 and stats[50].derniere_sortie is None
    etoiles = {s.numero: s for s in statistiques_numeros(tirages, etoiles=True)}
    assert etoiles[2].ecart_max == 2 and etoiles[2].ecart_actuel == 0


def test_retro_test_jackpot_gagne(historique):
    t = trouver_tirage(historique, dt.date(2026, 11, 10))  # jackpot de 141,9 M€, 1 gagnant
    assert t.gagnants_europe[0] == 1
    resultat = retro_tester(t.combinaison, historique)
    jackpots = [g for g in resultat.gains if g.rang == 1 and g.jeu == "EuroMillions"]
    assert len(jackpots) == 1 and jackpots[0].date == t.date
    # Le joueur aurait partagé avec le gagnant réel : la moitié du jackpot.
    assert jackpots[0].montant == pytest.approx(t.rapports[0] / 2)
    assert resultat.nb_tirages == len(historique)
    assert resultat.mise_totale == pytest.approx(2.5 * len(historique))


def test_retro_test_jackpot_non_gagne_et_etoile_plus(historique):
    t = trouver_tirage(historique, dt.date(2026, 11, 24))  # jackpot non gagné ce jour-là
    resultat = retro_tester(t.combinaison, historique, etoile_plus=True, depuis=dt.date(2026, 1, 1))
    assert [(g.date, g.rang) for g in resultat.gains_inconnus] == [(t.date, 1)]
    assert resultat.mise_totale == pytest.approx(3.5 * resultat.nb_tirages)
    assert any(g.jeu == "Étoile+" for g in resultat.gains)
    assert resultat.debut >= dt.date(2026, 1, 1)
    assert 0 < resultat.taux_retour < 1


def test_retro_test_ligne_officielle_sans_effectifs(historique):
    """31/01/2020 : la FDJ publie les rapports mais pas les effectifs européens."""
    t = trouver_tirage(historique, dt.date(2020, 1, 31))
    assert t.gagnants_europe == (0,) * 13 and t.rapports[12] > 0
    grille = Grille.simple(EM, list(t.numeros[:2]) + [44, 45, 46], [11, 12])  # 2 + 0
    resultat = retro_tester(grille, [t])
    assert resultat.gains[0].rang == 13
    assert resultat.gains[0].montant == pytest.approx(t.rapports[12])


def test_retro_test_multiple(historique):
    grille = Grille.depuis_texte(EM, "1 2 3 4 5 6 + 1 2 3")
    resultat = retro_tester(grille, historique[-10:])
    assert resultat.mise_totale == pytest.approx(2.5 * 18 * 10)
