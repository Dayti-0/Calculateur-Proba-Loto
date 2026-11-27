"""Calculateur de probabilités EuroMillions – My Million de la FDJ.

Probabilités exactes, grilles multiples, espérance de gain, génération de
grilles et statistiques sur l'historique officiel des tirages.

Exemple ::

    >>> from proba_loto import EUROMILLIONS, Grille, probabilite_gain
    >>> float(1 / probabilite_gain(EUROMILLIONS))  # doctest: +ELLIPSIS
    12.97...
    >>> grille = Grille.depuis_texte(EUROMILLIONS, "3 5 37 44 49 + 5 6")
    >>> grille.nb_combinaisons_simples
    1
"""

__version__ = "2.0.0"

from .jeux import ETOILE_PLUS, EUROMILLIONS, Jeu, Rang, TableDeGains, obtenir_jeu
from .probabilites import (
    nb_combinaisons,
    probabilite,
    probabilite_gain,
    probabilite_rang,
    tableau_probabilites,
)
from .grilles import ErreurGrille, Grille, verifier
from .multiples import analyser_multiple, cout_multiple
from .generateur import Generateur
from .esperance import calculer_esperance

__all__ = [
    "__version__",
    "EUROMILLIONS",
    "ETOILE_PLUS",
    "Jeu",
    "Rang",
    "TableDeGains",
    "obtenir_jeu",
    "nb_combinaisons",
    "probabilite",
    "probabilite_rang",
    "probabilite_gain",
    "tableau_probabilites",
    "Grille",
    "ErreurGrille",
    "verifier",
    "analyser_multiple",
    "cout_multiple",
    "Generateur",
    "calculer_esperance",
]
