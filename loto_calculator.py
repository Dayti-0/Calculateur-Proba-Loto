"""
Calculateur de probabilités pour le Loto Français
Le Loto français: 5 numéros entre 1 et 49 + 1 numéro chance entre 1 et 10
"""
import math
from typing import List, Tuple, Dict, Optional
import random


def format_number(n: int) -> str:
    """Formate un entier à la française: 19068840 -> '19 068 840'"""
    return f"{n:,}".replace(",", " ")


def format_odds(probability: float) -> str:
    """Formate une probabilité en '1 sur X' (arrondi au plus proche)"""
    if probability <= 0:
        return "Impossible"
    x = 1 / probability
    if x >= 100:
        return f"1 sur {format_number(round(x))}"
    text = f"{x:.1f}"
    if text.endswith(".0"):
        text = text[:-2]
    return f"1 sur {text.replace('.', ',')}"


class LotoCalculator:
    """Classe pour calculer les probabilités du Loto français"""

    # Constantes du Loto français
    TOTAL_NUMBERS = 49
    NUMBERS_TO_PICK = 5
    TOTAL_CHANCE = 10

    # Les 9 rangs de gain: (rang, description, [(bons numéros, numéro chance trouvé), ...])
    WINNING_RANKS = [
        (1, "5 numéros + numéro chance", [(5, True)]),
        (2, "5 numéros", [(5, False)]),
        (3, "4 numéros + numéro chance", [(4, True)]),
        (4, "4 numéros", [(4, False)]),
        (5, "3 numéros + numéro chance", [(3, True)]),
        (6, "3 numéros", [(3, False)]),
        (7, "2 numéros + numéro chance", [(2, True)]),
        (8, "2 numéros", [(2, False)]),
        (9, "0 ou 1 numéro + numéro chance", [(1, True), (0, True)]),
    ]

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

    def favorable_outcomes(self, correct_numbers: int, correct_chance: bool) -> int:
        """
        Nombre de combinaisons donnant exactement `correct_numbers` bons numéros,
        avec ou sans le bon numéro chance.
        """
        ways_to_get_correct = self.combination(self.NUMBERS_TO_PICK, correct_numbers)
        ways_to_get_wrong = self.combination(
            self.TOTAL_NUMBERS - self.NUMBERS_TO_PICK,
            self.NUMBERS_TO_PICK - correct_numbers
        )
        chance_ways = 1 if correct_chance else self.TOTAL_CHANCE - 1
        return ways_to_get_correct * ways_to_get_wrong * chance_ways

    @staticmethod
    def rank_for(correct_numbers: int, correct_chance: bool) -> Optional[int]:
        """
        Retourne le rang de gain (1 à 9) correspondant à un résultat,
        ou None si le résultat ne rapporte rien.
        """
        if correct_numbers >= 2:
            return (5 - correct_numbers) * 2 + (1 if correct_chance else 2)
        return 9 if correct_chance else None

    def probability_rank(self, correct_numbers: int, correct_chance: bool) -> Dict:
        """
        Calcule la probabilité d'avoir exactement `correct_numbers` bons numéros

        Args:
            correct_numbers: Nombre de numéros corrects (0-5)
            correct_chance: Si le numéro chance est correct

        Returns:
            Dict avec probabilité, ratio et rang de gain correspondant
        """
        if not 0 <= correct_numbers <= self.NUMBERS_TO_PICK:
            raise ValueError("Le nombre de bons numéros doit être entre 0 et 5")

        favorable = self.favorable_outcomes(correct_numbers, correct_chance)
        probability = favorable / self.total_combinations

        return {
            'correct_numbers': correct_numbers,
            'correct_chance': correct_chance,
            'rank': self.rank_for(correct_numbers, correct_chance),
            'favorable_outcomes': favorable,
            'total_combinations': self.total_combinations,
            'probability': probability,
            'odds': format_odds(probability),
        }

    def probability_of_rank(self, rank: int) -> Dict:
        """Calcule la probabilité d'obtenir un rang de gain donné (1 à 9)"""
        for number, description, combos in self.WINNING_RANKS:
            if number == rank:
                favorable = sum(self.favorable_outcomes(k, c) for k, c in combos)
                probability = favorable / self.total_combinations
                return {
                    'rank': number,
                    'rank_description': f"Rang {number}: {description}",
                    'favorable_outcomes': favorable,
                    'total_combinations': self.total_combinations,
                    'probability': probability,
                    'odds': format_odds(probability),
                }
        raise ValueError("Le rang doit être entre 1 et 9")

    def get_all_winning_probabilities(self) -> List[Dict]:
        """Retourne les probabilités pour les 9 rangs de gain du Loto"""
        return [self.probability_of_rank(rank) for rank, _, _ in self.WINNING_RANKS]

    def probability_any_win(self) -> Dict:
        """Probabilité de gagner au moins un rang (n'importe lequel)"""
        favorable = sum(r['favorable_outcomes'] for r in self.get_all_winning_probabilities())
        probability = favorable / self.total_combinations
        return {
            'favorable_outcomes': favorable,
            'total_combinations': self.total_combinations,
            'probability': probability,
            'odds': format_odds(probability),
        }

    def display_probabilities(self):
        """Affiche toutes les probabilités de gain"""
        print("=" * 70)
        print("PROBABILITÉS DE GAIN AU LOTO FRANÇAIS")
        print("=" * 70)
        print(f"\nNombre total de combinaisons possibles: {format_number(self.total_combinations)}")
        print("\nRangs de gain:")
        print("-" * 70)

        for rank in self.get_all_winning_probabilities():
            print(f"\n{rank['rank_description']}")
            print(f"  Probabilité: {rank['probability']:.10f} ({rank['probability']*100:.8f}%)")
            print(f"  Chances: {rank['odds']}")

        any_win = self.probability_any_win()
        print("\n" + "-" * 70)
        print(f"Gagner au moins un rang: {any_win['odds']} ({any_win['probability']*100:.2f}%)")


