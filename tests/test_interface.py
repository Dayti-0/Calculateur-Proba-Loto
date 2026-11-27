"""Interface graphique : génération de la page et cohérence avec la bibliothèque."""

import json
import math
import re

import pytest

from proba_loto import interface
from proba_loto.historique import DONNEES_EMBARQUEES, lire_csv_normalise


def _bloc(page, identifiant):
    motif = rf'<script id="{identifiant}" type="application/json">(.*?)</script>'
    return re.search(motif, page, re.S).group(1)


@pytest.fixture(scope="module")
def page(historique):
    return interface.construire_page(historique)


def test_page_complete_et_autonome(page, historique):
    assert page.startswith("<!doctype html>")
    assert "/*REGLES*/" not in page and "/*HISTORIQUE*/" not in page
    regles = json.loads(_bloc(page, "donnees-regles"))
    assert regles["jeu"]["nom"] == "EuroMillions"
    assert len(regles["jeu"]["gains"]["rangs"]) == 13 and len(regles["jeu"]["options"][0]["rangs"]) == 10
    assert regles["jeu"]["prixGrille"] == 2.5 and regles["jeu"]["multipleCombinaisonsMax"] == 396
    assert len(regles["popularite"]["numeros"]) == 50 and len(regles["popularite"]["etoiles"]) == 12
    assert regles["popularite"]["correlation"] > 0.9
    histo = json.loads(_bloc(page, "donnees-historique"))
    assert len(histo["lignes"]) == len(historique)
    assert all(len(ligne) == len(interface.COLONNES_HISTORIQUE) == 54 for ligne in histo["lignes"])
    assert histo["lignes"][0][:8] == [20160927, 6, 9, 13, 39, 41, 2, 12]
    assert "loto" not in page.lower().replace("proba_loto", "").replace("proba-loto", "")


def test_page_sans_historique_integre(historique):
    page = interface.construire_page(historique, integrer_historique=False)
    assert _bloc(page, "donnees-historique") == ""
    assert "fetch('historique.json')" in page


def test_fragment_publiable(page):
    fragment = interface.extraire_fragment(page)
    for balise in ("<!doctype", "<html", "<head>", "</head>", "<body", "</body>"):
        assert balise not in fragment.lower()
    assert fragment.startswith("<title>Calculateur EuroMillions</title>")
    assert "<style>" in fragment and "window.CalculateurEuroMillions" in fragment
    with pytest.raises(ValueError):
        interface.extraire_fragment("<html></html>")


def _sans_donnees(page):
    return re.sub(r'(<script id="donnees-[a-z]+" type="application/json">).*?(</script>)', r"\1\2", page, flags=re.S)


def _proches(a, b):
    """Égalité tolérante pour les nombres flottants (calculs pouvant varier d'un système à l'autre)."""
    if isinstance(a, float) or isinstance(b, float):
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_proches(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_proches(x, y) for x, y in zip(a, b))
    return a == b


def test_page_livree_a_jour():
    """interface.html (racine du dépôt) doit être régénérée après toute modification."""
    if not interface.INTERFACE_DEPOT.exists():
        pytest.skip("page absente (installation sans le dépôt)")
    livree = interface.INTERFACE_DEPOT.read_text(encoding="utf-8")
    attendu = interface.construire_page(lire_csv_normalise(DONNEES_EMBARQUEES))
    message = (
        "interface.html n'est pas à jour : lancez « python -m proba_loto --donnees "
        "proba_loto/data/euromillions.csv interface --sortie interface.html --sans-ouvrir »"
    )
    assert _sans_donnees(livree) == _sans_donnees(attendu), message
    assert _proches(json.loads(_bloc(livree, "donnees-regles")), json.loads(_bloc(attendu, "donnees-regles"))), message
    assert json.loads(_bloc(livree, "donnees-historique")) == json.loads(_bloc(attendu, "donnees-historique")), message


def test_ecriture_et_ouverture(tmp_path, historique, monkeypatch):
    chemin = interface.ecrire_interface(tmp_path / "x.html", historique)
    assert chemin.read_text(encoding="utf-8").startswith("<!doctype html>")
    defaut = interface.ecrire_interface(None, historique)
    assert defaut.name == "interface.html" and defaut.parent.name == "proba-loto"
    ouverts = []
    monkeypatch.setattr(interface.webbrowser, "open", lambda url: ouverts.append(url) or True)
    assert interface.ouvrir_interface(chemin) is True
    assert ouverts == [chemin.resolve().as_uri()]
    monkeypatch.setattr(interface.webbrowser, "open", lambda url: False)
    assert interface.ouvrir_interface(chemin) is False


def test_modele_invalide(tmp_path, monkeypatch, historique):
    faux = tmp_path / "modele.html"
    faux.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(interface, "MODELE", faux)
    with pytest.raises(ValueError):
        interface.construire_page(historique)
