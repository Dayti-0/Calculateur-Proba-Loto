"""Interface en ligne de commande : ``python -m proba_loto <commande>``.

Sans commande, un menu interactif est proposé.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import re
import sys
import textwrap
from typing import Callable, Dict, List, Optional, Sequence, TextIO, Tuple

from . import __version__
from . import affichage as fmt
from .analyse import analyser_grille, bornes_somme
from .esperance import SITUATIONS, calculer_esperance, jackpot_rentable
from .generateur import STRATEGIES, Generateur
from .grilles import ErreurGrille, Grille, verifier
from .historique import (
    DONNEES_EMBARQUEES,
    ErreurHistorique,
    TirageHistorique,
    charger,
    mettre_a_jour,
    trouver_tirage,
)
from .jeux import (
    EM_PLAFOND_JACKPOT,
    ETOILE_PLUS,
    EUROMILLIONS,
    JEUX,
    Jeu,
    TableDeGains,
    obtenir_jeu,
)
from .multiples import analyser_multiple, cout_multiple
from .popularite import ModelePopularite, estimer_popularite
from .probabilites import (
    LigneProbabilite,
    gain_moyen_theorique,
    nb_combinaisons,
    nb_tirages_pour,
    probabilite_gain,
    tableau_probabilites,
)
from .simulation import simuler
from .statistiques import retro_tester, statistiques_numeros, khi2_uniformite

__all__ = ["main", "construire_parseur"]

JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
RAPPEL_HASARD = (
    "Rappel : chaque combinaison a exactement la même probabilité de sortir ; "
    "aucune méthode ne peut prédire un tirage."
)
AIDE_JEU_RESPONSABLE = (
    "Les jeux d'argent sont interdits aux mineurs. Besoin d'aide : "
    "Joueurs Info Service, 09 74 75 13 13 (appel non surtaxé)."
)


class ErreurUtilisateur(Exception):
    """Erreur de saisie, affichée sans trace d'appel."""


# ---------------------------------------------------------------------------
# Contexte partagé (jeu choisi, historique chargé à la demande)
# ---------------------------------------------------------------------------


class Contexte:
    def __init__(self, jeu: Jeu, donnees: Optional[str] = None, sortie: Optional[TextIO] = None) -> None:
        self.jeu = jeu
        self.donnees = donnees
        self.sortie = sortie or sys.stdout
        self._historique: Optional[List[TirageHistorique]] = None
        self._modele: Optional[ModelePopularite] = None

    def ecrire(self, texte: str = "") -> None:
        print(texte, file=self.sortie)

    def paragraphe(self, texte: str, retrait: str = "") -> None:
        """Écrit un texte explicatif en le coupant proprement à 100 colonnes."""
        self.ecrire(
            textwrap.fill(
                texte,
                width=100,
                initial_indent=retrait,
                subsequent_indent=retrait + "  ",
                break_on_hyphens=False,
            )
        )

    def historique(self) -> List[TirageHistorique]:
        if self._historique is None:
            self._historique = charger(self.donnees)
        return self._historique

    def historique_si_disponible(self) -> Optional[List[TirageHistorique]]:
        try:
            return self.historique()
        except (ErreurHistorique, OSError):
            return None

    def modele(self) -> Optional[ModelePopularite]:
        if self.jeu is not EUROMILLIONS:
            return None
        if self._modele is None:
            historique = self.historique_si_disponible()
            if not historique:
                return None
            self._modele = estimer_popularite(historique)
        return self._modele

    def exiger_euromillions(self, fonction: str) -> None:
        if self.jeu is not EUROMILLIONS:
            raise ErreurUtilisateur(
                f"fonction réservée à l'EuroMillions ({fonction}) : l'historique officiel et la "
                "répartition des gains utilisés par cet outil concernent ce jeu."
            )


# ---------------------------------------------------------------------------
# Lecture des saisies
# ---------------------------------------------------------------------------


def lire_montant(texte: str) -> float:
    """« 59M », « 59 M€ », « 1,5 M », « 17 000 000 », « 250m », « 2k » → euros."""
    brut = texte.strip().lower().replace("€", "").replace("eur", "").replace("_", "")
    brut = brut.replace(" ", " ").replace("\xa0", " ")
    multiplicateur = 1.0
    correspondance = re.fullmatch(r"([\d\s.,]+)\s*(m|millions?|md|milliards?|k|mille)?", brut)
    if not correspondance:
        raise ErreurUtilisateur(f"montant illisible : « {texte} » (exemples : 59M, 17 000 000)")
    nombre, unite = correspondance.groups()
    if unite in ("m", "million", "millions"):
        multiplicateur = 1e6
    elif unite in ("md", "milliard", "milliards"):
        multiplicateur = 1e9
    elif unite in ("k", "mille"):
        multiplicateur = 1e3
    nombre = nombre.replace(" ", "")
    if "," in nombre and "." in nombre:
        nombre = nombre.replace(".", "").replace(",", ".")
    else:
        nombre = nombre.replace(",", ".")
    try:
        return float(nombre) * multiplicateur
    except ValueError:
        raise ErreurUtilisateur(f"montant illisible : « {texte} »") from None


def lire_date(texte: str) -> dt.date:
    for format_date in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(texte.strip(), format_date).date()
        except ValueError:
            continue
    raise ErreurUtilisateur(f"date illisible : « {texte} » (format attendu JJ/MM/AAAA)")


def lire_grille(contexte: Contexte, texte: str, multiple: bool = True) -> Grille:
    try:
        return Grille.depuis_texte(contexte.jeu, texte, autoriser_multiple=multiple)
    except ErreurGrille as erreur:
        raise ErreurUtilisateur(str(erreur)) from None


def date_longue(date: dt.date) -> str:
    return f"{JOURS[date.weekday()]} {date:%d/%m/%Y}"


# ---------------------------------------------------------------------------
# Commandes
# ---------------------------------------------------------------------------


def _ligne_rang(jeu: Jeu, table: TableDeGains, ligne: LigneProbabilite, avec_gain: bool) -> List[str]:
    rang = ligne.rang
    cellules = [
        str(rang.numero),
        ligne.libelle,
        fmt.chances(ligne.probabilite),
        fmt.pourcentage(ligne.probabilite),
    ]
    if avec_gain:
        if table is jeu.gains and rang.numero == 1:
            gain = "jackpot"
        else:
            valeur = gain_moyen_theorique(jeu, rang, table)
            gain = fmt.euros(valeur, 0 if valeur and valeur >= 100 else 2) if valeur is not None else "variable"
        cellules.append(gain)
    return cellules


