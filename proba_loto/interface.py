"""Interface graphique : une page web autonome générée à partir des règles et des données.

La page (``interface.html`` à la racine du dépôt) s'ouvre d'un double-clic, sans
installation ni connexion : toutes les données (règles officielles, historique
des tirages, popularité des numéros) y sont intégrées. Elle est générée à partir
du modèle ``proba_loto/web/interface.html`` pour que la page et la bibliothèque
Python partagent exactement les mêmes règles et les mêmes données.
"""

from __future__ import annotations

import json
import webbrowser
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from . import __version__
from .analyse import bornes_somme
from .esperance import _VENTES_A, _VENTES_B, PART_FRANCE
from .historique import TirageHistorique, charger, fichier_cache
from .jeux import (
    EM_JACKPOT_MINIMUM,
    EM_PART_RANG1_APRES_5_TIRAGES,
    EM_PART_RANG1_DEBUT_CYCLE,
    EM_PLAFOND_JACKPOT,
    EUROMILLIONS,
    MY_MILLION_GAIN,
    MY_MILLION_MISE,
    Jeu,
    TableDeGains,
)
from .popularite import estimer_popularite
from .simulation import CODES_MY_MILLION_PAR_DEFAUT, JACKPOT_MOYEN_PAR_DEFAUT

__all__ = [
    "MODELE",
    "INTERFACE_DEPOT",
    "COLONNES_HISTORIQUE",
    "donnees_regles",
    "donnees_historique",
    "construire_page",
    "extraire_fragment",
    "ecrire_interface",
    "ouvrir_interface",
]

MODELE = Path(__file__).resolve().parent / "web" / "interface.html"
INTERFACE_DEPOT = Path(__file__).resolve().parent.parent / "interface.html"
"""Emplacement de la page dans le dépôt (absent d'une installation par pip)."""

COLONNES_HISTORIQUE = (
    ["date", "n1", "n2", "n3", "n4", "n5", "e1", "e2"]
    + [f"rapport_r{k}" for k in range(1, 14)]
    + [f"gagnants_europe_r{k}" for k in range(1, 14)]
    + [f"rapport_etoile_plus_r{k}" for k in range(1, 11)]
    + [f"gagnants_etoile_plus_r{k}" for k in range(1, 11)]
)

_REPERE_REGLES = "/*REGLES*/"
_REPERE_HISTORIQUE = "/*HISTORIQUE*/"


def _nombre(valeur: Union[int, float, Fraction, None]) -> Union[int, float, None]:
    if valeur is None:
        return None
    flottant = float(valeur)
    return int(flottant) if flottant.is_integer() else round(flottant, 6)


def _table(table: TableDeGains) -> Dict[str, Any]:
    return {
        "nom": table.nom,
        "mise": _nombre(table.mise),
        "partGagnants": _nombre(table.part_gagnants),
        "rangs": [
            {
                "numero": rang.numero,
                "correspondances": [list(c) for c in rang.correspondances],
                "part": _nombre(rang.part),
            }
            for rang in table.rangs
        ],
    }


def _jeu(jeu: Jeu) -> Dict[str, Any]:
    return {
        "cle": jeu.cle,
        "nom": jeu.nom,
        "numerosMax": jeu.numeros_max,
        "numerosParGrille": jeu.numeros_par_grille,
        "bonusMax": jeu.bonus_max,
        "bonusParGrille": jeu.bonus_par_grille,
        "bonusNom": jeu.bonus_nom,
        "bonusNomPluriel": jeu.bonus_nom_pluriel,
        "prixGrille": _nombre(jeu.prix_grille),
        "gains": _table(jeu.gains),
        "options": [_table(o) for o in jeu.options],
        "multipleNumerosMax": jeu.multiple_numeros_max,
        "multipleBonusMax": jeu.multiple_bonus_max,
        "multipleCombinaisonsMax": jeu.multiple_combinaisons_max,
        "joursTirage": list(jeu.jours_tirage),
        "bornesSomme": list(bornes_somme(jeu)),
        "reference": jeu.reference,
    }


