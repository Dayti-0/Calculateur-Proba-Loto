"""Règles officielles de l'EuroMillions – My Million, décrites comme des données.

Toutes les valeurs proviennent du règlement EuroMillions – My Million et Étoile+
de la Française des Jeux, homologué par l'ANJ le 27 mars 2025 (décision
2025-PR-054, dernière modification du 17 janvier 2025) : articles 2.4 (mise),
3.1 (combinaisons multiples), 4.2.2 à 4.2.5 (rangs, répartition, plafond),
5 (My Million) et 6 (Étoile+).

Décrire les règles comme des données (et non dans le code des calculs) permet
d'intégrer une évolution du règlement — par exemple la réforme de l'EuroMillions
annoncée pour le 2 mars 2027 — en ajoutant simplement une nouvelle définition.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Optional, Tuple

__all__ = [
    "Rang",
    "TableDeGains",
    "Jeu",
    "EUROMILLIONS",
    "ETOILE_PLUS",
    "JEUX",
    "obtenir_jeu",
    "MY_MILLION_MISE",
    "MY_MILLION_GAIN",
    "EM_PART_RANG1_DEBUT_CYCLE",
    "EM_PART_RANG1_APRES_5_TIRAGES",
    "EM_JACKPOT_MINIMUM",
    "EM_PLAFOND_JACKPOT",
    "EM_TIRAGES_AU_PLAFOND",
]


@dataclass(frozen=True)
class Rang:
    """Un rang de gain.

    ``correspondances`` liste les couples (bons numéros, bons numéros
    complémentaires) qui donnent droit à ce rang.

    ``part`` est la fraction de la masse des gains affectée au rang.
    """

    numero: int
    correspondances: Tuple[Tuple[int, int], ...]
    part: Optional[Fraction] = None


@dataclass(frozen=True)
class TableDeGains:
    """Table de rangs d'un jeu ou d'une option (ex. Étoile+)."""

    nom: str
    rangs: Tuple[Rang, ...]
    mise: Fraction
    """Mise par combinaison simple consacrée à cette table (en euros)."""
    part_gagnants: Fraction
    """Part des mises reversée aux gagnants (globalement, pas tirage par tirage)."""

    def rang_pour(self, bons_numeros: int, bons_bonus: int) -> Optional[Rang]:
        """Rang obtenu pour une combinaison simple, ou ``None`` si perdante."""
        for rang in self.rangs:
            if (bons_numeros, bons_bonus) in rang.correspondances:
                return rang
        return None

    def rang(self, numero: int) -> Rang:
        for rang in self.rangs:
            if rang.numero == numero:
                return rang
        raise KeyError(f"{self.nom} : pas de rang {numero}")

    @property
    def masse_par_grille(self) -> Fraction:
        """Montant reversé aux gagnants pour chaque combinaison simple jouée."""
        return self.mise * self.part_gagnants


@dataclass(frozen=True)
class Jeu:
    """Description complète d'un jeu de tirage."""

    cle: str
    nom: str
    numeros_max: int
    numeros_par_grille: int
    bonus_max: int
    bonus_par_grille: int
    bonus_nom: str
    bonus_nom_pluriel: str
    prix_grille: Fraction
    """Prix d'une grille simple payé par le joueur (jeux obligatoirement associés inclus)."""
    gains: TableDeGains
    options: Tuple[TableDeGains, ...]
    multiple_numeros_max: int
    multiple_bonus_max: int
    multiple_combinaisons_max: int
    """Plus grand nombre de combinaisons simples autorisé pour une grille multiple."""
    jours_tirage: Tuple[str, ...]
    reference: str

    def __repr__(self) -> str:
        return f"Jeu({self.cle!r})"

    @property
    def tirages_par_semaine(self) -> int:
        return len(self.jours_tirage)

    def option(self, nom: str) -> TableDeGains:
        cle = _normaliser(nom)
        for option in self.options:
            if _normaliser(option.nom) == cle:
                return option
        raise KeyError(f"{self.nom} : option inconnue « {nom} »")

    def libelle_bonus(self, nombre: int) -> str:
        """« 2 étoiles », « 1 étoile », « 0 étoile »."""
        nom = self.bonus_nom_pluriel if nombre > 1 else self.bonus_nom
        return f"{nombre} {nom}"

    def libelle_correspondance(self, bons_numeros: int, bons_bonus: int) -> str:
        numeros = f"{bons_numeros} numéro{'s' if bons_numeros > 1 else ''}"
        return f"{numeros} + {self.libelle_bonus(bons_bonus)}"

    def libelle_rang(self, rang: Rang) -> str:
        return " ou ".join(self.libelle_correspondance(a, b) for a, b in rang.correspondances)


def _normaliser(texte: str) -> str:
    return (
        texte.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("+", "plus")
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )


