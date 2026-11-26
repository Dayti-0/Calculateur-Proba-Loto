"""Lecture de l'historique officiel FDJ (brut et normalisé) et données livrées."""

import datetime as dt
import io
import zipfile

import pytest

from proba_loto import historique as h
from proba_loto.jeux import EUROMILLIONS as EM
from proba_loto.probabilites import gain_moyen_theorique

ENTETE_FDJ = ";".join(
    ["annee_numero_de_tirage", "jour_de_tirage", "date_de_tirage", "numéro_de_tirage_dans_le_cycle",
     "date_de_forclusion", "boule_1", "boule_2", "boule_3", "boule_4", "boule_5", "etoile_1", "etoile_2",
     "boules_gagnantes_en_ordre_croissant", "etoiles_gagnantes_en_ordre_croissant"]
    + [c for k in range(1, 14) for c in (
        f"nombre_de_gagnant_au_rang{k}_Euro_Millions_en_france",
        f"nombre_de_gagnant_au_rang{k}_Euro_Millions_en_europe",
        f"rapport_du_rang{k}_Euro_Millions")]
    + [c for k in range(1, 11) for c in (f"nombre_de_gagnant_au_rang{k}_Etoile+", f"rapport_du_rang{k}_Etoile+")]
    + ["numero_My_Million", "numero_Tirage_Exceptionnel_Euro_Million", ""]
)


def _ligne_fdj(date, boules, etoiles, rapport13="4,30"):
    gains = []
    for k in range(1, 14):
        gains += ["1", "5", rapport13 if k == 13 else "10,5"]
    etoile_plus = ["2", "2,3"] * 10
    return ";".join(
        ["26094", "MARDI   ", date, "4", "23/02/2027", *map(str, boules), *map(str, etoiles), "-", "-"]
        + gains + etoile_plus + ["UY 854  8017", "", ""]
    )


CSV_FDJ = "\n".join(
    [
        ENTETE_FDJ,
        _ligne_fdj("24/11/2026", [37, 44, 3, 5, 49], [6, 5]),
        _ligne_fdj("20/11/2026", [8, 21, 24, 36, 49], [1, 8], "5,10"),
        _ligne_fdj("23/09/2016", [1, 2, 3, 4, 5], [11, 1]),  # ancienne formule : ignoré
    ]
)


def test_donnees_livrees(historique):
    assert len(historique) >= 1061
    assert historique[0].date == dt.date(2016, 9, 27)
    dates = [t.date for t in historique]
    assert dates == sorted(dates) and len(set(dates)) == len(dates)
    assert all(t.date.weekday() in (1, 4) for t in historique)  # mardis et vendredis
    assert {(b - a).days for a, b in zip(dates, dates[1:])} <= {3, 4}  # aucun tirage manquant


def test_tirage_du_24_novembre_2026(historique):
    t = h.trouver_tirage(historique, dt.date(2026, 11, 24))
    assert t.numeros == (3, 5, 37, 44, 49) and t.etoiles == (5, 6)
    assert t.rapports[1] == 486463 and t.gagnants_europe[1] == 1 and t.gagnants_france[1] == 0
    assert t.rapports[12] == pytest.approx(4.30) and t.gagnants_europe[12] == 716665
    assert t.rapports_etoile_plus[9] == pytest.approx(2.30)
    assert t.code_my_million == "UY 854 8017"
    assert str(t) == "24/11/2026  03 05 37 44 49  ★  05 06"
    with pytest.raises(h.ErreurHistorique):
        h.trouver_tirage(historique, dt.date(2026, 11, 25))


@pytest.mark.parametrize("encodage", ["latin-1", "utf-8"])
def test_lecture_du_format_officiel(encodage):
    tirages = h.lire_csv_fdj(CSV_FDJ.encode(encodage))
    assert [t.date for t in tirages] == [dt.date(2026, 11, 20), dt.date(2026, 11, 24)]
    dernier = tirages[-1]
    assert dernier.numeros == (3, 5, 37, 44, 49) and dernier.etoiles == (5, 6)
    assert dernier.rapports[12] == pytest.approx(4.30) and dernier.rapports[0] == pytest.approx(10.5)
    assert dernier.gagnants_europe == (5,) * 13 and dernier.gagnants_france == (1,) * 13
    assert dernier.gagnants_etoile_plus == (2,) * 10
    assert dernier.code_my_million == "UY 854 8017"


