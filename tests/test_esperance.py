"""Espérance de gain : formules, cas limites et cohérence avec les données réelles."""

import datetime as dt
import math

import pytest

from proba_loto.esperance import (
    PART_FRANCE,
    calculer_esperance,
    estimer_ventes,
    jackpot_rentable,
)

P = 1 / 139_838_160


def test_rangs_2_a_13_et_options():
    e = calculer_esperance(17e6, ventes=20e6, codes_my_million=5e6)
    assert e.rangs_2_a_13 == pytest.approx(0.44)  # 1,10 € × 40 %
    assert e.excedent_plafond == 0
    assert e.my_million == pytest.approx(0.20)
    assert e.mise == 2.5 and e.etoile_plus_moyen == 0
    avec = calculer_esperance(17e6, ventes=20e6, codes_my_million=5e6, etoile_plus=True)
    assert avec.mise == 3.5 and avec.etoile_plus_moyen == pytest.approx(0.60)
    assert avec.total == pytest.approx(e.total + 0.60)


def test_partage_du_jackpot():
    seul = calculer_esperance(100e6, ventes=1, codes_my_million=1e6)
    assert seul.jackpot_moyen == pytest.approx(100e6 * P)
    assert seul.proba_partage == 0
    s = 20e6
    e = calculer_esperance(100e6, ventes=s, codes_my_million=1e6)
    # Identité : J × P(au moins un gagnant parmi S grilles) / S.
    assert e.jackpot_moyen == pytest.approx(100e6 * (1 - (1 - P) ** s) / s, rel=1e-6)
    assert e.proba_partage == pytest.approx(1 - math.exp(-(s - 1) * P), rel=1e-9)
    impopulaire = calculer_esperance(100e6, ventes=s, codes_my_million=1e6, indice_popularite=0.5)
    assert impopulaire.jackpot_moyen > e.jackpot_moyen


def test_situations_plafond():
    normal = calculer_esperance(250e6, ventes=50e6)
    plafond = calculer_esperance(250e6, ventes=50e6, situation="plafond")
    assert plafond.excedent_plafond == pytest.approx(1.10 * 0.42)
    assert plafond.jackpot_moyen == pytest.approx(normal.jackpot_moyen)
    force = calculer_esperance(250e6, ventes=50e6, situation="doit-etre-gagne")
    assert force.jackpot_moyen == pytest.approx(250e6 / 50e6)
    assert force.taux_retour > 1  # rare cas d'espérance positive


def test_jamais_rentable_en_tirage_ordinaire():
    seuil = jackpot_rentable()
    assert seuil is not None and seuil > 250e6
    assert jackpot_rentable(indice_popularite=0.47) > 250e6
    for jackpot in (17e6, 100e6, 250e6):
        assert calculer_esperance(jackpot).taux_retour < 1


def test_entrees_invalides():
    with pytest.raises(ValueError):
        calculer_esperance(300e6)
    with pytest.raises(ValueError):
        calculer_esperance(-1)
    with pytest.raises(ValueError):
        calculer_esperance(50e6, situation="inconnue")
    with pytest.raises(ValueError):
        calculer_esperance(50e6, ventes=0)
    with pytest.raises(ValueError):
        calculer_esperance(50e6, indice_popularite=0)
    with pytest.raises(ValueError, match="plafond"):
        calculer_esperance(100e6, situation="plafond")


def test_estimation_des_ventes_coherente_avec_les_donnees(historique):
    """Recalcule la relation ventes/jackpot sur l'historique livré."""
    parts = [0.0035, 0.0037, 0.0026, 0.0130, 0.0145, 0.0270, 0.0327, 0.1030, 0.1659]
    points = []
    for t in historique:
        if t.date < dt.date(2020, 2, 4) or t.gagnants_europe[0] == 0:
            continue
        masse = sum(t.rapports[r] * t.gagnants_europe[r] for r in range(4, 13))
        ventes = masse / (1.10 * sum(parts))
        points.append((math.log(t.rapports[0] * t.gagnants_europe[0]), math.log(ventes)))
    n = len(points)
    mx = sum(x for x, _ in points) / n
    my = sum(y for _, y in points) / n
    pente = sum((x - mx) * (y - my) for x, y in points) / sum((x - mx) ** 2 for x, _ in points)
    assert pente == pytest.approx(0.342, abs=0.01)
    assert estimer_ventes(50e6) == pytest.approx(math.exp(my + pente * (math.log(50e6) - mx)), rel=0.02)
    assert estimer_ventes(17e6) < estimer_ventes(100e6) < estimer_ventes(250e6)


def test_part_france_coherente_avec_les_donnees(historique):
    parts = sorted(
        sum(t.gagnants_france[5:]) / sum(t.gagnants_europe[5:])
        for t in historique
        if t.date >= dt.date(2020, 2, 4) and sum(t.gagnants_europe[5:]) > 0
    )
    assert parts[len(parts) // 2] == pytest.approx(PART_FRANCE, abs=0.005)