def cmd_probas(args: argparse.Namespace, ctx: Contexte) -> None:
    jeu = ctx.jeu
    tables = [jeu.gains]
    if args.etoile_plus:
        ctx.exiger_euromillions("option Étoile+")
        tables.append(ETOILE_PLUS)
    total = nb_combinaisons(jeu)
    ctx.ecrire(f"{jeu.nom} : probabilités exactes pour une grille simple ({fmt.euros(jeu.prix_grille)})")
    ctx.ecrire(
        f"{fmt.entier(total)} combinaisons possibles : {jeu.numeros_par_grille} numéros parmi "
        f"{jeu.numeros_max} et {jeu.bonus_par_grille} {jeu.bonus_nom if jeu.bonus_par_grille == 1 else jeu.bonus_nom_pluriel} "
        f"parmi {jeu.bonus_max}"
    )
    avec_gain = jeu is EUROMILLIONS
    for table in tables:
        ctx.ecrire()
        if table is not jeu.gains:
            ctx.ecrire(f"Option {table.nom} ({fmt.euros(table.mise)} par grille, {fmt.pourcentage(table.part_gagnants)} des mises reversés)")
        lignes = [_ligne_rang(jeu, table, ligne, avec_gain) for ligne in tableau_probabilites(jeu, table)]
        entetes = ["Rang", "Combinaison", "Chances", "Probabilité"] + (["Gain moyen*"] if avec_gain else [])
        ctx.ecrire(fmt.tableau(lignes, entetes, "dgddd"))
        p = probabilite_gain(jeu, table)
        ctx.ecrire(f"  Tous rangs : {fmt.chances(p, decimales=2)} ({fmt.pourcentage(p)})")
    if avec_gain:
        ctx.ecrire()
        ctx.paragraphe(
            "* Gain moyen d'un gagnant, déduit de la répartition réglementaire (mise × part des "
            "gagnants × part du rang ÷ probabilité). Les rapports réels varient d'un tirage à "
            "l'autre selon le nombre de gagnants.",
            "  ",
        )
    jackpot = jeu.gains.rang(1)
    p1 = float(tableau_probabilites(jeu)[0].probabilite)
    grilles = max(1, args.grilles)
    p_tirage = p1 * grilles
    par_semaine = jeu.tirages_par_semaine
    ctx.ecrire()
    ctx.ecrire(
        f"En jouant {grilles} grille{'s' if grilles > 1 else ''} à chaque tirage "
        f"({par_semaine} par semaine, soit {fmt.euros(float(jeu.prix_grille) * grilles * par_semaine * 52.1775, 0)} par an) :"
    )
    ctx.ecrire(f"  - attente moyenne avant de gagner le rang {jackpot.numero} : {fmt.duree(1 / p_tirage, par_semaine)} ;")
    ctx.ecrire(
        f"  - 50 % de chances de l'avoir gagné au moins une fois : après "
        f"{fmt.duree(nb_tirages_pour(p_tirage, 0.5), par_semaine)}."
    )
    ctx.ecrire()
    ctx.ecrire(f"Source : {jeu.reference}.")


def cmd_generer(args: argparse.Namespace, ctx: Contexte) -> None:
    jeu = ctx.jeu
    if args.nombre < 1 or args.nombre > 1000:
        raise ErreurUtilisateur("le nombre de grilles doit être compris entre 1 et 1000")
    modele = ctx.modele() if jeu is EUROMILLIONS else None
    historique = ctx.historique_si_disponible() if jeu is EUROMILLIONS else None
    dernier = historique[-1].combinaison if historique else None
    generateur = Generateur(jeu, graine=args.graine, modele=modele, dernier_tirage=dernier)
    try:
        grilles = generateur.grilles(args.nombre, args.strategie, args.numeros or (), args.bonus or ())
    except ErreurGrille as erreur:
        raise ErreurUtilisateur(str(erreur)) from None
    titre = f"{len(grilles)} grille{'s' if len(grilles) > 1 else ''} {jeu.nom} – stratégie {args.strategie}"
    ctx.ecrire(titre)
    largeur = len(str(len(grilles)))
    for numero, grille in enumerate(grilles, 1):
        ligne = f"  {numero:>{largeur}}.  {grille}"
        if modele is not None:
            ligne += f"   indice de popularité {fmt.decimal(modele.indice(grille), 2)}"
        ctx.ecrire(ligne)
        if args.details:
            _afficher_analyse(ctx, grille, modele, dernier, retrait="       ")
    ctx.ecrire()
    p = float(tableau_probabilites(jeu)[0].probabilite)
    ctx.paragraphe(
        f"Chaque grille a exactement {fmt.chances(p, phrase=True)} de gagner le rang 1, "
        "quelle que soit la stratégie."
    )
    if modele is not None:
        ctx.paragraphe(
            "Indice de popularité : nombre de grilles identiques attendues chez les autres joueurs, "
            "relativement à une combinaison moyenne (1,00). Un indice de 0,50 divise par deux "
            "le nombre attendu de co-gagnants, donc le risque de partager un gain."
        )
    if args.strategie == "couverture":
        couverts = {n for g in grilles for n in g.numeros}
        ctx.ecrire(f"Couverture : {len(couverts)} numéros différents sur {jeu.numeros_max}.")


def _texte_gains(gains: Dict[int, int]) -> str:
    return ", ".join(f"{n} × rang {r}" for r, n in gains.items())


