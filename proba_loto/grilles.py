"""Grilles (simples ou multiples) : saisie, validation et vérification d'un tirage."""

from __future__ import annotations

import itertools
import math
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, Optional, Sequence, Tuple

from .affichage import liste_numeros
from .jeux import Jeu, Rang, TableDeGains

__all__ = [
    "ErreurGrille",
    "Grille",
    "Verification",
    "verifier",
    "repartition_gains",
    "nb_combinaisons_simples",
    "verifier_multiple_autorisee",
    "configurations_multiples",
]


class ErreurGrille(ValueError):
    """Grille invalide (numéros hors bornes, doublons, multiple non autorisée...)."""


def nb_combinaisons_simples(jeu: Jeu, nb_numeros: int, nb_bonus: int) -> int:
    """Nombre de combinaisons simples contenues dans une grille multiple."""
    return math.comb(nb_numeros, jeu.numeros_par_grille) * math.comb(nb_bonus, jeu.bonus_par_grille)


def verifier_multiple_autorisee(jeu: Jeu, nb_numeros: int, nb_bonus: int) -> None:
    """Lève :class:`ErreurGrille` si cette grille multiple n'est pas proposée par la FDJ.

    Le tableau officiel (art. 3.1 du règlement EuroMillions) correspond
    exactement à : bornes min/max sur les numéros et complémentaires, et un nombre
    de combinaisons simples ne dépassant pas 396.
    """
    k, j = jeu.numeros_par_grille, jeu.bonus_par_grille
    if not k <= nb_numeros <= jeu.multiple_numeros_max:
        raise ErreurGrille(
            f"{jeu.nom} : une grille comporte de {k} à {jeu.multiple_numeros_max} numéros "
            f"(reçu {nb_numeros})"
        )
    if not j <= nb_bonus <= jeu.multiple_bonus_max:
        raise ErreurGrille(
            f"{jeu.nom} : une grille comporte de {j} à {jeu.multiple_bonus_max} "
            f"{jeu.bonus_nom_pluriel} (reçu {nb_bonus})"
        )
    total = nb_combinaisons_simples(jeu, nb_numeros, nb_bonus)
    if total > jeu.multiple_combinaisons_max:
        raise ErreurGrille(
            f"{jeu.nom} : la multiple {nb_numeros} numéros × {nb_bonus} {jeu.bonus_nom_pluriel} "
            f"représente {total} grilles simples ; la FDJ n'accepte pas plus de "
            f"{jeu.multiple_combinaisons_max} grilles par multiple"
        )


def configurations_multiples(jeu: Jeu) -> Iterator[Tuple[int, int]]:
    """Toutes les grilles (simples et multiples) acceptées : couples (numéros, complémentaires)."""
    for n in range(jeu.numeros_par_grille, jeu.multiple_numeros_max + 1):
        for e in range(jeu.bonus_par_grille, jeu.multiple_bonus_max + 1):
            if nb_combinaisons_simples(jeu, n, e) <= jeu.multiple_combinaisons_max:
                yield n, e


_SEPARATEUR = re.compile(
    r"[+/|*★☆]|\b(?:etoiles?|étoiles?|stars?|chance|n°\s*chance|num[ée]ro\s+chance)\b",
    re.IGNORECASE,
)
_NOMBRE = re.compile(r"\d+")


@dataclass(frozen=True)
class Grille:
    """Une grille simple ou multiple. Les numéros sont triés et validés à la création."""

    jeu: Jeu
    numeros: Tuple[int, ...]
    bonus: Tuple[int, ...]
    autoriser_multiple: bool = field(default=True, compare=False, repr=False)

    def __post_init__(self) -> None:
        jeu = self.jeu
        numeros = tuple(sorted(int(n) for n in self.numeros))
        bonus = tuple(sorted(int(b) for b in self.bonus))
        object.__setattr__(self, "numeros", numeros)
        object.__setattr__(self, "bonus", bonus)
        _verifier_ensemble(numeros, 1, jeu.numeros_max, "numéro", "numéros")
        _verifier_ensemble(bonus, 1, jeu.bonus_max, jeu.bonus_nom, jeu.bonus_nom_pluriel)
        if self.autoriser_multiple:
            verifier_multiple_autorisee(jeu, len(numeros), len(bonus))
        elif len(numeros) != jeu.numeros_par_grille or len(bonus) != jeu.bonus_par_grille:
            raise ErreurGrille(
                f"{jeu.nom} : une grille simple comporte exactement {jeu.numeros_par_grille} "
                f"numéros et {jeu.bonus_par_grille} {jeu.bonus_nom_pluriel if jeu.bonus_par_grille > 1 else jeu.bonus_nom} "
                f"(reçu {len(numeros)} et {len(bonus)})"
            )

    # ------------------------------------------------------------------ saisie
    @classmethod
    def simple(cls, jeu: Jeu, numeros: Iterable[int], bonus: Iterable[int]) -> Grille:
        return cls(jeu, tuple(numeros), tuple(bonus), autoriser_multiple=False)

    @classmethod
    def depuis_texte(cls, jeu: Jeu, texte: str, autoriser_multiple: bool = True) -> Grille:
        """Lit une grille saisie librement.

        Formats acceptés (exemples EuroMillions) : ``"3 5 37 44 49 + 5 6"``,
        ``"3-5-37-44-49 / 5-6"``, ``"3,5,37,44,49 étoiles 5,6"`` ou, pour une
        grille simple, les 7 nombres à la suite ``"3 5 37 44 49 5 6"``.
        """
        morceaux = _SEPARATEUR.split(texte, maxsplit=1)
        if len(morceaux) == 2:
            numeros = [int(x) for x in _NOMBRE.findall(morceaux[0])]
            bonus = [int(x) for x in _NOMBRE.findall(morceaux[1])]
        else:
            nombres = [int(x) for x in _NOMBRE.findall(texte)]
            attendu = jeu.numeros_par_grille + jeu.bonus_par_grille
            if len(nombres) != attendu:
                raise ErreurGrille(
                    f"grille « {texte} » : séparez les numéros des {jeu.bonus_nom_pluriel} "
                    f"par « + » (ex. « 3 5 37 44 49 + {' '.join(str(i + 1) for i in range(jeu.bonus_par_grille))} »)"
                )
            numeros, bonus = nombres[: jeu.numeros_par_grille], nombres[jeu.numeros_par_grille :]
        return cls(jeu, tuple(numeros), tuple(bonus), autoriser_multiple=autoriser_multiple)

    # ------------------------------------------------------------- propriétés
    @property
    def est_multiple(self) -> bool:
        return (
            len(self.numeros) > self.jeu.numeros_par_grille
            or len(self.bonus) > self.jeu.bonus_par_grille
        )

    @property
    def nb_combinaisons_simples(self) -> int:
        return nb_combinaisons_simples(self.jeu, len(self.numeros), len(self.bonus))

    def combinaisons_simples(self) -> Iterator[Grille]:
        """Décompose une grille multiple en ses grilles simples."""
        for numeros in itertools.combinations(self.numeros, self.jeu.numeros_par_grille):
            for bonus in itertools.combinations(self.bonus, self.jeu.bonus_par_grille):
                yield Grille.simple(self.jeu, numeros, bonus)

    def __repr__(self) -> str:
        return f"Grille({self.jeu.cle}: {self})"

    def __str__(self) -> str:
        return f"{liste_numeros(self.numeros)}  ★  {liste_numeros(self.bonus)}"


