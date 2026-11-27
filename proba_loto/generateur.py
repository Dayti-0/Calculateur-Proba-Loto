"""Génération de grilles.

Stratégies disponibles :

* ``aleatoire`` : tirage uniforme (générateur cryptographique du système, ou
  pseudo-aléatoire reproductible si une graine est fournie) ;
* ``equilibree`` : grille au profil « typique » (voir :func:`profil_equilibre`) ;
* ``anti-partage`` : privilégie les numéros et étoiles peu joués et écarte les
  motifs populaires, pour réduire le nombre de co-gagnants en cas de gain ;
* ``couverture`` : plusieurs grilles qui utilisent un maximum de numéros et
  d'étoiles différents (10 grilles EuroMillions couvrent les 50 numéros).

Aucune stratégie ne modifie la probabilité de gagner : chaque combinaison a
exactement une chance sur 139 838 160 de sortir. Seule la stratégie
anti-partage agit, sur le montant moyen d'un gain éventuel.
"""

from __future__ import annotations

import random
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .analyse import motifs_populaires, profil_equilibre
from .grilles import ErreurGrille, Grille
from .jeux import Jeu

__all__ = ["STRATEGIES", "Generateur"]

STRATEGIES = ("aleatoire", "equilibree", "anti-partage", "couverture")

_ESSAIS_MAX = 20_000
# Réglage anti-partage : poids = popularité^-4, puis meilleure de 5 grilles
# acceptables. Indice médian ≈ 0,47 (deux fois moins de co-gagnants attendus)
# tout en conservant les 50 numéros et les 12 étoiles en circulation : pousser
# davantage concentrerait les grilles sur quelques numéros, qui finiraient par
# devenir populaires à leur tour.
_EXPOSANT_ANTI_PARTAGE = 4.0
_CANDIDATS_ANTI_PARTAGE = 5


def _verifier_favoris(valeurs: Iterable[int], maximum: int, nom: str) -> Tuple[int, ...]:
    favoris = tuple(int(v) for v in valeurs)
    hors_bornes = [v for v in favoris if not 1 <= v <= maximum]
    if hors_bornes:
        raise ErreurGrille(f"{nom} favoris hors bornes (1 à {maximum}) : {', '.join(map(str, hors_bornes))}")
    if len(set(favoris)) != len(favoris):
        doublons = sorted({v for v in favoris if favoris.count(v) > 1})
        raise ErreurGrille(f"{nom} favoris en double : {', '.join(map(str, doublons))}")
    return favoris