def cmd_verifier(args: argparse.Namespace, ctx: Contexte) -> None:
    jeu = ctx.jeu
    if args.etoile_plus:
        ctx.exiger_euromillions("option Étoile+")
    grille = lire_grille(ctx, args.grille)
    tirage_historique: Optional[TirageHistorique] = None
    if args.tirage:
        tirage = lire_grille(ctx, args.tirage, multiple=False)
        ctx.ecrire(f"Tirage saisi : {tirage}")
    else:
        ctx.exiger_euromillions("vérification sur l'historique officiel ; utilisez --tirage")
        historique = ctx.historique()
        if args.date:
            tirage_historique = trouver_tirage(historique, lire_date(args.date))
        else:
            tirage_historique = historique[-1]
        tirage = tirage_historique.combinaison
        ctx.ecrire(f"Tirage du {date_longue(tirage_historique.date)} : {tirage}")
    tables = [jeu.gains] + ([ETOILE_PLUS] if args.etoile_plus else [])
    ctx.ecrire(f"Votre grille : {grille}" + (f"  ({grille.nb_combinaisons_simples} grilles simples)" if grille.est_multiple else ""))
    resultat = verifier(grille, tirage)
    ctx.ecrire(
        f"  Bons numéros : {fmt.liste_numeros(resultat.bons_numeros) or 'aucun'} ({len(resultat.bons_numeros)})"
        f"  |  {jeu.bonus_nom_pluriel} : {fmt.liste_numeros(resultat.bons_bonus) or 'aucun'} ({len(resultat.bons_bonus)})"
    )
    total = 0.0
    total_connu = True
    for table in tables:
        resultat = verifier(grille, tirage, table)
        if not resultat.gains:
            ctx.ecrire(f"  {table.nom} : aucun gain.")
            continue
        for rang_numero, nombre in resultat.gains.items():
            rang = table.rang(rang_numero)
            libelle = f"  {table.nom} rang {rang_numero} ({jeu.libelle_rang(rang)})"
            if nombre > 1:
                libelle += f" × {nombre}"
            montant: Optional[float] = None
            source = ""
            if tirage_historique is not None:
                if table is ETOILE_PLUS:
                    rapport = tirage_historique.rapports_etoile_plus[rang_numero - 1]
                else:
                    rapport = tirage_historique.rapports[rang_numero - 1]
                if rapport > 0:
                    montant = rapport * nombre
                    source = "rapport officiel"
                else:
                    source = "aucun gagnant officiel à ce rang ce jour-là : montant non publié"
            else:
                moyen = gain_moyen_theorique(jeu, rang, table)
                if moyen is not None:
                    montant = moyen * nombre
                    source = "gain moyen estimé"
                else:
                    source = "montant variable"
            if montant is None:
                total_connu = False
                ctx.ecrire(f"{libelle} : {source}")
            else:
                total += montant
                ctx.ecrire(f"{libelle} : {fmt.euros(montant)} ({source})")
    mise = float(cout_multiple(jeu, len(grille.numeros), len(grille.bonus), tables[1:]))
    if total:
        ctx.ecrire(f"  Total{' (hors montants inconnus)' if not total_connu else ''} : {fmt.euros(total)} pour {fmt.euros(mise)} misés.")


def cmd_multiple(args: argparse.Namespace, ctx: Contexte) -> None:
    jeu = ctx.jeu
    table = jeu.gains
    try:
        analyse = analyser_multiple(jeu, args.numeros, args.bonus)
    except ErreurGrille as erreur:
        raise ErreurUtilisateur(str(erreur)) from None
    cout = cout_multiple(jeu, args.numeros, args.bonus)
    ctx.ecrire(
        f"Grille multiple {jeu.nom} : {args.numeros} numéros × {args.bonus} "
        f"{jeu.bonus_nom_pluriel if args.bonus > 1 else jeu.bonus_nom}"
    )
    texte_cout = f"  = {fmt.entier(analyse.nb_simples)} grilles simples, {fmt.euros(cout)} par tirage"
    if jeu is EUROMILLIONS:
        texte_cout += f" ({fmt.euros(cout_multiple(jeu, args.numeros, args.bonus, [ETOILE_PLUS]))} avec Étoile+)"
    ctx.ecrire(texte_cout)
    p = analyse.probabilite_gain
    ctx.ecrire(f"  Probabilité de gagner au moins un rang : {fmt.chances(p, decimales=2)} ({fmt.pourcentage(p)})")
    au_moins = analyse.probabilite_au_moins_un()
    ctx.ecrire(
        f"  Probabilité d'avoir au moins une grille au rang 1 : {fmt.chances(au_moins.get(1, 0))}"
        f" (au lieu de {fmt.chances(tableau_probabilites(jeu)[0].probabilite)} pour une grille simple)"
    )
    ctx.ecrire()
    ctx.ecrire("  Probabilité selon le meilleur rang obtenu :")
    meilleur = analyse.probabilite_meilleur_rang()
    lignes = [[f"rang {r}", jeu.libelle_rang(table.rang(r)), fmt.chances(pr)] for r, pr in meilleur.items()]
    ctx.ecrire(fmt.tableau(lignes, ["Meilleur rang", "Combinaison", "Chances"], "ggd", marge="    "))
    ctx.ecrire()
    ctx.ecrire("  Répartition des gains selon le tirage (tableau des rangs en cas de multiple) :")
    lignes = []
    for scenario in analyse.scenarios_gagnants():
        lignes.append(
            [
                jeu.libelle_correspondance(scenario.bons_numeros, scenario.bons_bonus),
                fmt.chances(scenario.probabilite),
                _texte_gains(scenario.gains),
            ]
        )
    ctx.ecrire(
        fmt.tableau(lignes, ["Trouvés dans votre multiple", "Chances", "Grilles gagnantes"], "gdg", marge="    ")
    )
    ctx.ecrire()
    ctx.paragraphe(
        "Une multiple coûte exactement le prix de ses grilles simples : elle augmente vos "
        "chances dans la même proportion que votre mise, sans avantage mathématique.",
        "  ",
    )


def _decrire_situation(situation: str) -> str:
    return {
        "normal": "tirage ordinaire",
        "plafond": f"jackpot au plafond ({fmt.montant_compact(EM_PLAFOND_JACKPOT)}) : l'excédent est versé au rang 2",
        "doit-etre-gagne": "jackpot qui doit être distribué (5e tirage au plafond ou tirage « forcément gagné »)",
    }[situation]


