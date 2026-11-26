# Audit et refonte du projet — novembre 2026

## Résumé

La version initiale (un commit, trois scripts Python, Loto uniquement) contenait des **erreurs
de probabilités dans la documentation**, des **règles du Loto incomplètes**, plusieurs **bugs**
(plantages, grilles invalides, rangs mal calculés) et un discours laissant entendre que certaines
stratégies amélioraient les chances. Elle ne gérait pas l'EuroMillions.

Le projet a été réécrit en un package Python sans dépendance, **centré sur l'EuroMillions –
My Million et l'Étoile+**, dont toutes les règles proviennent des règlements officiels de la FDJ
et toutes les statistiques des 1 061 tirages réels publiés par la FDJ. Chaque chiffre affiché est
vérifié par une suite de 149 tests (Python 3.10 à 3.14, typage `mypy --strict`).

## Méthode

1. Lecture et exécution du code d'origine, reproduction de chaque défaut.
2. Récupération des sources primaires : règlement EuroMillions – My Million et Étoile+ (homologué
   par l'ANJ le 27 mars 2025), règlement du Loto (homologué le 19 février 2026), archives
   officielles des tirages FDJ.
3. Vérification de l'état des règles au 26 novembre 2026 (la réforme annoncée pour le 30 septembre
   2026 a été reportée au 2 mars 2027).
4. Réécriture, puis validation croisée : règlements, énumération exhaustive, données réelles.

## Constats sur la version initiale

| # | Gravité | Constat | Correction |
|---|---|---|---|
| 1 | Critique | **Tableau du README faux** pour les rangs 3 à 7 du Loto, et en contradiction avec le code : « 1 sur 218 901 » au lieu de 1 sur 86 677 (rang 3), 24 322 au lieu de 9 631, 4 378 au lieu de 2 016, 486 au lieu de 224, 703 au lieu de 144 (rang 7). | Probabilités exactes en fractions, testées contre le tableau du règlement. |
| 2 | Majeure | **Rangs 8 et 9 du Loto absents** (réforme de 2019) : le rang 9 (N° Chance, remboursement de 2,20 €) est pourtant le gain le plus fréquent ; la probabilité globale (1 sur 5,99) n'était pas donnée. | Les 9 rangs officiels, y compris le rang 9 à double condition. |
| 3 | Majeure | **Cotes tronquées au lieu d'arrondies** (`int(1/p)`) : « 1 sur 86 676 », « 9 630 », « 2 015 », « 223 », « 143 » au lieu de 86 677, 9 631, 2 016, 224, 144. Séparateurs de milliers à l'anglaise (« 19,068,840 »). | Arrondi correct, format français (« 19 068 840 », « 21,9 »). |
| 4 | Majeure | **`exemples.py` annonçait de faux rangs** pour toutes les combinaisons gagnantes : 5 numéros + Chance affiché « Rang 7 », 5 numéros « Rang 3 », 3 numéros « Rang 7 »… ; 2 numéros (rang 8) jamais reconnu. | Détermination du rang par la table officielle, testée pour chaque couple (numéros, complémentaires). |
| 5 | Majeure | **Plantage avec un seul numéro favori** (`random.randint(2, 1)`), que la CLI présentait comme « Format invalide ». | Favoris validés ; 1 à N favoris acceptés, sous-ensemble tiré s'il y en a trop. |
| 6 | Majeure | **Favoris en double → grilles invalides** : avec `[7, 7, 7]`, 2 000 grilles sur 2 000 contenaient un doublon. | Erreur explicite sur doublon ou valeur hors bornes. |
| 7 | Majeure | **Discours trompeur** : générateur « intelligent », grille « optimisée », numéros « chauds » ; la grille « équilibrée » promettait un équilibre pair/impair non implémenté. | Chaque stratégie est décrite pour ce qu'elle fait ; rappel systématique que les chances ne changent pas ; seule la stratégie anti-partage agit, sur le partage, de façon mesurée. |
| 8 | Fonctionnelle | **Pas d'EuroMillions**, ni d'Étoile+, de grilles multiples, d'espérance de gain ou de données réelles. | Voir « Ce qui a été construit ». |
| 9 | Mineure | `probability_rank` sans contrôle : 6 bons numéros → `ValueError: factorial() not defined for negative values`. | Contrôle des bornes avec message clair. |
| 10 | Mineure | CLI : fermeture de l'entrée standard → trace `EOFError` ; `except Exception` générique masquant les erreurs. | Menu robuste (fin de saisie, Ctrl-C), erreurs utilisateur affichées proprement, code de sortie 2. |
| 11 | Mineure | Générateur `random` sans graine possible ni générateur cryptographique. | `SystemRandom` par défaut, graine optionnelle pour la reproductibilité. |
| 12 | Mineure | `exemples.py` bloquant (`input()` entre chaque exemple), objets inutilisés dans la CLI, réimplémentation de `math.comb` par factorielles. | Exemples non interactifs, code simplifié. |
| 13 | Qualité | Aucun test, pas de packaging, pas d'intégration continue, licence « MIT » annoncée sans fichier `LICENSE`, URL de clonage factice, structure du README incomplète. | 149 tests, `pyproject.toml` (commande `proba-loto`), GitHub Actions, `LICENSE`, documentation réécrite. |

Les anciens scripts `loto_calculator.py` et `loto_cli.py` sont remplacés par le package
`proba_loto` (`python3 -m proba_loto`) ; `exemples.py` a été réécrit.

## Ce qui a été construit (EuroMillions en priorité)