class Generateur:
    """Générateur de grilles pour un jeu donné.

    ``graine`` rend les tirages reproductibles (utile pour les tests ou pour
    rejouer une sélection) ; sans graine, le générateur cryptographique du
    système d'exploitation est utilisé.

    ``modele`` est un ``ModelePopularite`` (EuroMillions) utilisé par la
    stratégie anti-partage ; ``dernier_tirage`` permet d'écarter les grilles
    trop proches du dernier résultat, souvent rejoué.
    """

    def __init__(
        self,
        jeu: Jeu,
        graine: Optional[int] = None,
        modele: Optional[object] = None,
        dernier_tirage: Optional[Grille] = None,
    ) -> None:
        self.jeu = jeu
        self.rng: random.Random = random.Random(graine) if graine is not None else random.SystemRandom()
        self.modele = modele
        self.dernier_tirage = dernier_tirage

    # ------------------------------------------------------------ utilitaires
    def _completer(
        self,
        fixes: Sequence[int],
        maximum: int,
        taille: int,
        poids: Optional[Dict[int, float]] = None,
    ) -> Tuple[int, ...]:
        """Complète ``fixes`` jusqu'à ``taille`` valeurs distinctes parmi 1..maximum."""
        if len(fixes) > taille:
            fixes = self.rng.sample(list(fixes), taille)
        exclus = set(fixes)
        restantes = [v for v in range(1, maximum + 1) if v not in exclus]
        manque = taille - len(fixes)
        if poids is None:
            choisis = self.rng.sample(restantes, manque)
        else:
            # Tirage pondéré sans remise (Efraimidis et Spirakis) : on garde
            # les ``manque`` plus grandes clés u^(1/poids).
            cles = sorted(
                restantes,
                key=lambda v: self.rng.random() ** (1.0 / poids[v]),
                reverse=True,
            )
            choisis = cles[:manque]
        return tuple(sorted([*fixes, *choisis]))

    def _poids_anti_partage(self) -> Tuple[Optional[Dict[int, float]], Optional[Dict[int, float]]]:
        modele = self.modele
        if modele is None or not getattr(modele, "estime_sur_donnees", False):
            # Sans données de popularité : privilégier les numéros > 31, peu
            # joués car ils ne peuvent pas être des jours de naissance.
            return {n: (2.0 if n > 31 else 1.0) for n in range(1, self.jeu.numeros_max + 1)}, None
        facteurs_n = modele.facteurs_numeros  # type: ignore[attr-defined]
        facteurs_e = modele.facteurs_etoiles  # type: ignore[attr-defined]
        return (
            {n: f ** -_EXPOSANT_ANTI_PARTAGE for n, f in facteurs_n.items()},
            {e: f ** -_EXPOSANT_ANTI_PARTAGE for e, f in facteurs_e.items()},
        )

    def _accepte_anti_partage(self, grille: Grille) -> bool:
        if motifs_populaires(grille, self.dernier_tirage):
            return False
        # Au moins deux numéros qui ne peuvent pas être un jour du mois.
        return sum(1 for n in grille.numeros if n > 31) >= 2

    # --------------------------------------------------------------- grilles
    def grille(
        self,
        strategie: str = "aleatoire",
        numeros_favoris: Iterable[int] = (),
        bonus_favoris: Iterable[int] = (),
    ) -> Grille:
        """Génère une grille simple selon la stratégie demandée."""
        if strategie == "couverture":
            return self.grilles(1, "couverture", numeros_favoris, bonus_favoris)[0]
        if strategie not in STRATEGIES:
            raise ValueError(f"stratégie inconnue « {strategie} » (choix : {', '.join(STRATEGIES)})")
        jeu = self.jeu
        favoris_n = _verifier_favoris(numeros_favoris, jeu.numeros_max, "numéros")
        favoris_b = _verifier_favoris(bonus_favoris, jeu.bonus_max, jeu.bonus_nom_pluriel)
        poids_n: Optional[Dict[int, float]] = None
        poids_b: Optional[Dict[int, float]] = None
        if strategie == "anti-partage":
            poids_n, poids_b = self._poids_anti_partage()

        def candidat() -> Grille:
            return Grille.simple(
                jeu,
                self._completer(favoris_n, jeu.numeros_max, jeu.numeros_par_grille, poids_n),
                self._completer(favoris_b, jeu.bonus_max, jeu.bonus_par_grille, poids_b),
            )

        if strategie == "aleatoire":
            return candidat()
        if strategie == "equilibree":
            for _ in range(_ESSAIS_MAX):
                grille = candidat()
                if profil_equilibre(grille):
                    return grille
            raise ErreurGrille(
                "impossible de construire une grille équilibrée avec ces numéros favoris"
            )
        return self._anti_partage(candidat)

    def _anti_partage(self, candidat: Callable[[], Grille]) -> Grille:
        indice = getattr(self.modele, "indice", None)
        utilise_modele = (
            callable(indice)
            and getattr(self.modele, "estime_sur_donnees", False)
        )
        acceptables: List[Grille] = []
        premiere: Optional[Grille] = None
        for _ in range(_ESSAIS_MAX):
            grille = candidat()
            premiere = premiere or grille
            if self._accepte_anti_partage(grille):
                acceptables.append(grille)
                if not utilise_modele or len(acceptables) >= _CANDIDATS_ANTI_PARTAGE:
                    break
        if not acceptables:
            # Des favoris peuvent rendre les critères inatteignables : on garde
            # alors une grille pondérée telle quelle.
            assert premiere is not None
            return premiere
        if utilise_modele:
            return min(acceptables, key=lambda g: float(indice(g)))  # type: ignore[misc]
        return acceptables[0]

    def grilles(
        self,
        nombre: int,
        strategie: str = "aleatoire",
        numeros_favoris: Iterable[int] = (),
        bonus_favoris: Iterable[int] = (),
        distinctes: bool = True,
    ) -> List[Grille]:
        """Génère ``nombre`` grilles (toutes différentes si ``distinctes``)."""
        if nombre < 1:
            raise ValueError("le nombre de grilles doit être au moins 1")
        favoris_n = tuple(numeros_favoris)
        favoris_b = tuple(bonus_favoris)
        if strategie == "couverture":
            return self._couverture(nombre, favoris_n, favoris_b, distinctes)
        resultat: List[Grille] = []
        deja: Set[Grille] = set()
        essais = 0
        while len(resultat) < nombre:
            grille = self.grille(strategie, favoris_n, favoris_b)
            essais += 1
            if distinctes and grille in deja:
                if essais > nombre * 1000:
                    raise ErreurGrille(
                        f"impossible de produire {nombre} grilles différentes avec ces contraintes"
                    )
                continue
            deja.add(grille)
            resultat.append(grille)
        return resultat

    def _couverture(
        self,
        nombre: int,
        numeros_favoris: Sequence[int],
        bonus_favoris: Sequence[int],
        distinctes: bool,
    ) -> List[Grille]:
        """Grilles réparties pour couvrir le plus de numéros et d'étoiles possible."""
        jeu = self.jeu
        favoris_n = _verifier_favoris(numeros_favoris, jeu.numeros_max, "numéros")
        favoris_b = _verifier_favoris(bonus_favoris, jeu.bonus_max, jeu.bonus_nom_pluriel)
        if len(favoris_n) > jeu.numeros_par_grille or len(favoris_b) > jeu.bonus_par_grille:
            raise ErreurGrille("trop de favoris pour la stratégie couverture")
        paquet_n: List[int] = []
        paquet_b: List[int] = []

        def piocher(paquet: List[int], maximum: int, exclus: Sequence[int], taille: int) -> List[int]:
            choisis: List[int] = []
            disponibles = [v for v in range(1, maximum + 1) if v not in exclus]
            while len(choisis) < taille:
                if not paquet:
                    nouveau = disponibles[:]
                    self.rng.shuffle(nouveau)
                    paquet.extend(nouveau)
                valeur = paquet.pop(0)
                if valeur in choisis:
                    # Valeur déjà prise dans cette grille : on la remet en fin de paquet.
                    paquet.append(valeur)
                    if len(set(paquet) - set(choisis)) == 0:
                        paquet.clear()
                    continue
                choisis.append(valeur)
            return choisis

        resultat: List[Grille] = []
        deja: Set[Grille] = set()
        essais = 0
        while len(resultat) < nombre:
            numeros = list(favoris_n) + piocher(
                paquet_n, jeu.numeros_max, favoris_n, jeu.numeros_par_grille - len(favoris_n)
            )
            bonus = list(favoris_b) + piocher(
                paquet_b, jeu.bonus_max, favoris_b, jeu.bonus_par_grille - len(favoris_b)
            )
            grille = Grille.simple(jeu, numeros, bonus)
            essais += 1
            if distinctes and grille in deja:
                if essais > nombre * 1000:
                    raise ErreurGrille(
                        f"impossible de produire {nombre} grilles différentes avec ces contraintes"
                    )
                continue
            deja.add(grille)
            resultat.append(grille)
        return resultat
