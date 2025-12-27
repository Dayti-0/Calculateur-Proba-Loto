"""
Calculateur de probabilités pour le Loto Français
Le Loto français: 5 numéros entre 1 et 49 + 1 numéro chance entre 1 et 10
"""
import math
from typing import List, Tuple, Dict
import random
from collections import Counter


class LotoCalculator:
    """Classe pour calculer les probabilités du Loto français"""

    # Constantes du Loto français
    TOTAL_NUMBERS = 49
    NUMBERS_TO_PICK = 5
    TOTAL_CHANCE = 10

    def __init__(self):
        self.total_combinations = self.calculate_total_combinations()

    @staticmethod
    def combination(n: int, k: int) -> int:
        """Calcule C(n,k) = n! / (k! * (n-k)!)"""
        return math.factorial(n) // (math.factorial(k) * math.factorial(n - k))

    def calculate_total_combinations(self) -> int:
        """Calcule le nombre total de combinaisons possibles"""
        main_combinations = self.combination(self.TOTAL_NUMBERS, self.NUMBERS_TO_PICK)
        return main_combinations * self.TOTAL_CHANCE

    def probability_rank(self, correct_numbers: int, correct_chance: bool) -> Dict:
        """
        Calcule la probabilité d'obtenir un certain rang

        Args:
            correct_numbers: Nombre de numéros corrects (0-5)
            correct_chance: Si le numéro chance est correct

        Returns:
            Dict avec probabilité et ratio
        """
        # Combinaisons pour avoir exactement correct_numbers bons numéros
        ways_to_get_correct = self.combination(self.NUMBERS_TO_PICK, correct_numbers)
        ways_to_get_wrong = self.combination(
            self.TOTAL_NUMBERS - self.NUMBERS_TO_PICK,
            self.NUMBERS_TO_PICK - correct_numbers
        )

        main_combinations = ways_to_get_correct * ways_to_get_wrong

        # Probabilité du numéro chance
        chance_prob = 1 if correct_chance else 9

        favorable_outcomes = main_combinations * chance_prob
        probability = favorable_outcomes / self.total_combinations

        return {
            'correct_numbers': correct_numbers,
            'correct_chance': correct_chance,
            'favorable_outcomes': favorable_outcomes,
            'total_combinations': self.total_combinations,
            'probability': probability,
            'odds': f"1 sur {int(1/probability):,}" if probability > 0 else "Impossible"
        }

    def get_all_winning_probabilities(self) -> List[Dict]:
        """Retourne les probabilités pour tous les rangs de gain du Loto"""
        ranks = [
            (5, True, "Rang 1: 5 numéros + numéro chance"),
            (5, False, "Rang 2: 5 numéros"),
            (4, True, "Rang 3: 4 numéros + numéro chance"),
            (4, False, "Rang 4: 4 numéros"),
            (3, True, "Rang 5: 3 numéros + numéro chance"),
            (3, False, "Rang 6: 3 numéros"),
            (2, True, "Rang 7: 2 numéros + numéro chance"),
        ]

        results = []
        for correct_nums, correct_chance, description in ranks:
            prob = self.probability_rank(correct_nums, correct_chance)
            prob['rank_description'] = description
            results.append(prob)

        return results

    def display_probabilities(self):
        """Affiche toutes les probabilités de gain"""
        print("=" * 70)
        print("PROBABILITÉS DE GAIN AU LOTO FRANÇAIS")
        print("=" * 70)
        print(f"\nNombre total de combinaisons possibles: {self.total_combinations:,}")
        print("\nRangs de gain:")
        print("-" * 70)

        for rank in self.get_all_winning_probabilities():
            print(f"\n{rank['rank_description']}")
            print(f"  Probabilité: {rank['probability']:.10f} ({rank['probability']*100:.8f}%)")
            print(f"  Chances: {rank['odds']}")


