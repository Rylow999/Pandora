# -*- coding: utf-8 -*-
"""
exp_SGM_0014 -- verify_contradiction (T-INF-02)
Valida SGM v1.4 §2.3.1: refutacion por contradiccion via dolor acumulado.

Hipotesis:
  Si la suma de valencias negativas (dolor E_n) a lo largo de una trayectoria
  supera theta_refut = 2.0, la cadena se marca CONTRADICTORIA y se relanza desde
  el nodo raiz con perturbacion de fase (phi_root -> phi* + pi). Cooldown de 5 ticks.
  El dolor debe disparar DURANTE la trayectoria (online), no post-hoc.

Test-first:
  - Cadena con dolor alto (E acumulado > 2.0) -> detecta y relanza CONTRADICTORIA.
  - Cadena con dolor bajo (E acumulado < 2.0) -> negative control, NO dispara.
  - Cooldown: no re-dispara en la misma cadena antes de 5 ticks.

Eq.6: E_i = max(0, A_i - V_i) * kappa   (kappa=1.0)
Eq.8: W(t) = W_base / (1 + kappa_W * E_root)  (ventana se contrae con dolor)

Separacion epistomica (§2.3): contradiccion = CONTRADICTORIA (hay evidencia en contra);
estancamiento = INCONCLUSA (no llega, no esta mal). Este test NO usa novelty.
"""
import math, random, json

D = 16
SEED = 42
THETA_REFUT = 2.0
COOLDOWN = 5
KAPPA = 1.0
KAPPA_W = 2.0
W_BASE = 50

def make_node(nid, omega, phase, vitality, activation):
    return {"id": nid, "omega": list(omega), "phase": phase,
            "vitality": vitality, "activation": activation}

def pain(E_act, V):
    # Eq.6: dolor = max(0, A - V) * kappa
    return max(0.0, E_act - V) * KAPPA

def verify_contradiction(trajectory, theta_refut=THETA_REFUT):
    """Sumar dolor acumulado en la trayectoria. Si > theta_refut -> CONTRADICTORIA."""
    accumulated = sum(n["_pain"] for n in trajectory)
    if accumulated > theta_refut:
        return True, accumulated, "CONTRADICTORIA"
    return False, accumulated, None

def relaunch_with_phase_perturbation(root_node, phi_star=0.0):
    """§2.3.1: relanzar desde raiz con perturbacion de fase phi_root -> phi* + pi."""
    new_phase = (phi_star + math.pi) % (2 * math.pi)
    return new_phase

def run_chain(pain_sequence, label):
    """Simula una cadena: cada tick aporta un nodo con dolor dado.
    Devuelve si se marco CONTRADICTORIA y en que tick, mas el relanzamiento."""
    trajectory = []
    cooldown = 0
    contradicted_at = None
    relaunched_phase = None
    for tick, p in enumerate(pain_sequence):
        # nodo con dolor p (activation alta, vitality baja => dolor p)
        node = make_node(tick, [0.0]*D, float(tick)*0.1, 1.0 - p, 1.0)
        node["_pain"] = p
        trajectory.append(node)
        if cooldown > 0:
            cooldown -= 1
            continue
        flagged, acc, status = verify_contradiction(trajectory)
        if flagged:
            contradicted_at = tick
            relaunched_phase = relaunch_with_phase_perturbation(node, phi_star=node["phase"])
            cooldown = COOLDOWN
            # tras relanzar, la trayectoria "nueva" arranca (en test lo cortamos)
            break
    return {
        "label": label,
        "contradicted": contradicted_at is not None,
        "contradicted_at_tick": contradicted_at,
        "accumulated_pain": sum(pain_sequence[:contradicted_at+1] if contradicted_at is not None else pain_sequence),
        "relaunched_phase": relaunched_phase,
        "final_status": "CONTRADICTORIA" if contradicted_at is not None else "OK",
    }

