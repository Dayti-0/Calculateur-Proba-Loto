"""Parité des calculs JavaScript de l'interface avec la bibliothèque Python.

La page est ouverte dans Chromium (Playwright pour Node) ; le test est ignoré
si Node ou Playwright ne sont pas disponibles.
"""

import json
import math
import random
import shutil
import subprocess

import pytest

from proba_loto.analyse import motifs_populaires, profil_equilibre
from proba_loto.esperance import calculer_esperance, jackpot_rentable
from proba_loto.grilles import Grille, configurations_multiples, repartition_gains
from proba_loto.interface import ecrire_interface
from proba_loto.jeux import ETOILE_PLUS as EP, EUROMILLIONS as EM
from proba_loto.multiples import analyser_multiple
from proba_loto.probabilites import gain_moyen_theorique, probabilite_gain, probabilite_rang
from proba_loto.statistiques import khi2_uniformite, p_valeur_khi2, retro_tester, statistiques_numeros

NODE = shutil.which("node")


def _playwright_disponible() -> bool:
    if not NODE:
        return False
    try:
        return subprocess.run([NODE, "-e", "require('playwright')"], capture_output=True, timeout=60).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


pytestmark = pytest.mark.skipif(not _playwright_disponible(), reason="Node et Playwright requis")

SCRIPT = r"""
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [page_html, fichier_cas, sortie] = process.argv.slice(2);
  const navigateur = await chromium.launch();
  const page = await navigateur.newPage();
  const erreurs = [];
  page.on('pageerror', e => erreurs.push(String(e)));
  await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  await page.goto('file://' + page_html);
  await page.waitForFunction(() => window.CalculateurEuroMillions && window.CalculateurEuroMillions.historique().length > 0);
  const cas = JSON.parse(fs.readFileSync(fichier_cas, 'utf8'));
  const res = await page.evaluate(cas => {
    const A = window.CalculateurEuroMillions, H = A.historique(), o = {};
    o.probas = A.TABLE.rangs.map(r => A.probaRang(r)).concat(A.EP.rangs.map(r => A.probaRang(r)));
    o.probaGain = [A.probaGain(A.TABLE), A.probaGain(A.EP)];
    o.gains = A.TABLE.rangs.map(r => A.gainMoyen(r, A.TABLE)).concat(A.EP.rangs.map(r => A.gainMoyen(r, A.EP)));
    o.multiples = [];
    for (let n = 5; n <= 10; n++) for (let e = 2; e <= 12; e++) if (A.erreurMultiple(n, e) === null) o.multiples.push([n, e, A.analyseMultiple(n, e).pGain]);
    o.repartitions = cas.repartitions.map(([n, e, a, b, ep]) => Object.fromEntries(A.repartition(n, e, a, b, ep ? A.EP : A.TABLE)));
    o.grilles = cas.grilles.map(([n, e]) => [A.indice(n, e), A.profilEquilibre(n), A.motifs(n, H[H.length - 1]).length]);
    o.esperances = cas.esperances.map(x => { try { const e = A.esperance(x); return [e.total, e.jack, e.partage]; } catch (err) { return null; } });
    o.seuils = [A.jackpotRentable({}), A.jackpotRentable({ indicePop: 0.47 })];
    o.pvaleurs = cas.pvaleurs.map(([x, d]) => A.pValeurKhi2(x, d));
    const sn = A.statsValeurs(H, false), se = A.statsValeurs(H, true);
    o.khi2 = [A.khi2(Object.fromEntries(sn.map(s => [s.valeur, s.sorties])), 50, 5, H.length).p,
              A.khi2(Object.fromEntries(se.map(s => [s.valeur, s.sorties])), 12, 2, H.length).p];
    o.retros = cas.retros.map(([n, e, ep]) => { const r = A.retro(n, e, H, ep); return [r.mise, r.total, r.inconnus.length]; });
    o.lectures = cas.lectures.map(t => { try { return A.lireCombinaison(t); } catch (err) { return null; } });
    o.generees = ['aleatoire', 'anti-partage', 'equilibree', 'couverture'].map(s => A.generer(s, 10, [], [], H[H.length - 1]));
    return o;
  }, cas);
  res.erreurs = erreurs;
  fs.writeFileSync(sortie, JSON.stringify(res));
  await navigateur.close();
})();
"""


def _proche(a, b, rel=1e-9):
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-13)