def test_format_officiel_invalide():
    with pytest.raises(h.ErreurHistorique, match="colonne"):
        h.lire_csv_fdj("date_de_tirage;boule_1\n24/11/2026;1\n")
    with pytest.raises(h.ErreurHistorique, match="invalide"):
        h.lire_csv_fdj("\n".join([ENTETE_FDJ, _ligne_fdj("24/11/2026", [1, 2, 3, 4, 51], [1, 2])]))
    with pytest.raises(h.ErreurHistorique, match="date"):
        h.lire_csv_fdj("\n".join([ENTETE_FDJ, _ligne_fdj("hier", [1, 2, 3, 4, 5], [1, 2])]))
    with pytest.raises(h.ErreurHistorique, match="vide"):
        h.lire_csv_fdj("")


def test_archive_zip_et_detection_de_format(tmp_path):
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("euromillions_202002.csv", CSV_FDJ.encode("latin-1"))
    contenu = tampon.getvalue()
    assert len(h.lire_archive(contenu)) == 2
    (tmp_path / "a.zip").write_bytes(contenu)
    (tmp_path / "b.csv").write_bytes(CSV_FDJ.encode("utf-8"))
    tirages = h.lire_fichier(tmp_path / "a.zip")
    assert h.lire_fichier(tmp_path / "b.csv") == tirages
    h.ecrire_csv_normalise(tirages, tmp_path / "normalise.csv")
    assert h.lire_fichier(tmp_path / "normalise.csv") == tirages
    vide = io.BytesIO()
    with zipfile.ZipFile(vide, "w") as archive:
        archive.writestr("lisezmoi.txt", "rien")
    with pytest.raises(h.ErreurHistorique, match="aucun fichier CSV"):
        h.lire_archive(vide.getvalue())


def test_aller_retour_du_format_normalise(historique, tmp_path):
    chemin = tmp_path / "copie.csv"
    h.ecrire_csv_normalise(historique, chemin)
    assert h.lire_csv_normalise(chemin) == historique
    with pytest.raises(h.ErreurHistorique, match="colonnes absentes"):
        (tmp_path / "faux.csv").write_text("date,n1\n2026-11-24,1\n", encoding="utf-8")
        h.lire_csv_normalise(tmp_path / "faux.csv")


def test_charger_prefere_le_plus_recent(historique, tmp_path, monkeypatch):
    cache = tmp_path / "cache.csv"
    monkeypatch.setattr(h, "fichier_cache", lambda: cache)
    assert h.charger()[-1].date == historique[-1].date  # pas de cache : données livrées
    h.ecrire_csv_normalise(historique[:100], cache)
    assert len(h.charger()) == len(historique)  # cache plus ancien : ignoré
    recent = h.lire_csv_fdj(CSV_FDJ)[1]
    plus_recent = h.TirageHistorique(**{**recent.__dict__, "date": dt.date(2030, 1, 1)})
    h.ecrire_csv_normalise(list(historique) + [plus_recent], cache)
    assert h.charger()[-1].date == dt.date(2030, 1, 1)
    assert len(h.charger(h.DONNEES_EMBARQUEES)) == len(historique)


def test_mise_a_jour_sans_reseau(tmp_path, monkeypatch):
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as archive:
        archive.writestr("x.csv", CSV_FDJ)
    appels = []

    def faux_telechargement(urls, delai):
        appels.append(urls[0])
        return tampon.getvalue()

    monkeypatch.setattr(h, "_telecharger", faux_telechargement)
    chemin, tirages = h.mettre_a_jour(tmp_path / "maj.csv")
    assert len(appels) == len(h.SOURCES_FDJ)
    assert chemin.exists() and len(tirages) == 2
    assert h.lire_csv_normalise(chemin) == tirages


def test_gains_moyens_reels_conformes_a_la_repartition(historique):
    """Les rapports observés depuis février 2020 valident les parts du règlement."""
    recents = [t for t in historique if t.date >= dt.date(2020, 2, 4)]
    for numero in range(5, 14):
        observes = [t.rapports[numero - 1] for t in recents if t.gagnants_europe[numero - 1] > 0]
        moyenne = sum(observes) / len(observes)
        theorique = gain_moyen_theorique(EM, EM.gains.rang(numero))
        assert moyenne == pytest.approx(theorique, rel=0.10), numero
