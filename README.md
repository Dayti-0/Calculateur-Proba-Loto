# Calculateur de Probabilités - Loto Français

Un calculateur de probabilités complet pour le Loto français avec générateur de grilles intelligent basé sur différentes stratégies.

## À propos du Loto Français

Le Loto français fonctionne selon les règles suivantes:
- **5 numéros** à choisir entre 1 et 49
- **1 numéro chance** à choisir entre 1 et 10
- Nombre total de combinaisons possibles: **19 068 840**

## Fonctionnalités

### 1. Calcul des Probabilités
- Calcul précis des probabilités pour les 9 rangs de gain
- Affichage des chances de gagner (ex: "1 sur 19 068 840")
- Pourcentages et statistiques détaillées

### 2. Générateur de Grilles Intelligent

#### Grille Aléatoire
Génération complètement aléatoire d'une grille de Loto.

#### Grille Équilibrée
Génère une grille au hasard qui respecte toujours:
- 2 ou 3 numéros pairs (et donc 2 ou 3 impairs)
- 2 ou 3 numéros bas entre 1 et 24 (et donc 2 ou 3 hauts entre 25 et 49)
- Des numéros dans au moins 3 tranches différentes (1-10, 11-20, 21-30, 31-40, 41-49)

#### Grille avec Numéros Favoris
Intègre vos numéros favoris ou "chauds" dans la grille générée:
- Choisissez vos numéros porte-bonheur
- 2 ou 3 de vos numéros favoris seront inclus dans la grille (un seul favori fonctionne aussi)
- Complété automatiquement avec des numéros aléatoires

#### Génération Multiple
Générez plusieurs grilles d'un coup (jusqu'à 20).

### 3. Analyse de Grilles

Pour chaque grille générée ou personnalisée, obtenez:
- Somme totale des numéros
- Nombre de pairs vs impairs
- Répartition bas (1-24) vs hauts (25-49)
- Nombre de tranches couvertes (1-10, 11-20, etc.)
- Détection de numéros consécutifs

## Installation

Aucune dépendance externe requise! Le programme utilise uniquement la bibliothèque standard Python.

```bash
# Cloner le dépôt
git clone https://github.com/votre-username/Calculateur-Proba-Loto.git
cd Calculateur-Proba-Loto

# Python 3.6+ requis
python3 --version
```

## Utilisation

### Interface graphique (Recommandé)

Ouvrez simplement le fichier **`interface.html`** en double-cliquant dessus : il s'ouvre dans votre navigateur.
Rien à installer, pas de ligne de commande, et cela marche aussi sur téléphone et sans connexion Internet.

L'interface propose trois onglets :
- **Générer** : choisissez la méthode (au hasard, grille équilibrée ou avec vos numéros favoris), le nombre de grilles (1 à 20), puis touchez « Générer ». Chaque grille peut être copiée ou vérifiée.
- **Ma grille** : cochez 5 numéros et 1 numéro Chance comme sur un vrai bulletin, obtenez l'analyse de la grille, puis comparez-la à un tirage pour voir le rang obtenu.
- **Probabilités** : le tableau des 9 rangs de gain et un calculateur pour n'importe quelle combinaison.

Votre grille, vos favoris et vos réglages sont retenus par le navigateur d'une visite à l'autre.

### Interface en Ligne de Commande

Lancez l'interface interactive:

```bash
python3 loto_cli.py
```

Menu disponible:
```
1. Afficher les probabilités de gain
2. Générer une grille aléatoire
3. Générer une grille équilibrée
4. Générer plusieurs grilles aléatoires
5. Générer une grille avec numéros favoris
6. Analyser une grille personnalisée
7. Calculer la probabilité d'une combinaison
0. Quitter
```

### Utilisation Programmatique

```python
from loto_calculator import LotoCalculator, LotoGridGenerator

# Créer le calculateur
calc = LotoCalculator()

# Afficher toutes les probabilités
calc.display_probabilities()

# Calculer la probabilité d'une combinaison précise
prob = calc.probability_rank(correct_numbers=5, correct_chance=True)
print(f"Probabilité de gagner le jackpot: {prob['odds']}")  # 1 sur 19 068 840

# Probabilité d'un rang de gain (1 à 9)
print(calc.probability_of_rank(9)['odds'])  # 1 sur 10,8

# Rang obtenu avec 3 bons numéros + numéro chance
print(calc.rank_for(3, True))  # 5

# Générer des grilles
gen = LotoGridGenerator()

# Grille aléatoire
numbers, chance = gen.generate_random_grid()
print(f"Numéros: {numbers}, Chance: {chance}")

# Grille équilibrée
numbers, chance = gen.generate_balanced_grid()

# Grille avec numéros favoris
hot_numbers = [7, 13, 23, 27, 41]
numbers, chance = gen.generate_with_hot_numbers(hot_numbers)

# Analyser une grille
analysis = gen.analyze_grid(numbers, chance)
print(analysis)
```

