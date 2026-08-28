#!/usr/bin/env python3
# exp_SGM_0013 - Mecanismo de DUDA / estancamiento (SGM v1.4 2.3.2, T-INF-04)
import json, time

EXPERIMENT_ID = "exp_SGM_0013_doubt_stagnation"
EXPERIMENT_NAME = "doubt_stagnation_mechanism"
PHASE = "Fase 2 - Inferencia simbolica + duda"
DATE = "2026-08-02"
W_BASE = 50
THETA_NOVELTY = 0.30
THETA_WINDOW_FRAC = 0.5
MIN_DURATION = 5
CONTRACTED_WINDOW = 20

class Chain:
    def __init__(self, W_base=W_BASE, contracted_window=CONTRACTED_WINDOW):
        self.mode = "RAZONAMIENTO"
        self.params = {"W_base": W_base, "lambda_eff": 5.0, "alpha_eff": 5.0}
        self.current_window_size = contracted_window
        self.visited_nodes = []
        self.stagnation_ticks = 0
        self.doubt_count = 0
        self.doubt_cooldown = 0
        self.status = "ACTIVA"

def check_stagnation(chain, theta_novelty=THETA_NOVELTY, theta_window_frac=THETA_WINDOW_FRAC, min_duration=MIN_DURATION):
    W_t = chain.current_window_size
    W_base = chain.params["W_base"]
    if W_t > theta_window_frac * W_base:
        chain.stagnation_ticks = 0
        return False
    recent = chain.visited_nodes[-int(W_t):] if W_t >= 1 else []
    if len(recent) == 0:
        return False
    novelty = len(set(recent)) / len(recent)
    if novelty < theta_novelty:
        chain.stagnation_ticks += 1
    else:
        chain.stagnation_ticks = 0
    return chain.stagnation_ticks >= min_duration

def handle_doubt(chain, alt_seed_candidates):
    chain.doubt_count += 1
    if chain.doubt_count == 1:
        chain.params["lambda_eff"] *= 0.6
        chain.params["alpha_eff"] *= 0.8
        chain.stagnation_ticks = 0
        return "relax"
    elif chain.doubt_count == 2:
        alt_seed = next((n for n in alt_seed_candidates if n not in chain.visited_nodes), None)
        if alt_seed is not None:
            chain.visited_nodes.clear()
            chain.stagnation_ticks = 0
            return ("relaunch", alt_seed)
        else:
            chain.doubt_count = 3
            return "no_alt"
    else:
        chain.mode = "DEFAULT"
        chain.status = "INCONCLUSA"
        return "abandon"

def simulate_chain(visit_sequence):
    chain = Chain()
    novelty_trace = []
    detected_at = None
    for tick, node_id in enumerate(visit_sequence):
        chain.visited_nodes.append(node_id)
        if len(chain.visited_nodes) >= CONTRACTED_WINDOW:
            is_stuck = check_stagnation(chain)
            W_t = chain.current_window_size
            recent = chain.visited_nodes[-int(W_t):]
            nov = len(set(recent)) / len(recent) if recent else 1.0
            novelty_trace.append(round(nov, 3))
            if is_stuck and detected_at is None:
                detected_at = tick + 1
                break
    return {"detected": detected_at is not None, "detected_at_tick": detected_at, "stagnation_ticks": chain.stagnation_ticks, "novelty_trace": novelty_trace}

def build_trap_sequence(trap_nodes, n_ticks):
    return [trap_nodes[i % len(trap_nodes)] for i in range(n_ticks)]

def build_exploring_sequence(trap_nodes, outside_nodes, n_ticks):
    all_nodes = trap_nodes + outside_nodes
    return [all_nodes[i % len(all_nodes)] for i in range(n_ticks)]

def test_escalation(trap_nodes, outside_nodes):
    chain = Chain()
    chain.visited_nodes = list(trap_nodes)
    steps = []
    r1 = handle_doubt(chain, outside_nodes)
    steps.append({"doubt_count": chain.doubt_count, "action": r1 if isinstance(r1, str) else r1[0], "lambda_eff": round(chain.params["lambda_eff"], 3), "alpha_eff": round(chain.params["alpha_eff"], 3)})
    r2 = handle_doubt(chain, outside_nodes)
    steps.append({"doubt_count": chain.doubt_count, "action": r2[0] if isinstance(r2, tuple) else r2, "alt_seed": r2[1] if isinstance(r2, tuple) else None})
    r3 = handle_doubt(chain, outside_nodes)
    steps.append({"doubt_count": chain.doubt_count, "action": r3, "final_mode": chain.mode, "final_status": chain.status})
    return steps, chain

