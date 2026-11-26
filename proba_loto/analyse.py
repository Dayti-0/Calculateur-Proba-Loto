"""Analyse descriptive d'une grille : profil statistique et motifs souvent joués.

Rappel essentiel : toutes les combinaisons ont exactement la même probabilité
de sortir. Le profil (somme, pairs/impairs...) décrit la grille mais ne change
rien aux chances de gain. Les motifs détectés ici sont ceux que beaucoup de
joueurs choisissent (dates, suites, dernier tirage...) : ils n'influent pas sur
la probabilité de gagner, mais sur le nombre de personnes avec qui un gain
serait partagé.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from typing import Dict, List, Optional, Sequence, Tuple

from .grilles import Grille
from .jeux import Jeu
from .probabilites import distribution_somme

__all__ = [
    "Motif",
    "AnalyseGrille",
    "analyser_grille",
    "motifs_populaires",
    "plus_longue_suite",
    "profil_equilibre",
    "bornes_somme",
]


@dataclass(frozen=True)
class Motif:
    code: str
    description: str


@dataclass(frozen=True)
class AnalyseGrille:
    grille: Grille
    somme: int
    rang_centile_somme: float
    """Part des combinaisons dont la somme des numéros est inférieure ou égale."""
    pairs: int
    proba_pairs: Fraction
    """Proportion des combinaisons ayant ce même nombre de numéros pairs."""
    bas: int
    seuil_bas: int
    proba_bas: Fraction
    dizaines: Dict[str, int]
    plus_longue_suite: int
    motifs: Tuple[Motif, ...]
    indice_popularite: Optional[float]

    @property
    def impairs(self) -> int:
        return len(self.grille.numeros) - self.pairs

    @property
    def hauts(self) -> int:
        return len(self.grille.numeros) - self.bas


def plus_longue_suite(numeros: Sequence[int]) -> int:
    """Longueur de la plus longue suite de numéros consécutifs (1 si aucune)."""
    if not numeros:
        return 0
    valeurs = sorted(numeros)
    meilleure = courante = 1
    for precedent, actuel in zip(valeurs, valeurs[1:]):
        courante = courante + 1 if actuel == precedent + 1 else 1
        meilleure = max(meilleure, courante)
    return meilleure


def _plus_longue_progression(numeros: Sequence[int]) -> int:
    """Plus longue progression arithmétique (raison ≥ 2) contenue dans la grille."""
    valeurs = sorted(numeros)
    ensemble = set(valeurs)
    meilleure = 2 if len(valeurs) >= 2 else len(valeurs)
    for i, a in enumerate(valeurs):
        for b in valeurs[i + 1 :]:
            raison = b - a
            if raison < 2:
                continue
            longueur, suivant = 2, b + raison
            while suivant in ensemble:
                longueur += 1
                suivant += raison
            meilleure = max(meilleure, longueur)
    return meilleure


def motifs_populaires(grille: Grille, dernier_tirage: Optional[Grille] = None) -> List[Motif]:
    """Motifs connus pour être sur-représentés dans les grilles des joueurs."""
    numeros = grille.numeros
    motifs = []
    suite = plus_longue_suite(numeros)
    if suite >= 3:
        motifs.append(Motif("suite", f"{suite} numéros consécutifs"))
    progression = _plus_longue_progression(numeros)
    if progression >= 4:
        motifs.append(Motif("progression", f"{progression} numéros en progression régulière"))
    if all(n <= 31 for n in numeros):
        motifs.append(Motif("dates", "tous les numéros ≤ 31 (dates d'anniversaire)"))
    finales: Dict[int, int] = {}
    for n in numeros:
        finales[n % 10] = finales.get(n % 10, 0) + 1
    if max(finales.values()) >= 4:
        motifs.append(Motif("finale", "4 numéros ou plus avec le même chiffre des unités"))
    if len({(n - 1) // 10 for n in numeros}) == 1:
        motifs.append(Motif("dizaine", "tous les numéros dans la même dizaine"))
    for diviseur in range(3, 11):
        if all(n % diviseur == 0 for n in numeros):
            motifs.append(Motif("multiples", f"tous multiples de {diviseur}"))
            break
    if dernier_tirage is not None:
        communs = len(set(numeros) & set(dernier_tirage.numeros))
        if communs >= 3:
            motifs.append(Motif("dernier-tirage", f"{communs} numéros du dernier tirage"))
    return motifs


@lru_cache(maxsize=8)
def _cumul_sommes(jeu: Jeu) -> Tuple[int, ...]:
    cumul, total = [], 0
    for nombre in distribution_somme(jeu):
        total += nombre
        cumul.append(total)
    return tuple(cumul)


def bornes_somme(jeu: Jeu, bas: float = 0.25, haut: float = 0.75) -> Tuple[int, int]:
    """Sommes délimitant la part centrale des combinaisons (par défaut, l'intervalle interquartile)."""
    cumul = _cumul_sommes(jeu)
    total = cumul[-1]
    minimum = next(s for s, c in enumerate(cumul) if c >= bas * total)
    maximum = next(s for s, c in enumerate(cumul) if c >= haut * total)
    return minimum, maximum


def _proba_hypergeometrique(population: int, favorables: int, tirage: int, succes: int) -> Fraction:
    return Fraction(
        math.comb(favorables, succes) * math.comb(population - favorables, tirage - succes),
        math.comb(population, tirage),
    )


def analyser_grille(
    grille: Grille,
    modele: Optional[object] = None,
    dernier_tirage: Optional[Grille] = None,
) -> AnalyseGrille:
    """Profil d'une grille simple ; ``modele`` est un ``ModelePopularite`` (EuroMillions)."""
    jeu = grille.jeu
    numeros = grille.numeros
    k, n = len(numeros), jeu.numeros_max
    somme = sum(numeros)
    cumul = _cumul_sommes(jeu)
    rang_centile = cumul[somme] / cumul[-1] if k == jeu.numeros_par_grille else float("nan")
    pairs = sum(1 for x in numeros if x % 2 == 0)
    seuil = n // 2
    bas = sum(1 for x in numeros if x <= seuil)
    dizaines: Dict[str, int] = {}
    for debut in range(0, n, 10):
        libelle = f"{max(1, debut)}-{min(n, debut + 9)}"
        dizaines[libelle] = sum(1 for x in numeros if max(1, debut) <= x <= debut + 9)
    indice = None
    if modele is not None and not grille.est_multiple:
        indice = modele.indice(grille)  # type: ignore[attr-defined]
    return AnalyseGrille(
        grille=grille,
        somme=somme,
        rang_centile_somme=rang_centile,
        pairs=pairs,
        proba_pairs=_proba_hypergeometrique(n, n // 2, jeu.numeros_par_grille, pairs),
        bas=bas,
        seuil_bas=seuil,
        proba_bas=_proba_hypergeometrique(n, seuil, jeu.numeros_par_grille, bas),
        dizaines=dizaines,
        plus_longue_suite=plus_longue_suite(numeros),
        motifs=tuple(motifs_populaires(grille, dernier_tirage)),
        indice_popularite=indice,
    )


def profil_equilibre(grille: Grille) -> bool:
    """Critères d'une grille « équilibrée » (profil le plus fréquent des tirages).

    Somme dans l'intervalle interquartile, 2 ou 3 numéros pairs, 2 ou 3 numéros
    dans la moitié basse, pas plus de 2 numéros consécutifs et au moins 3
    dizaines différentes. Ce profil est fréquent parce qu'il regroupe beaucoup
    de combinaisons, pas parce qu'une combinaison donnée y serait plus probable.
    """
    jeu = grille.jeu
    numeros = grille.numeros
    minimum, maximum = bornes_somme(jeu)
    pairs = sum(1 for x in numeros if x % 2 == 0)
    bas = sum(1 for x in numeros if x <= jeu.numeros_max // 2)
    return (
        minimum <= sum(numeros) <= maximum
        and pairs in (2, 3)
        and bas in (2, 3)
        and plus_longue_suite(numeros) <= 2
        and len({(x - 1) // 10 for x in numeros}) >= 3
    )
