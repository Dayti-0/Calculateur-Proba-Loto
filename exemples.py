#!/usr/bin/env python3
"""
Exemples d'utilisation du module loto_calculator
"""
from loto_calculator import LotoCalculator, LotoGridGenerator


def exemple_1_calcul_probabilites():
    """Exemple 1: Calculer et afficher les probabilités"""
    print("\n" + "=" * 70)
    print("EXEMPLE 1: Calcul des probabilités de gain")
    print("=" * 70)

    calc = LotoCalculator()

    # Afficher toutes les probabilités
    calc.display_probabilities()

    # Calculer une probabilité spécifique
    print("\n\nCalcul personnalisé:")
    print("-" * 70)
    prob = calc.probability_rank(3, True)
    print(f"\nProbabilité d'avoir 3 numéros + chance:")
    print(f"  {prob['probability']:.8%}")
    print(f"  Soit {prob['odds']}")


def exemple_2_generation_simple():
    """Exemple 2: Génération simple de grilles"""
    print("\n" + "=" * 70)
    print("EXEMPLE 2: Génération simple de grilles")
    print("=" * 70)

    gen = LotoGridGenerator()

    # Grille aléatoire
    print("\n1. Une grille aléatoire:")
    numbers, chance = gen.generate_random_grid()
    gen.display_grid(numbers, chance, with_analysis=True)

    # Plusieurs grilles
    print("\n2. Cinq grilles aléatoires:")
    grids = gen.generate_multiple_grids(5)
    for i, (nums, ch) in enumerate(grids, 1):
        print(f"\nGrille {i}: {' - '.join(str(n).zfill(2) for n in nums)} | Chance: {ch}")


def exemple_3_grilles_strategiques():
    """Exemple 3: Grilles avec stratégies"""
    print("\n" + "=" * 70)
    print("EXEMPLE 3: Grilles stratégiques")
    print("=" * 70)

    gen = LotoGridGenerator()

    # Grille équilibrée
    print("\n1. Grille équilibrée (répartition optimale):")
    numbers, chance = gen.generate_balanced_grid()
    gen.display_grid(numbers, chance, with_analysis=True)

    # Grille avec numéros "chauds"
    print("\n2. Grille avec numéros favoris [7, 13, 21, 27, 42]:")
    hot = [7, 13, 21, 27, 42]
    numbers, chance = gen.generate_with_hot_numbers(hot)
    gen.display_grid(numbers, chance, with_analysis=True)
    print(f"\nNuméros favoris utilisés: {[n for n in hot if n in numbers]}")


def exemple_4_analyse_grille():
    """Exemple 4: Analyse détaillée d'une grille"""
    print("\n" + "=" * 70)
    print("EXEMPLE 4: Analyse détaillée d'une grille")
    print("=" * 70)

    gen = LotoGridGenerator()

    # Grille personnalisée à analyser
    ma_grille = [7, 14, 21, 28, 35]
    mon_chance = 7

    print(f"\nGrille à analyser: {ma_grille}")
    print(f"Numéro chance: {mon_chance}")

    # Analyse complète
    analysis = gen.analyze_grid(ma_grille, mon_chance)

    print("\nRésultats de l'analyse:")
    print("-" * 70)
    print(f"Somme totale: {analysis['sum']}")
    print(f"Numéros pairs: {analysis['even_count']}")
    print(f"Numéros impairs: {analysis['odd_count']}")
    print(f"Numéros bas (1-24): {analysis['low_count']}")
    print(f"Numéros hauts (25-49): {analysis['high_count']}")
    print(f"Tranches couvertes: {analysis['ranges_covered']} sur 5")
    print(f"Numéros consécutifs présents: {'Oui' if analysis['consecutive'] else 'Non'}")

    # Affichage formaté
    gen.display_grid(ma_grille, mon_chance, with_analysis=True)


def exemple_5_comparaison_strategies():
    """Exemple 5: Comparaison de différentes stratégies"""
    print("\n" + "=" * 70)
    print("EXEMPLE 5: Comparaison de stratégies")
    print("=" * 70)

    gen = LotoGridGenerator()

    strategies = [
        ("Aléatoire", gen.generate_random_grid),
        ("Équilibrée", gen.generate_balanced_grid),
    ]

    print("\nGénération de 3 grilles par stratégie:\n")

    for strategy_name, strategy_func in strategies:
        print(f"\n{strategy_name}:")
        print("-" * 50)

        total_sum = 0
        total_even = 0
        total_consecutive = 0

        for i in range(3):
            numbers, chance = strategy_func()
            analysis = gen.analyze_grid(numbers, chance)

            print(f"  Grille {i+1}: {' - '.join(str(n).zfill(2) for n in numbers)}")
            print(f"    Somme: {analysis['sum']}, Pairs: {analysis['even_count']}, " +
                  f"Consécutifs: {'Oui' if analysis['consecutive'] else 'Non'}")

            total_sum += analysis['sum']
            total_even += analysis['even_count']
            total_consecutive += 1 if analysis['consecutive'] else 0

        print(f"\n  Moyenne somme: {total_sum/3:.1f}")
        print(f"  Moyenne pairs: {total_even/3:.1f}")
        print(f"  Grilles avec consécutifs: {total_consecutive}/3")


def exemple_6_simulation():
    """Exemple 6: Simulation de jeu"""
    print("\n" + "=" * 70)
    print("EXEMPLE 6: Simulation d'un jeu complet")
    print("=" * 70)

    gen = LotoGridGenerator()
    calc = LotoCalculator()

    # Simuler un tirage gagnant
    tirage = sorted([7, 14, 23, 31, 42])
    chance_tirage = 5

    print(f"\nTirage gagnant (simulé):")
    print(f"Numéros: {' - '.join(str(n).zfill(2) for n in tirage)}")
    print(f"Numéro Chance: {chance_tirage}")

    # Générer plusieurs grilles et voir les résultats
    print(f"\n\nVérification de 10 grilles aléatoires:")
    print("-" * 70)

    for i in range(10):
        numbers, chance = gen.generate_random_grid()

        # Compter les bons numéros
        correct_nums = len(set(numbers) & set(tirage))
        correct_chance = (chance == chance_tirage)

        print(f"\nGrille {i+1}: {' - '.join(str(n).zfill(2) for n in numbers)} | Chance: {chance}")
        print(f"  Résultat: {correct_nums} bon(s) numéro(s)", end="")
        if correct_chance:
            print(" + numéro chance ✓")
        else:
            print("")

        # Afficher le rang si gagnant
        rang = calc.rank_for(correct_nums, correct_chance)
        if rang is not None:
            print(f"  🎉 GAGNANT - Rang {rang}")


def main():
    """Fonction principale - lance tous les exemples"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "EXEMPLES D'UTILISATION DU CALCULATEUR LOTO" + " " * 11 + "║")
    print("╚" + "═" * 68 + "╝")

    exemples = [
        exemple_1_calcul_probabilites,
        exemple_2_generation_simple,
        exemple_3_grilles_strategiques,
        exemple_4_analyse_grille,
        exemple_5_comparaison_strategies,
        exemple_6_simulation,
    ]

    for i, exemple in enumerate(exemples, 1):
        exemple()
        if i < len(exemples):
            input("\n\nAppuyez sur Entrée pour continuer vers l'exemple suivant...")

    print("\n\n" + "=" * 70)
    print("FIN DES EXEMPLES")
    print("=" * 70)
    print("\nPour une interface graphique, ouvrez le fichier interface.html")
    print("Pour une utilisation en ligne de commande, lancez: python3 loto_cli.py")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
