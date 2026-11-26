"""Statistiques sur l'historique réel : fréquences, écarts, test du khi² et rétro-test."""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .grilles import Grille, verifier
from .historique import TirageHistorique
from .jeux import ETOILE_PLUS, EUROMILLIONS

__all__ = [
    "StatNumero",
    "statistiques_numeros",
    "ResultatKhi2",
    "khi2_uniformite",
    "p_valeur_khi2",
    "GainRetro",
    "ResultatRetro",
    "retro_tester",
]


# ---------------------------------------------------------------------------
# Fréquences et écarts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StatNumero:
    numero: int
    sorties: int
    ecart_actuel: int
    """Nombre de tirages depuis la dernière sortie (0 : sorti au dernier tirage)."""
    ecart_max: int
    """Plus longue absence observée (en tirages)."""
    derniere_sortie: Optional[dt.date]


def statistiques_numeros(
    tirages: Sequence[TirageHistorique], etoiles: bool = False
) -> List[StatNumero]:
    """Fréquence de sortie et écarts de chaque numéro (ou de chaque étoile)."""
    maximum = EUROMILLIONS.bonus_max if etoiles else EUROMILLIONS.numeros_max
    sorties = {v: 0 for v in range(1, maximum + 1)}
    dernier_index: Dict[int, int] = {}
    ecart_max = {v: 0 for v in sorties}
    for index, tirage in enumerate(tirages):
        for valeur in tirage.etoiles if etoiles else tirage.numeros:
            absence = index - dernier_index.get(valeur, -1) - 1
            ecart_max[valeur] = max(ecart_max[valeur], absence)
            dernier_index[valeur] = index
            sorties[valeur] += 1
    total = len(tirages)
    resultat = []
    for valeur in sorties:
        actuel = total - dernier_index.get(valeur, -1) - 1
        resultat.append(
            StatNumero(
                numero=valeur,
                sorties=sorties[valeur],
                ecart_actuel=actuel,
                ecart_max=max(ecart_max[valeur], actuel),
                derniere_sortie=tirages[dernier_index[valeur]].date if valeur in dernier_index else None,
            )
        )
    return resultat


# ---------------------------------------------------------------------------
# Test du khi² d'uniformité
# ---------------------------------------------------------------------------


