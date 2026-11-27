"""Popularité des numéros et des étoiles, estimée à partir des rapports officiels.

Principe : l'EuroMillions est un jeu de répartition. La somme affectée à un rang
est fixe (part réglementaire des mises) et partagée entre ses gagnants ; un
rapport faible signifie donc que beaucoup de joueurs avaient joué les numéros
sortis. Le rapport du rang 13 (2 bons numéros, 0 étoile, ~700 000 gagnants par
tirage) mesure ainsi la popularité des numéros tirés, sans dépendre du
volume des ventes : rapport = 1,10 € × 16,59 % × ventes / gagnants.

Le modèle est une régression ridge du logarithme du rapport sur les
indicatrices des numéros et étoiles tirés (plus un niveau propre à chaque
année, pour absorber l'évolution de la répartition des gains) :

* numéros : log(rapport rang 13) ;
* étoiles : log(rapport rang 11, 1 numéro + 2 étoiles), où les deux étoiles
  tirées doivent figurer sur la grille gagnante.

Pour le rang 13, un numéro joué par une proportion (1 + δ) fois plus grande de
grilles fait varier le nombre de gagnants de δ/3 environ (calcul
hypergéométrique exact : 0,0223 / 0,0670) ; le facteur de popularité d'un
numéro vaut donc exp(−3 β). Pour les étoiles du rang 11, il vaut exp(−γ).

Ces facteurs ne changent rien à la probabilité de gagner : ils estiment
seulement avec combien d'autres joueurs un gain serait partagé.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .grilles import Grille
from .historique import TirageHistorique
from .jeux import EUROMILLIONS

__all__ = ["ModelePopularite", "estimer_popularite", "indice_par_defaut"]

_NB_NUMEROS = EUROMILLIONS.numeros_max
_NB_ETOILES = EUROMILLIONS.bonus_max
_RANG_NUMEROS = 13
_RANG_ETOILES = 11
_SENSIBILITE_NUMEROS = 3.0  # inverse de d log(fraction 2+0) / d δ = 1/3
_SENSIBILITE_ETOILES = 1.0  # les deux étoiles sorties sont sur la grille gagnante


def _resoudre(matrice: List[List[float]], second_membre: List[float]) -> List[float]:
    """Résout un système linéaire par élimination de Gauss avec pivot partiel."""
    n = len(second_membre)
    a = [ligne[:] + [second_membre[i]] for i, ligne in enumerate(matrice)]
    for colonne in range(n):
        pivot = max(range(colonne, n), key=lambda i: abs(a[i][colonne]))
        if abs(a[pivot][colonne]) < 1e-12:
            raise ValueError("système singulier")
        a[colonne], a[pivot] = a[pivot], a[colonne]
        pivot_ligne = a[colonne]
        inverse = 1.0 / pivot_ligne[colonne]
        for i in range(colonne + 1, n):
            facteur = a[i][colonne] * inverse
            if facteur:
                ligne = a[i]
                for j in range(colonne, n + 1):
                    ligne[j] -= facteur * pivot_ligne[j]
    solution = [0.0] * n
    for i in range(n - 1, -1, -1):
        somme = a[i][n] - sum(a[i][j] * solution[j] for j in range(i + 1, n))
        solution[i] = somme / a[i][i]
    return solution


def _ridge(
    observations: Sequence[Tuple[Sequence[int], float]],
    nb_variables: int,
    penalites: Sequence[float],
) -> List[float]:
    """Régression ridge pour un plan d'expérience binaire et creux.

    Chaque observation est (indices des variables valant 1, valeur observée).
    """
    xtx = [[0.0] * nb_variables for _ in range(nb_variables)]
    xty = [0.0] * nb_variables
    for indices, y in observations:
        for i in indices:
            xty[i] += y
            ligne = xtx[i]
            for j in indices:
                ligne[j] += 1.0
    for i, penalite in enumerate(penalites):
        xtx[i][i] += penalite
    return _resoudre(xtx, xty)


def _plan(
    tirages: Sequence[TirageHistorique], rang: int, annees: Sequence[int]
) -> List[Tuple[List[int], float]]:
    index_annee = {a: i for i, a in enumerate(annees)}
    observations = []
    for t in tirages:
        rapport = t.rapports[rang - 1]
        if rapport <= 0 or t.date.year not in index_annee:
            continue
        indices = [n - 1 for n in t.numeros]
        indices += [_NB_NUMEROS + e - 1 for e in t.etoiles]
        indices.append(_NB_NUMEROS + _NB_ETOILES + index_annee[t.date.year])
        observations.append((indices, math.log(rapport)))
    return observations


def _coefficients(
    tirages: Sequence[TirageHistorique], rang: int, penalite: float
) -> Tuple[List[float], List[float]]:
    """Effets centrés des numéros et des étoiles sur log(rapport du rang)."""
    annees = sorted({t.date.year for t in tirages})
    observations = _plan(tirages, rang, annees)
    nb = _NB_NUMEROS + _NB_ETOILES + len(annees)
    # Les niveaux annuels jouent le rôle de constante (quasi non pénalisés).
    penalites = [penalite] * (_NB_NUMEROS + _NB_ETOILES) + [1e-6] * len(annees)
    beta = _ridge(observations, nb, penalites)
    numeros = beta[:_NB_NUMEROS]
    etoiles = beta[_NB_NUMEROS : _NB_NUMEROS + _NB_ETOILES]
    moyenne_n = sum(numeros) / len(numeros)
    moyenne_e = sum(etoiles) / len(etoiles)
    return [b - moyenne_n for b in numeros], [g - moyenne_e for g in etoiles]


def _correlation(x: Sequence[float], y: Sequence[float]) -> float:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else 0.0


def _symetrique_elementaire(poids: Sequence[float], ordre: int) -> float:
    """Polynôme symétrique élémentaire e_k(poids) : somme des produits de k poids distincts."""
    e = [1.0] + [0.0] * ordre
    for w in poids:
        for k in range(ordre, 0, -1):
            e[k] += e[k - 1] * w
    return e[ordre]


@dataclass(frozen=True)
class ModelePopularite:
    facteurs_numeros: Dict[int, float]
    """1,00 = popularité moyenne ; 1,25 = numéro présent sur 25 % de grilles en plus."""
    facteurs_etoiles: Dict[int, float]
    nb_tirages: int
    debut: Optional[dt.date]
    fin: Optional[dt.date]
    correlation_validation: Optional[float] = None
    """Corrélation entre rapports prédits et observés sur les tirages récents non utilisés pour l'estimation."""
    estime_sur_donnees: bool = True

    def indice(self, grille: Grille) -> float:
        """Nombre attendu de grilles identiques jouées, relativement à une combinaison moyenne.

        Sous l'hypothèse que les joueurs choisissent leurs numéros et leurs
        étoiles indépendamment selon ces facteurs de popularité :
        indice = Π w(numéros) / moyenne(Π w) × Π v(étoiles) / moyenne(Π v).
        Un indice de 0,5 signifie deux fois moins de co-gagnants attendus que
        pour une combinaison moyenne.
        """
        if grille.jeu is not EUROMILLIONS or grille.est_multiple:
            raise ValueError("l'indice de popularité concerne une grille simple EuroMillions")
        k, j = EUROMILLIONS.numeros_par_grille, EUROMILLIONS.bonus_par_grille
        w = self.facteurs_numeros
        v = self.facteurs_etoiles
        moyenne_w = _symetrique_elementaire(list(w.values()), k) / math.comb(_NB_NUMEROS, k)
        moyenne_v = _symetrique_elementaire(list(v.values()), j) / math.comb(_NB_ETOILES, j)
        produit_w = math.prod(w[n] for n in grille.numeros)
        produit_v = math.prod(v[e] for e in grille.bonus)
        return (produit_w / moyenne_w) * (produit_v / moyenne_v)

    def classement_numeros(self) -> List[Tuple[int, float]]:
        """Numéros du plus joué au moins joué."""
        return sorted(self.facteurs_numeros.items(), key=lambda e: -e[1])

    def classement_etoiles(self) -> List[Tuple[int, float]]:
        return sorted(self.facteurs_etoiles.items(), key=lambda e: -e[1])


