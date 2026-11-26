#!/usr/bin/env python3
"""Exemples d'utilisation de la bibliothèque ``proba_loto`` (sans interaction).

Lancer depuis la racine du dépôt : ``python3 exemples.py``
"""

from proba_loto import (
    EUROMILLIONS,
    ETOILE_PLUS,
    Generateur,
    Grille,
    analyser_multiple,
    calculer_esperance,
    probabilite_gain,
    tableau_probabilites,
    verifier,
)
from proba_loto import affichage as fmt
from proba_loto.historique import charger
from proba_loto.popularite import estimer_popularite
from proba_loto.statistiques import retro_tester


def titre(texte: str) -> None:
    print(f"\n=== {texte} ===")


def main() -> None:
    titre("1. Probabilités exactes de l'EuroMillions")
    for ligne in tableau_probabilites(EUROMILLIONS):
        print(f"  rang {ligne.rang.numero:>2} : {ligne.libelle:<22} {fmt.chances(ligne.probabilite)}")
    print(f"  Gagner quelque chose : {fmt.chances(probabilite_gain(EUROMILLIONS), decimales=2)}")

    titre("2. Vérifier une grille contre le dernier tirage officiel")
    historique = charger()
    dernier = historique[-1]
    grille = Grille.depuis_texte(EUROMILLIONS, "3 5 12 44 50 + 5 9")
    for table in (EUROMILLIONS.gains, ETOILE_PLUS):
        resultat = verifier(grille, dernier.combinaison, table)
        print(f"  {table.nom} le {dernier.date:%d/%m/%Y} : rangs gagnés {resultat.gains or 'aucun'}")

    titre("3. Générer des grilles peu jouées (moins de partage en cas de gain)")
    modele = estimer_popularite(historique)
    generateur = Generateur(EUROMILLIONS, graine=2026, modele=modele, dernier_tirage=dernier.combinaison)
    for g in generateur.grilles(3, "anti-partage"):
        print(f"  {g}   indice de popularité {fmt.decimal(modele.indice(g), 2)}")

    titre("4. Une grille multiple 7 numéros × 3 étoiles")
    analyse = analyser_multiple(EUROMILLIONS, 7, 3)
    print(f"  {analyse.nb_simples} grilles simples ; gagner au moins un rang : "
          f"{fmt.chances(analyse.probabilite_gain, decimales=2)}")

    titre("5. Espérance de gain pour un jackpot de 59 M€")
    e = calculer_esperance(59e6)
    print(f"  {fmt.euros(e.total)} récupérés en moyenne pour {fmt.euros(e.mise)} misés "
          f"({fmt.pourcentage(e.taux_retour)})")

    titre("6. Rétro-test : la grille 7 13 17 19 23 + 3 7 jouée à chaque tirage depuis 2016")
    retro = retro_tester(Grille.depuis_texte(EUROMILLIONS, "7 13 17 19 23 + 3 7"), historique)
    print(f"  Mise {fmt.euros(retro.mise_totale)}, gains {fmt.euros(retro.total_gains)} "
          f"({fmt.pourcentage(retro.taux_retour)})")


if __name__ == "__main__":
    main()