def _gamma_incomplete_sup(a: float, x: float) -> float:
    """Fonction gamma incomplète supérieure régularisée Q(a, x) = Γ(a, x) / Γ(a)."""
    if a <= 0 or x < 0:
        raise ValueError("paramètres invalides pour la fonction gamma incomplète")
    if x == 0:
        return 1.0
    prefacteur = math.exp(-x + a * math.log(x) - math.lgamma(a))
    if x < a + 1:
        # Développement en série de P(a, x) = 1 − Q(a, x).
        terme = somme = 1.0 / a
        n = a
        for _ in range(100_000):
            n += 1
            terme *= x / n
            somme += terme
            if abs(terme) < abs(somme) * 1e-16:
                break
        return min(1.0, max(0.0, 1.0 - somme * prefacteur))
    # Fraction continue (algorithme de Lentz modifié).
    minuscule = 1e-300
    b = x + 1 - a
    c = 1 / minuscule
    d = 1 / b
    h = d
    for i in range(1, 100_000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = minuscule if abs(d) < minuscule else d
        c = b + an / c
        c = minuscule if abs(c) < minuscule else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-16:
            break
    return min(1.0, max(0.0, prefacteur * h))


def p_valeur_khi2(statistique: float, ddl: int) -> float:
    """Probabilité qu'un khi² à ``ddl`` degrés de liberté dépasse ``statistique``."""
    if ddl <= 0:
        raise ValueError("le nombre de degrés de liberté doit être positif")
    return _gamma_incomplete_sup(ddl / 2, max(0.0, statistique) / 2)


@dataclass(frozen=True)
class ResultatKhi2:
    statistique: float
    ddl: int
    p_valeur: float
    attendu: float
    """Nombre de sorties attendu pour chaque valeur sous l'hypothèse d'un tirage équitable."""

    @property
    def conclusion(self) -> str:
        if self.p_valeur < 0.01:
            return "écart significatif avec un tirage équitable (p < 1 %)"
        if self.p_valeur < 0.05:
            return "écart faiblement significatif (p < 5 %), à confirmer sur d'autres données"
        return "aucun écart significatif : les fréquences sont compatibles avec le hasard"


def khi2_uniformite(comptes: Dict[int, int], nb_valeurs: int, tires_par_tirage: int, nb_tirages: int) -> ResultatKhi2:
    """Test du khi² d'uniformité des sorties.

    Les ``k`` valeurs d'un même tirage étant distinctes (tirage sans remise), la
    statistique de Pearson est multipliée par (N − 1)/(N − k) pour suivre
    asymptotiquement une loi du khi² à N − 1 degrés de liberté.
    """
    attendu = nb_tirages * tires_par_tirage / nb_valeurs
    pearson = sum((comptes.get(v, 0) - attendu) ** 2 / attendu for v in range(1, nb_valeurs + 1))
    statistique = pearson * (nb_valeurs - 1) / (nb_valeurs - tires_par_tirage)
    ddl = nb_valeurs - 1
    return ResultatKhi2(statistique, ddl, p_valeur_khi2(statistique, ddl), attendu)


# ---------------------------------------------------------------------------
# Rétro-test : « et si j'avais joué cette grille à chaque tirage ? »
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GainRetro:
    date: dt.date
    jeu: str
    """« EuroMillions » ou « Étoile+ »."""
    rang: int
    nombre: int
    """Nombre de combinaisons simples gagnantes à ce rang (plusieurs pour une multiple)."""
    montant: Optional[float]
    """Montant total estimé ; ``None`` si personne n'a gagné ce rang (montant non publié)."""


@dataclass
class ResultatRetro:
    grille: Grille
    etoile_plus: bool
    nb_tirages: int
    debut: Optional[dt.date]
    fin: Optional[dt.date]
    mise_totale: float
    gains: List[GainRetro] = field(default_factory=list)

    @property
    def total_gains(self) -> float:
        return sum(g.montant for g in self.gains if g.montant is not None)

    @property
    def gains_inconnus(self) -> List[GainRetro]:
        return [g for g in self.gains if g.montant is None]

    @property
    def taux_retour(self) -> float:
        return self.total_gains / self.mise_totale if self.mise_totale else 0.0

    def par_rang(self) -> Dict[Tuple[str, int], Tuple[int, float]]:
        resultat: Dict[Tuple[str, int], Tuple[int, float]] = {}
        for g in self.gains:
            nombre, montant = resultat.get((g.jeu, g.rang), (0, 0.0))
            resultat[(g.jeu, g.rang)] = (nombre + g.nombre, montant + (g.montant or 0.0))
        return dict(sorted(resultat.items(), key=lambda e: (e[0][0] != "EuroMillions", e[0][1])))

    def meilleurs_gains(self, nombre: int = 5) -> List[GainRetro]:
        connus = [g for g in self.gains if g.montant is not None]
        return sorted(connus, key=lambda g: g.montant or 0.0, reverse=True)[:nombre]


def _part_si_gagnant(rapport: float, gagnants: int, ajout: int) -> Optional[float]:
    """Gain qu'aurait touché le joueur en s'ajoutant aux ``gagnants`` réels.

    Le montant affecté au rang étant réparti à parts égales, ``ajout``
    gagnants supplémentaires réduisent le gain unitaire d'un facteur
    gagnants / (gagnants + ajout).

    Quelques lignes officielles publient un rapport sans nombre de gagnants
    (ex. 31/01/2020 : effectifs européens absents) : le rapport est alors
    utilisé tel quel. Sans rapport, le montant est inconnu (``None``).
    """
    if rapport <= 0:
        return None
    if gagnants <= 0:
        return rapport * ajout
    return rapport * gagnants / (gagnants + ajout) * ajout


def retro_tester(
    grille: Grille,
    tirages: Sequence[TirageHistorique],
    etoile_plus: bool = False,
    depuis: Optional[dt.date] = None,
) -> ResultatRetro:
    """Rejoue une grille (simple ou multiple) sur chaque tirage de l'historique.

    Les gains utilisent les rapports officiels publiés pour la France, ajustés
    pour tenir compte du fait que le joueur aurait été un gagnant de plus.
    """
    if grille.jeu is not EUROMILLIONS:
        raise ValueError("le rétro-test n'est disponible que pour l'EuroMillions")
    selection = [t for t in tirages if depuis is None or t.date >= depuis]
    prix = float(EUROMILLIONS.prix_grille + (ETOILE_PLUS.mise if etoile_plus else 0))
    resultat = ResultatRetro(
        grille=grille,
        etoile_plus=etoile_plus,
        nb_tirages=len(selection),
        debut=selection[0].date if selection else None,
        fin=selection[-1].date if selection else None,
        mise_totale=prix * grille.nb_combinaisons_simples * len(selection),
    )
    for tirage in selection:
        combinaison = tirage.combinaison
        for rang, nombre in verifier(grille, combinaison).gains.items():
            montant = _part_si_gagnant(
                tirage.rapports[rang - 1], tirage.gagnants_europe[rang - 1], nombre
            )
            resultat.gains.append(GainRetro(tirage.date, "EuroMillions", rang, nombre, montant))
        if etoile_plus:
            for rang, nombre in verifier(grille, combinaison, ETOILE_PLUS).gains.items():
                montant = _part_si_gagnant(
                    tirage.rapports_etoile_plus[rang - 1],
                    tirage.gagnants_etoile_plus[rang - 1],
                    nombre,
                )
                resultat.gains.append(GainRetro(tirage.date, "Étoile+", rang, nombre, montant))
    return resultat
