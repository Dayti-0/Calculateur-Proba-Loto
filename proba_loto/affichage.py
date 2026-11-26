"""Mise en forme des nombres et des tableaux à la française."""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Iterable, Optional, Sequence, Union

Nombre = Union[int, float, Fraction]

__all__ = [
    "entier",
    "decimal",
    "euros",
    "montant_compact",
    "pourcentage",
    "pourcentage_fixe",
    "chances",
    "duree",
    "tableau",
    "liste_numeros",
]

ESPACE_MILLIERS = " "


def entier(valeur: Nombre) -> str:
    """``139838160`` → ``"139 838 160"`` (arrondi à l'entier le plus proche)."""
    n = int(round(float(valeur))) if not isinstance(valeur, int) else valeur
    return f"{n:,}".replace(",", ESPACE_MILLIERS)


def decimal(valeur: Nombre, decimales: int = 2) -> str:
    """``1234.5`` → ``"1 234,50"``."""
    texte = f"{float(valeur):,.{decimales}f}"
    return texte.replace(",", "\x00").replace(".", ",").replace("\x00", ESPACE_MILLIERS)


def euros(valeur: Nombre, decimales: int = 2) -> str:
    """``2.5`` → ``"2,50 €"`` ; les montants entiers élevés sont affichés sans centimes."""
    v = float(valeur)
    if abs(v) >= 100_000 and float(v).is_integer():
        decimales = 0
    return f"{decimal(v, decimales)} €"


def montant_compact(valeur: Nombre) -> str:
    """``59_000_000`` → ``"59 M€"`` ; ``1_500_000`` → ``"1,5 M€"``."""
    v = float(valeur)
    if abs(v) >= 1_000_000:
        millions = v / 1_000_000
        if millions.is_integer():
            return f"{entier(millions)} M€"
        return f"{decimal(millions, 1)} M€"
    return euros(v)


def _sans_zeros(texte: str) -> str:
    """``"60,0"`` → ``"60"`` ; ``"4,50"`` → ``"4,5"``."""
    if "," in texte:
        texte = texte.rstrip("0").rstrip(",")
    return texte


def pourcentage(proportion: Nombre, chiffres_significatifs: int = 3) -> str:
    """Affiche une proportion en pourcentage avec assez de décimales pour être lisible.

    ``0.0769`` → ``"7,69 %"`` ; ``0.6`` → ``"60 %"`` ; ``7.15e-9`` → ``"0,000000715 %"``.
    """
    p = float(proportion) * 100
    if p == 0:
        return "0 %"
    if abs(p) >= 1:
        decimales = max(0, chiffres_significatifs - 1 - int(math.floor(math.log10(abs(p)))))
        decimales = min(decimales, 2)
    else:
        decimales = chiffres_significatifs - 1 - int(math.floor(math.log10(abs(p))))
    return f"{_sans_zeros(decimal(p, decimales))} %"


def pourcentage_fixe(proportion: Nombre, decimales: int = 1) -> str:
    """Pourcentage à nombre de décimales constant (pour les colonnes de tableau)."""
    return f"{decimal(float(proportion) * 100, decimales)} %"


def chances(probabilite: Nombre, decimales: int = 1, phrase: bool = False) -> str:
    """Probabilité → ``"1 sur 139 838 160"`` (ou ``"1 chance sur ..."`` si ``phrase``).

    En dessous de 1 000, le nombre est affiché avec ``decimales`` décimales
    (sans zéro inutile : ``"1 sur 224"``, ``"1 sur 21,9"``).
    """
    p = float(probabilite)
    if p <= 0:
        return "aucune chance" if phrase else "impossible"
    inverse = 1 / p
    if inverse >= 1000:
        nombre = entier(inverse)
    else:
        nombre = _sans_zeros(decimal(inverse, decimales))
    return f"1 chance sur {nombre}" if phrase else f"1 sur {nombre}"


def duree(nb_tirages: float, tirages_par_semaine: int) -> str:
    """Convertit un nombre de tirages en durée lisible (semaines, ans)."""
    semaines = nb_tirages / tirages_par_semaine
    annees = semaines / 52.1775
    if annees >= 2:
        return f"{entier(annees)} ans"
    if semaines >= 2:
        return f"{entier(semaines)} semaines"
    return f"{entier(nb_tirages)} tirage{'s' if nb_tirages >= 2 else ''}"


def liste_numeros(nombres: Iterable[int]) -> str:
    return " ".join(f"{n:02d}" for n in nombres)


def tableau(
    lignes: Sequence[Sequence[object]],
    entetes: Optional[Sequence[str]] = None,
    alignements: Optional[str] = None,
    marge: str = "  ",
) -> str:
    """Construit un tableau texte aligné.

    ``alignements`` contient une lettre par colonne : ``g`` (gauche) ou ``d``
    (droite). Par défaut, la première colonne est à gauche et les autres à droite.
    """
    cellules = [[str(c) for c in ligne] for ligne in lignes]
    if entetes is not None:
        cellules.insert(0, [str(e) for e in entetes])
    if not cellules:
        return ""
    nb_colonnes = max(len(ligne) for ligne in cellules)
    for ligne in cellules:
        ligne.extend([""] * (nb_colonnes - len(ligne)))
    if alignements is None:
        alignements = "g" + "d" * (nb_colonnes - 1)
    largeurs = [max(len(ligne[i]) for ligne in cellules) for i in range(nb_colonnes)]
    sortie = []
    for index, ligne in enumerate(cellules):
        morceaux = []
        for i, cellule in enumerate(ligne):
            if alignements[i] == "d":
                morceaux.append(cellule.rjust(largeurs[i]))
            else:
                morceaux.append(cellule.ljust(largeurs[i]))
        sortie.append(marge + "  ".join(morceaux).rstrip())
        if index == 0 and entetes is not None:
            sortie.append(marge + "  ".join("-" * largeur for largeur in largeurs))
    return "\n".join(sortie)