def cmd_esperance(args: argparse.Namespace, ctx: Contexte) -> None:
    ctx.exiger_euromillions("calcul d'espérance")
    ventes = lire_montant(args.ventes) if args.ventes else None
    codes = lire_montant(args.codes_my_million) if args.codes_my_million else None
    indice = 1.0
    if args.grille:
        grille = lire_grille(ctx, args.grille, multiple=False)
        modele = ctx.modele()
        if modele is None:
            raise ErreurUtilisateur("historique indisponible : impossible d'estimer la popularité de la grille")
        indice = modele.indice(grille)
        ctx.ecrire(f"Grille {grille} : indice de popularité {fmt.decimal(indice, 2)}")
    if not args.jackpot and args.situation == "normal":
        _tableau_esperance(ctx, ventes, codes, args.etoile_plus, indice)
        return
    jackpot = lire_montant(args.jackpot) if args.jackpot else float(EM_PLAFOND_JACKPOT)
    try:
        e = calculer_esperance(jackpot, ventes, codes, args.situation, args.etoile_plus, indice)
    except ValueError as erreur:
        raise ErreurUtilisateur(str(erreur)) from None
    ctx.ecrire(f"Espérance de gain d'une grille EuroMillions – My Million, jackpot {fmt.montant_compact(jackpot)}")
    ctx.ecrire(f"  Situation : {_decrire_situation(args.situation)}")
    origine = "valeur fournie" if ventes is not None else "estimation d'après le jackpot"
    ctx.paragraphe(
        f"Hypothèses : {fmt.decimal(e.ventes / 1e6, 1)} M de grilles jouées en Europe ({origine}), "
        f"{fmt.decimal(e.codes_my_million / 1e6, 1)} M de codes My Million en France",
        "  ",
    )
    lignes = [["Rangs 2 à 13", fmt.euros(e.rangs_2_a_13)]]
    if e.excedent_plafond:
        lignes.append(["Excédent du plafond reversé au rang 2", fmt.euros(e.excedent_plafond)])
    lignes.append(["Jackpot (partage avec les autres gagnants compris)", fmt.euros(e.jackpot_moyen)])
    lignes.append(["My Million (1 M€ pour un code français)", fmt.euros(e.my_million)])
    if args.etoile_plus:
        lignes.append(["Étoile+ (60 % des mises de l'option)", fmt.euros(e.etoile_plus_moyen)])
    lignes.append(["Total récupéré en moyenne", f"{fmt.euros(e.total)} pour {fmt.euros(e.mise)} misés ({fmt.pourcentage(e.taux_retour)})"])
    ctx.ecrire(fmt.tableau(lignes, alignements="gd"))
    if e.perte_moyenne > 0:
        ctx.ecrire(f"  Perte moyenne : {fmt.euros(e.perte_moyenne)} par grille.")
    else:
        ctx.paragraphe(
            f"Espérance positive (+{fmt.euros(-e.perte_moyenne)} par grille) : situation exceptionnelle, "
            "mais la probabilité de gain ne change pas et le risque de tout perdre reste quasi certain.",
            "  ",
        )
    if args.situation != "doit-etre-gagne":
        ctx.ecrire(
            f"  Si vous gagnez le jackpot : {fmt.pourcentage(e.proba_partage)} de risque de le partager, "
            f"part moyenne {fmt.pourcentage(e.part_moyenne_jackpot)}."
        )
    if args.situation == "normal":
        _seuil_rentabilite(ctx, ventes, codes, args.etoile_plus, indice)


def _tableau_esperance(
    ctx: Contexte, ventes: Optional[float], codes: Optional[float], etoile_plus: bool, indice: float
) -> None:
    ctx.ecrire("Espérance de gain d'une grille EuroMillions – My Million selon le jackpot (tirage ordinaire)")
    lignes = []
    for jackpot in (17e6, 50e6, 100e6, 150e6, 200e6, 250e6):
        e = calculer_esperance(jackpot, ventes, codes, "normal", etoile_plus, indice)
        lignes.append(
            [
                fmt.montant_compact(jackpot),
                f"{fmt.decimal(e.ventes / 1e6, 1)} M",
                fmt.euros(e.total),
                fmt.pourcentage_fixe(e.taux_retour),
                fmt.euros(e.perte_moyenne),
                fmt.pourcentage_fixe(e.proba_partage),
            ]
        )
    ctx.ecrire(
        fmt.tableau(
            lignes,
            ["Jackpot", "Grilles jouées", "Récupéré", "Retour", "Perte/grille", "Risque de partage"],
            "dddddd",
        )
    )
    ctx.ecrire(f"  Mise : {fmt.euros(2.5 + (1 if etoile_plus else 0))} par grille{' (Étoile+ comprise)' if etoile_plus else ''}.")
    _seuil_rentabilite(ctx, ventes, codes, etoile_plus, indice)
    ctx.ecrire("  Détail d'un cas : --jackpot 59M ; tirages au plafond : --jackpot 250M --situation plafond")


def _seuil_rentabilite(
    ctx: Contexte, ventes: Optional[float], codes: Optional[float], etoile_plus: bool, indice: float
) -> None:
    seuil = jackpot_rentable(ventes, codes, etoile_plus, indice)
    if seuil is None:
        ctx.ecrire("  Aucun jackpot, même illimité, ne rendrait le jeu rentable avec ces hypothèses.")
    elif seuil > EM_PLAFOND_JACKPOT:
        ctx.paragraphe(
            f"Seuil de rentabilité théorique : jackpot de {fmt.montant_compact(round(seuil, -6))}, "
            f"supérieur au plafond réglementaire de {fmt.montant_compact(EM_PLAFOND_JACKPOT)} : "
            "un tirage ordinaire n'est jamais rentable.",
            "  ",
        )
    else:
        ctx.ecrire(f"  Seuil de rentabilité théorique : jackpot de {fmt.montant_compact(round(seuil, -6))}.")


