"""Probabilités exactes (en fractions rationnelles) des rangs de gain.

Le nombre de combinaisons simples ayant exactement ``a`` bons numéros et ``b``
bonnes étoiles suit une loi
hypergéométrique double :

    C(k, a) × C(n − k, k − a) × C(j, b) × C(m − j, j − b)

pour un jeu où l'on choisit ``k`` numéros parmi ``n`` et ``j`` complémentaires
parmi ``m``. Pour l'EuroMillions : C(50, 5) × C(12, 2) = 139 838 160 combinaisons.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import List, Optional

from .jeux import Jeu, Rang, TableDeGains

__all__ = [
    "nb_combinaisons",
    "nb_correspondances",
    "probabilite",
    "probabilite_rang",
    "probabilite_gain",
    "LigneProbabilite",
    "tableau_probabilites",
    "gain_moyen_theorique",
    "probabilite_au_moins_une_fois",
    "nb_tirages_pour",
    "distribution_somme",
]


def nb_combinaisons(jeu: Jeu) -> int:
    """Nombre de combinaisons simples possibles (139 838 160 pour l'EuroMillions)."""
    return math.comb(jeu.numeros_max, jeu.numeros_par_grille) * math.comb(
        jeu.bonus_max, jeu.bonus_par_grille
    )


def nb_correspondances(jeu: Jeu, bons_numeros: int, bons_bonus: int) -> int:
    """Nombre de combinaisons simples ayant exactement ces bons numéros / complémentaires."""
    k, n = jeu.numeros_par_grille, jeu.numeros_max
    j, m = jeu.bonus_par_grille, jeu.bonus_max
    if not (0 <= bons_numeros <= k and 0 <= bons_bonus <= j):
        raise ValueError(
            f"{jeu.nom} : on ne peut trouver que 0 à {k} numéros et 0 à {j} "
            f"{jeu.bonus_nom_pluriel} (reçu {bons_numeros} et {bons_bonus})"
        )
    return (
        math.comb(k, bons_numeros)
        * math.comb(n - k, k - bons_numeros)
        * math.comb(j, bons_bonus)
        * math.comb(m - j, j - bons_bonus)
    )


def probabilite(jeu: Jeu, bons_numeros: int, bons_bonus: int) -> Fraction:
    """Probabilité exacte d'obtenir exactement ces bons numéros avec une grille simple."""
    return Fraction(nb_correspondances(jeu, bons_numeros, bons_bonus), nb_combinaisons(jeu))


def probabilite_rang(jeu: Jeu, rang: Rang) -> Fraction:
    return sum(
        (probabilite(jeu, a, b) for a, b in rang.correspondances), start=Fraction(0)
    )


def probabilite_gain(jeu: Jeu, table: Optional[TableDeGains] = None) -> Fraction:
    """Probabilité de gagner au moins le plus petit rang avec une grille simple."""
    table = table or jeu.gains
    return sum((probabilite_rang(jeu, r) for r in table.rangs), start=Fraction(0))


@dataclass(frozen=True)
class LigneProbabilite:
    rang: Rang
    libelle: str
    cas_favorables: int
    probabilite: Fraction

    @property
    def une_chance_sur(self) -> float:
        return float(1 / self.probabilite)


def tableau_probabilites(
    jeu: Jeu, table: Optional[TableDeGains] = None
) -> List[LigneProbabilite]:
    """Tableau des rangs avec leurs probabilités exactes."""
    table = table or jeu.gains
    total = nb_combinaisons(jeu)
    lignes = []
    for rang in table.rangs:
        cas = sum(nb_correspondances(jeu, a, b) for a, b in rang.correspondances)
        lignes.append(
            LigneProbabilite(
                rang=rang,
                libelle=jeu.libelle_rang(rang),
                cas_favorables=cas,
                probabilite=Fraction(cas, total),
            )
        )
    return lignes


def gain_moyen_theorique(jeu: Jeu, rang: Rang, table: Optional[TableDeGains] = None) -> Optional[float]:
    """Gain moyen d'un gagnant au rang donné, déduit de la répartition réglementaire.

    Exemple (EuroMillions, rang 13) : 2,20 € × 50 % × 16,59 % / P(2 + 0) ≈ 4,00 €.
    Retourne ``None`` pour le jackpot (montant variable) ou si la part est inconnue.
    """
    table = table or jeu.gains
    if rang.part is None or (table is jeu.gains and rang.numero == 1):
        return None
    return float(table.masse_par_grille * rang.part / probabilite_rang(jeu, rang))


def probabilite_au_moins_une_fois(p: float, essais: float) -> float:
    """Probabilité qu'un évènement de probabilité ``p`` survienne au moins une fois.

    Calcul stable numériquement même pour des probabilités infimes :
    1 − (1 − p)^n = −expm1(n × log1p(−p)).
    """
    p = float(p)
    if p >= 1:
        return 1.0
    if p <= 0 or essais <= 0:
        return 0.0
    return -math.expm1(essais * math.log1p(-p))


def nb_tirages_pour(p: float, probabilite_cible: float = 0.5) -> float:
    """Nombre d'essais nécessaires pour atteindre ``probabilite_cible`` d'au moins un succès."""
    p = float(p)
    if not 0 < probabilite_cible < 1:
        raise ValueError("la probabilité cible doit être strictement comprise entre 0 et 1")
    if p >= 1:
        return 1.0
    return math.log1p(-probabilite_cible) / math.log1p(-p)


def distribution_somme(jeu: Jeu) -> List[int]:
    """Nombre de tirages de numéros donnant chaque somme possible (programmation dynamique).

    ``resultat[s]`` = nombre d'ensembles de ``k`` numéros distincts parmi
    1..n dont la somme vaut ``s``. Sert à situer la somme d'une grille.
    """
    k, n = jeu.numeros_par_grille, jeu.numeros_max
    somme_max = sum(range(n - k + 1, n + 1))
    # comptes[t][s] : nombre de sous-ensembles de taille t et de somme s
    comptes = [[0] * (somme_max + 1) for _ in range(k + 1)]
    comptes[0][0] = 1
    for numero in range(1, n + 1):
        for t in range(min(k, numero), 0, -1):
            ligne, precedente = comptes[t], comptes[t - 1]
            for s in range(somme_max, numero - 1, -1):
                if precedente[s - numero]:
                    ligne[s] += precedente[s - numero]
    return comptes[k]
