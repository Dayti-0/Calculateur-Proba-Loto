"""Historique officiel des tirages EuroMillions publié par la FDJ.

Les archives officielles (https://www.fdj.fr/jeux-de-tirage/euromillions-my-million/historique)
sont des fichiers CSV séparés par des « ; », encodés en UTF-8 ou ISO-8859-1
selon les années. Ce module sait :

* lire ces fichiers bruts (ou les archives ZIP) ;
* les convertir en un CSV normalisé, compact et versionnable
  (``proba_loto/data/euromillions.csv``, livré avec le projet) ;
* les retélécharger pour mettre l'historique à jour (commande ``maj``).

Seuls les tirages de la formule actuelle (5 numéros sur 50 et 2 étoiles sur 12,
depuis le 27 septembre 2016) sont pris en charge.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import os
import sys
import unicodedata
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .grilles import Grille
from .jeux import EUROMILLIONS

__all__ = [
    "TirageHistorique",
    "ErreurHistorique",
    "DEBUT_FORMULE_ACTUELLE",
    "DONNEES_EMBARQUEES",
    "SOURCES_FDJ",
    "lire_csv_fdj",
    "lire_archive",
    "lire_csv_normalise",
    "ecrire_csv_normalise",
    "lire_fichier",
    "charger",
    "fichier_cache",
    "telecharger_historique",
    "mettre_a_jour",
    "trouver_tirage",
]

DEBUT_FORMULE_ACTUELLE = dt.date(2016, 9, 27)
"""Premier tirage avec 12 étoiles (formule toujours en vigueur)."""

DONNEES_EMBARQUEES = Path(__file__).resolve().parent / "data" / "euromillions.csv"

NB_RANGS = 13
NB_RANGS_ETOILE_PLUS = 10

_API_FDJ = "https://www.sto.api.fdj.fr/anonymous/service-draw-info/v3/documentations/"
_MEDIA_FDJ = "https://media.fdj.fr/static-draws/csv/euromillions/"

SOURCES_FDJ: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "27/09/2016 – 26/02/2019",
        (_API_FDJ + "1a2b3c4d-9876-4562-b3fc-2c963f66afc6", _MEDIA_FDJ + "euromillions_201609.zip"),
    ),
    (
        "01/03/2019 – 31/01/2020",
        (_API_FDJ + "1a2b3c4d-9876-4562-b3fc-2c963f66afd6", _MEDIA_FDJ + "euromillions_201902.zip"),
    ),
    (
        "depuis le 04/02/2020",
        (_API_FDJ + "1a2b3c4d-9876-4562-b3fc-2c963f66afe6", _MEDIA_FDJ + "euromillions_202002.zip"),
    ),
)
"""Archives officielles couvrant la formule actuelle (URL principale puis URL de secours)."""


class ErreurHistorique(ValueError):
    """Fichier d'historique illisible ou incohérent."""


@dataclass(frozen=True)
class TirageHistorique:
    """Un tirage réel et ses rapports officiels (montants en euros)."""

    date: dt.date
    numeros: Tuple[int, ...]
    etoiles: Tuple[int, ...]
    gagnants_europe: Tuple[int, ...]
    gagnants_france: Tuple[int, ...]
    rapports: Tuple[float, ...]
    """Gain unitaire par rang (0 si aucun gagnant à ce rang)."""
    gagnants_etoile_plus: Tuple[int, ...] = (0,) * NB_RANGS_ETOILE_PLUS
    rapports_etoile_plus: Tuple[float, ...] = (0.0,) * NB_RANGS_ETOILE_PLUS
    code_my_million: str = ""

    @property
    def combinaison(self) -> Grille:
        return Grille.simple(EUROMILLIONS, self.numeros, self.etoiles)

    def __str__(self) -> str:
        return f"{self.date:%d/%m/%Y}  {self.combinaison}"


# ---------------------------------------------------------------------------
# Lecture du format officiel FDJ
# ---------------------------------------------------------------------------


def _decoder(contenu: Union[bytes, str]) -> str:
    if isinstance(contenu, str):
        return contenu
    for encodage in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return contenu.decode(encodage)
        except UnicodeDecodeError:
            continue
    raise ErreurHistorique("encodage du fichier non reconnu")  # pragma: no cover


def _normaliser_entete(nom: str) -> str:
    nom = unicodedata.normalize("NFKD", nom.strip().lower())
    return "".join(c for c in nom if not unicodedata.combining(c) and c != "�")


