"""Mise en forme à la française."""

from fractions import Fraction

from proba_loto import affichage as fmt
from proba_loto.analyse import analyser_grille, bornes_somme, motifs_populaires, plus_longue_suite
from proba_loto.grilles import Grille
from proba_loto.jeux import EUROMILLIONS as EM


def test_nombres():
    assert fmt.entier(139_838_160) == "139 838 160"
    assert fmt.entier(999.6) == "1 000"
    assert fmt.decimal(1234.5) == "1 234,50"
    assert fmt.euros(2.5) == "2,50 €"
    assert fmt.euros(17_000_000) == "17 000 000 €"
    assert fmt.montant_compact(59e6) == "59 M€"
    assert fmt.montant_compact(1.5e6) == "1,5 M€"
    assert fmt.montant_compact(950) == "950,00 €"


def test_pourcentages_et_chances():
    assert fmt.pourcentage(0.0771) == "7,71 %"
    assert fmt.pourcentage(0.6) == "60 %"
    assert fmt.pourcentage(Fraction(1, 139_838_160)) == "0,000000715 %"
    assert fmt.pourcentage(0) == "0 %"
    assert fmt.chances(Fraction(1, 139_838_160)) == "1 sur 139 838 160"
    assert fmt.chances(1 / 21.9) == "1 sur 21,9"
    assert fmt.chances(1 / 224) == "1 sur 224"
    assert fmt.chances(1 / 12.97, decimales=2) == "1 sur 12,97"
    assert fmt.chances(1 / 5.7, phrase=True) == "1 chance sur 5,7"
    assert fmt.chances(0) == "impossible"


def test_durees_et_tableau():
    assert fmt.duree(139_838_160, 2) == "1 340 024 ans"
    assert fmt.duree(10, 2) == "5 semaines"
    assert fmt.duree(1, 2) == "1 tirage"
    texte = fmt.tableau([["a", "1"], ["bb", "22"]], ["Col", "N"])
    assert texte.splitlines() == ["  Col   N", "  ---  --", "  a     1", "  bb   22"]
    assert fmt.tableau([]) == ""


def test_analyse_de_grille():
    assert plus_longue_suite([1, 2, 3, 10, 11]) == 3
    assert plus_longue_suite([]) == 0
    motifs = {m.code for m in motifs_populaires(Grille.depuis_texte(EM, "7 17 27 37 47 + 1 2"))}
    assert {"progression", "finale"} <= motifs
    dernier = Grille.depuis_texte(EM, "3 5 37 44 49 + 5 6")
    motifs = {m.code for m in motifs_populaires(Grille.depuis_texte(EM, "3 5 37 40 42 + 1 2"), dernier)}
    assert "dernier-tirage" in motifs
    assert {m.code for m in motifs_populaires(Grille.depuis_texte(EM, "3 9 15 27 42 + 1 2"))} == {"multiples"}
    analyse = analyser_grille(Grille.depuis_texte(EM, "3 5 37 44 49 + 5 6"))
    assert analyse.somme == 138 and analyse.pairs == 1 and analyse.impairs == 4
    assert analyse.bas == 2 and analyse.hauts == 3
    assert 0 < analyse.rang_centile_somme < 1
    assert analyse.indice_popularite is None
    assert bornes_somme(EM) == (106, 149)