def cmd_simuler(args: argparse.Namespace, ctx: Contexte) -> None:
    ctx.exiger_euromillions("simulation")
    jackpot = lire_montant(args.jackpot) if args.jackpot else None
    try:
        r = simuler(
            annees=args.annees,
            grilles_par_tirage=args.grilles,
            joueurs=args.joueurs,
            jackpot=jackpot,
            etoile_plus=args.etoile_plus,
            graine=args.graine,
        )
    except ValueError as erreur:
        raise ErreurUtilisateur(str(erreur)) from None
    ctx.ecrire(
        f"Simulation : {fmt.entier(r.joueurs)} joueur{'s' if r.joueurs > 1 else ''}, {r.grilles_par_tirage} "
        f"grille{'s' if r.grilles_par_tirage > 1 else ''} à chaque tirage{' avec Étoile+' if r.etoile_plus else ''} "
        f"pendant {fmt.decimal(args.annees, 0 if float(args.annees).is_integer() else 1)} an{'s' if args.annees >= 2 else ''} "
        f"({fmt.entier(r.tirages)} tirages)"
    )
    ctx.ecrire(f"  Mise de chaque joueur : {fmt.euros(r.mise_par_joueur)} (jackpot supposé : {fmt.montant_compact(r.jackpot)})")
    ctx.ecrire(
        f"  Gains récupérés : moyenne {fmt.euros(r.gain_moyen)} ({fmt.pourcentage(r.taux_retour)}), "
        f"médiane {fmt.euros(r.gain_median)} ({fmt.pourcentage(r.gain_median / r.mise_par_joueur)})"
    )
    ctx.ecrire(f"  Joueurs ayant gagné plus qu'ils n'ont misé : {fmt.pourcentage(r.part_joueurs_gagnants)}")
    ctx.ecrire(f"  Meilleur bilan : {fmt.euros(r.meilleur_bilan)}")
    jackpots = r.victoires.get(("EuroMillions", 1), 0)
    ctx.ecrire(f"  Jackpots gagnés : {jackpots}  |  codes My Million gagnants : {r.my_million}")
    for jeu_nom in ("EuroMillions", "Étoile+"):
        details = [(rang, n) for (j, rang), n in sorted(r.victoires.items()) if j == jeu_nom]
        if details:
            ctx.ecrire(f"  Gains {jeu_nom} (tous joueurs) : " + ", ".join(f"rang {rang} : {fmt.entier(n)}" for rang, n in details))
    ctx.ecrire()
    ctx.ecrire(
        "La moyenne inclut des gains rarissimes (jackpot, My Million) ; la médiane reflète "
        "ce que vit un joueur typique."
    )


def _intro_historique(ctx: Contexte, tirages: Sequence[TirageHistorique]) -> None:
    ctx.ecrire(
        f"Historique EuroMillions : {fmt.entier(len(tirages))} tirages du {tirages[0].date:%d/%m/%Y} "
        f"au {tirages[-1].date:%d/%m/%Y} (source : FDJ)"
    )


