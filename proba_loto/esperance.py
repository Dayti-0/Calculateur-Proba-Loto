"""Espérance de gain d'une grille EuroMillions – My Million (avec ou sans Étoile+).

Modèle (par grille simple, pour un tirage) :

* Rangs 2 à 13 : 50 % de la mise EuroMillions (2,20 €) revient aux gagnants,
  soit 1,10 € par grille, dont 40 % pour les rangs 2 à 13 ; ces montants sont
  toujours distribués lors du tirage (report au rang inférieur s'il n'y a pas
  de gagnant). Par symétrie, chaque grille en reçoit en moyenne
  1,10 € × 40 % = 0,44 €.
* Jackpot : un gagnant le partage avec les autres gagnants éventuels. Avec
  ``S`` grilles jouées en Europe, le nombre K d'autres gagnants suit
  approximativement une loi de Poisson de paramètre λ = (S − 1) / 139 838 160
  (multiplié par l'indice de popularité de la grille), et la part moyenne vaut
  E[1/(1+K)] = (1 − e^−λ) / λ.
* Plafond (250 M€) : l'excédent destiné au jackpot (42 % de 1,10 €) est versé
  au rang 2 ; au 5e tirage au plafond, le jackpot doit être distribué
  (au rang 2 s'il n'y a pas de gagnant au rang 1) : chaque grille en reçoit
  alors en moyenne J / S.
* My Million : 1 M€ pour un code tiré parmi tous les codes français du tirage.
* Étoile+ : 60 % des mises (1 €) sont redistribués, soit 0,60 € par option.

Les volumes de ventes, lorsqu'ils ne sont pas fournis, sont estimés à partir
des rapports officiels FDJ 2020-2026 (voir :func:`estimer_ventes`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .jeux import (
    EM_PART_RANG1_APRES_5_TIRAGES,
    EM_PLAFOND_JACKPOT,
    ETOILE_PLUS,
    EUROMILLIONS,
    MY_MILLION_GAIN,
)
from .probabilites import nb_combinaisons

__all__ = [
    "SITUATIONS",
    "Esperance",
    "calculer_esperance",
    "estimer_ventes",
    "estimer_codes_my_million",
    "jackpot_rentable",
    "PART_FRANCE",
]

SITUATIONS = ("normal", "plafond", "doit-etre-gagne")

# log(grilles jouées en Europe) = A + B × log(jackpot), ajusté sur les 114
# tirages 2020-2026 où le jackpot a été remporté (ventes déduites des montants
# distribués aux rangs 5 à 13 ; corrélation 0,75).
_VENTES_A = 10.924
_VENTES_B = 0.342

PART_FRANCE = 0.216
"""Part des grilles jouées en France (médiane 2020-2026 des gagnants des rangs 6 à 13)."""

_COMBINAISONS = nb_combinaisons(EUROMILLIONS)


def estimer_ventes(jackpot: float) -> float:
    """Nombre de grilles jouées en Europe, estimé d'après le montant du jackpot.

    Ordres de grandeur : 17 M€ → 16 M de grilles ; 100 M€ → 30 M ; 250 M€ → 41 M.
    Les tirages exceptionnels (plafond atteint) peuvent dépasser nettement ces valeurs.
    """
    return math.exp(_VENTES_A + _VENTES_B * math.log(max(float(jackpot), 1.0)))


def estimer_codes_my_million(ventes: float) -> float:
    return PART_FRANCE * ventes


def _part_moyenne(lam: float) -> float:
    """E[1/(1+K)] pour K suivant une loi de Poisson de paramètre ``lam``."""
    if lam < 1e-9:
        return 1.0 - lam / 2
    return -math.expm1(-lam) / lam


@dataclass(frozen=True)
class Esperance:
    jackpot: float
    ventes: float
    codes_my_million: float
    situation: str
    etoile_plus: bool
    indice_popularite: float
    mise: float
    rangs_2_a_13: float
    excedent_plafond: float
    jackpot_moyen: float
    my_million: float
    etoile_plus_moyen: float
    part_moyenne_jackpot: float
    """Part moyenne du jackpot qui vous reviendrait si vous le gagniez."""
    proba_partage: float
    """Probabilité de devoir partager le jackpot si vous le gagnez."""

    @property
    def total(self) -> float:
        return (
            self.rangs_2_a_13
            + self.excedent_plafond
            + self.jackpot_moyen
            + self.my_million
            + self.etoile_plus_moyen
        )

    @property
    def taux_retour(self) -> float:
        return self.total / self.mise

    @property
    def perte_moyenne(self) -> float:
        return self.mise - self.total


def calculer_esperance(
    jackpot: float,
    ventes: Optional[float] = None,
    codes_my_million: Optional[float] = None,
    situation: str = "normal",
    etoile_plus: bool = False,
    indice_popularite: float = 1.0,
) -> Esperance:
    """Espérance de gain d'une grille simple pour un tirage."""
    if situation not in SITUATIONS:
        raise ValueError(f"situation inconnue « {situation} » (choix : {', '.join(SITUATIONS)})")
    if jackpot <= 0:
        raise ValueError("le jackpot doit être positif")
    if jackpot > EM_PLAFOND_JACKPOT:
        raise ValueError(
            f"le jackpot ne peut pas dépasser le plafond réglementaire de {EM_PLAFOND_JACKPOT / 1e6:.0f} M€"
        )
    if situation == "plafond" and jackpot < EM_PLAFOND_JACKPOT:
        raise ValueError(
            f"la situation « plafond » suppose un jackpot égal au plafond ({EM_PLAFOND_JACKPOT / 1e6:.0f} M€)"
        )
    if indice_popularite <= 0:
        raise ValueError("l'indice de popularité doit être positif")
    s = float(ventes) if ventes is not None else estimer_ventes(jackpot)
    if s < 1:
        raise ValueError("le nombre de grilles jouées doit être au moins 1")
    codes = float(codes_my_million) if codes_my_million is not None else estimer_codes_my_million(s)
    if codes < 1:
        raise ValueError("le nombre de codes My Million doit être au moins 1")

    table = EUROMILLIONS.gains
    masse = float(table.masse_par_grille)  # 1,10 €
    part_rangs_2_13 = float(sum(r.part for r in table.rangs if r.numero > 1 and r.part is not None))
    rangs_2_a_13 = masse * part_rangs_2_13
    excedent = masse * float(EM_PART_RANG1_APRES_5_TIRAGES) if situation != "normal" else 0.0

    p = 1.0 / _COMBINAISONS
    lam = (s - 1) * p * indice_popularite
    part = _part_moyenne(lam)
    if situation == "doit-etre-gagne":
        jackpot_moyen = jackpot / s
    else:
        jackpot_moyen = jackpot * p * part

    mise = float(EUROMILLIONS.prix_grille) + (float(ETOILE_PLUS.mise) if etoile_plus else 0.0)
    return Esperance(
        jackpot=float(jackpot),
        ventes=s,
        codes_my_million=codes,
        situation=situation,
        etoile_plus=etoile_plus,
        indice_popularite=indice_popularite,
        mise=mise,
        rangs_2_a_13=rangs_2_a_13,
        excedent_plafond=excedent,
        jackpot_moyen=jackpot_moyen,
        my_million=MY_MILLION_GAIN / codes,
        etoile_plus_moyen=float(ETOILE_PLUS.masse_par_grille) if etoile_plus else 0.0,
        part_moyenne_jackpot=part,
        proba_partage=-math.expm1(-lam),
    )


