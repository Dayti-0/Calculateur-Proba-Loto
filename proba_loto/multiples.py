"""Grilles multiples : coût, probabilités et répartition des gains."""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple

from .grilles import nb_combinaisons_simples, repartition_gains, verifier_multiple_autorisee
from .jeux import Jeu, TableDeGains

__all__ = ["Scenario", "AnalyseMultiple", "analyser_multiple", "cout_multiple"]


def cout_multiple(
    jeu: Jeu, nb_numeros: int, nb_bonus: int, options: Sequence[TableDeGains] = ()
) -> Fraction:
    """Prix d'une grille multiple pour un tirage (options comprises)."""
    simples = nb_combinaisons_simples(jeu, nb_numeros, nb_bonus)
    return simples * (jeu.prix_grille + sum((o.mise for o in options), start=Fraction(0)))


@dataclass(frozen=True)
class Scenario:
    """Une issue possible du tirage pour la multiple : ``a`` numéros et ``b`` complémentaires trouvés."""

    bons_numeros: int
    bons_bonus: int
    probabilite: Fraction
    gains: Dict[int, int]


@dataclass(frozen=True)
class AnalyseMultiple:
    jeu: Jeu
    table: TableDeGains
    nb_numeros: int
    nb_bonus: int
    nb_simples: int
    scenarios: Tuple[Scenario, ...]

    @property
    def probabilite_gain(self) -> Fraction:
        """Probabilité qu'au moins une combinaison simple soit gagnante."""
        return sum((s.probabilite for s in self.scenarios if s.gains), start=Fraction(0))

    def probabilite_meilleur_rang(self) -> Dict[int, Fraction]:
        """Probabilité que le meilleur rang atteint soit ``r``, pour chaque rang."""
        resultat: Dict[int, Fraction] = {}
        for s in self.scenarios:
            if s.gains:
                meilleur = min(s.gains)
                resultat[meilleur] = resultat.get(meilleur, Fraction(0)) + s.probabilite
        return dict(sorted(resultat.items()))

    def probabilite_au_moins_un(self) -> Dict[int, Fraction]:
        """Probabilité d'avoir au moins une combinaison gagnante à chaque rang."""
        resultat: Dict[int, Fraction] = {}
        for s in self.scenarios:
            for rang in s.gains:
                resultat[rang] = resultat.get(rang, Fraction(0)) + s.probabilite
        return dict(sorted(resultat.items()))

    def esperance_gagnantes(self) -> Dict[int, Fraction]:
        """Nombre moyen de combinaisons gagnantes par rang et par tirage."""
        resultat: Dict[int, Fraction] = {}
        for s in self.scenarios:
            for rang, nombre in s.gains.items():
                resultat[rang] = resultat.get(rang, Fraction(0)) + s.probabilite * nombre
        return dict(sorted(resultat.items()))

    def scenarios_gagnants(self) -> List[Scenario]:
        """Issues gagnantes, de la meilleure à la plus modeste (format du tableau FDJ)."""
        gagnants = [s for s in self.scenarios if s.gains]
        return sorted(gagnants, key=lambda s: (-s.bons_numeros, -s.bons_bonus))


def analyser_multiple(
    jeu: Jeu, nb_numeros: int, nb_bonus: int, table: Optional[TableDeGains] = None
) -> AnalyseMultiple:
    """Analyse exacte d'une grille multiple.

    Le nombre ``a`` de numéros tirés parmi les ``n`` cochés suit une loi
    hypergéométrique : P(a) = C(n, a) × C(N − n, k − a) / C(N, k), et de même
    pour les complémentaires ; les deux tirages sont indépendants.
    """
    verifier_multiple_autorisee(jeu, nb_numeros, nb_bonus)
    table = table or jeu.gains
    k, j = jeu.numeros_par_grille, jeu.bonus_par_grille
    total_numeros = math.comb(jeu.numeros_max, k)
    total_bonus = math.comb(jeu.bonus_max, j)
    scenarios = []
    for a in range(0, k + 1):
        cas_a = math.comb(nb_numeros, a) * math.comb(jeu.numeros_max - nb_numeros, k - a)
        if not cas_a:
            continue
        for b in range(0, j + 1):
            cas_b = math.comb(nb_bonus, b) * math.comb(jeu.bonus_max - nb_bonus, j - b)
            if not cas_b:
                continue
            scenarios.append(
                Scenario(
                    bons_numeros=a,
                    bons_bonus=b,
                    probabilite=Fraction(cas_a, total_numeros) * Fraction(cas_b, total_bonus),
                    gains=repartition_gains(jeu, nb_numeros, nb_bonus, a, b, table),
                )
            )
    return AnalyseMultiple(
        jeu=jeu,
        table=table,
        nb_numeros=nb_numeros,
        nb_bonus=nb_bonus,
        nb_simples=nb_combinaisons_simples(jeu, nb_numeros, nb_bonus),
        scenarios=tuple(scenarios),
    )