class LotoGridGenerator:
    """Génère des grilles de Loto selon différentes stratégies"""

    def __init__(self):
        self.calculator = LotoCalculator()

    def generate_random_grid(self) -> Tuple[List[int], int]:
        """Génère une grille complètement aléatoire"""
        numbers = sorted(random.sample(range(1, 50), 5))
        chance = random.randint(1, 10)
        return numbers, chance

    def generate_multiple_grids(self, count: int) -> List[Tuple[List[int], int]]:
        """Génère plusieurs grilles aléatoires"""
        return [self.generate_random_grid() for _ in range(count)]

    def generate_balanced_grid(self) -> Tuple[List[int], int]:
        """
        Génère une grille équilibrée:
        - Mélange de nombres pairs et impairs
        - Répartition sur toutes les tranches (1-10, 11-20, etc.)
        """
        numbers = []

        # Diviser en tranches de 10
        ranges = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 49)]

        # Prendre au moins un nombre dans 3-4 tranches différentes
        num_ranges = random.randint(3, 4)
        selected_ranges = random.sample(ranges, num_ranges)

        for i, range_tuple in enumerate(selected_ranges):
            if i < 4:  # S'assurer de ne pas dépasser 5 nombres
                numbers.append(random.randint(range_tuple[0], range_tuple[1]))

        # Compléter jusqu'à 5 nombres si nécessaire
        while len(numbers) < 5:
            num = random.randint(1, 49)
            if num not in numbers:
                numbers.append(num)

        numbers = sorted(numbers)
        chance = random.randint(1, 10)

        return numbers, chance

    def generate_with_hot_numbers(self, hot_numbers: List[int]) -> Tuple[List[int], int]:
        """
        Génère une grille en favorisant certains numéros "chauds"

        Args:
            hot_numbers: Liste de numéros considérés comme "chauds"
        """
        # Prendre 2-3 numéros "chauds"
        num_hot = random.randint(2, min(3, len(hot_numbers)))
        selected_hot = random.sample(hot_numbers, num_hot)

        # Compléter avec des numéros aléatoires
        remaining_numbers = [n for n in range(1, 50) if n not in selected_hot]
        additional = random.sample(remaining_numbers, 5 - num_hot)

        numbers = sorted(selected_hot + additional)
        chance = random.randint(1, 10)

        return numbers, chance

    def analyze_grid(self, numbers: List[int], chance: int) -> Dict:
        """Analyse une grille et retourne ses caractéristiques"""
        return {
            'numbers': numbers,
            'chance': chance,
            'sum': sum(numbers),
            'even_count': sum(1 for n in numbers if n % 2 == 0),
            'odd_count': sum(1 for n in numbers if n % 2 == 1),
            'low_count': sum(1 for n in numbers if n <= 24),  # 1-24
            'high_count': sum(1 for n in numbers if n > 24),  # 25-49
            'consecutive': self._has_consecutive(numbers),
        }

    @staticmethod
    def _has_consecutive(numbers: List[int]) -> bool:
        """Vérifie s'il y a des numéros consécutifs"""
        for i in range(len(numbers) - 1):
            if numbers[i + 1] - numbers[i] == 1:
                return True
        return False

    def display_grid(self, numbers: List[int], chance: int, with_analysis: bool = False):
        """Affiche une grille de manière formatée"""
        print("\n" + "=" * 50)
        print("GRILLE DE LOTO")
        print("=" * 50)
        print(f"Numéros: {' - '.join(str(n).zfill(2) for n in numbers)}")
        print(f"Numéro Chance: {chance}")

        if with_analysis:
            analysis = self.analyze_grid(numbers, chance)
            print("\nAnalyse de la grille:")
            print(f"  Somme des numéros: {analysis['sum']}")
            print(f"  Pairs: {analysis['even_count']} | Impairs: {analysis['odd_count']}")
            print(f"  Bas (1-24): {analysis['low_count']} | Hauts (25-49): {analysis['high_count']}")
            print(f"  Numéros consécutifs: {'Oui' if analysis['consecutive'] else 'Non'}")

        print("=" * 50)


def main_demo():
    """Démonstration du calculateur"""
    calc = LotoCalculator()
    gen = LotoGridGenerator()

    # Afficher les probabilités
    calc.display_probabilities()

    print("\n\n")
    print("=" * 70)
    print("GÉNÉRATION DE GRILLES")
    print("=" * 70)

    # Générer des grilles aléatoires
    print("\n1. Grille aléatoire:")
    numbers, chance = gen.generate_random_grid()
    gen.display_grid(numbers, chance, with_analysis=True)

    # Générer une grille équilibrée
    print("\n2. Grille équilibrée:")
    numbers, chance = gen.generate_balanced_grid()
    gen.display_grid(numbers, chance, with_analysis=True)

    # Générer avec numéros chauds
    print("\n3. Grille avec numéros 'chauds' (exemple: 7, 13, 23, 27, 41):")
    hot = [7, 13, 23, 27, 41]
    numbers, chance = gen.generate_with_hot_numbers(hot)
    gen.display_grid(numbers, chance, with_analysis=True)


if __name__ == "__main__":
    main_demo()
