"""Simulation de Monte-Carlo : que se passe-t-il quand on joue pendant des années ?

Chaque grille simple d'un tirage produit une issue (bons numéros, bonnes
étoiles) tirée selon sa probabilité exacte. Les gains utilisent :

* rangs 2 à 13 (et Étoile+) : le gain moyen déduit de la répartition
  réglementaire (validé sur les rapports réels 2020-2026) ;
* jackpot : un montant fixe choisi (par défaut, la moyenne des jackpots
  effectivement remportés depuis 2016) ;
* My Million : 1 M€ avec une chance sur le nombre de codes du tirage.

Les grilles d'un même tirage sont traitées comme indépendantes : c'est exact
pour une grille par tirage, et une très bonne approximation au-delà.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .esperance import PART_FRANCE
from .jeux import ETOILE_PLUS, EUROMILLIONS, MY_MILLION_GAIN
from .probabilites import gain_moyen_theorique, nb_correspondances

__all__ = ["ResultatSimulation", "simuler", "JACKPOT_MOYEN_PAR_DEFAUT"]

JACKPOT_MOYEN_PAR_DEFAUT = 84_000_000
"""Moyenne des 177 jackpots remportés entre septembre 2016 et novembre 2026 (≈ 83,7 M€)."""
CODES_MY_MILLION_PAR_DEFAUT = PART_FRANCE * 23_100_000
"""Codes My Million d'un tirage ordinaire (≈ 21,6 % des 23,1 M de grilles médianes)."""
LIMITE_ISSUES = 50_000_000


@dataclass
class ResultatSimulation:
    joueurs: int
    tirages: int
    grilles_par_tirage: int
    etoile_plus: bool
    mise_par_joueur: float
    jackpot: float
    bilans: List[float]
    """Gains totaux de chaque joueur simulé."""
    victoires: Counter[Tuple[str, int]] = field(default_factory=Counter)
    """Nombre total de gains par (jeu, rang) sur l'ensemble des joueurs."""
    my_million: int = 0

    @property
    def gain_moyen(self) -> float:
        return sum(self.bilans) / len(self.bilans)

    @property
    def gain_median(self) -> float:
        valeurs = sorted(self.bilans)
        milieu = len(valeurs) // 2
        if len(valeurs) % 2:
            return valeurs[milieu]
        return (valeurs[milieu - 1] + valeurs[milieu]) / 2

    @property
    def part_joueurs_gagnants(self) -> float:
        """Proportion de joueurs ayant gagné plus qu'ils n'ont misé."""
        return sum(1 for g in self.bilans if g > self.mise_par_joueur) / len(self.bilans)

    @property
    def meilleur_bilan(self) -> float:
        return max(self.bilans)

    @property
    def taux_retour(self) -> float:
        return self.gain_moyen / self.mise_par_joueur


def _poisson(rng: random.Random, lam: float) -> int:
    """Tirage d'une loi de Poisson (algorithme de Knuth, adapté aux petits λ)."""
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    seuil, k, produit = math.exp(-lam), 0, rng.random()
    while produit > seuil:
        k += 1
        produit *= rng.random()
    return k


def _issues(
    etoile_plus: bool, jackpot: float
) -> Tuple[List[Tuple[int, int]], List[int], List[float], List[Tuple[Optional[int], Optional[int]]]]:
    """Issues possibles d'une grille, poids cumulés, gains et rangs associés."""
    jeu = EUROMILLIONS
    issues: List[Tuple[int, int]] = []
    cumul: List[int] = []
    gains: List[float] = []
    rangs: List[Tuple[Optional[int], Optional[int]]] = []
    total = 0
    for a in range(jeu.numeros_par_grille + 1):
        for b in range(jeu.bonus_par_grille + 1):
            total += nb_correspondances(jeu, a, b)
            issues.append((a, b))
            cumul.append(total)
            gain = 0.0
            rang_em = jeu.gains.rang_pour(a, b)
            if rang_em is not None:
                gain += jackpot if rang_em.numero == 1 else gain_moyen_theorique(jeu, rang_em) or 0.0
            rang_ep = ETOILE_PLUS.rang_pour(a, b) if etoile_plus else None
            if rang_ep is not None:
                gain += gain_moyen_theorique(jeu, rang_ep, ETOILE_PLUS) or 0.0
            gains.append(gain)
            rangs.append(
                (rang_em.numero if rang_em else None, rang_ep.numero if rang_ep else None)
            )
    return issues, cumul, gains, rangs


def simuler(
    annees: float = 10,
    grilles_par_tirage: int = 1,
    joueurs: int = 1000,
    jackpot: Optional[float] = None,
    etoile_plus: bool = False,
    codes_my_million: Optional[float] = None,
    graine: Optional[int] = None,
    tirages_par_semaine: Optional[int] = None,
) -> ResultatSimulation:
    """Simule ``joueurs`` personnes jouant ``grilles_par_tirage`` grilles à chaque tirage."""
    if annees <= 0 or grilles_par_tirage < 1 or joueurs < 1:
        raise ValueError("durée, nombre de grilles et nombre de joueurs doivent être positifs")
    par_semaine = tirages_par_semaine or EUROMILLIONS.tirages_par_semaine
    tirages = max(1, int(round(annees * 52.1775 * par_semaine)))
    par_joueur = tirages * grilles_par_tirage
    if par_joueur * joueurs > LIMITE_ISSUES:
        raise ValueError(
            f"simulation trop volumineuse ({par_joueur * joueurs:,} grilles) : "
            f"réduisez la durée, le nombre de grilles ou de joueurs"
        )
    jackpot = float(jackpot) if jackpot is not None else float(JACKPOT_MOYEN_PAR_DEFAUT)
    codes = float(codes_my_million) if codes_my_million is not None else CODES_MY_MILLION_PAR_DEFAUT
    rng = random.Random(graine) if graine is not None else random.Random()
    issues, cumul, gains, rangs = _issues(etoile_plus, jackpot)
    indices = list(range(len(issues)))
    prix = float(EUROMILLIONS.prix_grille) + (float(ETOILE_PLUS.mise) if etoile_plus else 0.0)
    compte_issues: Counter[int] = Counter()
    bilans = []
    my_million = 0
    for _ in range(joueurs):
        tirees = rng.choices(indices, cum_weights=cumul, k=par_joueur)
        comptes = Counter(tirees)
        compte_issues.update(comptes)
        total = sum(gains[i] * n for i, n in comptes.items())
        gagnes = _poisson(rng, par_joueur / codes)
        my_million += gagnes
        bilans.append(total + gagnes * MY_MILLION_GAIN)
    victoires: Counter[Tuple[str, int]] = Counter()
    for i, n in compte_issues.items():
        rang_em, rang_ep = rangs[i]
        if rang_em is not None:
            victoires[("EuroMillions", rang_em)] += n
        if rang_ep is not None:
            victoires[("Étoile+", rang_ep)] += n
    return ResultatSimulation(
        joueurs=joueurs,
        tirages=tirages,
        grilles_par_tirage=grilles_par_tirage,
        etoile_plus=etoile_plus,
        mise_par_joueur=prix * par_joueur,
        jackpot=jackpot,
        bilans=bilans,
        victoires=victoires,
        my_million=my_million,
    )