def _verifier_ensemble(valeurs: Sequence[int], minimum: int, maximum: int, nom: str, pluriel: str) -> None:
    hors_bornes = [v for v in valeurs if not minimum <= v <= maximum]
    if hors_bornes:
        raise ErreurGrille(
            f"{pluriel} hors bornes : {', '.join(map(str, hors_bornes))} "
            f"(autorisé : {minimum} à {maximum})"
        )
    doublons = sorted({v for v in valeurs if valeurs.count(v) > 1})
    if doublons:
        raise ErreurGrille(f"{nom} en double : {', '.join(map(str, doublons))}")


@dataclass(frozen=True)
class Verification:
    """Résultat d'une grille (simple ou multiple) face à un tirage."""

    grille: Grille
    tirage: Grille
    table: TableDeGains
    bons_numeros: Tuple[int, ...]
    bons_bonus: Tuple[int, ...]
    gains: Dict[int, int]
    """Nombre de combinaisons simples gagnantes par numéro de rang."""

    @property
    def rang(self) -> Optional[Rang]:
        """Meilleur rang obtenu (``None`` si aucun gain)."""
        if not self.gains:
            return None
        return self.table.rang(min(self.gains))

    @property
    def nb_gagnantes(self) -> int:
        return sum(self.gains.values())


def verifier(grille: Grille, tirage: Grille, table: Optional[TableDeGains] = None) -> Verification:
    """Compare une grille (simple ou multiple) au tirage et compte les gains par rang.

    Pour une multiple comportant ``n`` numéros dont ``a`` sortis et ``e``
    complémentaires dont ``b`` sortis, le nombre de combinaisons simples ayant
    exactement ``x`` bons numéros et ``y`` bons complémentaires vaut
    C(a, x) × C(n − a, k − x) × C(b, y) × C(e − b, j − y).
    """
    if grille.jeu != tirage.jeu:
        raise ErreurGrille("la grille et le tirage ne sont pas du même jeu")
    if tirage.est_multiple:
        raise ErreurGrille("un tirage comporte exactement les numéros d'une grille simple")
    table = table or grille.jeu.gains
    bons_numeros = tuple(n for n in grille.numeros if n in tirage.numeros)
    bons_bonus = tuple(b for b in grille.bonus if b in tirage.bonus)
    gains = repartition_gains(
        grille.jeu,
        len(grille.numeros),
        len(grille.bonus),
        len(bons_numeros),
        len(bons_bonus),
        table,
    )
    return Verification(grille, tirage, table, bons_numeros, bons_bonus, gains)


def repartition_gains(
    jeu: Jeu,
    nb_numeros: int,
    nb_bonus: int,
    bons_numeros: int,
    bons_bonus: int,
    table: Optional[TableDeGains] = None,
) -> Dict[int, int]:
    """Gains d'une grille (multiple) selon le nombre de numéros et complémentaires trouvés.

    Reproduit le « tableau des rangs de gain en cas de combinaison multiple » de la FDJ.
    """
    table = table or jeu.gains
    k, j = jeu.numeros_par_grille, jeu.bonus_par_grille
    gains: Dict[int, int] = {}
    for x in range(0, k + 1):
        nb_x = math.comb(bons_numeros, x) * math.comb(nb_numeros - bons_numeros, k - x)
        if not nb_x:
            continue
        for y in range(0, j + 1):
            nb_y = math.comb(bons_bonus, y) * math.comb(nb_bonus - bons_bonus, j - y)
            if not nb_y:
                continue
            rang = table.rang_pour(x, y)
            if rang is not None:
                gains[rang.numero] = gains.get(rang.numero, 0) + nb_x * nb_y
    return dict(sorted(gains.items()))