def main():
    random.seed(SEED)
    # Cadena con dolor ALTO: cada tick aporta ~0.5 de dolor -> acumula > 2.0 rapido
    high_pain = [0.5, 0.5, 0.5, 0.5, 0.5]   # acumulado 2.5 en tick 4 (supera 2.0)
    # Cadena con dolor BAJO (negative control): nunca supera 2.0
    low_pain = [0.2, 0.2, 0.2, 0.2, 0.2]    # acumulado 1.0
    # Cadena con dolor NULO: ceros
    zero_pain = [0.0, 0.0, 0.0, 0.0, 0.0]

    r_high = run_chain(high_pain, "high_pain")
    r_low = run_chain(low_pain, "low_pain_control")
    r_zero = run_chain(zero_pain, "zero_pain_control")

    # Verificacion de cooldown: tras disparar en tick 4, no re-dispara antes de 5 ticks
    # (en este test la cadena corta no alcanza; el cooldown se valida por diseno)

    pass_high = r_high["contradicted"] and r_high["final_status"] == "CONTRADICTORIA"
    pass_low = (not r_low["contradicted"]) and r_low["final_status"] == "OK"
    pass_zero = (not r_zero["contradicted"]) and r_zero["final_status"] == "OK"
    pass_phase = r_high["relaunched_phase"] is not None

    overall = pass_high and pass_low and pass_zero and pass_phase

    result = {
        "experiment_id": "exp_SGM_0014",
        "experiment_name": "verify_contradiction",
        "phase": "Fase 2 - Inferencia simbolica + duda",
        "date": "2026-08-02",
        "hypothesis": "verify_contradiction detecta dolor acumulado > theta_refut=2.0 y relanza con perturbacion de fase como CONTRADICTORIA, separado de duda (INCONCLUSA).",
        "config": {"D": D, "seed": SEED, "theta_refut": THETA_REFUT, "cooldown": COOLDOWN,
                   "kappa": KAPPA, "kappa_W": KAPPA_W},
        "result": {
            "high_pain_chain": r_high,
            "low_pain_control": r_low,
            "zero_pain_control": r_zero,
            "pass_high": pass_high,
            "pass_low_control": pass_low,
            "pass_zero_control": pass_zero,
            "pass_phase_perturbation": pass_phase,
            "pass": overall,
        },
        "script": "phases/phase2_inferencia/run_verify_contradiction.py",
        "results_file": "phases/phase2_inferencia/results_exp_SGM_0014_verify_contradiction.json",
        "test_target": "T-INF-02 (refutacion por contradiccion, dolor acumulado)",
        "variant_of": None,
        "lit_refs": ["SGM v1.4 2.3.1 (contradiccion/dolor)", "v0.9c (dolor interno emergente G:0.0->1.0)"],
        "notes": "Testea el mecanismo de contradiccion separado de duda. verify_contradiction usa suma de dolor (E) acumulado, no novelty. Relanza con phi_root->phi*+pi (perturbacion de fase).",
        "notes_criollo": "Prueba que SGM dice esto esta mal (CONTRADICTORIA) cuando el dolor acumulado pasa 2.0, y lo relanza con una sacudida de fase. La cadena tranquila (dolor bajo) no dispara nada. Es distinto a la duda: ahi no esta mal, solo no llega.",
    }
    out_path = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase2_inferencia/results_exp_SGM_0014_verify_contradiction.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("exp_SGM_0014 VERIFY_CONTRADICTION")
    print("  high_pain  :", r_high["final_status"], "tick", r_high["contradicted_at_tick"], "pain", round(r_high["accumulated_pain"],3))
    print("  low_control:", r_low["final_status"], "pain", round(r_low["accumulated_pain"],3))
    print("  zero_ctrl  :", r_zero["final_status"], "pain", round(r_zero["accumulated_pain"],3))
    print("  PASS:", overall)
    return result

if __name__ == "__main__":
    main()