def cmd_stats(args: argparse.Namespace, ctx: Contexte) -> None:
    ctx.exiger_euromillions("statistiques sur l'historique")
    tirages = ctx.historique()
    if args.depuis:
        depuis = lire_date(args.depuis)
        tirages = [t for t in tirages if t.date >= depuis]
        if not tirages:
            raise ErreurUtilisateur("aucun tirage depuis cette date")
    _intro_historique(ctx, tirages)
    nombre = max(1, args.top)
    for etoiles, nom, maximum, par_tirage in ((False, "Numéros", 50, 5), (True, "Étoiles", 12, 2)):
        e = "e" if etoiles else ""
        stats = statistiques_numeros(tirages, etoiles)
        test = khi2_uniformite({s.numero: s.sorties for s in stats}, maximum, par_tirage, len(tirages))
        par_frequence = sorted(stats, key=lambda s: (-s.sorties, s.numero))
        ctx.ecrire()
        ctx.ecrire(f"{nom} (sorties attendues pour chacun{e} : {fmt.decimal(test.attendu, 1)})")
        n = min(nombre, len(stats) // 2)
        ctx.ecrire(f"  Les plus sorti{e}s  : " + ", ".join(f"{s.numero} ({s.sorties})" for s in par_frequence[:n]))
        ctx.ecrire(f"  Les moins sorti{e}s : " + ", ".join(f"{s.numero} ({s.sorties})" for s in par_frequence[::-1][:n]))
        par_ecart = sorted(stats, key=lambda s: -s.ecart_actuel)[:n]
        ctx.ecrire(
            f"  Absent{e}s depuis le plus longtemps : "
            + ", ".join(f"{s.numero} ({s.ecart_actuel} tirages)" for s in par_ecart)
        )
        ctx.paragraphe(
            f"Test du khi² d'uniformité : χ² = {fmt.decimal(test.statistique, 1)} ({test.ddl} ddl), "
            f"p = {fmt.decimal(test.p_valeur, 3)} → {test.conclusion}.",
            "  ",
        )
    ctx.ecrire()
    ctx.ecrire("Derniers tirages :")
    for tirage in tirages[-5:][::-1]:
        ctx.ecrire(f"  {date_longue(tirage.date):<20} {tirage.combinaison}")
    ctx.ecrire()
    ctx.paragraphe(
        "Les écarts et fréquences passés ne prédisent rien : un numéro « en retard » n'a pas plus "
        "de chances de sortir au prochain tirage (les tirages sont indépendants)."
    )


def cmd_popularite(args: argparse.Namespace, ctx: Contexte) -> None:
    ctx.exiger_euromillions("estimation de popularité")
    modele = ctx.modele()
    if modele is None:
        raise ErreurUtilisateur("historique indisponible : lancez d'abord « maj »")
    ctx.ecrire(
        f"Popularité estimée des numéros chez les joueurs européens ({fmt.entier(modele.nb_tirages)} tirages, "
        f"{modele.debut:%d/%m/%Y} – {modele.fin:%d/%m/%Y})"
    )
    ctx.paragraphe(
        "Méthode : un gain partagé entre beaucoup de gagnants révèle des numéros très joués. "
        "Le modèle explique les rapports des rangs 13 (numéros) et 11 (étoiles) par les "
        "numéros et étoiles tirés."
    )
    if modele.correlation_validation is not None:
        ctx.paragraphe(
            f"Validation : corrélation de {fmt.decimal(modele.correlation_validation, 2)} entre rapports prédits "
            "et observés sur les 25 % de tirages les plus récents, non utilisés pour l'estimation."
        )

    def variation(facteur: float) -> str:
        ecart = round((facteur - 1) * 100)
        if ecart == 0:
            return "±0 %"
        return f"{'+' if ecart > 0 else '−'}{abs(ecart)} %"

    nombre = max(1, args.top)
    classement = modele.classement_numeros()
    ctx.ecrire()
    ctx.ecrire("Numéros les plus joués  : " + ", ".join(f"{n} ({variation(f)})" for n, f in classement[:nombre]))
    ctx.ecrire("Numéros les moins joués : " + ", ".join(f"{n} ({variation(f)})" for n, f in classement[::-1][:nombre]))
    etoiles = modele.classement_etoiles()
    ctx.ecrire("Étoiles, de la plus jouée à la moins jouée : " + ", ".join(f"{e} ({variation(f)})" for e, f in etoiles))
    bas = [f for n, f in classement if n <= 31]
    haut = [f for n, f in classement if n > 31]
    ctx.ecrire()
    ctx.ecrire(
        f"Numéros 1 à 31 (dates) : {variation(sum(bas) / len(bas))} en moyenne ; "
        f"32 à 50 : {variation(sum(haut) / len(haut))}."
    )
    ctx.paragraphe(
        "Ces écarts ne changent pas vos chances de gagner, seulement le partage des gains : "
        "« generer --strategie anti-partage » s'en sert pour proposer des grilles moins jouées."
    )


def cmd_retro(args: argparse.Namespace, ctx: Contexte) -> None:
    ctx.exiger_euromillions("rétro-test")
    grille = lire_grille(ctx, args.grille)
    tirages = ctx.historique()
    depuis = lire_date(args.depuis) if args.depuis else None
    resultat = retro_tester(grille, tirages, args.etoile_plus, depuis)
    if not resultat.nb_tirages:
        raise ErreurUtilisateur("aucun tirage sur la période demandée")
    ctx.ecrire(
        f"Si vous aviez joué {grille}{' avec Étoile+' if args.etoile_plus else ''} à chaque tirage "
        f"du {resultat.debut:%d/%m/%Y} au {resultat.fin:%d/%m/%Y} ({fmt.entier(resultat.nb_tirages)} tirages) :"
    )
    ctx.ecrire(f"  Mise totale : {fmt.euros(resultat.mise_totale)}")
    ctx.ecrire(
        f"  Gains : {fmt.euros(resultat.total_gains)} ({fmt.pourcentage(resultat.taux_retour)} de la mise), "
        f"bilan {fmt.euros(resultat.total_gains - resultat.mise_totale)}"
    )
    lignes = []
    for (jeu_nom, rang), (nombre, montant) in resultat.par_rang().items():
        table = ETOILE_PLUS if jeu_nom == "Étoile+" else EUROMILLIONS.gains
        lignes.append([f"{jeu_nom} rang {rang}", EUROMILLIONS.libelle_rang(table.rang(rang)), fmt.entier(nombre), fmt.euros(montant)])
    if lignes:
        ctx.ecrire(fmt.tableau(lignes, ["Rang", "Combinaison", "Fois", "Montant"], "ggdd"))
    for gain in resultat.gains_inconnus:
        ctx.ecrire(
            f"  Le {gain.date:%d/%m/%Y} : {gain.jeu} rang {gain.rang} atteint, mais personne ne l'a gagné "
            "ce jour-là : montant non publié (non compté)."
        )
    meilleurs = resultat.meilleurs_gains(3)
    if meilleurs:
        ctx.ecrire("  Meilleurs gains : " + ", ".join(f"{fmt.euros(g.montant or 0)} le {g.date:%d/%m/%Y} ({g.jeu} rang {g.rang})" for g in meilleurs))
    ctx.ecrire("  Montants : rapports officiels France, ajustés comme si vous aviez été un gagnant de plus.")


def _afficher_analyse(
    ctx: Contexte,
    grille: Grille,
    modele: Optional[ModelePopularite],
    dernier: Optional[Grille],
    retrait: str = "  ",
) -> None:
    analyse = analyser_grille(grille, modele, dernier)
    jeu = grille.jeu
    minimum, maximum = bornes_somme(jeu)
    ctx.ecrire(
        f"{retrait}Somme des numéros : {analyse.somme} (centile {fmt.decimal(analyse.rang_centile_somme * 100, 0)} ; "
        f"la moitié des combinaisons ont une somme entre {minimum} et {maximum})"
    )
    ctx.ecrire(
        f"{retrait}Pairs/impairs : {analyse.pairs}/{analyse.impairs} (profil de {fmt.pourcentage(analyse.proba_pairs)} des combinaisons)"
        f"  |  bas (≤ {analyse.seuil_bas})/hauts : {analyse.bas}/{analyse.hauts} ({fmt.pourcentage(analyse.proba_bas)})"
    )
    dizaines = ", ".join(f"{k} : {v}" for k, v in analyse.dizaines.items() if v)
    ctx.ecrire(f"{retrait}Dizaines : {dizaines}  |  plus longue suite : {analyse.plus_longue_suite}")
    if analyse.motifs:
        ctx.ecrire(f"{retrait}Motifs très joués : " + " ; ".join(m.description for m in analyse.motifs))
    else:
        ctx.ecrire(f"{retrait}Aucun motif connu pour être très joué.")
    if analyse.indice_popularite is not None:
        ctx.ecrire(f"{retrait}Indice de popularité : {fmt.decimal(analyse.indice_popularite, 2)} (1,00 = combinaison moyenne)")


def cmd_analyser(args: argparse.Namespace, ctx: Contexte) -> None:
    grille = lire_grille(ctx, args.grille, multiple=False)
    modele = ctx.modele()
    historique = ctx.historique_si_disponible() if ctx.jeu is EUROMILLIONS else None
    dernier = historique[-1].combinaison if historique else None
    ctx.ecrire(f"Analyse de la grille {grille}")
    _afficher_analyse(ctx, grille, modele, dernier)
    ctx.ecrire()
    ctx.paragraphe(
        f"Probabilité de gagner le rang 1 : {fmt.chances(tableau_probabilites(ctx.jeu)[0].probabilite, phrase=True)}, "
        "comme toute autre grille. Le profil ne change pas les chances ; les motifs et la "
        "popularité influent seulement sur le partage d'un éventuel gain."
    )


def cmd_maj(args: argparse.Namespace, ctx: Contexte) -> None:
    ctx.ecrire("Téléchargement de l'historique officiel depuis fdj.fr…")
    chemin, tirages = mettre_a_jour(args.sortie)
    ctx.ecrire(
        f"{fmt.entier(len(tirages))} tirages enregistrés dans {chemin} "
        f"(du {tirages[0].date:%d/%m/%Y} au {tirages[-1].date:%d/%m/%Y})."
    )


# ---------------------------------------------------------------------------
# Menu interactif
# ---------------------------------------------------------------------------


class FinDuMenu(Exception):
    pass


def _lire_clavier(question: str) -> str:
    # ``input`` est résolu à l'appel (et non à la définition) pour rester remplaçable.
    return input(question)


def _demander(question: str, defaut: str = "", lire: Callable[[str], str] = _lire_clavier) -> str:
    suffixe = f" [{defaut}]" if defaut else ""
    try:
        reponse = lire(f"{question}{suffixe} : ").strip()
    except (EOFError, KeyboardInterrupt):
        raise FinDuMenu from None
    return reponse or defaut


def menu(ctx: Contexte, lire: Callable[[str], str] = _lire_clavier) -> int:
    """Menu interactif ; chaque choix exécute la commande correspondante."""
    options: List[Tuple[str, str, Callable[[], List[str]]]] = [
        ("1", "Probabilités de gain", lambda: ["probas"] + (["--etoile-plus"] if ctx.jeu is EUROMILLIONS else [])),
        ("2", "Générer des grilles", lambda: _menu_generer(ctx, lire)),
        ("3", "Vérifier une grille", lambda: _menu_verifier(ctx, lire)),
        ("4", "Grille multiple : coût et probabilités", lambda: _menu_multiple(ctx, lire)),
        ("5", "Espérance de gain (EuroMillions)", lambda: _menu_esperance(lire)),
        ("6", "Simuler des années de jeu (EuroMillions)", lambda: _menu_simuler(lire)),
        ("7", "Statistiques des tirages réels (EuroMillions)", lambda: ["stats"]),
        ("8", "Popularité des numéros (EuroMillions)", lambda: ["popularite"]),
        ("9", "Rejouer une grille sur l'historique (EuroMillions)", lambda: ["retro", _demander("Grille", "3 5 37 44 49 + 5 6", lire)]),
        ("10", "Analyser une grille", lambda: ["analyser", _demander("Grille", _exemple(ctx.jeu), lire)]),
    ]
    while True:
        ctx.ecrire()
        ctx.ecrire("=" * 62)
        ctx.ecrire(f"  CALCULATEUR {ctx.jeu.nom.upper()}  (version {__version__})")
        ctx.ecrire("=" * 62)
        for cle, libelle, _ in options:
            ctx.ecrire(f"  {cle:>2}. {libelle}")
        autre = "Loto" if ctx.jeu is EUROMILLIONS else "EuroMillions"
        ctx.ecrire(f"   J. Passer au {autre}")
        ctx.ecrire("   0. Quitter")
        try:
            choix = _demander("\nVotre choix", lire=lire).upper()
            if choix in ("0", "Q"):
                break
            if choix == "J":
                ctx.jeu = JEUX["loto"] if ctx.jeu is EUROMILLIONS else EUROMILLIONS
                ctx._modele = None
                continue
            action = next((a for cle, _, a in options if cle == choix), None)
            if action is None:
                ctx.ecrire("Choix invalide.")
                continue
            arguments = ["--jeu", ctx.jeu.cle] + action()
            ctx.ecrire()
            executer(arguments, ctx)
            _demander("\nEntrée pour revenir au menu", lire=lire)
        except FinDuMenu:
            break
    ctx.ecrire("\nAu revoir. " + AIDE_JEU_RESPONSABLE)
    return 0


def _exemple(jeu: Jeu) -> str:
    return "3 5 37 44 49 + 5 6" if jeu is EUROMILLIONS else "3 5 37 44 49 + 7"


def _menu_generer(ctx: Contexte, lire: Callable[[str], str]) -> List[str]:
    nombre = _demander("Nombre de grilles", "5", lire)
    strategie = _demander(f"Stratégie ({', '.join(STRATEGIES)})", "aleatoire", lire)
    favoris = _demander("Numéros favoris (facultatif, ex. 7 13)", "", lire)
    arguments = ["generer", "-n", nombre, "--strategie", strategie]
    if favoris:
        arguments += ["--numeros", *favoris.replace(",", " ").split()]
    return arguments


def _menu_verifier(ctx: Contexte, lire: Callable[[str], str]) -> List[str]:
    grille = _demander("Votre grille", _exemple(ctx.jeu), lire)
    if ctx.jeu is EUROMILLIONS:
        date = _demander("Date du tirage (JJ/MM/AAAA, vide = dernier tirage)", "", lire)
        return ["verifier", grille] + (["--date", date] if date else [])
    tirage = _demander("Tirage (numéros + N° Chance)", "", lire)
    return ["verifier", grille, "--tirage", tirage]


def _menu_multiple(ctx: Contexte, lire: Callable[[str], str]) -> List[str]:
    numeros = _demander("Nombre de numéros cochés", "6", lire)
    bonus = _demander(f"Nombre de {ctx.jeu.bonus_nom_pluriel} cochés", "3" if ctx.jeu is EUROMILLIONS else "1", lire)
    return ["multiple", numeros, bonus]


def _menu_esperance(lire: Callable[[str], str]) -> List[str]:
    jackpot = _demander("Jackpot annoncé (ex. 59M, vide = tableau)", "", lire)
    return ["esperance"] + (["--jackpot", jackpot] if jackpot else [])


def _menu_simuler(lire: Callable[[str], str]) -> List[str]:
    annees = _demander("Durée en années", "10", lire)
    grilles = _demander("Grilles par tirage", "1", lire)
    return ["simuler", "--annees", annees, "--grilles", grilles]


# ---------------------------------------------------------------------------
# Analyse des arguments
# ---------------------------------------------------------------------------


def _ajouter_bonus(parseur: argparse.ArgumentParser, aide: str) -> None:
    parseur.add_argument(
        "--etoiles", "--chance", "--bonus", dest="bonus", type=int, nargs="+", metavar="N", help=aide
    )


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(
        prog="proba-loto",
        description="Calculateur EuroMillions et Loto : probabilités exactes, grilles, espérance, statistiques réelles.",
        epilog="Exemple : python -m proba_loto probas  |  python -m proba_loto generer -n 5 --strategie anti-partage",
    )
    parseur.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parseur.add_argument("--jeu", default="euromillions", help="euromillions (défaut) ou loto")
    parseur.add_argument("--donnees", metavar="FICHIER", help="historique à utiliser (CSV normalisé, CSV ou ZIP FDJ)")
    sous = parseur.add_subparsers(dest="commande", metavar="commande")

    p = sous.add_parser("probas", help="probabilités exactes de chaque rang")
    p.add_argument("--etoile-plus", action="store_true", help="afficher aussi l'option Étoile+")
    p.add_argument("--grilles", type=int, default=1, help="grilles jouées par tirage (pour les durées)")
    p.set_defaults(fonction=cmd_probas)

    p = sous.add_parser("generer", help="générer des grilles")
    p.add_argument("-n", "--nombre", type=int, default=1, help="nombre de grilles (défaut : 1)")
    p.add_argument("--strategie", choices=STRATEGIES, default="aleatoire")
    p.add_argument("--numeros", type=int, nargs="+", metavar="N", help="numéros favoris à inclure")
    _ajouter_bonus(p, "étoiles (ou N° Chance) favoris à inclure")
    p.add_argument("--graine", type=int, help="graine pour des tirages reproductibles")
    p.add_argument("--details", action="store_true", help="analyser chaque grille")
    p.set_defaults(fonction=cmd_generer)

    p = sous.add_parser("verifier", help="vérifier une grille (simple ou multiple) contre un tirage")
    p.add_argument("grille", help='ex. "3 5 37 44 49 + 5 6"')
    groupe = p.add_mutually_exclusive_group()
    groupe.add_argument("--date", help="date du tirage dans l'historique (défaut : dernier tirage)")
    groupe.add_argument("--tirage", help="combinaison gagnante saisie manuellement")
    p.add_argument("--etoile-plus", action="store_true", help="vérifier aussi l'option Étoile+")
    p.set_defaults(fonction=cmd_verifier)

    p = sous.add_parser("multiple", help="coût, probabilités et gains d'une grille multiple")
    p.add_argument("numeros", type=int, help="nombre de numéros cochés")
    p.add_argument("bonus", type=int, help="nombre d'étoiles (ou de N° Chance) cochés")
    p.set_defaults(fonction=cmd_multiple)

    p = sous.add_parser("esperance", help="espérance de gain selon le jackpot (EuroMillions)")
    p.add_argument("--jackpot", help="montant annoncé, ex. 59M (sans : tableau de 17 à 250 M€)")
    p.add_argument("--ventes", help="grilles jouées en Europe pour ce tirage (défaut : estimation)")
    p.add_argument("--codes-my-million", help="codes My Million en jeu (défaut : 21,6 %% des ventes)")
    p.add_argument("--situation", choices=SITUATIONS, default="normal")
    p.add_argument("--etoile-plus", action="store_true", help="inclure l'option Étoile+ (+1 €)")
    p.add_argument("--grille", help="tenir compte de la popularité de cette grille")
    p.set_defaults(fonction=cmd_esperance)

    p = sous.add_parser("simuler", help="simuler des années de jeu (EuroMillions)")
    p.add_argument("--annees", type=float, default=10)
    p.add_argument("--grilles", type=int, default=1, help="grilles par tirage")
    p.add_argument("--joueurs", type=int, default=1000, help="nombre de joueurs simulés")
    p.add_argument("--jackpot", help="montant du jackpot en cas de gain (défaut : moyenne historique 84 M€)")
    p.add_argument("--etoile-plus", action="store_true")
    p.add_argument("--graine", type=int)
    p.set_defaults(fonction=cmd_simuler)

    p = sous.add_parser("stats", help="fréquences, écarts et test du khi² sur les tirages réels")
    p.add_argument("--depuis", help="ne garder que les tirages depuis cette date")
    p.add_argument("--top", type=int, default=5, help="nombre de valeurs affichées")
    p.set_defaults(fonction=cmd_stats)

    p = sous.add_parser("popularite", help="numéros et étoiles les plus et les moins joués")
    p.add_argument("--top", type=int, default=10)
    p.set_defaults(fonction=cmd_popularite)

    p = sous.add_parser("retro", help="rejouer une grille sur tout l'historique réel")
    p.add_argument("grille")
    p.add_argument("--etoile-plus", action="store_true")
    p.add_argument("--depuis", help="date de début")
    p.set_defaults(fonction=cmd_retro)

    p = sous.add_parser("analyser", help="profil d'une grille et motifs très joués")
    p.add_argument("grille")
    p.set_defaults(fonction=cmd_analyser)

    p = sous.add_parser("maj", help="mettre à jour l'historique depuis fdj.fr")
    p.add_argument("--sortie", help=f"fichier de destination (défaut : cache utilisateur ; données livrées : {DONNEES_EMBARQUEES.name})")
    p.set_defaults(fonction=cmd_maj)

    p = sous.add_parser("menu", help="menu interactif")
    p.set_defaults(fonction=None)
    return parseur


def executer(arguments: Sequence[str], ctx: Optional[Contexte] = None) -> int:
    parseur = construire_parseur()
    args = parseur.parse_args(list(arguments))
    try:
        jeu = obtenir_jeu(args.jeu)
    except KeyError as erreur:
        parseur.error(str(erreur.args[0]))
    if ctx is None:
        ctx = Contexte(jeu, args.donnees)
    else:
        ctx.jeu = jeu
        if args.donnees:
            ctx.donnees = args.donnees
    fonction = getattr(args, "fonction", None)
    if fonction is None:
        return menu(ctx)
    try:
        fonction(args, ctx)
    except (ErreurUtilisateur, ErreurGrille, ErreurHistorique) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 2
    return 0


def main(arguments: Optional[Sequence[str]] = None) -> int:
    for flux in (sys.stdout, sys.stderr):
        reconfigurer = getattr(flux, "reconfigure", None)
        if reconfigurer is not None:
            with contextlib.suppress(ValueError, OSError):  # flux non reconfigurable
                reconfigurer(errors="replace")
    try:
        return executer(sys.argv[1:] if arguments is None else arguments)
    except KeyboardInterrupt:
        print("\nInterrompu.", file=sys.stderr)
        return 130
    except BrokenPipeError:  # pragma: no cover - ex. sortie redirigée vers « head »
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
