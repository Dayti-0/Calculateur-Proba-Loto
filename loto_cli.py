#!/usr/bin/env python3
"""
Interface en ligne de commande pour le calculateur de Loto
"""
import sys
from loto_calculator import LotoCalculator, LotoGridGenerator


def print_menu():
    """Affiche le menu principal"""
    print("\n" + "=" * 70)
    print(" " * 15 + "CALCULATEUR LOTO FRANÇAIS")
    print("=" * 70)
    print("\nOptions:")
    print("  1. Afficher les probabilités de gain")
    print("  2. Générer une grille aléatoire")
    print("  3. Générer une grille équilibrée")
    print("  4. Générer plusieurs grilles aléatoires")
    print("  5. Générer une grille avec numéros favoris")
    print("  6. Analyser une grille personnalisée")
    print("  7. Calculer la probabilité d'un rang spécifique")
    print("  0. Quitter")
    print("=" * 70)


def option_1_probabilities():
    """Option 1: Afficher les probabilités"""
    calc = LotoCalculator()
    calc.display_probabilities()


def option_2_random_grid():
    """Option 2: Générer une grille aléatoire"""
    gen = LotoGridGenerator()
    numbers, chance = gen.generate_random_grid()
    gen.display_grid(numbers, chance, with_analysis=True)


def option_3_balanced_grid():
    """Option 3: Générer une grille équilibrée"""
    gen = LotoGridGenerator()
    numbers, chance = gen.generate_balanced_grid()
    gen.display_grid(numbers, chance, with_analysis=True)


def option_4_multiple_grids():
    """Option 4: Générer plusieurs grilles"""
    try:
        count = int(input("\nCombien de grilles voulez-vous générer? (1-20): "))
        if count < 1 or count > 20:
            print("❌ Veuillez entrer un nombre entre 1 et 20")
            return

        gen = LotoGridGenerator()
        grids = gen.generate_multiple_grids(count)

        print(f"\n{'=' * 70}")
        print(f"GÉNÉRATION DE {count} GRILLE(S)")
        print(f"{'=' * 70}")

        for i, (numbers, chance) in enumerate(grids, 1):
            print(f"\nGrille #{i}")
            print(f"Numéros: {' - '.join(str(n).zfill(2) for n in numbers)}")
            print(f"Numéro Chance: {chance}")
            print("-" * 50)

    except ValueError:
        print("❌ Erreur: Veuillez entrer un nombre valide")


def option_5_hot_numbers():
    """Option 5: Générer avec numéros favoris"""
    print("\nEntrez vos numéros favoris (entre 1 et 49)")
    print("Séparez-les par des espaces (ex: 7 13 23 27 41)")

    try:
        input_str = input("Numéros favoris: ")
        hot_numbers = [int(n) for n in input_str.split()]

        # Validation
        if not hot_numbers:
            print("❌ Aucun numéro saisi")
            return

        if any(n < 1 or n > 49 for n in hot_numbers):
            print("❌ Les numéros doivent être entre 1 et 49")
            return

        if len(set(hot_numbers)) != len(hot_numbers):
            print("❌ Vous avez des numéros en double")
            return

        gen = LotoGridGenerator()
        numbers, chance = gen.generate_with_hot_numbers(hot_numbers)
        print(f"\n✓ Grille générée avec {len(hot_numbers)} numéro(s) favori(s)")
        gen.display_grid(numbers, chance, with_analysis=True)

        # Afficher quels numéros favoris ont été utilisés
        used_favorites = [n for n in hot_numbers if n in numbers]
        if used_favorites:
            print(f"\nNuméros favoris utilisés: {', '.join(map(str, used_favorites))}")

    except ValueError:
        print("❌ Erreur: Format invalide. Utilisez des nombres séparés par des espaces")


def option_6_analyze_custom():
    """Option 6: Analyser une grille personnalisée"""
    print("\nAnalyse d'une grille personnalisée")
    print("Entrez 5 numéros entre 1 et 49, séparés par des espaces:")

    try:
        input_str = input("Numéros (ex: 5 12 23 34 45): ")
        numbers = [int(n) for n in input_str.split()]

        # Validation
        if len(numbers) != 5:
            print(f"❌ Vous devez entrer exactement 5 numéros (vous en avez entré {len(numbers)})")
            return

        if any(n < 1 or n > 49 for n in numbers):
            print("❌ Les numéros doivent être entre 1 et 49")
            return

        if len(set(numbers)) != 5:
            print("❌ Vous avez des numéros en double")
            return

        chance = int(input("Numéro Chance (1-10): "))
        if chance < 1 or chance > 10:
            print("❌ Le numéro chance doit être entre 1 et 10")
            return

        numbers = sorted(numbers)
        gen = LotoGridGenerator()
        gen.display_grid(numbers, chance, with_analysis=True)

    except ValueError:
        print("❌ Erreur: Format invalide. Utilisez des nombres entiers")


def option_7_specific_probability():
    """Option 7: Calculer la probabilité d'un rang spécifique"""
    print("\nCalcul de probabilité pour un rang spécifique")

    try:
        correct_nums = int(input("Combien de numéros corrects? (0-5): "))
        if correct_nums < 0 or correct_nums > 5:
            print("❌ Le nombre doit être entre 0 et 5")
            return

        chance_input = input("Numéro chance correct? (oui/non): ").lower()
        correct_chance = chance_input in ['oui', 'o', 'y', 'yes']

        calc = LotoCalculator()
        result = calc.probability_rank(correct_nums, correct_chance)

        print("\n" + "=" * 70)
        print("RÉSULTAT DU CALCUL")
        print("=" * 70)
        print(f"Configuration: {correct_nums} numéro(s) correct(s)", end="")
        print(f" + numéro chance" if correct_chance else " sans numéro chance")
        print(f"\nCombinaisons favorables: {result['favorable_outcomes']:,}")
        print(f"Combinaisons totales: {result['total_combinations']:,}")
        print(f"Probabilité: {result['probability']:.10f} ({result['probability']*100:.8f}%)")
        print(f"Chances de gagner: {result['odds']}")
        print("=" * 70)

    except ValueError:
        print("❌ Erreur: Entrée invalide")


def main():
    """Fonction principale du CLI"""
    calculator = LotoCalculator()
    generator = LotoGridGenerator()

    while True:
        print_menu()

        try:
            choice = input("\nChoisissez une option (0-7): ").strip()

            if choice == '0':
                print("\n👋 Au revoir et bonne chance!")
                sys.exit(0)
            elif choice == '1':
                option_1_probabilities()
            elif choice == '2':
                option_2_random_grid()
            elif choice == '3':
                option_3_balanced_grid()
            elif choice == '4':
                option_4_multiple_grids()
            elif choice == '5':
                option_5_hot_numbers()
            elif choice == '6':
                option_6_analyze_custom()
            elif choice == '7':
                option_7_specific_probability()
            else:
                print("❌ Option invalide. Veuillez choisir entre 0 et 7")

            input("\nAppuyez sur Entrée pour continuer...")

        except KeyboardInterrupt:
            print("\n\n👋 Au revoir et bonne chance!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Erreur inattendue: {e}")
            input("\nAppuyez sur Entrée pour continuer...")


if __name__ == "__main__":
    main()
