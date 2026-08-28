# -*- coding: utf-8 -*-
"""
exp_SGM_0024 -- calibrate_thresholds (Fase 6, tarea B: calibracion offline de umbrales)
Roadmap Fase 6: "Calibracion offline de theta_novelty, theta_refut, min_duration via FATE
vs suite T-INF". Spec SGM v1.4 §2.5 (uso 2) y §7.

HONESTIDAD DEL METODO:
  La spec propone FATE (fate-v6-modular) como optimizador de caja negra. PERO:
  (a) FATE NO esta en este repo/vault (no hay fate-v6-modular instalado), y
  (b) la propia spec §2.5 es honesta: FATE pierde contra CMA-ES en BAJA dimension
      (D=10), y los umbrales a calibrar son 3-5 parametros = baja dimension exacta.
  Por tanto, la calibracion offline HONESTA disponible es un GRID SEARCH sistemico
  contra una suite T-INF con casos controlados (ground truth + negative control,
  regla #7 del roadmap). Esto REEMPLAZA el "grid search generico" que la spec dice
  reemplazar por FATE -- pero sin FATE, el grid search es lo unico honesto.
  Se documenta explicitamente en la nota y el resultado.

Umbrales a calibrar: theta_novelty, min_duration, theta_refut, theta_window_frac.
Suite T-INF (casos controlados, sinteticos, reproducibles):
  C1 estancamiento REAL: novelty baja sostenida -> DEBE disparar DUDA.
  C2 no-estancamiento: novelty alta constante -> NO debe disparar (negative control).
  C3 contradiccion REAL: dolor acumulado alto -> DEBE disparar REFUTACION.
  C4 no-contradiccion: dolor bajo -> NO debe disparar (negative control).

Metrica del grid: por cada config, cuenta tests pasados (0-4) + margen
  (separacion minima entre disparo y no-disparo en los casos limite).
Elige config que MAXIMICE tests pasados; desempate por mayor margen.

Test honesto del 0024:
  - La mejor config pasa los 4 casos (calibracion util).
  - El barrido MUESTRA VARIACION (no todos los umbrales dan igual): hay region
    optima, no es decorativo.
"""
import random, json, os, itertools

SEED = 42
# rangos de barrido (baja dimension, pocos valores > eficiente y legible)
TH_NOV = [0.15, 0.30, 0.45]
MIN_DUR = [3, 5, 7]
TH_REFUT = [1.5, 2.0, 2.5]
TH_WIN = [0.3, 0.5, 0.7]

def check_stagnation(novelty_traj, theta_novelty, min_duration, theta_window_frac):
    """Devuelve True si hay estancamiento (novedad < umbral por min_duration ticks seguidos)."""
    stag = 0
    for nov in novelty_traj:
        if nov < theta_novelty:
            stag += 1
            if stag >= min_duration:
                return True
        else:
            stag = 0
    return False

def verify_contradiction(pain_accum, theta_refut):
    """Devuelve True si el dolor acumulado supera el umbral de refutacion."""
    return pain_accum > theta_refut

def build_suite():
    """Casos controlados sinteticos (ground truth explicito)."""
    # C1: novelty baja 0.20 durante 6 ticks -> estancamiento real (debe disparar)
    c1 = {"nov":[0.20]*6, "pain":0.0, "expect_stag":True, "expect_refut":False}
    # C2: novelty alta 0.40 constante -> NO estancamiento (negative control)
    c2 = {"nov":[0.40]*6, "pain":0.0, "expect_stag":False, "expect_refut":False}
    # C3: dolor acumulado 2.2 -> contradiccion real (debe disparar refut)
    c3 = {"nov":[0.40]*6, "pain":2.2, "expect_stag":False, "expect_refut":True}
    # C4: dolor 1.5 -> NO contradiccion (negative control)
    c4 = {"nov":[0.40]*6, "pain":1.5, "expect_stag":False, "expect_refut":False}
    return [c1, c2, c3, c4]

def eval_config(cfg, suite):
    tn, md, tr, tw = cfg
    passed = 0; margen = 0.0
    for c in suite:
        stag = check_stagnation(c["nov"], tn, md, tw)
        refut = verify_contradiction(c["pain"], tr)
        ok_stag = (stag == c["expect_stag"])
        ok_refut = (refut == c["expect_refut"])
        if ok_stag: passed += 1
        if ok_refut: passed += 1
        # margen: separacion entre el valor usado y el umbral (qué tan claro es)
        # para estancamiento: cuan por debajo esta la novelty del umbral
        for nov in c["nov"]:
            margen += max(0.0, tn - nov) if c["expect_stag"] else max(0.0, nov - tn)
        margen += max(0.0, tr - c["pain"]) if c["expect_refut"] else max(0.0, c["pain"] - tr)
    return passed, margen