def jackpot_rentable(
    ventes: Optional[float] = None,
    codes_my_million: Optional[float] = None,
    etoile_plus: bool = False,
    indice_popularite: float = 1.0,
) -> Optional[float]:
    """Jackpot à partir duquel l'espérance dépasserait la mise (situation normale).

    Retourne ``None`` si ce seuil n'existe pas (même avec un jackpot gigantesque),
    ce qui arrive lorsque le partage du jackpot plafonne l'espérance.
    """

    def ecart(j: float) -> float:
        e = _esperance_sans_plafond(j, ventes, codes_my_million, etoile_plus, indice_popularite)
        return e.total - e.mise

    bas, haut = 1e6, 1e12
    if ecart(haut) < 0:
        return None
    if ecart(bas) >= 0:
        return bas
    for _ in range(200):
        milieu = math.sqrt(bas * haut)
        if ecart(milieu) >= 0:
            haut = milieu
        else:
            bas = milieu
        if haut / bas < 1 + 1e-9:
            break
    return haut


def _esperance_sans_plafond(
    jackpot: float,
    ventes: Optional[float],
    codes_my_million: Optional[float],
    etoile_plus: bool,
    indice_popularite: float,
) -> Esperance:
    """Comme :func:`calculer_esperance`, sans la limite du plafond (pour la recherche de seuil)."""
    s = float(ventes) if ventes is not None else estimer_ventes(jackpot)
    codes = float(codes_my_million) if codes_my_million is not None else estimer_codes_my_million(s)
    reference = calculer_esperance(
        min(jackpot, EM_PLAFOND_JACKPOT), s, codes, "normal", etoile_plus, indice_popularite
    )
    p = 1.0 / _COMBINAISONS
    return Esperance(
        **{
            **reference.__dict__,
            "jackpot": jackpot,
            "jackpot_moyen": jackpot * p * reference.part_moyenne_jackpot,
        }
    )