def _normaliser(facteurs: Dict[int, float]) -> Dict[int, float]:
    moyenne = sum(facteurs.values()) / len(facteurs)
    return {k: v / moyenne for k, v in facteurs.items()}


def estimer_popularite(
    tirages: Sequence[TirageHistorique],
    penalite: float = 5.0,
    validation: bool = True,
) -> ModelePopularite:
    """Estime la popularité des numéros et étoiles à partir des rapports des rangs 13 et 11."""
    tirages = [t for t in tirages if t.rapports[_RANG_NUMEROS - 1] > 0 and t.rapports[_RANG_ETOILES - 1] > 0]
    if len(tirages) < 200:
        raise ValueError("au moins 200 tirages sont nécessaires pour estimer la popularité")
    beta_numeros, _ = _coefficients(tirages, _RANG_NUMEROS, penalite)
    _, gamma_etoiles = _coefficients(tirages, _RANG_ETOILES, penalite)
    facteurs_numeros = _normaliser(
        {n + 1: math.exp(-_SENSIBILITE_NUMEROS * b) for n, b in enumerate(beta_numeros)}
    )
    facteurs_etoiles = _normaliser(
        {e + 1: math.exp(-_SENSIBILITE_ETOILES * g) for e, g in enumerate(gamma_etoiles)}
    )
    correlation = None
    if validation:
        correlation = _valider(tirages, penalite)
    return ModelePopularite(
        facteurs_numeros=facteurs_numeros,
        facteurs_etoiles=facteurs_etoiles,
        nb_tirages=len(tirages),
        debut=tirages[0].date,
        fin=tirages[-1].date,
        correlation_validation=correlation,
    )


def _valider(tirages: Sequence[TirageHistorique], penalite: float) -> float:
    """Estime sur les 75 % plus anciens tirages, mesure la prédiction sur les 25 % récents."""
    coupure = int(len(tirages) * 0.75)
    apprentissage, test = tirages[:coupure], tirages[coupure:]
    beta, gamma = _coefficients(apprentissage, _RANG_NUMEROS, penalite)
    predits = [
        sum(beta[n - 1] for n in t.numeros) + sum(gamma[e - 1] for e in t.etoiles) for t in test
    ]
    observes = [math.log(t.rapports[_RANG_NUMEROS - 1]) for t in test]
    return _correlation(predits, observes)


def indice_par_defaut() -> ModelePopularite:
    """Modèle neutre (tous les facteurs à 1) utilisé quand aucun historique n'est disponible."""
    return ModelePopularite(
        facteurs_numeros={n: 1.0 for n in range(1, _NB_NUMEROS + 1)},
        facteurs_etoiles={e: 1.0 for e in range(1, _NB_ETOILES + 1)},
        nb_tirages=0,
        debut=None,
        fin=None,
        estime_sur_donnees=False,
    )