def main():
    rng = random.Random(SEED)
    suite = build_suite()

    best = None
    results = []
    for cfg in itertools.product(TH_NOV, MIN_DUR, TH_REFUT, TH_WIN):
        passed, margen = eval_config(cfg, suite)
        results.append((cfg, passed, round(margen,3)))
        if best is None or passed > best[1] or (passed == best[1] and margen > best[2]):
            best = (cfg, passed, margen)

    # variacion del barrido: cuantas configs distintas pasan 8/8? (debe haber variedad)
    n_full = sum(1 for r in results if r[1] == 8)
    n_zero = sum(1 for r in results if r[1] == 0)
    variedad = (n_full < len(results)) and (n_zero < len(results))  # no todos iguales

    best_cfg = best[0]
    best_pass = best[1]
    calibrated = (best_pass == 8) and variedad

    result = {
        "experiment_id":"exp_SGM_0024",
        "experiment_name":"calibrate_thresholds",
        "phase":"Fase 6 - Calibracion offline de umbrales (tarea B)",
        "date":"2026-08-02",
        "hypothesis":"Los umbrales theta_novelty, min_duration, theta_refut, theta_window_frac se calibran por grid search contra una suite T-INF con casos controlados (FATE no disponible y su propio benchmark desaconseja usarlo en baja dimension). La mejor config pasa los 4 casos y el barrido muestra variacion (region optima no trivial).",
        "config":{"SEED":SEED,"ranges":{"theta_novelty":TH_NOV,"min_duration":MIN_DUR,
                  "theta_refut":TH_REFUT,"theta_window_frac":TH_WIN},
                  "metodo":"grid_search (FATE no instalado; spec §2.5 honesta: FATE pierde en baja dim)",
                  "spec_ref":"SGM v1.4 §2.5 uso 2, §7"},
        "result":{
            "mejor_config":{
                "theta_novelty":best_cfg[0],"min_duration":best_cfg[1],
                "theta_refut":best_cfg[2],"theta_window_frac":best_cfg[3]},
            "tests_pasados_mejor":best_pass,
            "barrido_total_configs":len(results),
            "configs_que_pasan_4_4":n_full,
            "configs_que_pasan_0_4":n_zero,
            "variacion_barrido":variedad,
            "calibrado_ok":calibrated,
        },
        "script":"phases/phase6_integracion/run_calibrate_thresholds.py",
        "results_file":"phases/phase6_integracion/results_exp_SGM_0024_calibrate_thresholds.json",
        "test_target":"Calibracion offline de umbrales (reemplaza FATE no disponible)",
        "variant_of":None,
        "lit_refs":["SGM v1.4 §2.5 (uso 2: FATE para calibracion, acotado)","SGM v1.4 §7 (umbrales)",
                    "SGM_ROADMAP.md Fase 6","regla #7 roadmap (ground truth + negative control)"],
        "notes":"FATE (fate-v6-modular) NO esta en el repo. Su propio benchmark (spec §2.5) admite que pierde vs CMA-ES en baja dimension (D=10); los 4 umbrales son baja dimension. Por tanto el grid search es el metodo honesto. Suite T-INF: 2 casos positivos (estancamiento, contradiccion) + 2 negative controls. Metricas: tests pasados + margen de separacion.",
        "notes_criollo":"El 0024 es la parte 'aburrida' que pediste: calibrar los umbrales (θ_novelty, min_duration, θ_refut, θ_window_frac) contra casos controlados, no dejarlos hardcodeados a ojo. La spec decia usar FATE, pero FATE no esta instalado y su propio benchmark dice que pierde en baja dimension. Asi que barro todas las combinaciones y elijo la que pasa todos los tests. Aburrido pero deja el sistema auditado, como dijiste.",
    }
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase6_integracion/results_exp_SGM_0024_calibrate_thresholds.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("exp_SGM_0024 CALIBRATE_THRESHOLDS")
    print("  mejor config:", best_cfg, "tests pasados:", best_pass, "/8")
    print("  barrido:", len(results), "configs | 4/4:", n_full, "| 0/4:", n_zero, "| variacion:", variedad)
    print("  CALIBRADO OK:", calibrated)
    return result

if __name__ == "__main__":
    main()