class LotoGridGenerator:
    """Génère des grilles de Loto selon différentes stratégies"""

    # Tranches utilisées pour la grille équilibrée et l'analyse
    RANGES = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 49)]

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

    def is_balanced(self, numbers: List[int]) -> bool:
        """
        Une grille est équilibrée si elle a:
        - 2 ou 3 numéros pairs (donc 2 ou 3 impairs)
        - 2 ou 3 numéros bas (1-24) (donc 2 ou 3 hauts)
        - des numéros dans au moins 3 tranches différentes (1-10, 11-20, etc.)
        """
        analysis = self.analyze_grid(numbers, 1)
        return (
            2 <= analysis['even_count'] <= 3
            and 2 <= analysis['low_count'] <= 3
            and analysis['ranges_covered'] >= 3
        )

    def generate_balanced_grid(self) -> Tuple[List[int], int]:
        """
        Génère une grille équilibrée (voir is_balanced):
        - Mélange de nombres pairs et impairs
        - Mélange de numéros bas et hauts
        - Répartition sur au moins 3 tranches (1-10, 11-20, etc.)
        """
        # Environ 4 grilles sur 10 tirées au hasard sont équilibrées:
        # on tire jusqu'à en obtenir une.
        while True:
            numbers, chance = self.generate_random_grid()
            if self.is_balanced(numbers):
                return numbers, chance

    def generate_with_hot_numbers(self, hot_numbers: List[int]) -> Tuple[List[int], int]:
        """
        Génère une grille en favorisant certains numéros "chauds"

        La grille reprend 2 ou 3 des numéros chauds (ou le seul numéro donné),
        complétés par des numéros aléatoires.

        Args:
            hot_numbers: Liste de numéros considérés comme "chauds" (1 à 49, sans doublon)
        """
        if not hot_numbers:
            raise ValueError("Il faut au moins un numéro favori")
        if any(n < 1 or n > 49 for n in hot_numbers):
            raise ValueError("Les numéros favoris doivent être entre 1 et 49")
        if len(set(hot_numbers)) != len(hot_numbers):
            raise ValueError("Les numéros favoris ne doivent pas contenir de doublon")

        # Prendre 2-3 numéros "chauds" (ou moins s'il y en a moins)
        num_hot = random.randint(min(2, len(hot_numbers)), min(3, len(hot_numbers)))
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
            'ranges_covered': sum(1 for low, high in self.RANGES
                                  if any(low <= n <= high for n in numbers)),
            'consecutive': self._has_consecutive(numbers),
        }

    @staticmethod
    def _has_consecutive(numbers: List[int]) -> bool:
        """Vérifie s'il y a des numéros consécutifs"""
        numbers = sorted(numbers)
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
            print(f"  Tranches couvertes: {analysis['ranges_covered']} sur 5")
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