def main():
    print("=" * 64)
    print("  %s: Mecanismo de Duda / Estancamiento" % EXPERIMENT_ID)
    print("=" * 64)
    trap_nodes = [0, 1, 2, 3, 4]
    outside_nodes = [5, 6, 7, 8, 9]
    trap_seq = build_trap_sequence(trap_nodes, n_ticks=30)
    trap_result = simulate_chain(trap_seq)
    explore_seq = build_exploring_sequence(trap_nodes, outside_nodes, n_ticks=30)
    explore_result = simulate_chain(explore_seq)
    escalation_steps, final_chain = test_escalation(trap_nodes, outside_nodes)
    novelty_trap = sum(trap_result["novelty_trace"]) / len(trap_result["novelty_trace"])
    novelty_explore = (sum(explore_result["novelty_trace"]) / len(explore_result["novelty_trace"]) if explore_result["novelty_trace"] else 1.0)
    print("--- Cadena ATREPADA en trampa (5 nodos, W_t=20) ---")
    print("  novelty promedio: %.3f" % novelty_trap)
    print("  Detectado?: %s" % trap_result["detected"])
    print("  Detectado en tick: %s" % trap_result["detected_at_tick"])
    print("--- NEGATIVE CONTROL ---")
    print("  novelty promedio: %.3f" % novelty_explore)
    print("  Detectado (debe ser False)?: %s" % explore_result["detected"])
    print("--- ESCALADA DE DUDA ---")
    for s in escalation_steps:
        line = "  doubt=%d: accion=%s" % (s["doubt_count"], s["action"])
        if "lambda_eff" in s:
            line += "  lambda*0.6=%s, alpha*0.8=%s" % (s["lambda_eff"], s["alpha_eff"])
        if "alt_seed" in s and s["alt_seed"] is not None:
            line += "  semilla_alt=%s" % s["alt_seed"]
        if "final_status" in s:
            line += "  -> modo=%s, status=%s" % (s["final_mode"], s["final_status"])
        print(s)
    pass_stagnation = (trap_result["detected"] and not explore_result["detected"] and novelty_trap < THETA_NOVELTY <= novelty_explore)
    pass_escalation = (escalation_steps[0]["action"] == "relax" and escalation_steps[1]["action"] == "relaunch" and escalation_steps[2]["action"] == "abandon" and final_chain.status == "INCONCLUSA" and final_chain.mode == "DEFAULT")
    global_pass = pass_stagnation and pass_escalation
    print("=" * 64)
    print("  VEREDICTO")
    print("=" * 64)
    print("  Stagnation detecta trampa (novelty=%.3f < %.2f): %s" % (novelty_trap, THETA_NOVELTY, trap_result["detected"]))
    print("  Negative control limpio (novelty=%.3f >= %.2f): %s" % (novelty_explore, THETA_NOVELTY, not explore_result["detected"]))
    print("  Escalada relax->relaunch->abandon: %s" % pass_escalation)
    print("  Estado final = INCONCLUSA: %s" % (final_chain.status == "INCONCLUSA"))
    print("  GLOBAL: %s" % ("PASS" if global_pass else "FAIL"))
    output = {"experiment_id": EXPERIMENT_ID, "experiment_name": EXPERIMENT_NAME, "phase": PHASE, "date": DATE, "hypothesis": "check_stagnation detecta cadenas atrapadas y handle_doubt escala relax->relaunch->abandon como INCONCLUSA.", "config": {"W_base": W_BASE, "theta_novelty": THETA_NOVELTY, "theta_window_frac": THETA_WINDOW_FRAC, "min_duration": MIN_DURATION, "contracted_window": CONTRACTED_WINDOW, "trap_nodes": trap_nodes, "outside_nodes": outside_nodes}, "result": {"trap_chain": {"detected": trap_result["detected"], "detected_at_tick": trap_result["detected_at_tick"], "novelty_avg": round(novelty_trap, 4), "stagnation_ticks": trap_result["stagnation_ticks"]}, "negative_control": {"detected": explore_result["detected"], "novelty_avg": round(novelty_explore, 4)}, "escalation": escalation_steps, "final_status": final_chain.status, "final_mode": final_chain.mode, "pass_stagnation": pass_stagnation, "pass_escalation": pass_escalation, "pass": global_pass}, "script": "phases/phase2_inferencia/run_doubt_stagnation.py", "results_file": "phases/phase2_inferencia/results_exp_SGM_0013_doubt_stagnation.json", "test_target": "T-INF-04 (deteccion de estancamiento + respuesta escalonada de duda)", "baseline_for": [], "variant_of": None, "lit_refs": ["SGM v1.4 2.3.2 (duda/estancamiento)", "Kirkpatrick et al. PNAS 2017 (EWC)"], "notes": "Testea el mecanismo de duda separado de contradiccion. check_stagnation usa metrica de conteo (novelty = nodos unicos / ventana).", "notes_criollo": "Prueba que SGM duda cuando se estanca. La cadena atrapada (novelty 0.25) dispara la duda tras 5 ticks. La que explora (novelty 0.50) no dispara nada. La duda escala: relaja, prueba otra semilla, y si nada funciona abandona como INCONCLUSA."}
    out_path = "/data/user/0/com.hermesagent.android/files/home/rizoma_docs/phases/phase2_inferencia/results_exp_SGM_0013_doubt_stagnation.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print("Resultados guardados en: %s" % out_path)

if __name__ == "__main__":
    main()
