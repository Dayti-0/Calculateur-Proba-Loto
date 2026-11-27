"""Interface en ligne de commande et menu interactif."""

import pytest

from proba_loto import cli
from proba_loto.historique import DONNEES_EMBARQUEES

DONNEES = ["--donnees", str(DONNEES_EMBARQUEES)]


def lancer(capsys, *arguments):
    code = cli.main(list(arguments))
    sortie = capsys.readouterr()
    return code, sortie.out, sortie.err


def test_probas(capsys):
    code, out, _ = lancer(capsys, "probas", "--etoile-plus")
    assert code == 0
    assert "1 sur 139 838 160" in out and "1 sur 12,97" in out
    assert "Option Étoile+" in out and "1 sur 4,73" in out
    assert "1 340 024 ans" in out


def test_generer(capsys):
    code, out, _ = lancer(capsys, *DONNEES, "generer", "-n", "3", "--strategie", "anti-partage", "--graine", "1")
    assert code == 0 and out.count("★") == 3 and "indice de popularité" in out
    code, out, _ = lancer(capsys, "generer", "--numeros", "7", "13", "--etoiles", "3", "--graine", "1", "--details")
    assert code == 0 and "07" in out and "Somme des numéros" in out
    code, _, err = lancer(capsys, "generer", "--numeros", "7", "7")
    assert code == 2 and "double" in err


def test_verifier(capsys):
    code, out, _ = lancer(capsys, *DONNEES, "verifier", "3 5 12 44 50 + 5 9", "--etoile-plus")
    assert code == 0
    assert "24/11/2026" in out and "rang 9" in out and "12,20 €" in out and "2,90 €" in out
    code, out, _ = lancer(capsys, *DONNEES, "verifier", "3 5 37 44 49 10 + 5 6 9", "--date", "24/11/2026")
    assert code == 0 and "18 grilles simples" in out and "montant non publié" in out
    code, out, _ = lancer(capsys, "verifier", "1 2 3 4 5 + 1 2", "--tirage", "1 2 3 40 41 + 1 9")
    assert code == 0 and "rang 9" in out and "gain moyen estimé" in out
    code, _, err = lancer(capsys, *DONNEES, "verifier", "1 2 3 4 5 + 1 2", "--date", "25/11/2026")
    assert code == 2 and "aucun tirage" in err


def test_multiple(capsys):
    code, out, _ = lancer(capsys, "multiple", "7", "3")
    assert code == 0 and "63 grilles simples" in out and "157,50 €" in out and "220,50 €" in out
    assert "1 sur 2 219 653" in out
    code, _, err = lancer(capsys, "multiple", "8", "5")
    assert code == 2 and "396" in err


def test_esperance(capsys):
    code, out, _ = lancer(capsys, "esperance")
    assert code == 0 and "250 M€" in out and "jamais rentable" in out
    code, out, _ = lancer(capsys, *DONNEES, "esperance", "--jackpot", "59M", "--grille", "36 41 43 46 48 + 11 12")
    assert code == 0 and "indice de popularité 0,27" in out and "Perte moyenne" in out
    code, out, _ = lancer(capsys, "esperance", "--jackpot", "250M", "--situation", "doit-etre-gagne", "--ventes", "70M")
    assert code == 0 and "Espérance positive" in out
    code, out, _ = lancer(capsys, "esperance", "--situation", "plafond")
    assert code == 0 and "jackpot 250 M€" in out and "Excédent du plafond" in out
    code, _, err = lancer(capsys, "esperance", "--jackpot", "300M")
    assert code == 2 and "plafond" in err


def test_simuler(capsys):
    code, out, _ = lancer(capsys, "simuler", "--annees", "1", "--joueurs", "20", "--graine", "1")
    assert code == 0 and "20 joueurs" in out and "médiane" in out
    code, _, err = lancer(capsys, "simuler", "--joueurs", "0")
    assert code == 2