def donnees_regles(tirages: Optional[Sequence[TirageHistorique]] = None) -> Dict[str, Any]:
    """Règles, constantes et popularité (données légères, toujours intégrées à la page)."""
    popularite = None
    if tirages:
        modele = estimer_popularite(tirages)
        popularite = {
            "numeros": [round(modele.facteurs_numeros[n], 12) for n in range(1, 51)],
            "etoiles": [round(modele.facteurs_etoiles[e], 12) for e in range(1, 13)],
            "correlation": round(modele.correlation_validation or 0.0, 4),
            "nbTirages": modele.nb_tirages,
            "debut": modele.debut.isoformat() if modele.debut else None,
            "fin": modele.fin.isoformat() if modele.fin else None,
        }
    return {
        "version": __version__,
        "jeu": _jeu(EUROMILLIONS),
        "constantes": {
            "myMillionMise": _nombre(MY_MILLION_MISE),
            "myMillionGain": MY_MILLION_GAIN,
            "partRang1Debut": _nombre(EM_PART_RANG1_DEBUT_CYCLE),
            "partRang1Apres": _nombre(EM_PART_RANG1_APRES_5_TIRAGES),
            "jackpotMinimum": EM_JACKPOT_MINIMUM,
            "plafond": EM_PLAFOND_JACKPOT,
            "ventesA": _VENTES_A,
            "ventesB": _VENTES_B,
            "partFrance": PART_FRANCE,
            "jackpotMoyen": JACKPOT_MOYEN_PAR_DEFAUT,
            "codesMyMillion": CODES_MY_MILLION_PAR_DEFAUT,
        },
        "popularite": popularite,
    }


def donnees_historique(tirages: Sequence[TirageHistorique]) -> Dict[str, Any]:
    """Historique compact : une ligne de nombres par tirage (voir ``COLONNES_HISTORIQUE``)."""
    lignes: List[List[Union[int, float, None]]] = []
    for t in tirages:
        lignes.append(
            [int(t.date.strftime("%Y%m%d")), *t.numeros, *t.etoiles]
            + [_nombre(r) for r in t.rapports]
            + list(t.gagnants_europe)
            + [_nombre(r) for r in t.rapports_etoile_plus]
            + list(t.gagnants_etoile_plus)
        )
    return {"colonnes": COLONNES_HISTORIQUE, "lignes": lignes}


def _json(donnees: Any) -> str:
    # « </ » ne doit jamais apparaître dans un bloc <script>.
    return json.dumps(donnees, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def construire_page(
    tirages: Optional[Sequence[TirageHistorique]] = None, integrer_historique: bool = True
) -> str:
    """Page HTML complète. Sans historique intégré, la page lit ``historique.json`` à côté d'elle."""
    if tirages is None:
        tirages = charger()
    modele = MODELE.read_text(encoding="utf-8")
    if _REPERE_REGLES not in modele or _REPERE_HISTORIQUE not in modele:
        raise ValueError("modèle d'interface invalide : repères de données absents")
    historique = _json(donnees_historique(tirages)) if integrer_historique else ""
    return modele.replace(_REPERE_REGLES, _json(donnees_regles(tirages))).replace(
        _REPERE_HISTORIQUE, historique
    )


def extraire_fragment(page: str) -> str:
    """Contenu publiable sans squelette (sans doctype, html, head ni body)."""
    debut, fin_entete = "<!--DEBUT_PAGE-->", "<!--FIN_ENTETE-->"
    debut_corps, fin = "<!--DEBUT_CORPS-->", "<!--FIN_PAGE-->"
    try:
        entete = page.split(debut, 1)[1].split(fin_entete, 1)[0]
        corps = page.split(debut_corps, 1)[1].split(fin, 1)[0]
    except IndexError:
        raise ValueError("repères de fragment absents du modèle") from None
    return entete.strip() + "\n" + corps.strip() + "\n"


def ecrire_interface(
    sortie: Optional[Union[str, Path]] = None,
    tirages: Optional[Sequence[TirageHistorique]] = None,
) -> Path:
    """Écrit la page (par défaut dans le cache utilisateur, avec l'historique le plus récent)."""
    chemin = Path(sortie) if sortie is not None else fichier_cache().with_name("interface.html")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(construire_page(tirages), encoding="utf-8")
    return chemin


def ouvrir_interface(chemin: Union[str, Path]) -> bool:
    """Ouvre la page dans le navigateur ; ``False`` si aucun navigateur n'est disponible."""
    try:
        return bool(webbrowser.open(Path(chemin).resolve().as_uri()))
    except (webbrowser.Error, OSError):
        return False