* **Règles officielles décrites comme des données** (`jeux.py`) : EuroMillions (13 rangs, parts
  de chaque rang, 2,20 € + 0,30 € My Million, 1,10 € par grille aux gagnants, jackpot minimum
  17 M€, plafond 250 M€), Étoile+ (10 rangs, 1 €, 60 % redistribués), Loto (9 rangs).
* **Probabilités exactes** de chaque rang, avec gain moyen théorique et durées d'attente.
* **Grilles multiples** : tableau officiel des combinaisons autorisées et des prix, probabilités
  exactes, tableau des gains selon le tirage, vérification par décomposition.
* **Vérification** d'une grille simple ou multiple contre n'importe quel tirage officiel, avec les
  rapports réels (EuroMillions et Étoile+).
* **Espérance de gain** : rangs 2 à 13, partage du jackpot (loi de Poisson), My Million, Étoile+,
  situations de plafond et de jackpot « forcément distribué », seuil de rentabilité.
* **Historique officiel** des 1 061 tirages (27/09/2016 → 24/11/2026) livré, lecture des formats
  FDJ (ZIP, CSV UTF-8 ou ISO-8859-1), mise à jour par `maj`.
* **Statistiques** : fréquences, écarts, test du khi² corrigé pour le tirage sans remise.
* **Popularité des numéros** estimée à partir des rapports réels (régression ridge en Python pur),
  validée hors échantillon, et **stratégie anti-partage** qui s'en sert.
* **Rétro-test** d'une grille sur tout l'historique et **simulation** de Monte-Carlo.
* **CLI complète et menu interactif**, sorties en français, messages d'erreur clairs.

## Vérifications effectuées

| Vérification | Résultat |
|---|---|
| 13 rangs EuroMillions, 10 rangs Étoile+, 9 rangs Loto | identiques aux tableaux des règlements (au dixième ou à l'unité près, selon la précision publiée) |
| 33 configurations multiples EuroMillions et 32 Loto, avec leurs prix | identiques aux tableaux officiels |
| Formule des probabilités | confirmée par énumération exhaustive d'un jeu réduit ; somme des issues = 1 exactement |
| Gains des multiples | identiques à la décomposition en grilles simples (40 multiples aléatoires, EuroMillions et Étoile+) |
| Gains moyens théoriques des rangs 5 à 13 | à moins de 10 % des moyennes réelles de 711 tirages (2020-2026) ; rang 13 : 4,00 € contre 3,98 € |
| Données livrées | strictement identiques aux archives FDJ brutes ; aucun tirage manquant (écarts de 3 ou 4 jours) |
| Équité des tirages réels | khi² corrigé : p = 0,29 (numéros), p = 0,18 (étoiles) |
| Modèle de popularité | corrélation de 0,97 sur les tirages récents non utilisés pour l'estimation ; coefficients stables entre les deux moitiés de l'historique (corrélation > 0,97) |
| Générateur aléatoire | uniformité vérifiée sur 20 000 grilles ; indice de popularité moyen = 1,00 sur grilles aléatoires |
| Python 3.10, 3.11, 3.12, 3.13, 3.14 et `mypy --strict` | tous les tests passent, aucune erreur de typage |

## Anomalies relevées dans les sources officielles

* **Règlement EuroMillions** : la cote du rang 5 (4 + 1) est publiée à 31 075,2 alors que la valeur
  exacte est 31 075,15. Pour l'Étoile+, le règlement annonce « environ une chance sur 4,8 » de
  gagner, mais ses propres rangs totalisent 29 594 459 combinaisons gagnantes sur 139 838 160,
  soit **1 sur 4,73**.
* **Archives des tirages FDJ** : le 31/01/2020, les nombres de gagnants « en Europe » sont tous à 0
  alors que les rapports sont publiés ; les 30/09/2022 et 04/08/2023, un rapport Étoile+ de rang 1
  est publié sans gagnant. Ces lignes sont conservées telles quelles et traitées sans erreur
  (le rétro-test utilise alors le rapport publié).

## Limites et points d'attention

* **Réforme annoncée pour le 2 mars 2027** : plafond porté à 260 M€ puis jusqu'à 300 M€ par
  paliers, grille annoncée à 3 €, jeux additionnels refondus (l'Étoile+ pourrait disparaître). Le
  règlement correspondant n'étant pas publié, rien n'est intégré par anticipation ; la description
  des règles par des données permettra d'ajouter la nouvelle version simplement.
* **Espérance** : quand ils ne sont pas fournis, le nombre de grilles jouées et la part française
  sont estimés à partir des tirages passés ; les arrondis réglementaires des gains (au dixième
  d'euro inférieur) ne sont pas modélisés (effet de l'ordre de 1 %).
* **Popularité** : modèle au premier ordre, qui suppose des choix de numéros et d'étoiles
  indépendants. Les motifs très joués (suites, dates, dernier tirage…) sont donc écartés
  séparément par le générateur. Si beaucoup de joueurs adoptaient la stratégie anti-partage, les
  numéros qu'elle privilégie deviendraient populaires : la pondération est volontairement modérée.
* **Loto** : probabilités, génération, vérification, multiples et analyse sont disponibles, mais
  pas l'espérance ni les statistiques (l'historique du Loto n'est pas intégré).

## Pistes

* Intégrer l'historique officiel du Loto (publié par la FDJ au même format) pour étendre
  statistiques, popularité et rétro-test.
* Mettre à jour `jeux.py` dès la publication du règlement de la réforme EuroMillions de 2027.
* Proposer une interface web statique reprenant les calculs pour les non-utilisateurs de Python.