### Démonstration

Lancez la démonstration intégrée:

```bash
python3 loto_calculator.py
```

Cela affichera:
- Toutes les probabilités de gain
- Exemples de grilles aléatoires, équilibrées et avec numéros chauds
- Analyses détaillées de chaque grille

## Probabilités de Gain

| Rang | Combinaison | Probabilité | Chances |
|------|-------------|-------------|---------|
| 1 | 5 numéros + chance | 0,00000524 % | 1 sur 19 068 840 |
| 2 | 5 numéros | 0,0000472 % | 1 sur 2 118 760 |
| 3 | 4 numéros + chance | 0,00115 % | 1 sur 86 677 |
| 4 | 4 numéros | 0,0104 % | 1 sur 9 631 |
| 5 | 3 numéros + chance | 0,0496 % | 1 sur 2 016 |
| 6 | 3 numéros | 0,446 % | 1 sur 224 |
| 7 | 2 numéros + chance | 0,695 % | 1 sur 144 |
| 8 | 2 numéros | 6,25 % | 1 sur 16 |
| 9 | 0 ou 1 numéro + chance | 9,25 % | 1 sur 10,8 |
| | **Au moins un rang** | **16,7 %** | **1 sur 6** |

## Exemples de Grilles Générées

### Grille Aléatoire
```
Numéros: 08 - 15 - 23 - 31 - 47
Numéro Chance: 7
```

### Grille Équilibrée
```
Numéros: 03 - 18 - 24 - 35 - 42
Numéro Chance: 4

Analyse:
  Somme des numéros: 122
  Pairs: 3 | Impairs: 2
  Bas (1-24): 3 | Hauts (25-49): 2
  Tranches couvertes: 5 sur 5
  Numéros consécutifs: Non
```

### Grille avec Numéros Favoris (7, 13, 23, 27, 41)
```
Numéros: 07 - 13 - 19 - 27 - 41
Numéro Chance: 9

Numéros favoris utilisés: 7, 13, 27, 41
```

## Structure du Projet

```
Calculateur-Proba-Loto/
├── interface.html        # Interface graphique (à ouvrir dans le navigateur)
├── loto_calculator.py    # Module principal (calculs et génération)
├── loto_cli.py          # Interface en ligne de commande
├── exemples.py          # Exemples d'utilisation du module
├── README.md            # Documentation
└── .gitignore          # Fichiers à ignorer
```

## Fonctionnalités Avancées

### Analyse de Grille Personnalisée

Vous pouvez analyser vos propres grilles:

```python
gen = LotoGridGenerator()
my_numbers = [5, 12, 23, 34, 45]
my_chance = 7

analysis = gen.analyze_grid(my_numbers, my_chance)
gen.display_grid(my_numbers, my_chance, with_analysis=True)
```

### Calculs Mathématiques

Le calculateur utilise la formule de combinaison:

```
C(n,k) = n! / (k! × (n-k)!)
```

Pour le Loto français:
- Combinaisons principales: C(49,5) = 1 906 884
- Avec numéro chance: 1 906 884 × 10 = 19 068 840

## Avertissement

Ce calculateur est fourni à des fins éducatives et de divertissement. Les jeux d'argent comportent des risques. Jouez de manière responsable.

**Note importante:** Les probabilités calculées sont mathématiquement exactes mais ne garantissent en aucun cas un gain. Chaque tirage est indépendant et aléatoire.

## Licence

MIT License - Libre d'utilisation et de modification

## Contribution

Les contributions sont les bienvenues! N'hésitez pas à:
- Signaler des bugs
- Proposer de nouvelles fonctionnalités
- Améliorer la documentation
- Optimiser le code

## Auteur

Créé avec Python 3 pour les passionnés de probabilités et de mathématiques.

## Ressources

- [Site officiel de la Française des Jeux](https://www.fdj.fr/)
- [Documentation Python](https://docs.python.org/3/)
- [Combinatoire et Probabilités](https://fr.wikipedia.org/wiki/Combinatoire)

---

**Bonne chance!** 🍀
