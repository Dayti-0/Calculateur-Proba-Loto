# Calculateur EuroMillions & Loto (FDJ)

[![Tests](https://github.com/dayti-0/Calculateur-Proba-Loto/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/dayti-0/Calculateur-Proba-Loto/actions/workflows/tests.yml)

Outil en ligne de commande et bibliothèque Python, **centrés sur l'EuroMillions – My Million**,
complétés par une page web autonome pour le Loto. Ils répondent avec des chiffres exacts et
vérifiés aux questions que se pose un joueur :

* Quelles sont mes chances réelles, rang par rang, avec ou sans Étoile+ ?
* Que vaut une grille multiple, et que rapporte-t-elle selon le tirage ?
* Combien récupère-t-on en moyenne pour 2,50 € misés, selon le jackpot ?
* Les tirages réels sont-ils équitables ? Quels numéros les autres joueurs choisissent-ils ?
* Comment choisir une grille qui, si elle gagne, sera partagée avec moins de monde ?

Toutes les règles proviennent des **règlements officiels de la FDJ** et les statistiques des
**1 061 tirages réels** publiés par la FDJ (27/09/2016 → 24/11/2026), livrés avec le projet et
actualisables en une commande. Aucune dépendance : Python 3.10 ou plus suffit.

> **Rappel honnête.** Chaque combinaison a exactement la même probabilité de sortir. Aucune
> méthode ne prédit un tirage ni n'augmente vos chances de gagner. Ce qui peut changer, c'est le
> nombre de personnes avec qui vous partageriez un gain : c'est le seul « avantage » que cet outil
> cherche à vous donner, et il est mesuré, pas promis.

## Ce qu'il faut retenir

| Question | Réponse (EuroMillions, règles en vigueur) |
|---|---|
| Gagner le jackpot (5 + 2) | 1 chance sur 139 838 160 |
| Gagner quelque chose | 1 chance sur 12,97 (1 sur 4,73 à l'Étoile+ seule) |
| Attente moyenne du jackpot avec 1 grille à chaque tirage | 1 340 024 ans |
| Part moyenne récupérée pour 2,50 € | de 33 % (jackpot de 17 M€) à 84 % (250 M€) |
| Jackpot qui rendrait le jeu rentable | ≈ 320 M€, au-dessus du plafond légal de 250 M€ : jamais en tirage ordinaire |
| Les tirages sont-ils équitables ? | Oui : test du khi² sur 1 061 tirages, p = 0,29 (numéros) et 0,18 (étoiles) |
| Numéros les plus joués par les Européens | 7 (+25 %), 13, 17, 23, 11, 12, 19, 9 — les numéros ≤ 31 (dates) en général |
| Numéros les moins joués | 46 (−18 %), 36, 41, 48, 47, 43, 40, 49 ; étoile 12 (−25 %) |
| Joueur typique sur 20 ans (simulation) | récupère 16 % de ses mises ; 0 joueur sur 1 000 finit gagnant |

## Installation

```bash
git clone https://github.com/dayti-0/Calculateur-Proba-Loto.git
```

```bash
cd Calculateur-Proba-Loto
```

Sans installation, depuis le dossier du projet :

```bash
python3 -m proba_loto
```

Ou installé comme commande `proba-loto` :

```bash
python3 -m pip install .
```

### Interface graphique (Loto)

Ouvrez **`interface.html`** d'un double-clic : la page s'affiche dans le navigateur, sans rien
installer, hors connexion et sur téléphone. Trois onglets :

* **Générer** : grilles au hasard, équilibrées ou avec vos numéros favoris (1 à 20 grilles) ;
* **Ma grille** : cochez 5 numéros et 1 N° Chance comme sur un bulletin, obtenez l'analyse de la
  grille et comparez-la à un tirage ;
* **Probabilités** : les 9 rangs du Loto et un calculateur pour n'importe quelle combinaison.

La grille, les favoris et les réglages sont mémorisés par le navigateur. L'EuroMillions, lui, se
pilote depuis la ligne de commande ci-dessous.

## Utilisation

Sans argument, un **menu interactif** guide pas à pas. Toutes les fonctions existent aussi en
commandes directes (`python3 -m proba_loto <commande>` ou `proba-loto <commande>`) :

| Commande | Rôle |
|---|---|
| `probas [--etoile-plus]` | Probabilités exactes et gain moyen de chaque rang |
| `generer -n 5 --strategie anti-partage` | Grilles : `aleatoire`, `equilibree`, `anti-partage`, `couverture` ; favoris avec `--numeros` / `--etoiles` |
| `verifier "3 5 37 44 49 + 5 6" [--date JJ/MM/AAAA]` | Vérifie une grille simple ou multiple contre un tirage officiel (dernier par défaut) ou saisi (`--tirage`) |
| `multiple 7 3` | Coût, probabilités et tableau des gains d'une grille multiple |
| `esperance [--jackpot 59M]` | Espérance de gain, partage du jackpot, seuil de rentabilité |
| `simuler --annees 20` | Simule 1 000 joueurs pendant des années |
| `stats` | Fréquences, écarts et test du khi² sur les tirages réels |
| `popularite` | Numéros et étoiles les plus / moins joués (estimés d'après les gains réels) |
| `retro "7 13 17 19 23 + 3 7"` | Rejoue une grille sur tout l'historique avec les vrais rapports |
| `analyser "1 2 3 4 5 + 1 2"` | Profil d'une grille et motifs très joués |
| `maj` | Télécharge l'historique officiel à jour depuis fdj.fr |

Les grilles se saisissent librement : `"3 5 37 44 49 + 5 6"`, `"3-5-37-44-49 / 5-6"`,
`"3,5,37,44,49 étoiles 5,6"`. Pour le Loto, ajoutez `--jeu loto` (ex. `--jeu loto probas`) ;
le Loto dispose des probabilités, de la génération, de la vérification, des multiples et de
l'analyse.

### Probabilités

```text
$ proba-loto probas
EuroMillions : probabilités exactes pour une grille simple (2,50 €)
139 838 160 combinaisons possibles : 5 numéros parmi 50 et 2 étoiles parmi 12

  Rang  Combinaison                      Chances    Probabilité  Gain moyen*
  ----  ---------------------  -----------------  -------------  -----------
     1  5 numéros + 2 étoiles  1 sur 139 838 160  0,000000715 %      jackpot
     2  5 numéros + 1 étoile     1 sur 6 991 908    0,0000143 %    200 738 €
     3  5 numéros + 0 étoile     1 sur 3 107 515    0,0000322 %     20 851 €
     4  4 numéros + 2 étoiles      1 sur 621 503     0,000161 %      1 299 €
     5  4 numéros + 1 étoile        1 sur 31 075      0,00322 %        120 €
     6  3 numéros + 2 étoiles       1 sur 14 125      0,00708 %      57,49 €
     7  4 numéros + 0 étoile        1 sur 13 811      0,00724 %      39,50 €
     8  2 numéros + 2 étoiles        1 sur 985,5        0,101 %      14,09 €
     9  3 numéros + 1 étoile         1 sur 706,3        0,142 %      11,26 €
    10  3 numéros + 0 étoile         1 sur 313,9        0,319 %       9,32 €
    11  1 numéro + 2 étoiles         1 sur 187,7        0,533 %       6,75 €
    12  2 numéros + 1 étoile          1 sur 49,3         2,03 %       5,58 €
    13  2 numéros + 0 étoile          1 sur 21,9         4,57 %       4,00 €
  Tous rangs : 1 sur 12,97 (7,71 %)
```

\* Le gain moyen découle de la répartition du règlement (2,20 € × 50 % × part du rang ÷
probabilité) ; il est confirmé par les rapports réels de 2020-2026 (ex. rang 13 : 4,00 € théoriques,
3,98 € observés en moyenne). Ajoutez `--etoile-plus` pour la table des 10 rangs Étoile+.

### Générer des grilles peu jouées

```text
$ proba-loto generer -n 5 --strategie anti-partage --graine 7
5 grilles EuroMillions – stratégie anti-partage
  1.  20 30 36 48 49  ★  01 11   indice de popularité 0,48
  2.  01 16 37 46 50  ★  10 11   indice de popularité 0,47
  3.  33 41 43 47 48  ★  03 12   indice de popularité 0,43
  4.  35 37 42 45 48  ★  02 12   indice de popularité 0,42
  5.  30 39 42 46 48  ★  02 04   indice de popularité 0,59
```

L'**indice de popularité** estime combien d'autres joueurs ont choisi la même grille,
relativement à une combinaison moyenne (1,00). La stratégie anti-partage tire les numéros avec une
pondération favorable aux moins joués, écarte les motifs populaires (suites, dates, même finale,
progressions, dernier tirage…) et divise en moyenne par deux le nombre attendu de co-gagnants,
tout en gardant les 50 numéros en circulation. Sans `--graine`, le tirage utilise le générateur
cryptographique du système.

Autres stratégies : `aleatoire` (uniforme), `equilibree` (profil le plus fréquent des tirages :
somme centrale, 2-3 pairs…, sans effet sur les chances) et `couverture` (10 grilles couvrent les
50 numéros, 6 grilles les 12 étoiles).

### Vérifier une grille

```text
$ proba-loto verifier "3 5 12 44 50 + 5 9" --etoile-plus
Tirage du mardi 24/11/2026 : 03 05 37 44 49  ★  05 06
Votre grille : 03 05 12 44 50  ★  05 09
  Bons numéros : 03 05 44 (3)  |  étoiles : 05 (1)
  EuroMillions rang 9 (3 numéros + 1 étoile) : 12,20 € (rapport officiel)
  Étoile+ rang 6 (3 numéros + 1 étoile) : 2,90 € (rapport officiel)
  Total : 15,10 € pour 3,50 € misés.
```

Les grilles multiples sont décomposées automatiquement, et les montants proviennent des rapports
officiels du tirage choisi (`--date`).

### Grilles multiples

`proba-loto multiple 6 3` : 18 grilles simples pour 45 € (63 € avec Étoile+), 1 chance sur 8,3 de
gagner au moins un rang, et le tableau complet des gains selon le tirage, par exemple :

```text
    Trouvés dans votre multiple          Chances  Grilles gagnantes
    5 numéros + 2 étoiles        1 sur 7 768 787  1 × rang 1, 2 × rang 2, 5 × rang 4, 10 × rang 5
    4 numéros + 2 étoiles           1 sur 70 625  2 × rang 4, 4 × rang 5, 4 × rang 6, 8 × rang 9
```

Seules les combinaisons acceptées par la FDJ sont admises (5 à 10 numéros, 2 à 12 étoiles, au plus
396 grilles simples ; Loto : 5 à 9 numéros, au plus 168 grilles).

### Espérance de gain

```text
$ proba-loto esperance
Espérance de gain d'une grille EuroMillions – My Million selon le jackpot (tirage ordinaire)
  Jackpot  Grilles jouées  Récupéré  Retour  Perte/grille  Risque de partage
  -------  --------------  --------  ------  ------------  -----------------
    17 M€          16,5 M    0,84 €  33,4 %        1,66 €             11,1 %
    50 M€          23,8 M    0,96 €  38,5 %        1,54 €             15,7 %
   100 M€          30,2 M    1,24 €  49,5 %        1,26 €             19,4 %
   150 M€          34,7 M    1,52 €  60,9 %        0,98 €             22,0 %
   200 M€          38,3 M    1,81 €  72,5 %        0,69 €             24,0 %
   250 M€          41,3 M    2,10 €  84,0 %        0,40 €             25,6 %
  Mise : 2,50 € par grille.
  Seuil de rentabilité théorique : jackpot de 320 M€, supérieur au plafond réglementaire de 250 M€ :
    un tirage ordinaire n'est jamais rentable.
```

Avec `--jackpot 59M`, le détail est donné poste par poste (rangs 2 à 13, jackpot, My Million,
Étoile+). Les options `--ventes`, `--codes-my-million` et `--grille` (popularité de votre grille)
affinent le calcul. `--situation plafond` ou `doit-etre-gagne` traitent les tirages au plafond, où
l'excédent est reversé au rang 2 : ce sont les seuls cas où l'espérance approche ou dépasse la mise.

### Statistiques, popularité, rétro-test, simulation

* `stats` : fréquences, numéros absents depuis longtemps, test du khi² (corrigé pour le tirage sans
  remise) et derniers tirages. Conclusion sur 1 061 tirages : aucun écart avec le hasard.
* `popularite` : 7 (+25 %), 13 (+19 %), 17 (+17 %), 23 (+15 %) sont les plus joués ; 46 (−18 %),
  36 (−17 %), 41 (−16 %) les moins joués ; l'étoile 7 est sur-jouée (+17 %), la 12 boudée (−25 %).
* `retro "7 13 17 19 23 + 3 7"` : jouée à chaque tirage depuis 2016, cette grille aurait coûté
  2 652,50 € et rapporté 440,50 € (16,6 %).
* `simuler --annees 20` : sur 1 000 joueurs simulés pendant 20 ans, mise de 5 217,50 € chacun,
  médiane récupérée 839 € (16,1 %), aucun joueur gagnant.

## Utilisation en Python

```python
>>> from proba_loto import EUROMILLIONS, Grille, verifier, analyser_multiple, calculer_esperance
>>> from proba_loto import affichage as fmt
>>> from proba_loto.probabilites import probabilite_gain
>>> fmt.chances(probabilite_gain(EUROMILLIONS), decimales=2)
'1 sur 12,97'
>>> grille = Grille.depuis_texte(EUROMILLIONS, "3 5 12 44 50 + 5 9")
>>> tirage = Grille.depuis_texte(EUROMILLIONS, "3 5 37 44 49 + 5 6")
>>> verifier(grille, tirage).gains  # rang → nombre de grilles gagnantes
{9: 1}
>>> analyser_multiple(EUROMILLIONS, 7, 3).nb_simples
63
>>> e = calculer_esperance(59e6, ventes=25e6, codes_my_million=5e6)
>>> fmt.euros(e.total), fmt.pourcentage(e.taux_retour)
('1,03 €', '41,1 %')

```

Le script [`exemples.py`](exemples.py) montre l'historique, la popularité et le rétro-test.

## Méthodes et sources

**Règles.** Elles sont décrites comme des données dans [`proba_loto/jeux.py`](proba_loto/jeux.py),
d'après le règlement EuroMillions – My Million et Étoile+ homologué par l'ANJ le 27 mars 2025
(décision 2025-PR-054) et le règlement du Loto homologué le 19 février 2026 (décision 2026-PR-023) :
mise de 2,50 € (2,20 € EuroMillions + 0,30 € My Million), 50 % des mises EuroMillions aux gagnants
(1,10 € par grille), part de chaque rang, jackpot minimum de 17 M€, plafond de 250 M€, Étoile+ à 1 €
(60 % redistribués), tableaux des multiples.

**Probabilités.** Calcul exact en fractions : le nombre de grilles ayant `a` bons numéros et `b`
bonnes étoiles vaut C(5, a)·C(45, 5−a)·C(2, b)·C(10, 2−b). Toutes les valeurs sont comparées aux
tableaux des règlements dans les tests.

**Espérance.** Les rangs 2 à 13 rapportent en moyenne 1,10 € × 40 % = 0,44 € par grille (ces sommes
sont toujours distribuées). Le jackpot est partagé : avec S grilles jouées, la part moyenne d'un
gagnant vaut (1 − e^−λ)/λ où λ = S / 139 838 160. My Million : 1 M€ ÷ nombre de codes français.
Quand vous ne les fournissez pas, les ventes sont estimées d'après le jackpot par une régression
sur les tirages 2020-2026 (17 M€ → 16 M de grilles, 250 M€ → 41 M), et la part française à 21,6 %.

**Popularité.** Un gain partagé entre beaucoup de gagnants révèle des numéros très joués : le
rapport du rang 13 (≈ 700 000 gagnants par tirage) mesure la popularité des numéros tirés,
indépendamment des ventes. Une régression ridge (Python pur) sur les 1 061 tirages, avec un niveau
par année, estime l'effet de chaque numéro (rang 13) et de chaque étoile (rang 11). Validation : le
modèle estimé sur les 75 % de tirages les plus anciens prédit les rapports des 25 % plus récents
avec une corrélation de 0,97.

**Statistiques.** Le khi² d'uniformité est multiplié par (N − 1)/(N − k) car les k numéros d'un
tirage sont distincts ; sans cette correction, le test serait trop indulgent.

**Données.** [`proba_loto/data/euromillions.csv`](proba_loto/data/euromillions.csv) est généré par
`maj` à partir des archives officielles FDJ ; voir [`SOURCE.md`](proba_loto/data/SOURCE.md). La
commande `maj` enregistre l'historique à jour dans le cache utilisateur (`~/.cache/proba-loto/`),
utilisé automatiquement s'il est plus récent.

## Règles en vigueur et évolutions annoncées

Les calculs suivent les règles en vigueur au 26 novembre 2026. Une réforme de l'EuroMillions,
d'abord prévue le 30 septembre 2026, a été reportée au **tirage du 2 mars 2027** : plafond du
jackpot porté de 250 M€ à 260 M€, puis par paliers jusqu'à 300 M€, grille annoncée à 3 € et jeux
additionnels refondus (l'Étoile+ pourrait être remplacée). Le détail officiel n'étant pas encore
publié, il n'est pas intégré : il suffira alors d'ajouter la nouvelle définition dans `jeux.py`.

## Développement

```bash
python3 -m pip install -e ".[dev]"
```

```bash
python3 -m pytest
```

```bash
python3 -m mypy
```

La suite (plus de 140 tests) vérifie chaque probabilité contre les règlements, les multiples
contre le tableau officiel et par énumération, la répartition théorique contre les rapports réels,
les générateurs (validité, uniformité, reproductibilité), l'espérance, l'historique, la CLI et le
menu. Elle tourne sous Python 3.10 à 3.14 via GitHub Actions. L'[audit](AUDIT.md) détaille les
corrections apportées à la première version.

```text
interface.html        page web autonome pour le Loto
exemples.py           exemples d'utilisation de la bibliothèque
proba_loto/
├── jeux.py           règles officielles (EuroMillions, Étoile+, Loto)
├── probabilites.py   probabilités exactes
├── grilles.py        saisie, validation, vérification
├── multiples.py      grilles multiples
├── generateur.py     stratégies de génération
├── analyse.py        profil et motifs d'une grille
├── esperance.py      espérance de gain
├── simulation.py     Monte-Carlo
├── historique.py     historique officiel FDJ (lecture, mise à jour)
├── statistiques.py   fréquences, khi², rétro-test
├── popularite.py     popularité des numéros
├── cli.py            ligne de commande et menu
└── data/             historique officiel livré
```

## Jouer de façon responsable

Les jeux d'argent sont interdits aux mineurs. Jouer comporte des risques : endettement,
isolement, dépendance. Pour être aidé : **Joueurs Info Service, 09 74 75 13 13** (appel non
surtaxé), [joueurs-info-service.fr](https://www.joueurs-info-service.fr).

Projet indépendant, sans lien avec la Française des Jeux. Les montants officiels font foi sur
[fdj.fr](https://www.fdj.fr).

## Licence

[MIT](LICENSE).