def test_stats_popularite_retro_analyser(capsys):
    code, out, _ = lancer(capsys, *DONNEES, "stats", "--top", "3")
    assert code == 0 and "1 061 tirages" in out and "khi²" in out and "Les plus sorties" in out
    code, out, _ = lancer(capsys, *DONNEES, "stats", "--depuis", "01/01/2026")
    assert code == 0 and "01/01/2026" not in out
    code, out, _ = lancer(capsys, *DONNEES, "popularite")
    assert code == 0 and "7 (+25 %)" in out and "Validation" in out
    code, out, _ = lancer(capsys, *DONNEES, "retro", "3 5 37 44 49 + 5 6", "--depuis", "2026-01-01")
    assert code == 0 and "Mise totale" in out and "montant non publié" in out
    code, out, _ = lancer(capsys, *DONNEES, "analyser", "1 2 3 4 5 + 1 2")
    assert code == 0 and "5 numéros consécutifs" in out and "dates d'anniversaire" in out
    code, _, err = lancer(capsys, "analyser", "1 2 3 + 1 2")
    assert code == 2


def test_maj(capsys, monkeypatch, tmp_path, historique):
    def fausse_maj(sortie):
        return tmp_path / "x.csv", historique

    monkeypatch.setattr(cli, "mettre_a_jour", fausse_maj)
    code, out, _ = lancer(capsys, "maj")
    assert code == 0 and "1 061 tirages" in out


def test_commande_inconnue(capsys):
    with pytest.raises(SystemExit) as sortie:
        cli.main(["inconnue"])
    assert sortie.value.code == 2


@pytest.mark.parametrize(
    "texte, attendu",
    [("59M", 59e6), ("59 M€", 59e6), ("1,5 M", 1.5e6), ("17 000 000", 17e6), ("250m", 250e6),
     ("2k", 2e3), ("1.234,5", 1234.5), ("1,2 milliard", 1.2e9)],
)
def test_lire_montant(texte, attendu):
    assert cli.lire_montant(texte) == pytest.approx(attendu)


def test_lire_montant_et_date_invalides():
    with pytest.raises(cli.ErreurUtilisateur):
        cli.lire_montant("beaucoup")
    with pytest.raises(cli.ErreurUtilisateur):
        cli.lire_date("demain")
    assert cli.lire_date("24/11/2026") == cli.lire_date("2026-11-24")


def _saisies(*reponses):
    file = list(reponses)

    def lire(_question):
        if not file:
            raise EOFError
        return file.pop(0)

    return lire


def test_menu_interactif(capsys):
    ctx = cli.Contexte(cli.EUROMILLIONS, str(DONNEES_EMBARQUEES))
    code = cli.menu(ctx, _saisies("4", "7", "3", "", "1", "", "99", "0"))
    out = capsys.readouterr().out
    assert code == 0
    assert "63 grilles simples" in out  # grille multiple 7 × 3
    assert "1 sur 139 838 160" in out and "Option Étoile+" in out
    assert "Choix invalide" in out and "Au revoir" in out
    assert "Loto" not in out


def test_menu_robuste_a_la_fin_de_saisie(capsys):
    # Ancien bug : EOFError non géré dans le menu (trace d'erreur).
    ctx = cli.Contexte(cli.EUROMILLIONS, str(DONNEES_EMBARQUEES))
    assert cli.menu(ctx, _saisies("1")) == 0
    assert "Au revoir" in capsys.readouterr().out


def test_sans_commande_ouvre_l_interface(monkeypatch, capsys):
    ouvertures = []
    monkeypatch.setattr(cli, "ouvrir_interface", lambda chemin: ouvertures.append(chemin) or True)
    assert cli.main([]) == 0
    assert len(ouvertures) == 1 and ouvertures[0].name == "interface.html" and ouvertures[0].exists()
    assert "Interface ouverte" in capsys.readouterr().out


def test_sans_navigateur_bascule_sur_le_menu(monkeypatch, capsys):
    def interrompu(_question):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "ouvrir_interface", lambda chemin: False)
    monkeypatch.setattr("builtins.input", interrompu)
    assert cli.main([]) == 0
    sortie = capsys.readouterr().out
    assert "Aucun navigateur" in sortie and "Au revoir" in sortie


def test_commande_interface(capsys, tmp_path, monkeypatch):
    chemin = tmp_path / "page.html"
    code, out, _ = lancer(capsys, *DONNEES, "interface", "--sortie", str(chemin), "--sans-ouvrir")
    assert code == 0 and chemin.exists() and str(chemin) in out
    assert "Calculateur EuroMillions" in chemin.read_text(encoding="utf-8")
    monkeypatch.setattr(cli, "ouvrir_interface", lambda c: False)
    code, out, _ = lancer(capsys, *DONNEES, "interface", "--sortie", str(chemin))
    assert code == 0 and "Aucun navigateur" in out