def _f(valeur: str) -> Fraction:
    return Fraction(valeur)


# ---------------------------------------------------------------------------
# EuroMillions – My Million (règlement FDJ, mars 2025)
# ---------------------------------------------------------------------------

MY_MILLION_MISE = _f("0.30")
"""Part de la grille à 2,50 € consacrée au code My Million (art. 2.4)."""
MY_MILLION_GAIN = 1_000_000
"""Un code My Million gagnant d'un million d'euros à chaque tirage (art. 5.2)."""

EM_PART_RANG1_DEBUT_CYCLE = _f("0.50")
"""Part de la masse des gains affectée au jackpot pendant les 5 premiers tirages d'un cycle."""
EM_PART_RANG1_APRES_5_TIRAGES = _f("0.42")
"""Part affectée au jackpot à partir du 6e tirage d'un cycle (art. 4.2.4.1)."""
EM_JACKPOT_MINIMUM = 17_000_000
"""Jackpot minimum garanti au premier tirage d'un cycle (art. 4.2.4.2.2.1)."""
EM_PLAFOND_JACKPOT = 250_000_000
"""Plafond du 1er rang en vigueur (200 M€ en 2020, +10 M€ par cycle, maximum 250 M€)."""
EM_TIRAGES_AU_PLAFOND = 5
"""Au 5e tirage consécutif au plafond sans gagnant, le jackpot descend au rang inférieur."""

_EM_RANGS = (
    Rang(1, ((5, 2),), part=EM_PART_RANG1_DEBUT_CYCLE),
    Rang(2, ((5, 1),), part=_f("0.0261")),
    Rang(3, ((5, 0),), part=_f("0.0061")),
    Rang(4, ((4, 2),), part=_f("0.0019")),
    Rang(5, ((4, 1),), part=_f("0.0035")),
    Rang(6, ((3, 2),), part=_f("0.0037")),
    Rang(7, ((4, 0),), part=_f("0.0026")),
    Rang(8, ((2, 2),), part=_f("0.0130")),
    Rang(9, ((3, 1),), part=_f("0.0145")),
    Rang(10, ((3, 0),), part=_f("0.0270")),
    Rang(11, ((1, 2),), part=_f("0.0327")),
    Rang(12, ((2, 1),), part=_f("0.1030")),
    Rang(13, ((2, 0),), part=_f("0.1659")),
)

ETOILE_PLUS = TableDeGains(
    nom="Étoile+",
    rangs=(
        Rang(1, ((5, 1),), part=_f("0.0010")),
        Rang(2, ((4, 2),), part=_f("0.0008")),
        Rang(3, ((4, 1),), part=_f("0.0010")),
        Rang(4, ((3, 2),), part=_f("0.0010")),
        Rang(5, ((2, 2),), part=_f("0.0025")),
        Rang(6, ((3, 1),), part=_f("0.0067")),
        Rang(7, ((1, 2),), part=_f("0.0315")),
        Rang(8, ((0, 2),), part=_f("0.1460")),
        Rang(9, ((2, 1),), part=_f("0.0825")),
        Rang(10, ((0, 1),), part=_f("0.7270")),
    ),
    mise=_f("1"),
    part_gagnants=_f("0.60"),
)
"""Option Étoile+ (1 € par combinaison simple, 60 % des mises aux gagnants, art. 6)."""

EUROMILLIONS = Jeu(
    cle="euromillions",
    nom="EuroMillions",
    numeros_max=50,
    numeros_par_grille=5,
    bonus_max=12,
    bonus_par_grille=2,
    bonus_nom="étoile",
    bonus_nom_pluriel="étoiles",
    prix_grille=_f("2.50"),
    gains=TableDeGains(
        nom="EuroMillions",
        rangs=_EM_RANGS,
        mise=_f("2.20"),
        part_gagnants=_f("0.50"),
    ),
    options=(ETOILE_PLUS,),
    multiple_numeros_max=10,
    multiple_bonus_max=12,
    multiple_combinaisons_max=396,
    jours_tirage=("mardi", "vendredi"),
    reference=(
        "Règlement FDJ EuroMillions – My Million et Étoile+, "
        "homologué par l'ANJ le 27 mars 2025 (décision 2025-PR-054)"
    ),
)

JEUX = {EUROMILLIONS.cle: EUROMILLIONS}


def obtenir_jeu(nom: str) -> Jeu:
    """Retourne un jeu à partir de son nom (« euromillions », « EuroMillions », « em »)."""
    cle = _normaliser(nom)
    alias = {"em": "euromillions", "euromillion": "euromillions"}
    cle = alias.get(cle, cle)
    try:
        return JEUX[cle]
    except KeyError:
        connus = ", ".join(sorted(JEUX))
        raise KeyError(f"jeu inconnu « {nom} » (jeux disponibles : {connus})") from None
