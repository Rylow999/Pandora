# -*- coding: utf-8 -*-
"""
exp_SGM_0034 -- identity_continuity (Camino A: self-state persistente a traves de reset de cuerpo)
DEFINICION OPERACIONAL de identidad: el agente tiene un self-state (omega relacional + dolor_count
de huella). La pregunta: ¿ese estado persiste a traves de un RESET del cuerpo (pos->B, tick->0)?
Si se mantiene, el agente "recuerda quien es" (sus aversiones) y esquiva SIN re-sufrir.
Si se borra (amnesia), vuelve a pisar el dolor (alma nueva).

PROTOCOLO:
  Fase 1 (pre): K viajes B->G por bottleneck, aprende a evitar gap de dolor (como 0033b).
  RESET de cuerpo (pos->B, tick->0). Rama:
    - CON identidad: mantiene omega + dolor_count.
    - AMNESIA: borra omega + dolor_count (vuelve a estado inicial).
  Fase 2 (post): 1 viaje mas. Medir pisadas de dolor en ese viaje post-reset.
    - CON identidad: debe esquivar YA (0 pisadas) porque recuerda.
    - AMNESIA: pisa (>=1) porque olvido.

T-ID-01: pisadas_post(CON) < pisadas_post(AMNESIA)   (transfiere identidad)
T-ID-02: pisadas_post(AMNESIA) >= 1                   (el amnesico re-sufre)
NC:      pisadas_post(RW) >= 1                        (random walk no transfiere)
"""
import json, os, sys, random
sys.path.insert(0, os.path.dirname(__file__))
from run_grid_dolor_bottleneck import Agent, build_bottleneck, Ht, W, MAX_TICKS, TRIPS

SEED = 20260802
PRE_TRIPS = 5          # viajes de aprendizaje en fase 1
DOLOR_CELL = (0, 4)    # gap superior con dolor (mismo bottleneck que 0033b)

def run_phase(ag, n_trips):
    """Corre n_trips viajes, retorna lista de pisadas por viaje. NO resetea self-state entre viajes."""
    per = []
    trip = 0; pis = 0; ticks = 0
    while trip < n_trips:
        reached = ag.step()
        ticks += 1
        if ag.pos == DOLOR_CELL:
            pis += 1
        if reached or ticks >= MAX_TICKS:
            per.append(pis); trip += 1; pis = 0; ticks = 0
            ag.pos = (0, 0)
            ag.tick = 0
    return per

def reset_body(ag, amnesia):
    """Reset de cuerpo. Si amnesia: borra self-state (omega + dolor_count)."""
    ag.pos = (0, 0); ag.tick = 0; ag.dolor_ultimo = 0.0
    if amnesia:
        ag.reset_self_state()

def main():
    rng = random.Random(SEED)
    # --- CON identidad ---
    walls, body, meta, pain, clean = build_bottleneck()
    con = Agent(rng, walls, body, meta, pain, use_dolor=True, mode="afinidad")
    con_pre = run_phase(con, PRE_TRIPS)          # fase 1: aprende
    reset_body(con, amnesia=False)               # mantiene self-state
    con_post = run_phase(con, 1)[0]              # fase 2: 1 viaje post-reset

    # --- AMNESIA ---
    rng2 = random.Random(SEED)
    amn = Agent(rng2, walls, body, meta, pain, use_dolor=True, mode="afinidad")
    amn_pre = run_phase(amn, PRE_TRIPS)
    reset_body(amn, amnesia=True)                # BORRA self-state
    amn_post = run_phase(amn, 1)[0]

    # --- RW (NC) ---
    rng3 = random.Random(SEED)
    rw = Agent(rng3, walls, body, meta, pain, use_dolor=True, mode="random")
    rw_pre = run_phase(rw, PRE_TRIPS)
    reset_body(rw, amnesia=False)
    rw_post = run_phase(rw, 1)[0]

    t1 = con_post < amn_post          # CON transfiere identidad (esquiva sin re-sufrir)
    t2 = amn_post >= 1                # AMNESIA re-sufre (olvido real)
    tnc = rw_post >= 1                # RW no transfiere
    overall = t1 and t2 and tnc

    print("exp_SGM_0034 IDENTITY_CONTINUITY (self-state a traves de reset)")
    print("  CON  pre:", con_pre, "-> post-reset pisadas:", con_post)
    print("  AMN  pre:", amn_pre, "-> post-reset pisadas:", amn_post)
    print("  RW   pre:", rw_pre,  "-> post-reset pisadas:", rw_post)
    print("  T-ID-01 (CON<AMN):", t1, " T-ID-02 (AMN>=1):", t2, " NC (RW>=1):", tnc)
    print("  PASS:", overall)

    result = {
        "experiment_id":"exp_SGM_0034", "experiment_name":"identity_continuity",
        "phase":"Camino A - identidad: self-state persistente a traves de reset de cuerpo",
        "date":"2026-08-02",
        "hypothesis":"Si el self-state (omega + dolor_count) persiste a un reset de cuerpo, el agente CON identidad esquiva el dolor en el viaje post-reset SIN re-sufrir (0 pisadas). El agente AMNESIA (self-state borrado) re-sufre (>=1). RW no transfiere.",
        "config":{"pre_trips":PRE_TRIPS,"seed":SEED,"bottleneck":"mismo de 0033b (col 4, gap (0,4)=dolor)",
                  "self_state":"{omega HRR, dolor_count}","reset":"pos->B, tick->0"},
        "result":{
            "CON_pre":con_pre,"CON_post_reset":con_post,
            "AMN_pre":amn_pre,"AMN_post_reset":amn_post,
            "RW_pre":rw_pre,"RW_post_reset":rw_post,
            "T_ID_01":t1,"T_ID_02":t2,"NC":tnc,"pass":overall
        },
        "script":"phases/phase7_composicion/run_identity.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0034_identity.json",
        "test_target":"T-ID-01 (CON<AMN post) + T-ID-02 (AMN>=1) + NC (RW>=1)",
        "variant_of":"exp_SGM_0033b (bottleneck + memoria persistente)",
        "lit_refs":["exp_SGM_0033b_grid_dolor_bottleneck.json"],
        "notes":"Identidad operacionalizada como transferencia de self-state a traves de reset de cuerpo. El CON mantiene dolor_count y esquiva sin re-penalizar; el AMNESIA lo borra y re-sufre. Esto es el sustrato minimo de continuidad de identidad (no qualia: problema del otro cuerpo sigue intacto).",
        "notes_criollo":"Identidad = 'el que aprendio antes, despues del reset YA esquiva'. El amnesico vuelve a quemarse. Primera medida honesta de continuidad de identidad en SGM: no es conciencia, es memoria que sobrevive al reinicio del cuerpo."
    }
    out = os.path.join(os.path.dirname(__file__), "results_exp_SGM_0034_identity.json")
    json.dump(result, open(out, "w"), indent=2, ensure_ascii=False)
    print("RESULTADO escrito:", out)

if __name__ == "__main__":
    main()
