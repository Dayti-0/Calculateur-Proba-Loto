# Données : historique officiel EuroMillions

`euromillions.csv` contient les résultats officiels de tous les tirages
EuroMillions de la formule actuelle (5 numéros sur 50, 2 étoiles sur 12), du
27/09/2016 au dernier tirage disponible lors de la génération du fichier.

* **Source** : archives publiées par la Française des Jeux sur
  <https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/historique>
  (fichiers `euromillions_4`, `euromillions_201902` et `euromillions_202002`).
* **Génération** : `python -m proba_loto maj --sortie proba_loto/data/euromillions.csv`
  (téléchargement, contrôle de chaque ligne, fusion, tri chronologique).
* **Colonnes** : date ; numéros `n1`…`n5` et étoiles `e1`, `e2` triés ;
  nombre de gagnants par rang en Europe et en France ; rapport (gain unitaire
  en euros, 0 si aucun gagnant) des 13 rangs ; gagnants et rapports des 10 rangs
  Étoile+ ; code My Million.

Particularités constatées dans les fichiers officiels (conservées telles quelles) :

* 31/01/2020 : les effectifs de gagnants « en Europe » sont tous à 0 alors que
  les rapports sont publiés ;
* 30/09/2022 et 04/08/2023 : un rapport Étoile+ de rang 1 est publié sans gagnant.