def test_calculs_javascript_identiques_au_python(tmp_path, historique, modele):
    rng = random.Random(11)
    configurations = list(configurations_multiples(EM))
    repartitions = []
    for _ in range(120):
        n, e = rng.choice(configurations)
        repartitions.append([n, e, rng.randint(0, 5), rng.randint(0, 2), rng.random() < 0.5])
    grilles = [[sorted(rng.sample(range(1, 51), 5)), sorted(rng.sample(range(1, 13), 2))] for _ in range(120)]
    esperances = [
        {"jackpot": j, "situation": s, "etoilePlus": ep, "indicePop": ind}
        for j in (17e6, 120e6, 250e6)
        for s in ("normal", "plafond", "doit-etre-gagne")
        for ep in (False, True)
        for ind in (1.0, 0.5)
    ]
    pvaleurs = [[x, d] for x in (0.5, 7.0, 53.9, 150.0) for d in (1, 11, 49)]
    retros = [[[3, 5, 37, 44, 49], [5, 6], True], [[7, 13, 17, 19, 23], [3, 7], False], [[1, 2, 3, 4, 5, 6], [1, 2, 3], True]]
    lectures = ["3 5 37 44 49 + 5 6", "3-5-37-44-49 / 5-6", "3 5 37 44 49 5 6", "1 2 3 4 4 + 1 2"]
    cas = dict(repartitions=repartitions, grilles=grilles, esperances=esperances, pvaleurs=pvaleurs, retros=retros, lectures=lectures)

    page = ecrire_interface(tmp_path / "interface.html", historique)
    (tmp_path / "cas.json").write_text(json.dumps(cas), encoding="utf-8")
    (tmp_path / "eval.js").write_text(SCRIPT, encoding="utf-8")
    subprocess.run([NODE, "eval.js", str(page), "cas.json", "res.json"], cwd=tmp_path, check=True, timeout=180)
    r = json.loads((tmp_path / "res.json").read_text(encoding="utf-8"))

    assert r["erreurs"] == []
    rangs = list(EM.gains.rangs) + list(EP.rangs)
    tables = [EM.gains] * 13 + [EP] * 10
    assert all(_proche(float(probabilite_rang(EM, rg)), v) for rg, v in zip(rangs, r["probas"]))
    assert _proche(float(probabilite_gain(EM)), r["probaGain"][0])
    assert _proche(float(probabilite_gain(EM, EP)), r["probaGain"][1])
    assert all(_proche(gain_moyen_theorique(EM, rg, t), v) for rg, t, v in zip(rangs, tables, r["gains"]))
    assert [(n, e) for n, e, _ in r["multiples"]] == configurations
    assert all(_proche(float(analyser_multiple(EM, n, e).probabilite_gain), p) for n, e, p in r["multiples"])
    for (n, e, a, b, ep), js in zip(repartitions, r["repartitions"]):
        assert js == {str(k): v for k, v in repartition_gains(EM, n, e, a, b, EP if ep else EM.gains).items()}
    dernier = historique[-1].combinaison
    for (n, e), (indice, profil, nb_motifs) in zip(grilles, r["grilles"]):
        g = Grille.simple(EM, n, e)
        assert _proche(modele.indice(g), indice)
        assert profil == profil_equilibre(g)
        assert nb_motifs == len(motifs_populaires(g, dernier))
    for x, js in zip(esperances, r["esperances"]):
        try:
            e = calculer_esperance(x["jackpot"], None, None, x["situation"], x["etoilePlus"], x["indicePop"])
        except ValueError:
            assert js is None
            continue
        assert all(_proche(a, b) for a, b in zip([e.total, e.jackpot_moyen, e.proba_partage], js))
    assert _proche(jackpot_rentable(), r["seuils"][0], rel=1e-6)
    assert _proche(jackpot_rentable(indice_popularite=0.47), r["seuils"][1], rel=1e-6)
    assert all(_proche(p_valeur_khi2(x, d), v, rel=1e-8) for (x, d), v in zip(pvaleurs, r["pvaleurs"]))
    sn, se = statistiques_numeros(historique), statistiques_numeros(historique, etoiles=True)
    n = len(historique)
    assert _proche(khi2_uniformite({s.numero: s.sorties for s in sn}, 50, 5, n).p_valeur, r["khi2"][0], rel=1e-8)
    assert _proche(khi2_uniformite({s.numero: s.sorties for s in se}, 12, 2, n).p_valeur, r["khi2"][1], rel=1e-8)
    for (nums, ets, ep), (mise, total, inconnus) in zip(retros, r["retros"]):
        res = retro_tester(Grille(EM, tuple(nums), tuple(ets)), historique, ep)
        assert _proche(res.mise_totale, mise) and _proche(res.total_gains, total)
        assert inconnus == len(res.gains_inconnus)
    assert r["lectures"][:3] == [{"numeros": [3, 5, 37, 44, 49], "etoiles": [5, 6]}] * 3
    assert r["lectures"][3] is None
    for lot in r["generees"]:
        assert len({tuple(g["numeros"] + g["etoiles"]) for g in lot}) == 10
        for g in lot:
            Grille.simple(EM, g["numeros"], g["etoiles"])