def _entier(valeur: str) -> int:
    valeur = valeur.strip().replace(" ", "")
    return int(valeur) if valeur else 0


def _montant(valeur: str) -> float:
    valeur = valeur.strip().replace(" ", "").replace(",", ".")
    return float(valeur) if valeur else 0.0


def _date(valeur: str) -> dt.date:
    valeur = valeur.strip()
    for format_date in ("%d/%m/%Y", "%Y%m%d", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(valeur, format_date).date()
        except ValueError:
            continue
    raise ErreurHistorique(f"date illisible : « {valeur} »")


def _valider(tirage: TirageHistorique, origine: str) -> None:
    numeros, etoiles = tirage.numeros, tirage.etoiles
    if (
        len(set(numeros)) != 5
        or not all(1 <= n <= 50 for n in numeros)
        or len(set(etoiles)) != 2
        or not all(1 <= e <= 12 for e in etoiles)
    ):
        raise ErreurHistorique(f"{origine} : tirage du {tirage.date} invalide {numeros} {etoiles}")


def lire_csv_fdj(contenu: Union[bytes, str], origine: str = "CSV FDJ") -> List[TirageHistorique]:
    """Lit un fichier d'historique au format officiel de la FDJ."""
    texte = _decoder(contenu)
    lecteur = csv.reader(io.StringIO(texte), delimiter=";")
    try:
        entete = [_normaliser_entete(c) for c in next(lecteur)]
    except StopIteration:
        raise ErreurHistorique(f"{origine} : fichier vide") from None
    index = {nom: i for i, nom in enumerate(entete) if nom}

    def colonne(nom: str, obligatoire: bool = True) -> Optional[int]:
        if nom in index:
            return index[nom]
        if obligatoire:
            raise ErreurHistorique(f"{origine} : colonne « {nom} » absente")
        return None

    i_date = colonne("date_de_tirage")
    i_boules = [colonne(f"boule_{k}") for k in range(1, 6)]
    i_etoiles = [colonne(f"etoile_{k}") for k in range(1, 3)]
    i_fr = [colonne(f"nombre_de_gagnant_au_rang{k}_euro_millions_en_france") for k in range(1, 14)]
    i_eu = [colonne(f"nombre_de_gagnant_au_rang{k}_euro_millions_en_europe") for k in range(1, 14)]
    i_rap = [colonne(f"rapport_du_rang{k}_euro_millions") for k in range(1, 14)]
    i_ep_g = [colonne(f"nombre_de_gagnant_au_rang{k}_etoile+", False) for k in range(1, 11)]
    i_ep_r = [colonne(f"rapport_du_rang{k}_etoile+", False) for k in range(1, 11)]
    i_code = colonne("numero_my_million", False)

    def valeur(ligne: Sequence[str], i: Optional[int]) -> str:
        return ligne[i] if i is not None and i < len(ligne) else ""

    tirages = []
    for numero_ligne, ligne in enumerate(lecteur, start=2):
        if not ligne or not "".join(ligne).strip():
            continue
        try:
            date = _date(valeur(ligne, i_date))
            if date < DEBUT_FORMULE_ACTUELLE:
                continue
            tirage = TirageHistorique(
                date=date,
                numeros=tuple(sorted(_entier(valeur(ligne, i)) for i in i_boules)),
                etoiles=tuple(sorted(_entier(valeur(ligne, i)) for i in i_etoiles)),
                gagnants_europe=tuple(_entier(valeur(ligne, i)) for i in i_eu),
                gagnants_france=tuple(_entier(valeur(ligne, i)) for i in i_fr),
                rapports=tuple(_montant(valeur(ligne, i)) for i in i_rap),
                gagnants_etoile_plus=tuple(_entier(valeur(ligne, i)) for i in i_ep_g),
                rapports_etoile_plus=tuple(_montant(valeur(ligne, i)) for i in i_ep_r),
                code_my_million=" ".join(valeur(ligne, i_code).split()),
            )
        except ValueError as erreur:
            raise ErreurHistorique(f"{origine}, ligne {numero_ligne} : {erreur}") from None
        _valider(tirage, f"{origine}, ligne {numero_ligne}")
        tirages.append(tirage)
    return sorted(tirages, key=lambda t: t.date)


def lire_archive(contenu: bytes, origine: str = "archive FDJ") -> List[TirageHistorique]:
    """Lit une archive ZIP de la FDJ (ou directement un CSV)."""
    if not zipfile.is_zipfile(io.BytesIO(contenu)):
        return lire_csv_fdj(contenu, origine)
    tirages: List[TirageHistorique] = []
    with zipfile.ZipFile(io.BytesIO(contenu)) as archive:
        noms = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not noms:
            raise ErreurHistorique(f"{origine} : aucun fichier CSV dans l'archive")
        for nom in noms:
            tirages.extend(lire_csv_fdj(archive.read(nom), f"{origine}/{nom}"))
    return sorted(tirages, key=lambda t: t.date)


# ---------------------------------------------------------------------------
# Format normalisé (livré avec le projet)
# ---------------------------------------------------------------------------

_COLONNES = (
    ["date", "n1", "n2", "n3", "n4", "n5", "e1", "e2"]
    + [f"gagnants_europe_r{k}" for k in range(1, NB_RANGS + 1)]
    + [f"gagnants_france_r{k}" for k in range(1, NB_RANGS + 1)]
    + [f"rapport_r{k}" for k in range(1, NB_RANGS + 1)]
    + [f"gagnants_etoile_plus_r{k}" for k in range(1, NB_RANGS_ETOILE_PLUS + 1)]
    + [f"rapport_etoile_plus_r{k}" for k in range(1, NB_RANGS_ETOILE_PLUS + 1)]
    + ["code_my_million"]
)


def _texte_montant(valeur: float) -> str:
    return f"{valeur:.2f}".rstrip("0").rstrip(".") if valeur else "0"


def ecrire_csv_normalise(tirages: Iterable[TirageHistorique], chemin: Union[str, Path]) -> None:
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(chemin.suffix + ".tmp")
    with open(temporaire, "w", encoding="utf-8", newline="") as fichier:
        ecrivain = csv.writer(fichier, lineterminator="\n")
        ecrivain.writerow(_COLONNES)
        for t in sorted(tirages, key=lambda t: t.date):
            ecrivain.writerow(
                [t.date.isoformat(), *t.numeros, *t.etoiles, *t.gagnants_europe, *t.gagnants_france]
                + [_texte_montant(r) for r in t.rapports]
                + list(t.gagnants_etoile_plus)
                + [_texte_montant(r) for r in t.rapports_etoile_plus]
                + [t.code_my_million]
            )
    os.replace(temporaire, chemin)


def lire_csv_normalise(chemin: Union[str, Path]) -> List[TirageHistorique]:
    chemin = Path(chemin)
    tirages = []
    with open(chemin, encoding="utf-8", newline="") as fichier:
        lecteur = csv.DictReader(fichier)
        manquantes = set(_COLONNES) - set(lecteur.fieldnames or ())
        if manquantes:
            raise ErreurHistorique(f"{chemin} : colonnes absentes : {', '.join(sorted(manquantes))}")
        for numero_ligne, ligne in enumerate(lecteur, start=2):
            try:
                tirage = TirageHistorique(
                    date=dt.date.fromisoformat(ligne["date"]),
                    numeros=tuple(sorted(int(ligne[f"n{k}"]) for k in range(1, 6))),
                    etoiles=tuple(sorted(int(ligne[f"e{k}"]) for k in range(1, 3))),
                    gagnants_europe=tuple(int(ligne[f"gagnants_europe_r{k}"]) for k in range(1, 14)),
                    gagnants_france=tuple(int(ligne[f"gagnants_france_r{k}"]) for k in range(1, 14)),
                    rapports=tuple(float(ligne[f"rapport_r{k}"]) for k in range(1, 14)),
                    gagnants_etoile_plus=tuple(
                        int(ligne[f"gagnants_etoile_plus_r{k}"]) for k in range(1, 11)
                    ),
                    rapports_etoile_plus=tuple(
                        float(ligne[f"rapport_etoile_plus_r{k}"]) for k in range(1, 11)
                    ),
                    code_my_million=ligne["code_my_million"],
                )
            except (TypeError, ValueError) as erreur:
                raise ErreurHistorique(f"{chemin}, ligne {numero_ligne} : {erreur}") from None
            _valider(tirage, f"{chemin}, ligne {numero_ligne}")
            tirages.append(tirage)
    return sorted(tirages, key=lambda t: t.date)


def lire_fichier(chemin: Union[str, Path]) -> List[TirageHistorique]:
    """Lit un historique : CSV normalisé, CSV FDJ brut ou archive ZIP FDJ."""
    chemin = Path(chemin)
    contenu = chemin.read_bytes()
    if zipfile.is_zipfile(io.BytesIO(contenu)):
        return lire_archive(contenu, str(chemin))
    premiere_ligne = _decoder(contenu).split("\n", 1)[0]
    if ";" in premiere_ligne:
        return lire_csv_fdj(contenu, str(chemin))
    return lire_csv_normalise(chemin)


# ---------------------------------------------------------------------------
# Chargement avec cache utilisateur
# ---------------------------------------------------------------------------


def fichier_cache() -> Path:
    """Emplacement de l'historique mis à jour par ``maj`` (hors du dossier d'installation)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "proba-loto" / "euromillions.csv"


_MEMOIRE: Dict[Tuple[str, int, int, int], List[TirageHistorique]] = {}


def _lire_avec_memoire(chemin: Path) -> List[TirageHistorique]:
    etat = chemin.stat()
    cle = (str(chemin.resolve()), etat.st_mtime_ns, etat.st_size, etat.st_ino)
    if cle not in _MEMOIRE:
        _MEMOIRE[cle] = lire_fichier(chemin)
    return _MEMOIRE[cle]


def charger(chemin: Optional[Union[str, Path]] = None) -> List[TirageHistorique]:
    """Charge l'historique le plus récent disponible.

    Ordre : fichier explicitement fourni, sinon le plus récent entre le cache
    utilisateur (mis à jour par ``maj``) et les données livrées avec le projet.
    """
    if chemin is not None:
        return list(_lire_avec_memoire(Path(chemin)))
    candidats: List[List[TirageHistorique]] = []
    for possible in (fichier_cache(), DONNEES_EMBARQUEES):
        if possible.is_file():
            try:
                tirages = _lire_avec_memoire(possible)
            except (OSError, ErreurHistorique):
                continue
            if tirages:
                candidats.append(tirages)
    if not candidats:
        raise ErreurHistorique(
            "aucun historique disponible : lancez « python -m proba_loto maj » pour le télécharger"
        )
    def recence(tirages: List[TirageHistorique]) -> Tuple[dt.date, int]:
        return tirages[-1].date, len(tirages)

    plus_recent = max(candidats, key=recence)
    return list(plus_recent)


def trouver_tirage(tirages: Sequence[TirageHistorique], date: dt.date) -> TirageHistorique:
    for tirage in tirages:
        if tirage.date == date:
            return tirage
    raise ErreurHistorique(f"aucun tirage EuroMillions le {date:%d/%m/%Y} dans l'historique")


# ---------------------------------------------------------------------------
# Téléchargement depuis la FDJ
# ---------------------------------------------------------------------------


def _telecharger(urls: Sequence[str], delai: float) -> bytes:
    erreurs = []
    for url in urls:
        requete = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (proba-loto)"})
        try:
            with urllib.request.urlopen(requete, timeout=delai) as reponse:  # noqa: S310 (URL fixe https)
                return bytes(reponse.read())
        except OSError as erreur:
            erreurs.append(f"{url} : {erreur}")
    raise ErreurHistorique("téléchargement impossible :\n  " + "\n  ".join(erreurs))


def telecharger_historique(delai: float = 60) -> List[TirageHistorique]:
    """Télécharge et fusionne les archives officielles de la formule actuelle."""
    tous: Dict[dt.date, TirageHistorique] = {}
    for libelle, urls in SOURCES_FDJ:
        for tirage in lire_archive(_telecharger(urls, delai), f"archive FDJ {libelle}"):
            tous[tirage.date] = tirage
    if not tous:
        raise ErreurHistorique("les archives téléchargées ne contiennent aucun tirage")
    return [tous[d] for d in sorted(tous)]


def mettre_a_jour(
    sortie: Optional[Union[str, Path]] = None, delai: float = 60
) -> Tuple[Path, List[TirageHistorique]]:
    """Télécharge l'historique officiel et l'enregistre au format normalisé."""
    tirages = telecharger_historique(delai)
    chemin = Path(sortie) if sortie is not None else fichier_cache()
    ecrire_csv_normalise(tirages, chemin)
    _MEMOIRE.clear()
    return chemin, tirages
