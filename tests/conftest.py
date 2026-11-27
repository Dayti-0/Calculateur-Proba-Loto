import pytest

from proba_loto.historique import DONNEES_EMBARQUEES, lire_csv_normalise
from proba_loto.popularite import estimer_popularite


@pytest.fixture(scope="session")
def historique():
    """Historique officiel livré avec le projet (indépendant du cache utilisateur)."""
    return lire_csv_normalise(DONNEES_EMBARQUEES)


@pytest.fixture(scope="session")
def modele(historique):
    return estimer_popularite(historique)


@pytest.fixture(autouse=True)
def cache_isole(tmp_path, monkeypatch):
    """Empêche les tests de lire ou d'écrire le vrai cache utilisateur."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "cache"))
